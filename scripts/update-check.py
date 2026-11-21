#!/usr/bin/env python3
"""update-check.py OUT --font font.json tells an operator what the installed skill would change in a shipped face.

WHAT IT'S FOR: a face folder records the skill version that built it (`skill_version` in manifest.json) and carries no scripts.
When the installed skill has another version, the operator needs to see whether adopting it changes the font before running the
build themselves. This script rebuilds the face with the INSTALLED skill into a temporary folder, compares the shipped woff2
files with that rebuild (by value and by render, through diff.py) and writes a report. It never writes into the face folder: the
operator approves by running the build command the report prints.

Steps, in order:
  1. OUT must not be the face folder or inside it (exit 1): the report is never written next to the face. OUT must be new,
     empty, or the OUT of an earlier update check, which a run marks with a `.update-check` file (exit 1 naming the files
     otherwise), because a run replaces update.md, update.json and diff/ there, and a site root given as OUT would lose its
     own diff/.
  2. The recorded version is `skill_version` from the manifest, or `--recorded VERSION` for a face built before 0.8.0 (exit 1 when
     neither is given, or when both are given and differ). The installed version is the VERSION file above scripts/.
  3. Equal versions: print `up to date` and exit 0, writing nothing and building nothing.
  4. Different: the drift check, then a rebuild into a temporary folder with the face's own requirements setting, then diff.py on
     the shipped files against the rebuild and a sha256 comparison of each shipped woff2 with its rebuild (diff.py's by-value
     section does not compare every table, so bytes can differ when no listed value does), then the report.

The drift check hashes each shipped woff2 and font.json, concepts.js and the skeletons file, and compares them with the manifest.
A mismatch is labelled drift in the report and is not an error: those differences cannot be attributed to the skill update. The
manifest holds no hash of the requirements file, so that input is not checked. The exact guarantee of a clean drift check: the
shipped files hash to what manifest.json says. It does NOT prove the shipped font is the output of the recorded version (the
manifest is an editable file), so whenever a group differs the report says attribution to the update is unverified; only a rebuild
at the recorded version (fetch-version.py) would verify it.

Report: OUT/update.md, OUT/update.json and OUT/diff/ (diff.py's output). The report is staged in a folder inside OUT and moved in
with update.md LAST, so a report is complete if and only if update.md exists (the three moves are not one atomic operation). Any
exit 1 after the OUT checks, whether a failure this script names or an unexpected exception (a file it cannot read),
removes the update.md, update.json and diff/ of an earlier run, so it cannot be read as this run's
result. A recorded version that names more than one font source (0.6.0, see versions.py) adds a notice to stderr, update.md and
update.json; the check still runs, because it fetches nothing.

Exit codes: 0 up to date, or no difference in any group; 3 something differs (a group by value, a render, or drift); 1 an error.
What it proves: by-value and FreeType-render differences on this machine between the shipped files and an installed rebuild; not a
browser.
"""
import argparse
import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
UNVERIFIED = ("Attribution to the skill update is unverified: the drift check proves the shipped files match manifest.json, not that they "
              "are the output of the recorded version; only a rebuild at the recorded version (fetch-version.py) would.")

sys.path.insert(0, str(HERE))
import versions  # noqa: E402  (stdlib-only module beside this script)


class Fail(Exception):
    """An error that ends the run with exit 1."""


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def tail(text, n=8):
    return "\n".join(text.strip().splitlines()[-n:])


OWNED = ("update.md", "update.json", "diff")  # what a run writes into OUT, and all it may replace or remove there
MARKER = ".update-check"  # left in OUT by every run, so a later run knows the folder is an update check's OUT


def remove_stale(out):
    """Removes the update.md, update.json and diff/ of an earlier run in OUT, and says so when there was one."""
    found = [out / n for n in OWNED if (out / n).exists()]
    left = []
    for p in found:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        except OSError as exc:
            left.append(f"{p.name} ({exc})")
    if left:
        sys.stderr.write(f"update-check.py: could not remove the report of an earlier run in {out}: {', '.join(left)}; "
                         "it describes a different state, so delete it before reading OUT\n")
    elif found:
        sys.stderr.write(f"update-check.py: removed the report of an earlier run in {out}; it described a different state\n")


def drift_of(cfg, manifest):
    """[{file, recorded, found}] for each shipped file whose sha256 differs from what the manifest records."""
    import build
    drift = []

    def compare(path, recorded):
        found = sha(path)
        if recorded != found:
            drift.append({"file": str(path), "recorded": recorded, "found": found})

    for g in cfg["groups"]:
        path = build.group_file(cfg, g)
        if not path.is_file():
            raise Fail(f"the shipped file for group {g} is missing: {path}")
        compare(path, (manifest.get("groups", {}).get(g) or {}).get("woff2_sha256"))
    sources = manifest.get("sources_sha256", {})
    compare(cfg["_path"], sources.get("font.json"))
    compare(cfg["_concepts"], sources.get("concepts.js"))
    if cfg.get("_skeletons"):
        compare(cfg["_skeletons"], sources.get(cfg["skeletons"]))
    return drift


