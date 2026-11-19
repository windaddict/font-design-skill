#!/usr/bin/env python3
"""Computes the compatibility digests of the three example fonts, and records the compatibility baseline.

WHAT IT'S FOR: 0.2 adds generator parameters whose defaults must leave every shipped font byte for byte
as it was. A rebuild that only has to "look the same" cannot prove that, and the woff2 files are not
tracked (fonts are never published from this repo), so there is nothing to diff against. This module
turns an example's build into three short digests that a tracked JSON file can hold, so
tests/test_backward_compat.py can compare a fresh build with what the baseline commit produced (0.1.0's `0fc4314` from 0.2 to 0.4; since
0.5.0 the commit that redrew the R's leg root, which moved every group's export and TTF digest: the fixture's `supersedes` entry records it).

The three digests, per example group:

  export_sha256    over the export JSON (the generator's output, before fontTools) with every `sig`
                   removed: per master `kerns`, `space`, `titles`, `minStrokeWidth`, and per glyph
                   `adv`, `polys`, `raw`, `runs`, `keptIdx`, `minw`. Pure node arithmetic, so it does
                   not depend on the Python or brotli build. `sig` is left out because 0.2 may add text
                   to the branch record (a token) without changing a coordinate; a changed decision
                   shows up in the coordinates anyway.
  ttf_sha256       over the woff2 decompressed by fontTools and re-serialised as a plain TTF
                   (flavor None, timestamps not recalculated). It does not depend on the brotli build.
  manifest_sha256  over the manifest with `sources_sha256` and `tools` removed (the source files
                   change by definition, and the tool versions differ between machines), each
                   group's `woff2_sha256` and `woff2_bytes` removed (they follow brotli), and each
                   group's `file` cut to its file name (a build with --out-dir records the absolute
                   output path, which differs per run).

The woff2 sha256 of each file is recorded too, together with the brotli version that compressed it. The woff2 bytes depend on brotli, so
tests/test_backward_compat.py compares them ONLY when the running brotli is the recorded one, and skips naming both versions otherwise.
None of the three digests above is a claim about woff2 bytes: they prove the outlines, the tables fontTools writes and the manifest figures.

Exact guarantee of tests/test_backward_compat.py against this fixture: the three examples' fresh digests EQUAL the recorded ones for the running
platform and node major, and the fixture names a baseline commit of git-sha shape and the version and record it superseded. The test does NOT
re-verify that the recorded digests came from that commit's scripts: that guard (`guard()` below) runs at --record time only, so a fixture
written by hand, or from --print with a pasted revision, passes the test. What ties the record to the commit is the recording path, not the test.

The record is keyed by PLATFORM AND NODE MAJOR VERSION (`darwin/26`, `linux/22`): the export digest is floating-point arithmetic, which
depends on V8 and, as the first Linux CI run showed, on the operating system too (the same node major version gave other digests for the
bract and driftwood fonts on Linux than on macOS). A platform and node that produces a different digest on the UNCHANGED 0.1.0 tree is not a
regression: record it, from the baseline commit's code, with the commands below (on Linux, the `record-baseline` workflow does it). The promise
"a 0.1 project rebuilds to the same fonts" is therefore per platform and node major version.

    .venv/bin/python3 tests/baseline_digest.py --print [--out F]        # the working tree's digests, as one entry (no guard)
    .venv/bin/python3 tests/baseline_digest.py --record --rev <baseline sha>   # add this platform/node entry to the fixture
    .venv/bin/python3 tests/baseline_digest.py --record --rev <baseline sha> --repo PATH --out F   # build a checkout of the baseline commit at PATH, write the entry only
    .venv/bin/python3 tests/baseline_digest.py --merge F [F ...]        # merge entry files into the fixture

--record refuses unless scripts/gen.js, export.js and build.py of the tree it builds (this one, or --repo) are byte-identical to REV's copies,
so a baseline cannot be recorded from modified code (the whole point is that it comes from the baseline commit). --merge refuses an entry recorded at another
revision.

Copyright 2026 John Knox. MIT licence.
"""
import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
TREE = REPO  # the tree whose scripts and examples are built: this repo, or a checkout of the baseline commit named by --repo
SCHEMA = "font-design/baseline-digests/v2"
ENTRY_SCHEMA = "font-design/baseline-entry/v1"
FIXTURE = REPO / "tests" / "fixtures" / "baseline.json"
# example -> extra build arguments: the neutral example has a requirements.json, the two precedents do
# not (smoke.sh step 2 declines the required-character check for them the same way)
EXAMPLES = {"neutral": [], "bract": ["--no-requirements"], "driftwood": ["--no-requirements"]}
GLYPH_FIELDS = ("adv", "polys", "raw", "runs", "keptIdx", "minw")
MASTER_FIELDS = ("kerns", "space", "titles", "minStrokeWidth")
MANIFEST_DROP = ("sources_sha256", "tools")
GROUP_DROP = ("woff2_sha256", "woff2_bytes")


