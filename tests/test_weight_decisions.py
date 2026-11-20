"""Weight cannot flip a branch decision, an italic group takes a heavy master, and the italic opening quotes hold their ink.

WHAT IT'S FOR: two defects a user's italic met when it needed a Bold master (docs/plan-italic-bold.md). First, `strokePolys` read
every geometry-dependent decision (the serif kind `|T[0]| > 0.1`, `vert`, `curved`, the teardrop side, the curl test, the partner
pairing) from the DRAWN tangent, and the drawn geometry moves with weight: `xf` widens heavier masters by `1 + 0.16 (W/W0 - 1)`
and the vertical fit pulls a flat stroke's ends in by half the stroke width. At 0.5.0 44 (glyph, concept, slant) cases over the
five concept files changed structure or record between mult 1 and some multiplier from 0.8 to 2.0, and the Driftwood example's
italic group refused a Bold master at x1.65 on the `w` (`serifA=head` against `serifA=diag`). Since 0.6.0 the decisions read the
geometry at mult 1 and xh 500 (`PU` in `glyph()`), as the x-height map's decisions already did. Second, `build.py`'s
`quote_glyphs()` gave the opening quotes the apostrophe's advance in an italic group, where the apostrophe is spaced over the
x-height band only and its slanted body overhangs the advance by 30 to 53 units; an opening quote is followed by a letter, so
its ink landed on that letter. Since 0.6.0 an italic group's `quoteleft` and `quotedblleft` grow to hold their ink with a right
side bearing that is never negative and equals the left wherever the ink, not the apostrophe-derived advance, sets the advance;
the roman and the closing quotes are unchanged.

The tests run the real generator (tests/weight_flips.js, one node process per concept and slant), the real exporter and the real
builder. The 0.5.0 code for the comparisons is read from git (BASELINE_REV). Exact guarantee of the comparison tests: nothing in any
example group's export JSON moved, no outline, kern or other advance moved in the built fonts, and the two italic groups' hmtx
differs on exactly the two opening quotes. They cannot see a defect shared by both sides of a comparison (both run the current
`export.js` where only `gen.js` is swapped, and the builder comparison runs each tree's own `build.py`).

FONT_DESIGN_WEIGHT_GEN names another gen.js to measure (a scratch copy carrying a mutation); unset, the real one.

Mutations watched red (2026-11-19, each applied to the real scripts/gen.js or scripts/build.py, the named tests run, the file restored
by digest; the log is in references/testing.md section 8): M1 `decideOn = mapOn`; M2 `xf(key, P, p)` in `unmapped()`; M3 `src500`
fitted with `P`; M3b `thin: P.thin` in `PU` (the Regular's width restored, its hairline not); the serif-kind threshold `0.1` made
`0.12` (GREEN here by design: the kind is a design choice both masters share, so it is caught by the digests of test_backward_compat
and by test f below); the tee token's side letter fixed to `L`; a head serif drawn one stroke width off its stem; Q1 the
`if italic_angle` gate removed; Q1' the opening rule removed; Q2 `round(max(xs))` for the advance; Q3 the rule applied to
`quotedblright`; Q4 `max()` dropped; a kern value nudged in `export.js`; an outline moved in `gen.js`.
"""
import importlib.util
import io
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, node, run

sys.path.insert(0, str(REPO / "tests"))
import baseline_digest as bd  # noqa: E402

GEN = pathlib.Path(os.environ.get("FONT_DESIGN_WEIGHT_GEN", REPO / "scripts" / "gen.js"))
FLIPS = REPO / "tests" / "weight_flips.js"
CONCEPT_FILES = sorted((REPO / "examples").glob("*/concepts.js")) + [REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]
BASELINE_REV = "5d0b29f"  # 0.5.0, the last release whose decisions read the drawn, weight-dependent geometry
EXAMPLE_GROUPS = [("neutral", "roman"), ("neutral", "italic"), ("bract", "roman"), ("driftwood", "roman"), ("driftwood", "italic")]
MULTS = [x / 100 for x in range(80, 201, 5) if x != 100]  # what weight_flips.js compares against mult 1: 24 multipliers
SERIF = re.compile(r"serif([AB])=(\w+)")
TEE = re.compile(r"tee=(\d+)@(\d+)(L|R|LR|=)/")


def fid(p):
    return p.parent.name + "/" + p.name


def concept_ids(f):
    r = run([node(), "-e", "const m=require(process.argv[1]);console.log(JSON.stringify(m.loadConcepts(process.argv[2]).map(c=>c.id)))", str(GEN), str(f)])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def flips_js(mode, gen, f, cid, slant, *rest):
    r = run([node(), str(FLIPS), mode, str(gen), str(f), cid, slant, *map(str, rest)])
    assert r.returncode == 0, f"{fid(f)} {cid} {slant}: weight_flips.js exited {r.returncode}: {r.stderr[-2000:]}"
    return json.loads(r.stdout)


