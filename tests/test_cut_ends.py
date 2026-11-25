"""A `cut` stroke end keeps no run of edge samples past its cut line next to its corner (0.11.0).

WHAT IT'S FOR: scripts/gen.js 0.10.0 draws a `cut` end by moving the last point of each edge onto the cut line and leaving the edge
samples before it where they were. On the edge whose corner moves back, those samples stand past the cut line, so the outline runs
out to the old end and returns: a spike. `scripts/export.js` counts a spike as a folded edge and `scripts/build.py` refuses a master
with one, so a face with `cut` stem ends cannot be built at all. These tests hold the fix to what a reader of the outlines would
check. The plan is docs/plan-cut-end-spikes.md; each test names its first assertion about the new behaviour by a marker in capitals
(CUT-SPIKE:, CUT-SPIKE-SHIPPED:, CUT-EXPORT-FOLD:, CUT-FACE-BUILD:), which is the message that test fails on against the 0.10.0
generator. The assertions before a marker are coverage checks (enough rows were measured and the named glyphs are among them), so a
probe that measures nothing cannot pass.

How the measure works. tests/cut_end_probe.js draws every glyph of a concept twice, with the concept's `cut` ends and with every `cut`
end replaced by `butt`, and reports one row per EDGE of every stroke end that stayed a `cut` end. Its header defines every figure.
The ones used here: `reach` (how far the cut moved the edge's end corner), `inReach` (how many samples before the end stood within
that distance of the uncut corner, measured along the edge), `spike` (the largest distance, among those samples, by which the outline
continues past the cut line after reaching the cut corner) and `run` (how many consecutive samples that is). The run ends at the
first sample on the safe side of the line, so a later sample past the line is not measured. On a curved terminal the body crosses
the infinite cut line again farther in: measured on 0.11.0 during the build review (2026-11-25, a scratch copy of the probe), 48
of the 11,616 edges keep such a sample, 16 to 52 samples in from the end and up to 16.42 units past the line (the italic `f` of
field and brush at mult 1.65). The clip does not pin those samples, and these tests do not hold them. That case is the one the
guarantee in references/generator.md section 5 excludes. Nothing is computed from
the generator's formulas. The cut direction is `cut` of the parameters params() builds from the concept (its own value,
or the default when it sets none), an input. TOL is the distance, in font units, below
which a sample counts as on the cut line.

The probe starts one node process per concept, side by side: a process that loads many generators runs out of heap, because node
keeps every required module alive.

FONT_DESIGN_CUT_SCRIPTS names another copy of the whole scripts/ folder, with a copy of VERSION beside it, for example a scratch copy
carrying one mutation (the watches in the plan's Verification section); unset, the real one.
"""
import concurrent.futures
import functools
import importlib.util as _ilu
import json
import math
import os
import pathlib
import pathlib as _pl
import re
import shutil
import sys

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
node = _mod.node
run = _mod.run

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_CUT_SCRIPTS", REPO / "scripts"))
PROBE = REPO / "tests" / "cut_end_probe.js"
EXAMPLES = REPO / "examples"
CONCEPT_FILES = [EXAMPLES / "bract" / "concepts.js", EXAMPLES / "driftwood" / "concepts.js", EXAMPLES / "neutral" / "concepts.js",
                 REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]
MULTS = [1, 1.3, 1.5, 1.65]
STYLES = ["roman", "italic"]
TOL = 0.05          # units
DEG = math.pi / 180
SHIPPED_PAIRS = {("bract/concepts.js", "field"), ("driftwood/concepts.js", "windswept"), ("templates/concepts.example.js", "grot"),
                 ("templates/concepts.example.js", "brush"), ("templates/concepts.genres.js", "grot"), ("templates/concepts.genres.js", "geometric")}

# The Cane concept of the request: a broad-nib sans with `cut` stem ends. `pow` 1, `xs` 1, `track` 0, `dot` 0.55 and `overshoot` 10 are
# NOT in the request; without them the concept draws non-finite coordinates (references/generator.md section 4 says only `id`, `W` and
# `ends` are required, which is wrong), so the fixture sets them.
CANE = {
    "id": "cane", "name": "Cane", "W": 114, "nib": 0, "thin": 0.85, "swell": 0.35, "wob": 0.015,
    "ends": {"s": "cut", "t": "butt", "u": "butt", "": "disk", "x": "exit"}, "cut": 32 * DEG,
    "joints": True, "crotch": 0.3, "xh": 550, "pow": 1, "xs": 1, "track": 0, "dot": 0.55, "overshoot": 10,
}