def canon(obj):
    """Canonical JSON bytes: sorted keys, no whitespace, so one value has one digest."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def export_digest(export):
    """The digest of one group's export JSON, with every `sig` removed (see the header)."""
    masters = {}
    for name in sorted(export["masters"]):
        m = export["masters"][name]
        masters[name] = {f: m[f] for f in MASTER_FIELDS}
        masters[name]["glyphs"] = {k: {f: g[f] for f in GLYPH_FIELDS} for k, g in sorted(m["glyphs"].items())}
    return sha(canon({"group": export["group"], "italic": export["italic"], "italicAngle": export["italicAngle"], "masters": masters}))


def ttf_digest(woff2_path):
    """The digest of a woff2 decompressed and re-serialised as a TTF."""
    from fontTools.ttLib import TTFont
    font = TTFont(str(woff2_path), recalcTimestamp=False)
    font.flavor = None
    buf = io.BytesIO()
    font.save(buf)
    return sha(buf.getvalue())


def manifest_digest(manifest):
    m = {k: v for k, v in manifest.items() if k not in MANIFEST_DROP}
    m["groups"] = {g: {k: v for k, v in spec.items() if k not in GROUP_DROP} for g, spec in manifest["groups"].items()}
    for spec in m["groups"].values():
        if "file" in spec:
            spec["file"] = pathlib.PurePosixPath(spec["file"]).name
    return sha(canon(m))


def build_example(name, out_dir, keep):
    """Builds one example into out_dir (outside the repo's own out/ folder), keeping each group's export
    JSON under `keep`. Returns the CompletedProcess."""
    ex = TREE / "examples" / name
    cmd = [sys.executable, str(TREE / "scripts" / "build.py"), "--font", str(ex / "font.json"), "--out-dir", str(out_dir),
           "--keep-masters", str(keep / "export.json"), *EXAMPLES[name]]
    if name == "neutral":
        cmd += ["--requirements", str(ex / "requirements.json")]
    return subprocess.run(cmd, cwd=TREE, capture_output=True, text=True)


def compute(work):
    """{"digests": {"<example>/<group>": {export_sha256, ttf_sha256, manifest_sha256}}, "woff2": {...}} for
    the working tree, building every example under `work`. Raises RuntimeError naming the build's stderr
    tail when a build fails, so a broken generator is a loud failure here and not a missing key."""
    work = pathlib.Path(work)
    digests, woff2 = {}, {}
    for name in EXAMPLES:
        out, keep = work / name / "out", work / name / "keep"
        out.mkdir(parents=True)
        keep.mkdir(parents=True)
        r = build_example(name, out, keep)
        if r.returncode != 0:
            raise RuntimeError(f"{name}: build.py exited {r.returncode}: {r.stderr[-1500:]}")
        manifest = json.loads((out / "manifest.json").read_text())
        mdig = manifest_digest(manifest)
        for group, spec in manifest["groups"].items():
            # one group builds to export.json, several to export-<group>.json (build.py --keep-masters)
            path = keep / f"export-{group}.json" if len(manifest["groups"]) > 1 else keep / "export.json"
            export = json.loads(path.read_text())
            assert export["group"] == group, f"{name}: {path.name} holds group {export['group']!r}, expected {group!r}"
            woff = (out / pathlib.Path(spec["file"]).name)
            digests[f"{name}/{group}"] = {"export_sha256": export_digest(export), "ttf_sha256": ttf_digest(woff), "manifest_sha256": mdig}
            woff2[f"{name}/{group}"] = sha(woff.read_bytes())
    return {"digests": digests, "woff2": woff2}


def brotli_version():
    import brotli
    return getattr(brotli, "__version__", "unknown")


def node_major():
    r = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
    return r.stdout.strip().lstrip("v").split(".")[0]


def platform_key():
    """`darwin/26`, `linux/22`: the platform and the node major version the digests are keyed by."""
    return f"{sys.platform}/{node_major()}"


def load_fixture():
    """The recorded baseline. A missing or malformed file raises: the compat test must FAIL, never skip."""
    data = json.loads(FIXTURE.read_text())
    assert data.get("schema") == SCHEMA, f"{FIXTURE.name}: unexpected schema {data.get('schema')!r}"
    assert isinstance(data.get("by_platform_node"), dict) and data["by_platform_node"], f"{FIXTURE.name}: no digests recorded"
    return data


def record_instructions(data, key):
    return (f"no digests recorded for {key} (recorded: {sorted(data['by_platform_node'])}). If this platform or node differs from the recorded ones only in "
            f"floating-point arithmetic, it is not a regression: record it from the baseline commit's code. On Linux run the `record-baseline` workflow "
            f"(.github/workflows/record-baseline.yml) and merge its artifact with `python tests/baseline_digest.py --merge ENTRY.json`; elsewhere, in a "
            f"checkout of {data['baseline_rev']}, `python tests/baseline_digest.py --record --rev {data['baseline_rev']} --out ENTRY.json --repo .` "
            f"then `--merge ENTRY.json` here")