def rebuild_and_diff(cfg, manifest, font, face_dir, sizes, tmp):
    """Copies the shipped group files to tmp/before, builds the face with the installed skill into tmp/after and runs diff.py
    on the pair into tmp/report. Returns (diff.json dict, requirements flags for the adoption command)."""
    import build
    before, after, report = tmp / "before", tmp / "after", tmp / "report"
    before.mkdir()
    for g in cfg["groups"]:
        shipped = build.group_file(cfg, g)
        shutil.copyfile(shipped, before / shipped.name)
    recorded_req = manifest.get("requirements")
    if recorded_req is None:
        req_flags = ["--no-requirements"]
    else:
        req_flags = ["--requirements", str((face_dir / recorded_req).resolve())]
    b = subprocess.run([sys.executable, str(HERE / "build.py"), "--font", str(font), "--out-dir", str(after), *req_flags],
                       capture_output=True, text=True, encoding="utf-8")
    if b.returncode != 0:
        raise Fail(f"build.py failed (exit {b.returncode}) rebuilding the face with the installed skill:\n{tail(b.stderr)}")
    cmd = [sys.executable, str(HERE / "diff.py"), str(report), "--font", str(font), "--before", str(before), "--after", str(after)]
    if sizes:
        cmd += ["--sizes", *[f"{s:g}" for s in sizes]]
    d = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if d.returncode != 0:
        raise Fail(f"diff.py failed (exit {d.returncode}); no report was written:\n{tail(d.stderr)}")
    identical = {g: sha(before / build.group_file(cfg, g).name) == sha(after / build.group_file(cfg, g).name) for g in cfg["groups"]}
    return json.loads((report / "diff.json").read_text(encoding="utf-8")), req_flags, identical


def write_md(cfg, font, face_dir, recorded, installed, notices, drift, data, differing, adoption, identical, anything):
    lines = [f"# Update check: {cfg['family']}", "",
             f"recorded skill version: {recorded} (manifest.json)      installed: {installed}", ""]
    if notices:
        lines += ["## Notice", ""] + notices + [""]
    if drift:
        lines += ["## Drift", ""]
        for e in drift:
            lines.append(f"{pathlib.Path(e['file']).name}: sha256 {str(e['recorded'])[:12]}... recorded, {e['found'][:12]}... found. "
                         "These differences cannot be attributed to the skill update.")
        lines.append("")
    lines += ["## By value", ""]
    for g, v in data["values"].items():
        diffs = v["differences"]
        if not diffs:
            lines.append(f"{g}: no difference by value")
            continue
        lines.append(f"{g}: {len(diffs)} difference(s) by value")
        lines += [f"- {x}" for x in diffs[:200]]
        if len(diffs) > 200:
            lines.append(f"- and {len(diffs) - 200} more, all in diff/diff.json")
    if anything:
        lines += ["", UNVERIFIED]
    lines += ["", "## Renders", "", f"{data['changed']} of {data['renders']} renders changed (diff/diff.md)", "",
              "## Bytes", ""]
    lines += [f"{g}: {'identical to the rebuild' if same else 'the woff2 files differ in bytes from the rebuild'}" for g, same in identical.items()]
    if not differing and not data["changed"] and not all(identical.values()):
        lines.append("No compared value and no render differs, but the bytes do: the by-value section does not compare every table.")
    lines += ["",
              "## Nothing was changed", "",
              f"Nothing in {face_dir} was changed. " + ("There is no difference in any group; adopting " + installed + " changes only manifest.json. "
                                                        if not (differing or data["changed"] or drift or not all(identical.values())) else "")
              + f"To adopt {installed}, run, from any directory,", "",
              adoption, "",
              "and commit the woff2 files and manifest.json.", ""]
    return "\n".join(lines)


def run(args):
    out = pathlib.Path(args.out).resolve()
    font = pathlib.Path(args.font).resolve()
    face_dir = font.parent
    if out == face_dir or face_dir in out.parents:
        sys.stderr.write(f"update-check.py: OUT {args.out} is inside the face folder {face_dir}; the update check never writes there\n")
        return 1, None
    if out.exists():
        # OUT is partly replaced on every run, so it must be new, empty, or an earlier update check's OUT (it holds the marker a
        # run leaves): never a folder that holds other work, even one whose only entry is a diff/ (a site root given as OUT).
        others = ([] if (out / MARKER).is_file() else sorted(p.name for p in out.iterdir())) if out.is_dir() else [out.name]
        if others:
            sys.stderr.write(f"update-check.py: OUT {args.out} holds files this check did not write ({', '.join(others[:5])}"
                             f"{', ...' if len(others) > 5 else ''}); give a new or empty folder, or the OUT of an earlier update check\n")
            return 1, None
    try:
        return body(args, out, font, face_dir), out
    except Fail as exc:
        sys.stderr.write(f"update-check.py: {exc}\n")
        remove_stale(out)
        return 1, out
    except Exception as exc:  # a read, copy or move this script did not anticipate: still exit 1 and leave no earlier report
        sys.stderr.write(f"update-check.py: unexpected {type(exc).__name__}: {exc}\n")
        remove_stale(out)
        return 1, out