# --- running the probe ----------------------------------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _probe(mode, spec_json):
    r = run([node(), str(PROBE), mode, str(SCRIPTS), spec_json])
    assert r.returncode == 0, f"cut_end_probe.js {mode} exited {r.returncode}:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout)


def spec_json(**kw):
    return json.dumps(kw, sort_keys=True)


def _parallel(specs, mode="ends"):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(specs))) as pool:
        parts = list(pool.map(lambda s: _probe(mode, s), specs))
    return [row for part in parts for row in part]


@functools.lru_cache(maxsize=None)
def cane_rows():
    """The `ends` rows of the Cane concept, roman and italic, four multipliers."""
    return _probe("ends", spec_json(inline=[CANE], only="cane", mults=MULTS, styles=STYLES))


@functools.lru_cache(maxsize=None)
def shipped_pairs():
    """(file, concept) for every concept of the five shipped concept files that maps an end to `cut`, found by running the generator's
    own concept loader (the probe's `cutconcepts` mode), not by reading the source text."""
    rows = _parallel([spec_json(files=[str(f)]) for f in CONCEPT_FILES], "cutconcepts")
    return tuple(sorted((r["file"], r["concept"]) for r in rows))


@functools.lru_cache(maxsize=None)
def shipped_rows():
    """The `ends` rows of every shipped concept with a `cut` end, one node process each."""
    by_label = {f"{f.parent.name}/{f.name}": f for f in CONCEPT_FILES}
    return _parallel([spec_json(files=[str(by_label[fl])], only=cid, mults=MULTS, styles=STYLES) for fl, cid in shipped_pairs()])


def worst(rows, field="spike", n=3):
    top = sorted(rows, key=lambda r: -r[field])[:n]
    where = ("file", "concept", "style", "mult", "key", "end", "edge")
    return "; ".join(" ".join(str(r[k]) for k in where if k in r) + f" {field} {r[field]:.2f}" for r in top)


# --- 1 and 2: no sample past the cut line -------------------------------------------------------------------------------------

def test_no_cut_end_keeps_a_sample_past_its_cut_line_on_the_cane_concept():
    """One module (`glyph()` of gen.js): the Cane concept, roman and italic at 10 degrees, mult 1 to 1.65, every key of G. Every edge of
    every `cut` end that stayed a cut end keeps no sample, among those the cut's reach covers, past its cut line (within 0.05 units)
    after the outline has reached the cut corner. Red on 0.10.0 at CUT-SPIKE: 931 of 1,912 edges, worst 95.68 units. The measure
    is the run of samples past the line that starts at the cut corner. A sample past the line after a safe-side sample is not
    measured (module docstring)."""
    rows = cane_rows()
    assert len(rows) >= 1800, f"only {len(rows)} edge rows were measured on the Cane concept"
    moved = [r for r in rows if r["reach"] > 1e-6]
    assert len(moved) >= 1800, f"only {len(moved)} of {len(rows)} Cane edges have a cut that moved the corner"
    for key in "lnLi":
        hit = [r for r in rows if r["style"] == "roman" and r["mult"] == 1.5 and r["key"] == key and r["reach"] > 30]
        assert hit, f"the roman {key} at mult 1.5 has no cut edge with a reach over 30 units"
    spiked = [r for r in rows if r["spike"] > TOL]
    assert not spiked, f"CUT-SPIKE: {len(spiked)} of {len(rows)} cut-end edges keep a sample more than {TOL} past the cut line; worst {worst(spiked)}"


def test_no_cut_end_keeps_a_sample_past_its_cut_line_in_any_shipped_concept():
    """One module, every concept of the five shipped concept files that maps an end to `cut` (found by running the loader): the same
    measure. The shipped concepts never built a face with a cut stem end, so this holds the repository's own recipes to it. Red on
    0.10.0 at CUT-SPIKE-SHIPPED: 3,817 of 9,704 edges, worst 126.26 units. The measure is the run of samples past the line that
    starts at the cut corner. A sample past the line after a safe-side sample is not measured (module docstring)."""
    pairs = set(shipped_pairs())
    assert SHIPPED_PAIRS <= pairs, f"the concepts with a cut end are {sorted(pairs)}; missing {sorted(SHIPPED_PAIRS - pairs)}"
    rows = shipped_rows()
    for fl, cid in sorted(pairs):
        n = len([r for r in rows if r["file"] == fl and r["concept"] == cid and r["reach"] > 1e-6])
        assert n >= 1000, f"{fl} {cid}: only {n} edges with a cut that moved the corner"
    assert len(rows) >= 9000, f"only {len(rows)} edge rows were measured in the shipped concepts"
    spiked = [r for r in rows if r["spike"] > TOL]
    assert not spiked, f"CUT-SPIKE-SHIPPED: {len(spiked)} of {len(rows)} cut-end edges keep a sample more than {TOL} past the cut line; worst {worst(spiked)}"