def judge(data, key, got):
    """Compares freshly computed digests (`got`, {group: {export_sha256, ttf_sha256, manifest_sha256}}) with the record for `key`. Returns
    ("unrecorded", instructions), ("differs", the differing group/digest lines) or ("ok", ""). Pure, so the keying is tested without a build."""
    rec = data["by_platform_node"].get(key)
    if rec is None:
        return "unrecorded", record_instructions(data, key)
    want = rec["digests"]
    if set(got) != set(want):
        return "differs", f"groups built {sorted(got)}, recorded {sorted(want)}"
    bad = [f"{g}: {k} is {got[g][k][:12]}, recorded {want[g][k][:12]}" for g in sorted(want) for k in sorted(want[g]) if got[g][k] != want[g][k]]
    return ("differs", "\n  ".join(bad)) if bad else ("ok", "")


def entry(got, rev):
    """One platform/node record as a file of its own, for merging: {schema, key, baseline_rev, record}."""
    got = dict(got)
    got["brotli"] = brotli_version()
    return {"schema": ENTRY_SCHEMA, "key": platform_key(), "baseline_rev": rev, "node": node_version(), "record": got}


def node_version():
    return subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip()


def guard(rev):
    for f in ("gen.js", "export.js", "build.py"):
        old = subprocess.run(["git", "-C", str(TREE), "show", f"{rev}:scripts/{f}"], capture_output=True)
        if old.returncode != 0:
            sys.exit(f"baseline_digest: git show {rev}:scripts/{f} failed in {TREE}: {old.stderr.decode()[:200]}")
        if (TREE / "scripts" / f).read_bytes() != old.stdout:
            sys.exit(f"baseline_digest: scripts/{f} in {TREE} differs from {rev}; a baseline is recorded from the unmodified 0.1.0 code only")


def merge_entries(paths):
    data = json.loads(FIXTURE.read_text()) if FIXTURE.is_file() else {"schema": SCHEMA, "baseline_rev": None, "by_platform_node": {}}
    for p in paths:
        e = json.loads(pathlib.Path(p).read_text())
        if e.get("schema") != ENTRY_SCHEMA or e.get("baseline_rev") is None:
            sys.exit(f"baseline_digest: {p} is not a recorded entry (an entry from --print carries no baseline revision and is never merged)")
        if data["baseline_rev"] not in (None, e["baseline_rev"]):
            sys.exit(f"baseline_digest: the fixture was recorded at {data['baseline_rev']}, {p} at {e['baseline_rev']}")
        data["baseline_rev"] = e["baseline_rev"]
        data["by_platform_node"][e["key"]] = e["record"]
        print(f"merged {e['key']} ({e.get('node')}) from {p}")
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def record(rev, out=None):
    guard(rev)
    with tempfile.TemporaryDirectory() as tmp:
        e = entry(compute(tmp), rev)
    if out:
        pathlib.Path(out).write_text(json.dumps(e, indent=2, sort_keys=True) + "\n")
        print(f"wrote the {e['key']} entry at {rev} -> {out}")
        return
    tmp_entry = pathlib.Path(tempfile.mkdtemp()) / "entry.json"
    tmp_entry.write_text(json.dumps(e))
    merge_entries([tmp_entry])


def main(argv=None):
    global TREE
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--print", action="store_true", dest="show", help="print the working tree's digests as one entry (no guard, no baseline revision)")
    ap.add_argument("--record", action="store_true", help="record this platform/node's digests from the baseline commit's code (needs --rev)")
    ap.add_argument("--merge", nargs="+", metavar="ENTRY", help="merge entry files written by --record --out into the fixture")
    ap.add_argument("--rev", help="the baseline commit the scripts must equal, for --record")
    ap.add_argument("--repo", help="the tree to build (default: this repo); for --record, a checkout of the baseline revision")
    ap.add_argument("--out", help="write the entry to this file instead of the fixture (--record) or stdout (--print)")
    args = ap.parse_args(argv)
    if args.repo:
        TREE = pathlib.Path(args.repo).resolve()
    if args.merge:
        merge_entries(args.merge)
    elif args.record:
        if not args.rev:
            ap.error("--record needs --rev")
        record(args.rev, args.out)
    elif args.show:
        with tempfile.TemporaryDirectory() as tmp:
            text = json.dumps(entry(compute(tmp), None), indent=2, sort_keys=True) + "\n"
        if args.out:
            pathlib.Path(args.out).write_text(text)
        else:
            print(text, end="")
    else:
        ap.error("pass --print, --record or --merge")


if __name__ == "__main__":
    main()