# --- a: no structure or record changes with weight ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def weight_flips():
    """{file: {"compared": n, "flips": [names]}} for every concept of every concept file, roman and italic, at the 24 multipliers."""
    out = {}
    for f in CONCEPT_FILES:
        compared, flips = 0, []
        for cid in concept_ids(f):
            for slant in ("roman", "italic"):
                r = flips_js("flips", GEN, f, cid, slant)
                compared += r["compared"]
                flips += [f"{cid} {slant} {k}: differs from mult 1 at {mults}" for k, mults in sorted(r["flips"].items())]
        out[fid(f)] = {"compared": compared, "flips": flips}
    return out


@pytest.mark.parametrize("f", CONCEPT_FILES, ids=fid)
def test_no_branch_or_structure_changes_with_weight(weight_flips, f):
    """Every concept of the file, roman and italic, every glyph: the polygon count, the points per polygon, the edge runs and the
    branch record at every multiplier from 0.8 to 2.0 in steps of 0.05 equal the ones at mult 1 (the comparison export.js makes
    between masters, restated). At least 10,000 comparisons per file, so an empty loop fails. Red at 0.5.0: 44 cases over the five
    files, the italic `w` of 19 concepts among them (docs/plan-italic-bold.md section 0.1)."""
    r = weight_flips[fid(f)]
    assert r["compared"] >= 10000, f"{fid(f)}: only {r['compared']} glyphs compared"
    assert not r["flips"], f"{fid(f)}: weight changed a structure or record:\n  " + "\n  ".join(r["flips"])


def test_the_weight_comparison_covers_the_concept_files(weight_flips):
    """The five files together give exactly 220,080 comparisons (measured on 2026-11-19: 131 keys x 24 multipliers per concept and
    slant), so a loop that silently dropped a file, a slant, a concept or one multiplier would fail here (review F004, diff review:
    a floor of 200,000 let two multipliers go). A new concept or glyph changes the count and this number with it, on purpose."""
    total = sum(r["compared"] for r in weight_flips.values())
    assert len(weight_flips) == 5 and total == 220080, f"{len(weight_flips)} files, {total} comparisons"


# --- b: an italic group takes a Bold master -------------------------------------------------------------------------

def italic_font_json(tmp, heavy):
    """A font.json beside the Driftwood example's concepts with one italic group at mult 1 and `heavy` (axis 400-700)."""
    cfg = json.loads((REPO / "examples" / "driftwood" / "font.json").read_text())
    cfg["concepts"] = str(REPO / "examples" / "driftwood" / "concepts.js")
    cfg["groups"] = {"italic": dict(cfg["groups"]["italic"])}
    cfg["groups"]["italic"]["masters"] = {"Regular": {"concept": "driftwood", "mult": 1, "location": {"wght": 400}},
                                         "Bold": {"concept": "driftwood", "mult": heavy, "location": {"wght": 700}}}
    cfg["groups"]["italic"]["instances"] = [{"name": "Italic", "location": {"wght": 400}}, {"name": "Bold Italic", "location": {"wght": 700}}]
    cfg["groups"]["italic"]["hairline_floors"] = {"Regular": 1, "Bold": 1}
    p = tmp / f"font-{heavy}.json"
    p.write_text(json.dumps(cfg))
    return p


def gen_dir_under_test(tmp):
    if GEN.resolve() == (REPO / "scripts" / "gen.js").resolve():
        return REPO / "scripts"
    d = tmp / "new"
    d.mkdir(exist_ok=True)
    shutil.copyfile(GEN, d / "gen.js")
    shutil.copyfile(REPO / "scripts" / "export.js", d / "export.js")
    return d


def test_an_italic_group_exports_with_a_bold_master(tmp_path):
    """The Driftwood example's concept in an italic group at mult 1 and 1.65 (the user's master) goes through the real export.js:
    exit 0, and the `w`'s record is identical in both masters and reads `serifA=head` on its first stroke (the operator's choice,
    2026-11-19: the head serif stays). A second group at mult 1 and 2.0 exports too. Red at 0.5.0: export.js exits 1 with "1 glyph(s)
    differ in structure or branch outcome between masters of group italic: w"."""
    gen_dir = gen_dir_under_test(tmp_path)
    for heavy in (1.65, 2.0):
        out = tmp_path / f"italic-{heavy}.json"
        r = run([node(), str(gen_dir / "export.js"), "--font", str(italic_font_json(tmp_path, heavy)), "--group", "italic", str(out)])
        assert r.returncode == 0, f"an italic group at mult 1 and {heavy} is refused: export.js exited {r.returncode}:\n{r.stderr[-1500:]}"
        e = json.loads(out.read_text())
        sigs = {mname: M["glyphs"]["w"]["sig"] for mname, M in e["masters"].items()}
        assert sigs["Regular"] == sigs["Bold"], f"mult 1 and {heavy}: the w's records differ:\n{sigs['Regular']}\n{sigs['Bold']}"
        assert "serifA=head" in sigs["Regular"][0], f"the w's first stroke should keep its head serif: {sigs['Regular'][0]}"


