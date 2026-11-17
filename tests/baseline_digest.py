#!/usr/bin/env python3
"""Computes the compatibility digests of the three example fonts, and records the 0.1.0 baseline.

WHAT IT'S FOR: 0.2 adds generator parameters whose defaults must leave every shipped font byte for byte
as it was. A rebuild that only has to "look the same" cannot prove that, and the woff2 files are not
tracked (fonts are never published from this repo), so there is nothing to diff against. This module
turns an example's build into three short digests that a tracked JSON file can hold, so
tests/test_backward_compat.py can compare a fresh build with what 0.1.0 produced.

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

The record is keyed by node major version, because the export digest is V8 arithmetic. A different node
that produces a different export digest on the UNCHANGED 0.1.0 tree is not a regression: record that
node's digests with --record after a `build.py --check` on a 0.1.0 checkout under it.

    .venv/bin/python3 tests/baseline_digest.py --print                  # digests of the working tree, as JSON
    .venv/bin/python3 tests/baseline_digest.py --record --rev 0fc4314   # add this node's digests to the fixture

--record refuses unless scripts/gen.js, export.js and build.py are byte-identical to REV's copies, so a
baseline cannot be recorded from modified code (the whole point is that it comes from 0.1.0).

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
FIXTURE = REPO / "tests" / "fixtures" / "baseline-0.1.0.json"
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
    ex = REPO / "examples" / name
    cmd = [sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(ex / "font.json"), "--out-dir", str(out_dir),
           "--keep-masters", str(keep / "export.json"), *EXAMPLES[name]]
    if name == "neutral":
        cmd += ["--requirements", str(ex / "requirements.json")]
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)


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


def load_fixture():
    """The recorded baseline. A missing or malformed file raises: the compat test must FAIL, never skip."""
    data = json.loads(FIXTURE.read_text())
    assert data.get("schema") == "font-design/baseline-digests/v1", f"{FIXTURE.name}: unexpected schema {data.get('schema')!r}"
    assert isinstance(data.get("by_node_major"), dict) and data["by_node_major"], f"{FIXTURE.name}: no digests recorded"
    return data


def record(rev):
    for f in ("gen.js", "export.js", "build.py"):
        old = subprocess.run(["git", "show", f"{rev}:scripts/{f}"], cwd=REPO, capture_output=True)
        if old.returncode != 0:
            sys.exit(f"baseline_digest: git show {rev}:scripts/{f} failed: {old.stderr.decode()[:200]}")
        if (REPO / "scripts" / f).read_bytes() != old.stdout:
            sys.exit(f"baseline_digest: scripts/{f} differs from {rev}; a baseline is recorded from the unmodified 0.1.0 code only")
    with tempfile.TemporaryDirectory() as tmp:
        got = compute(tmp)
    data = json.loads(FIXTURE.read_text()) if FIXTURE.is_file() else {
        "schema": "font-design/baseline-digests/v1", "baseline_rev": rev, "by_node_major": {}}
    if data["baseline_rev"] != rev:
        sys.exit(f"baseline_digest: the fixture was recorded at {data['baseline_rev']}, not {rev}")
    got["brotli"] = brotli_version()
    data["by_node_major"][node_major()] = got
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"recorded node {node_major()} digests for {len(got['digests'])} groups at {rev} -> {FIXTURE.relative_to(REPO)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--print", action="store_true", dest="show", help="print the working tree's digests as JSON")
    ap.add_argument("--record", action="store_true", help="add this node's digests to the fixture (needs --rev)")
    ap.add_argument("--rev", help="the 0.1.0 commit the scripts must equal, for --record")
    args = ap.parse_args(argv)
    if args.record:
        if not args.rev:
            ap.error("--record needs --rev")
        record(args.rev)
    elif args.show:
        with tempfile.TemporaryDirectory() as tmp:
            print(json.dumps(compute(tmp), indent=2, sort_keys=True))
    else:
        ap.error("pass --print or --record")


if __name__ == "__main__":
    main()