def body(args, out, font, face_dir):
    try:
        import build
    except ImportError as exc:
        raise Fail(f"cannot import build.py's packages ({exc}); run this with the skill's venv python, not {sys.executable}") from exc
    try:
        cfg = build.load_config(font)
        installed = build.read_skill_version()
    except build.CheckFailed as exc:
        raise Fail(str(exc)) from exc
    if not cfg["_manifest"].is_file():
        raise Fail(f"the face has no manifest at {cfg['_manifest']}; build it first")
    try:
        manifest = json.loads(cfg["_manifest"].read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Fail(f"cannot read the manifest {cfg['_manifest']}: {exc}") from exc
    in_manifest = manifest.get("skill_version")
    if args.recorded and in_manifest and args.recorded != in_manifest:
        raise Fail(f"--recorded {args.recorded} contradicts the manifest, which records {in_manifest}; give one or the other")
    recorded = args.recorded or in_manifest
    if not recorded:
        raise Fail("the manifest records no skill_version (a face built before 0.8.0 records none); pass --recorded VERSION, the version of the skill that built it")
    if recorded == installed:
        print(f"update-check.py: up to date: the face records {recorded} and the installed skill is {installed}; nothing to compare")
        return 0
    notice = versions.ambiguity_notice(recorded)
    notices = [notice] if notice else []
    for n in notices:
        sys.stderr.write(f"update-check.py: {n}\n")
    drift = drift_of(cfg, manifest)
    with tempfile.TemporaryDirectory() as tmp:
        data, req_flags, identical = rebuild_and_diff(cfg, manifest, font, face_dir, args.sizes, pathlib.Path(tmp))
        report = pathlib.Path(tmp) / "report"
        values = data["values"]
        differing = [g for g, v in values.items() if v["differences"]]
        # attribution is unverified whenever anything differs: listed values, renders or the bytes themselves
        anything = bool(differing or data["changed"] or not all(identical.values()))
        adoption = shlex.join([sys.executable, str(SKILL / "scripts" / "build.py"), "--font", str(font), *req_flags])
        md = write_md(cfg, font, face_dir, recorded, installed, notices, drift, data, differing, adoption, identical, anything)
        result = {"recorded": recorded, "installed": installed, "face": str(face_dir), "values": values, "renders": data["renders"],
                  "changed": data["changed"], "bytes_identical": identical, "changed_files": [], "drift": drift, "notices": notices,
                  "attribution": "unverified" if anything else "not applicable"}
        out.mkdir(parents=True, exist_ok=True)
        (out / MARKER).write_text("written by update-check.py; this folder is an update check's OUT and is replaced by the next run\n",
                                  encoding="utf-8")
        stage = pathlib.Path(tempfile.mkdtemp(dir=out, prefix=".update-stage-"))
        try:
            shutil.copytree(report, stage / "diff")
            (stage / "update.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            (stage / "update.md").write_text(md, encoding="utf-8")
            for n in ("update.md", "update.json", "diff"):
                p = out / n
                if p.is_dir():
                    shutil.rmtree(p)
                elif p.exists():
                    p.unlink()
            (stage / "diff").replace(out / "diff")
            (stage / "update.json").replace(out / "update.json")
            (stage / "update.md").replace(out / "update.md")  # last: update.md exists only when the report is complete
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    something = bool(differing or data["changed"] or drift or not all(identical.values()))
    print(f"update-check.py: recorded {recorded}, installed {installed}: {'differences found' if something else 'no difference in any group'}; "
          f"wrote {out / 'update.md'}")
    return 3 if something else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="the folder to write update.md, update.json and diff/ into; never the face folder or inside it")
    ap.add_argument("--font", required=True, help="the face's font.json")
    ap.add_argument("--recorded", metavar="VERSION", help="the skill version that built the face, for a face whose manifest has no skill_version")
    ap.add_argument("--sizes", nargs="+", type=float, metavar="PX", help="CSS px sizes diff.py renders (default: font.json review.sizes)")
    args = ap.parse_args(argv)
    rc, _out = run(args)
    return rc


if __name__ == "__main__":
    sys.exit(main())