# --- the F006 fixture: a fit-moved decision reads the Regular's hairline, not the heavier master's ----------------------

FIT_FIXTURE = r"""
const m = require(process.argv[1]);
const base = Object.assign({}, m.loadConcepts(process.argv[2])[0]);
// a monoline-ish serif concept whose level foot the fit lifts by W thin / 2 (nib 0: hwFlat is exactly that), with a hairline that
// grows with weight (thinGrow 0.5, so thin at mult 2 is thin / sqrt 2). The diagonal leaves the lifted foot, so its drawn tangent
// follows the half width: 48 / (500 - 30) at the Regular's width and hairline. Two glyphs put the serif-kind threshold |T[0]| > 0.1
// between the correct half width (30) and each wrong one: the heavier master's hairline at the Regular's width (21.2; glyph fit1 reads
// diag at 30 and head at 21.2) and the heavier master's width and hairline together (42.4; glyph fit2 reads head at 30 and diag at 42.4)
const c = Object.assign({}, base, { id: "fitfix", W: 200, thin: 0.3, thinGrow: 0.5, nib: 0, pow: 1.2, xs: 1, overshoot: 10, tear: false,
  dropAmt: undefined, flareAmt: undefined, hzThin: undefined, diagThin: undefined, roundGain: undefined, xh: 500,
  ends: Object.assign({}, base.ends, { s: "serif", "": "disk" }) });
m.G.fit1 = [m.S("M 0 0 L 100 0 L 147.7 500", "s", "s")];
m.G.fit2 = [m.S("M 0 0 L 100 0 L 146.6 500", "s", "s")];
const out = {};
for (const mult of [1, 1.5, 2]) {
  const P = m.params(c, mult, false);
  out[mult] = { fit1: m.glyph("fit1", P).sig, fit2: m.glyph("fit2", P).sig };
}
console.log(JSON.stringify(out));
"""