# --- 3 and 4: a face with cut stem ends -------------------------------------------------------------------------------------------

ANCHOR = 'ends: { s: "serif", t: "flare", u: "flare", "": "disk", x: "exit" },'


def make_face(dest):
    """A copy of examples/neutral in `dest` whose two concepts draw `cut` stem ends at 32 degrees."""
    dest.mkdir(parents=True)
    for name in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(EXAMPLES / "neutral" / name, dest / name)
    text = (dest / "concepts.js").read_text(encoding="utf-8")
    assert text.count(ANCHOR) == 2, f"examples/neutral/concepts.js: {ANCHOR!r} occurs {text.count(ANCHOR)} times, expected twice"
    (dest / "concepts.js").write_text(text.replace(ANCHOR, 'ends: { s: "cut", t: "flare", u: "flare", "": "disk", x: "exit" }, cut: 32 * DEG,'), encoding="utf-8")


def build_face(dest):
    make_face(dest)
    return run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(dest / "font.json"), "--requirements", str(dest / "requirements.json"),
                "--keep-masters", str(dest / "keep" / "export.json")])


def test_a_face_with_cut_stem_ends_exports_without_a_folded_edge(tmp_path):
    """Two modules, `gen.js` into `export.js` (the exporter's own fold measure, master compatibility and decimation): a copy of
    examples/neutral whose stem ends are `cut`. The roman group has 4 masters and the italic group 2, each draws at least 50 glyphs
    with a cut end, and none has a folded edge. Red on 0.10.0 at CUT-EXPORT-FOLD: 101, 102, 101, 102, 77 and 77 folded edges."""
    face = tmp_path / "face"
    make_face(face)
    exports = {}
    for group, n_masters in (("roman", 4), ("italic", 2)):
        out = face / "keep" / f"export-{group}.json"
        r = run([node(), str(SCRIPTS / "export.js"), "--font", str(face / "font.json"), "--group", group, str(out)])
        assert r.returncode == 0, f"export.js --group {group} exited {r.returncode}:\n{r.stderr[-2000:]}"
        exports[group] = json.loads(out.read_text(encoding="utf-8"))["masters"]
        assert len(exports[group]) == n_masters, f"the {group} export has {len(exports[group])} masters, expected {n_masters}"
        for name, m in exports[group].items():
            # the outcome the generator drew (` ends=A/B`), not the branch the concept asked for (` A=cut`): an end can ask for `cut`
            # and be drawn another way (the probe makes the same distinction)
            with_cut = [k for k, g in m["glyphs"].items() if any(re.search(r" ends=(cut/|\S*/cut\b)", s) for s in g["sig"])]
            assert len(with_cut) >= 50, f"{group}/{name}: only {len(with_cut)} glyphs hold an end drawn cut"
    folded = [(g, n, m["foldedEdges"], m["worstFoldAt"]) for g, ms in exports.items() for n, m in ms.items() if m["foldedEdges"] != 0]
    assert not folded, "CUT-EXPORT-FOLD: " + "; ".join(f"{g}/{n}: {c} folded edges, worst at {w}" for g, n, c, w in folded)


def test_a_face_with_cut_stem_ends_builds(tmp_path):
    """The whole tool: concepts.js to export.js to build.py to the woff2 files, with the builder's self-checks, for the same face.
    Red on 0.10.0 at CUT-FACE-BUILD: build.py exits 1 with `SELF-CHECK FAILED: TextRegular: 101 stroke edge(s) fold back`."""
    face = tmp_path / "face"
    r = build_face(face)
    assert r.returncode == 0, f"CUT-FACE-BUILD: build.py exited {r.returncode}:\n{r.stderr[-2000:]}"
    out = face / "out"
    woff2 = sorted(p.name for p in out.rglob("*.woff2"))
    assert len(woff2) >= 2, f"build.py wrote {len(woff2)} woff2 files under {out}: {woff2}"
    assert any(p.name == "manifest.json" for p in out.rglob("manifest.json")), f"no manifest.json under {out}"