def test_a_fit_moved_decision_reads_the_regular_width_and_hairline():
    """Two hand-built glyphs (a level foot and a diagonal leaving it) in a concept with `thinGrow`, drawn at mult 1, 1.5 and 2:
    the diagonal's serif kind is the mult-1 one at every weight (fit1 `diag`, fit2 `head`). The fit lifts the foot by the level half
    width, W thin / 2, and the diagonal's tangent follows it; fit1 flips when the deciding fit takes the heavier master's hairline at
    the Regular's width (review F006, mutation M3b: `thin: P.thin` in PU), fit2 when it takes the heavier master's width and hairline
    together (mutation M3). Red at 0.5.0 on fit2 (the fit at the drawn weight plus the widening read `diag` at mult 1.5 and 2)."""
    r = run([node(), "-e", FIT_FIXTURE, str(GEN), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    kinds = {g: {mult: SERIF.findall(" ".join(out[mult][g])) for mult in out} for g in ("fit1", "fit2")}
    assert kinds["fit1"]["1"] == [("A", "ball"), ("B", "diag")], f"fit1 at mult 1 should read a diag serif at its top: {out['1']['fit1']}"
    assert kinds["fit2"]["1"] == [("A", "ball"), ("B", "head")], f"fit2 at mult 1 should read a head serif at its top: {out['1']['fit2']}"
    bad = [f"{g} at mult {mult}: {out[mult][g]} against mult 1 {out['1'][g]}" for g in ("fit1", "fit2") for mult in ("1.5", "2") if out[mult][g] != out["1"][g]]
    assert not bad, "weight changed a fit-moved decision:\n  " + "\n  ".join(bad)


# --- the narrowed guarantee (F002): a T-join's pinned edge still reads the drawn geometry -------------------------------

TEE_FIXTURE = r"""
const m = require(process.argv[1]);
const base = Object.assign({}, m.loadConcepts(process.argv[2])[0]);
// the reviewer's crossing construction from tests/r_leg_junction.js: a level bar and an `i` leg whose drawn angle to the bar passes
// through perpendicular as the weight widens it (xs 1, shear 0.77, W 200)
const c = Object.assign({}, base, { id: "teecross", xs: 1, shear: 0.77, W: 200, tear: false, dropAmt: undefined, flareAmt: undefined,
  ends: Object.assign({}, base.ends, { s: "serif", "": "disk" }) });
m.G.teecross = [m.S("M 100 340 L 900 340"), m.S("M 500 340 L 750 0", "i", "s")];
const out = {};
for (let x = 80; x <= 200; x += 10) {
  const mult = x / 100, g = m.glyph("teecross", m.params(c, mult, false));
  out[mult] = { sig: g.sig, shape: JSON.stringify([g.polys.map(p => p.length), g.runs]) };
}
console.log(JSON.stringify(out));
"""


def test_a_near_perpendicular_t_join_still_pins_a_different_edge_per_weight():
    """What the 0.6.0 rule does NOT cover, pinned so the promise stays exact (review F002): the T-join's cut and the edges `clipPast`
    pins past it read the drawn geometry per master (generator.md section 12), so a leg that crosses perpendicular to its bar between
    two weights records `L` in one and `R` in the other and the exporter refuses the pair. The crossing construction drawn from mult
    0.8 to 2.0: the token's partner stroke and segment never change and no polygon or point count moves (the join is a width, not a
    decision), but the pinned edges take both `L` and `R` over the range (and `=`, neither, where the leg stands perpendicular). A pin
    of present behaviour, green before and after 0.6.0. Mutation: the side letter fixed to `L` (the set is {L}, red)."""
    r = run([node(), "-e", TEE_FIXTURE, str(GEN), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    tokens = {}
    for mult, rec in out.items():
        found = [TEE.search(s) for s in rec["sig"] if "tee=" in s]
        assert len(found) == 1 and found[0] is not None, f"mult {mult}: no tee token in {rec['sig']}"
        tokens[mult] = found[0].groups()
    assert len({rec["shape"] for rec in out.values()}) == 1, "the polygon or point counts moved with weight; only the pinned edge may"
    assert len({t[:2] for t in tokens.values()}) == 1, f"the partner stroke or segment moved with weight: {tokens}"
    sides = {t[2] for t in tokens.values()}
    assert {"L", "R"} <= sides, f"the pinned edge should take both letters across the weights (the decision reads drawn geometry): {tokens}"


# --- e: the builder's opening-quote rule, on synthetic apostrophes --------------------------------------------------------

def load_build(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def old_tree(tmp_path_factory):
    """The 0.5.0 tree (scripts and examples) from git archive, so its build.py and export.js can be run beside this tree's."""
    d = tmp_path_factory.mktemp("tree-0.5.0")
    archive = subprocess.run(["git", "-C", str(REPO), "archive", BASELINE_REV, "scripts", "examples"], capture_output=True)
    assert archive.returncode == 0, f"git archive {BASELINE_REV} failed: {archive.stderr.decode()[:300]}"
    subprocess.run(["tar", "-x", "-C", str(d)], input=archive.stdout, check=True)
    assert (d / "scripts" / "build.py").is_file() and (d / "examples" / "neutral" / "font.json").is_file()
    return d


def bearings(adv, polys):
    xs = [x for p in polys for x, y in p]
    return min(xs), adv - max(xs)


def test_quote_glyphs_opening_rule(old_tree):
    """`build.quote_glyphs` on three synthetic apostrophes, held against the 0.5.0 derivation read from git (the outlines of all six
    quote glyphs and the closing quotes' advances are point for point the 0.5.0 ones) and the rule restated here from the input: an
    apostrophe whose slanted body overhangs its advance, in an italic group, gives `quoteleft` and `quotedblleft` the advance
    `round(xMax + max(xMin, 0))` of their own ink (equal bearings when the ink starts right of the origin, a right bearing of 0 when it starts left of it) and leaves `quoteright`, `quotedblright` and the ticks alone; an apostrophe
    already inside its advance with a larger right bearing keeps the apostrophe-derived advance (`max()` binds: the only place that
    branch is observable, since on every shipped italic master the rule's value exceeds the old advance); the overhanging one in a
    roman group changes nothing. Mutations: Q1 (red on the roman case), Q1', Q2, Q3, Q4 (red on the second case)."""
    new = load_build(REPO / "scripts" / "build.py", "build_under_test")
    old = load_build(old_tree / "scripts" / "build.py", "build_0_5_0")
    body = [(20, 480), (60, 470), (130, 690), (90, 700)]  # a slanted mark: ink from x 20 to 130
    left = [[(x - 40, y) for x, y in body]]  # the same mark from x -20 to 90
    left = left[0]
    half = [(-20, 480), (20, 470), (90.5, 690), (50, 700)]  # ink from x -20 to 90.5
    cases = [
        ("overhanging, italic", [body], 90, 10.0, {"quoteleft": 150, "quotedblleft": round(90 + 110 * 1.45) + 60}),
        ("inside its advance, italic", [body], 200, 10.0, {}),
        ("overhanging, roman", [body], 90, 0.0, {}),
        # review F001 (diff review): ink starting left of the origin; the right bearing must still be >= 0, so the left extreme counts as 0
        ("overhanging from left of the origin, italic", [left], 50, 10.0, {"quoteleft": 90, "quotedblleft": round(90 + 110 * 1.45)}),
        # re-review F001: a right extreme at x .5 that round() takes down (90.5 -> 90); the advance is at least its ceiling
        ("a fractional right extreme, italic", [half], 50, 10.0, {"quoteleft": 91, "quotedblleft": math.ceil(90.5 + 110.5 * 1.45)}),
    ]
    for label, polys, adv, angle, grown in cases:
        got, ref = new.quote_glyphs(polys, adv, angle), old.quote_glyphs(polys, adv, angle)
        assert set(got) == set(ref) == {"quotesingle", "quotedbl", "quotedblright", "quoteleft", "quotedblleft"}, f"{label}: {sorted(got)}"
        for name in ref:
            assert got[name]["polys"] == ref[name]["polys"], f"{label} {name}: the outline differs from the 0.5.0 derivation"
            want = grown.get(name, ref[name]["adv"])
            assert got[name]["adv"] == want, f"{label} {name}: advance {got[name]['adv']}, expected {want} (0.5.0 gave {ref[name]['adv']})"
        if grown:
            for name in grown:
                lsb, rsb = bearings(got[name]["adv"], got[name]["polys"])
                assert rsb >= 0, f"{label} {name}: the ink overhangs the advance by {-rsb}"
                if lsb >= 0:
                    assert abs(lsb - rsb) <= 1, f"{label} {name}: bearings {lsb} / {rsb} are not equal"
        else:
            assert got["quoteleft"]["adv"] == adv and got["quotedblleft"]["adv"] == ref["quotedblleft"]["adv"], \
                f"{label}: the opening quotes should keep the apostrophe-derived advances"
    # the ink the rule rests on, restated: with adv 90 the mark's right edge (130) is 40 past the advance, so the grown advance is 130 + 20;
    # with adv 200 the right bearing (70) exceeds the left (20), so max() keeps 200
    assert bearings(90, [body]) == (20, -40) and bearings(200, [body]) == (20, 70)


# --- f: nothing but the italic opening quotes changed since 0.5.0 ----------------------------------------------------------

def build_tree(tree, name, out, keep):
    """build.py of `tree` on its own copy of the example, the way tests/baseline_digest.py builds a checkout."""
    ex = tree / "examples" / name
    cmd = [sys.executable, str(tree / "scripts" / "build.py"), "--font", str(ex / "font.json"), "--out-dir", str(out),
           "--keep-masters", str(keep / "export.json"), *bd.EXAMPLES[name]]
    if name == "neutral":
        cmd += ["--requirements", str(ex / "requirements.json")]
    r = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
    assert r.returncode == 0, f"{tree.name} {name}: build.py exited {r.returncode}: {r.stderr[-1500:]}"


def ttf_of(woff2):
    from fontTools.ttLib import TTFont
    f = TTFont(str(woff2), recalcTimestamp=False)
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    buf.seek(0)
    return TTFont(buf)


@pytest.fixture(scope="module")
def builds(old_tree, tmp_path_factory):
    """Every example group built by the 0.5.0 tree and by this one: {(example, group): (old, new)} with each side's export JSON, decoded
    TTF, woff2 path and the group's font.json spec."""
    work = tmp_path_factory.mktemp("builds")
    out = {}
    for label, tree in (("old", old_tree), ("new", REPO)):
        for name in bd.EXAMPLES:
            o, k = work / label / name / "out", work / label / name / "keep"
            o.mkdir(parents=True)
            k.mkdir(parents=True)
            build_tree(tree, name, o, k)
            manifest = json.loads((o / "manifest.json").read_text())
            cfg = json.loads((tree / "examples" / name / "font.json").read_text())
            for group, spec in manifest["groups"].items():
                path = k / f"export-{group}.json" if len(manifest["groups"]) > 1 else k / "export.json"
                woff = o / pathlib.Path(spec["file"]).name
                out.setdefault((name, group), {})[label] = {"export": json.loads(path.read_text()), "ttf": ttf_of(woff), "woff2": woff, "cfg": cfg["groups"][group]}
    assert set(out) == set(EXAMPLE_GROUPS), sorted(out)
    return out


def table_bytes(ttf, tag):
    return ttf.getTableData(tag) if tag in ttf else None


def tables_that_differ(a, b):
    """The sfnt tables whose bytes differ (GlyphOrder is fontTools' own pseudo-table, not a table of the font)."""
    return sorted(t for t in set(a.keys()) | set(b.keys()) if t != "GlyphOrder" and table_bytes(a, t) != table_bytes(b, t))


def plain(obj):
    """A table's attributes as comparable values: fontTools wraps `panose` in an object that compares by identity."""
    if hasattr(obj, "__dict__"):
        return plain(vars(obj))
    if isinstance(obj, dict):
        return {k: plain(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    return obj


def glyph_bytes(ttf, name):
    glyf = ttf["glyf"]
    return glyf[name].compile(glyf)


def expected_opening_advances(export, master):
    """From the EXPORT polygons of the master's apostrophe (not the compiled glyf bounds: review F005): `quoteleft` holds the
    apostrophe's own ink, which the 180 degree turn about the box centre leaves at the same x extent; `quotedblleft` adds the second
    mark 1.45 ink widths out."""
    xs = [x for p in export["masters"][master]["glyphs"]["'"]["polys"] for x, y in p]
    aw = max(xs) - min(xs)
    lo = max(min(xs), 0)  # ink left of the origin counts as 0 (review F001, diff review)
    return {"quoteleft": round(max(xs) + lo), "quotedblleft": round(max(xs) + 1.45 * aw + lo)}


def test_only_the_italic_opening_quotes_changed_since_0_5_0(builds):
    """Per example group, the 0.5.0 build against this tree's: the export JSON is identical (export digest: the generator's output does not
    move for any shipped group, decisions included); in a roman group the decoded TTF digest is identical; in an italic group every
    glyph's compiled `glyf` record is identical, GPOS is identical, the tables that differ are a subset of {hmtx, HVAR, gvar, OS/2, head}
    with OS/2 differing in `xAvgCharWidth` only, and at every master's location `hmtx` differs on exactly {quoteleft, quotedblleft}, each
    new advance equal to `round(xMax + xMin)` of the glyph's ink computed from the 0.5.0 export's apostrophe polygons. Red at 0.5.0 by
    design ("hmtx changed on [], expected ['quoteleft', 'quotedblleft']"): it pins that the quotes moved and that nothing else did."""
    from fontTools.varLib import instancer
    bad = []
    for (example, group), sides in builds.items():
        old, new = sides["old"], sides["new"]
        where = f"{example}/{group}"
        if bd.export_digest(old["export"]) != bd.export_digest(new["export"]):
            bad.append(f"{where}: the export JSON moved")
        for master in old["export"]["masters"]:
            og, ng = old["export"]["masters"][master]["glyphs"], new["export"]["masters"][master]["glyphs"]
            if og.keys() != ng.keys() or any(og[k]["sig"] != ng[k]["sig"] for k in og):
                bad.append(f"{where}/{master}: a branch record moved")
        ot, nt = old["ttf"], new["ttf"]
        if not old["cfg"].get("italic"):
            if bd.ttf_digest(old["woff2"]) != bd.ttf_digest(new["woff2"]):
                bad.append(f"{where}: a roman group's TTF moved: tables {tables_that_differ(ot, nt)}")
            continue
        diff = tables_that_differ(ot, nt)
        if not set(diff) <= {"hmtx", "HVAR", "gvar", "OS/2", "head"}:
            bad.append(f"{where}: tables differ beyond the opening quotes' advances: {diff}")
        if ot.getGlyphOrder() != nt.getGlyphOrder():
            bad.append(f"{where}: the glyph order changed")
        else:
            moved = [g for g in ot.getGlyphOrder() if glyph_bytes(ot, g) != glyph_bytes(nt, g)]
            if moved:
                bad.append(f"{where}: outlines moved on {moved}")
            # review F002 (diff review): equal glyf records say nothing about the variation deltas; every glyph but the two opening
            # quotes (whose phantom-point deltas carry the new advance) keeps its gvar variations
            gmoved = [g for g in ot.getGlyphOrder() if g not in ("quoteleft", "quotedblleft")
                      and ot["gvar"].variations.get(g, []) != nt["gvar"].variations.get(g, [])]
            if gmoved:
                bad.append(f"{where}: gvar variations moved on {gmoved}")
        if table_bytes(ot, "GPOS") != table_bytes(nt, "GPOS"):
            bad.append(f"{where}: GPOS moved")
        o2, n2 = plain(vars(ot["OS/2"])), plain(vars(nt["OS/2"]))
        o2.pop("xAvgCharWidth"), n2.pop("xAvgCharWidth")
        if o2 != n2:
            bad.append(f"{where}: OS/2 differs beyond xAvgCharWidth: {[k for k in o2 if o2[k] != n2.get(k)]}")
        # every outline and advance between the masters too (F002; re-review F002: HVAR is only sampled): instances on a grid of five
        # points per axis (ends, quarters, midpoint), every advance through HVAR and every outline through gvar at each
        import itertools
        axes = old["cfg"]["axes"]
        for point in itertools.product(*[[a["min"] + (a["max"] - a["min"]) * k / 4 for k in range(5)] for a in axes]):
            loc = {a["tag"]: v for a, v in zip(axes, point)}
            oi = instancer.instantiateVariableFont(ot, loc, inplace=False)
            ni = instancer.instantiateVariableFont(nt, loc, inplace=False)
            changed = sorted(g for g in ot.getGlyphOrder() if oi["hmtx"][g] != ni["hmtx"][g])
            if not set(changed) <= {"quotedblleft", "quoteleft"}:
                bad.append(f"{where} at {loc}: hmtx changed on {changed}, expected only the opening quotes")
            omoved = [g for g in ot.getGlyphOrder() if glyph_bytes(oi, g) != glyph_bytes(ni, g)]
            if omoved:
                bad.append(f"{where} at {loc}: instanced outlines moved on {omoved}")
        for master, spec in old["cfg"]["masters"].items():
            oi = instancer.instantiateVariableFont(ot, dict(spec["location"]), inplace=False)
            ni = instancer.instantiateVariableFont(nt, dict(spec["location"]), inplace=False)
            changed = sorted(g for g in ot.getGlyphOrder() if oi["hmtx"][g] != ni["hmtx"][g])
            if changed != ["quotedblleft", "quoteleft"]:
                bad.append(f"{where}/{master}: hmtx changed on {changed}, expected ['quotedblleft', 'quoteleft']")
            want = expected_opening_advances(old["export"], master)
            for g, adv in want.items():
                if ni["hmtx"][g][0] != adv:
                    bad.append(f"{where}/{master} {g}: advance {ni['hmtx'][g][0]}, expected {adv} from the 0.5.0 apostrophe's ink (0.5.0 gave {oi['hmtx'][g][0]})")
                if ni["hmtx"][g][1] != oi["hmtx"][g][1]:
                    bad.append(f"{where}/{master} {g}: the left side bearing moved {oi['hmtx'][g][1]} -> {ni['hmtx'][g][1]}")
    assert not bad, "\n".join(bad)


# --- F001: a mixed-concept group whose masters keep their decisions under the reset does not move ---------------------------

def test_a_mixed_concept_group_without_a_mult_1_master_per_concept_exports_as_0_5_0_did(old_tree, tmp_path):
    """The 0.6.0 rule resets each master's decisions to ITS OWN concept's mult-1 decisions, so a group whose masters use different
    concepts is covered by the compatibility promise only while every master keeps its decisions under that reset (review F001). The
    narrowed fixture: the bract example's `text` at mult 1 beside its `display` at mult 1.5, one roman group, the heavier concept with
    no mult-1 master of its own (the shipped bract roman has one per concept, so it cannot show this). Exported with the 0.5.0
    export.js and gen.js and with this tree's: the export JSON and every record are identical. Red if the reset moves a decision of
    the display master, which the generator.md section 11 promise says it may for a concept whose heavier master sits on a threshold;
    bract's does not."""
    cfg = json.loads((REPO / "examples" / "bract" / "font.json").read_text())
    cfg["concepts"] = str(REPO / "examples" / "bract" / "concepts.js")
    roman = dict(cfg["groups"]["roman"])
    roman["masters"] = {"TextRegular": {"concept": "text", "mult": 1, "location": {"wght": 400, "opsz": 24}},
                        "DisplayBold": {"concept": "display", "mult": 1.5, "location": {"wght": 700, "opsz": 72}}}
    cfg["groups"] = {"roman": roman}
    fj = tmp_path / "font.json"
    fj.write_text(json.dumps(cfg))
    exports = {}
    for label, d in (("old", old_tree / "scripts"), ("new", gen_dir_under_test(tmp_path))):
        out = tmp_path / f"{label}.json"
        r = run([node(), str(d / "export.js"), "--font", str(fj), "--group", "roman", str(out)])
        assert r.returncode == 0, f"{label}: export.js exited {r.returncode}: {r.stderr[-1500:]}"
        exports[label] = json.loads(out.read_text())
    assert bd.export_digest(exports["old"]) == bd.export_digest(exports["new"]), "the mixed-concept group's export moved"
    for master in exports["old"]["masters"]:
        og, ng = exports["old"]["masters"][master]["glyphs"], exports["new"]["masters"][master]["glyphs"]
        moved = sorted(k for k in og if og[k]["sig"] != ng[k]["sig"])
        assert not moved, f"{master}: records moved on {moved}"


# --- F003: a serif chosen from the reference geometry sits on the differently angled drawn stroke ---------------------------

def _contours(path):
    cs, cur = [], []
    for verb, pts in path.segments:
        if verb == "moveTo":
            cur = [pts[0]]
        elif verb == "lineTo":
            cur.append(pts[0])
        elif verb == "closePath":
            if cur:
                cs.append(cur)
            cur = []
        else:
            raise RuntimeError(f"unexpected path verb {verb}")
    if cur:
        cs.append(cur)
    return cs


def _area(poly):
    return abs(0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])))


def overlap_area(a, b):
    from pathops import Path, intersection
    pa, pb = Path(), Path()
    for path, poly in ((pa, a), (pb, b)):
        path.moveTo(*poly[0])
        for q in poly[1:]:
            path.lineTo(*q)
        path.close()
    out = Path()
    intersection([pa], [pb], out.getPen())
    return sum(_area(c) for c in _contours(out))


def stroke_groups(polys, runs):
    """The polygons per open stroke, in stroke order: the body (the one polygon with two edge runs) and the terminals that follow it."""
    groups = []
    for p, r in zip(polys, runs):
        if len(r) == 2:
            groups.append([p])
        elif groups:
            groups[-1].append(p)
    return groups


@pytest.fixture(scope="module")
def old_gen(old_tree):
    return old_tree / "scripts" / "gen.js"


def test_every_serif_chosen_from_the_reference_sits_on_its_drawn_stroke(old_gen):
    """Review F003: the serif kind is now read from the mult-1 geometry while the stroke it sits on is drawn at the master's weight, so a
    head serif is drawn on a stroke whose drawn tangent would have said `diag`. For the italic `w` and `W` of every concept of the
    five files, at mult 0.8, 0.9, 1.2, 1.4, 1.5, 1.65, 1.8 and 2.0: wherever the 0.5.0 generator (drawn kind) and this one (reference
    kind) disagree on a stroke's serif kind, every terminal polygon of that stroke in this tree's drawing overlaps the stroke's body
    (skia-pathops intersection, at least 1 square unit). At least 20 such disagreements must be found (27 cases over the five files at
    0.5.0: 19 `w`, 8 `W`), so a generator whose kinds agree everywhere fails the count, not the overlap. Mutations: a head serif drawn
    one stroke width off its stem (red on the overlap); the kind read from the drawn tangent again (red on the count)."""
    import pathops  # noqa: F401  required (requirements.txt): its absence fails this guard instead of skipping it (review F003, diff review)
    mults = ["0.8", "0.9", "1.2", "1.4", "1.5", "1.65", "1.8", "2.0"]
    disagreements, bad = 0, []
    for f in CONCEPT_FILES:
        for cid in concept_ids(f):
            for key in ("w", "W"):
                old = flips_js("records", old_gen, f, cid, "italic", key, *mults)
                new = flips_js("records", GEN, f, cid, "italic", key, *mults)
                for ms in mults:
                    o, n = old[ms], new[ms]
                    if o is None or n is None or "dot" in n["sig"]:
                        continue
                    groups = stroke_groups(n["polys"], n["runs"])
                    if len(groups) != len(n["sig"]):
                        bad.append(f"{fid(f)} {cid} {key} x{ms}: {len(groups)} stroke bodies for {len(n['sig'])} records")
                        continue
                    for si, (os_, ns) in enumerate(zip(o["sig"], n["sig"])):
                        if SERIF.findall(os_) == SERIF.findall(ns):
                            continue
                        disagreements += 1
                        body, terminals = groups[si][0], groups[si][1:]
                        if not terminals:
                            bad.append(f"{fid(f)} {cid} {key} x{ms} stroke {si}: a serif end with no terminal polygon ({ns})")
                        for t in terminals:
                            a = overlap_area(t, body)
                            if a < 1:
                                bad.append(f"{fid(f)} {cid} {key} x{ms} stroke {si}: a terminal of {len(t)} points overlaps its body by {a:.3f} square units "
                                           f"({ns}; 0.5.0 read {os_})")
    assert disagreements >= 20, f"only {disagreements} serif-kind disagreements between the 0.5.0 drawn kind and the reference kind were found"
    assert not bad, "\n".join(bad)
