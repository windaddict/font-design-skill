"""headSink buries the stem end under a lowercase head serif, and moves nothing else.

WHAT IT'S FOR: a lowercase head serif (the wedge scripts/gen.js serifPoly() draws on the top of b d h i j k l m n p r u) has a
top edge that slopes down to the left, while the stem under it ends flat. The stem's top-left corner therefore stands above the
wedge (2.8 units on the Driftwood example, up to 22 on a tall serif). `headSink` is an opt-in concept parameter, 0 to 0.7, that
moves the end down by `headSink x h` (h = the serif height) so the corner is hidden inside the wedge. These tests hold it to
what a reader of the outlines would check: the stem end lies under the wedge's top edge and inside the wedge, the depth is the
one the parameter names (with `serifGrow` included), nothing but the stems under a lowercase head moves, and advances, spacing
profiles and kerns stay those of the concept without the key. The plan is .claude/plans/head-sink.md (docs/plan-head-sink.md
once released); each test below is named there with the assertions it makes and the mutation that must turn it red.

How the measure works. Nothing is computed from the generator's formulas. tests/head_sink_probe.js draws glyphs and reports, for
each stem end that sits under a lowercase head, the end's two corner points and the 15 points of the wedge drawn over it. The
stem end is the segment between the two corners. At 21 x positions from 0.1 % to 99.9 % of the way from the left corner to the
right, `stem_y(x)` is the end's height there, and the wedge's boundary crossed with the vertical line at x gives a highest and
a lowest crossing. Then:
  poke       = max over the positions of (stem_y - wedge_top): how far the end stands above the wedge. Positive is the defect.
  left_poke  = the same at the first position, the stem's left edge.
  cover      = min over the positions of (stem_y - wedge_bottom): how far the end stays above the wedge's lower edge. A small
               figure means the end has sunk out of the serif.

FONT_DESIGN_HS_SCRIPTS names another scripts/ folder to test (a scratch copy carrying one mutation, for the watches in the
plan's Verification section); unset, the real one.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import importlib.util as _ilu
import pathlib as _pl

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
node = _mod.node
run = _mod.run

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_HS_SCRIPTS", REPO / "scripts"))
GEN = SCRIPTS / "gen.js"
PROBE = REPO / "tests" / "head_sink_probe.js"
DRIFTWOOD = REPO / "examples" / "driftwood"
NEUTRAL = REPO / "examples" / "neutral"
# gen.js UPPERISH, restated (not imported) so a change to it shows up as a failing test
UPPERISH = re.compile(r"^[A-Z0-9!?&$%/()\[\]#*©™ÁÀÂÄÉÈÊËÍÏÓÔÖÚÜÑÇ]$")
POSITIONS = [0.001 + (0.999 - 0.001) * i / 20 for i in range(21)]


def probe(spec):
    r = run([node(), str(PROBE), str(GEN), json.dumps(spec)])
    assert r.returncode == 0, f"head_sink_probe.js exited {r.returncode}:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout)


def hs_of(v):
    return v if isinstance(v, str) else float(v)


def index(recs):
    """{(file, concept, style, mult, variant, headSink): record}"""
    return {(r["file"], r["concept"], r["style"], float(r["mult"]), r["variant"], hs_of(r["headSink"])): r for r in recs}


def one(recs, style, mult, hs, variant=""):
    found = [r for r in recs if r["style"] == style and float(r["mult"]) == mult and hs_of(r["headSink"]) == hs and r["variant"] == variant]
    assert len(found) == 1, f"expected one record for {style} mult {mult} headSink {hs} variant {variant!r}, found {len(found)}"
    return found[0]


def serif_height(rec):
    """h = SW x serifH with SW = W0 x (W / W0)^serifGrow = W0 x mult^serifGrow, restated from the concept's own numbers."""
    return rec["W0"] * float(rec["mult"]) ** rec["serifGrow"] * rec["serifH"]


def end_keys(rec):
    return {(k, e["body"], e["end"]): e for k, g in rec["glyphs"].items() for e in g["ends"]}


def centre_y(end):
    return (end["corners"][0][1] + end["corners"][1][1]) / 2


def crossings(wedge, x):
    ys = []
    for i in range(len(wedge)):
        (px, py), (qx, qy) = wedge[i], wedge[(i + 1) % len(wedge)]
        if px == qx or x < min(px, qx) or x > max(px, qx):
            continue
        ys.append(py + (qy - py) * (x - px) / (qx - px))
    return ys


def measure(end, where):
    """poke, left_poke and cover of one stem end (the module docstring defines them)."""
    assert end["wedge"], f"{where}: no wedge found over the stem end"
    (x0, y0), (x1, y1) = sorted(end["corners"], key=lambda p: p[0])
    pokes, covers = [], []
    for t in POSITIONS:
        x = x0 + t * (x1 - x0)
        ys = crossings(end["wedge"], x)
        if not ys:
            continue
        stem_y = y0 + t * (y1 - y0)
        pokes.append(stem_y - max(ys))
        covers.append(stem_y - min(ys))
    assert pokes, f"{where}: the stem end lies outside the wedge's x range"
    return {"poke": max(pokes), "left_poke": pokes[0], "cover": min(covers)}


def all_measures(rec, label):
    return {(k, b, e): measure(end, f"{label} {k}") for (k, b, e), end in end_keys(rec).items()}


def ends_from_export(g):
    """The same ends as the probe reports, found from an export's undecimated polygons (`raw`), `runs` and `sig`."""
    polys, runs_all, sig = g["raw"], g["runs"], g["sig"]
    bodies = []
    for i, runs in enumerate(runs_all):
        if len(runs) != 2:
            continue
        flipped, n = runs[0][0] != 0, runs[0][1] - runs[0][0] + 1
        bodies.append((i, n, flipped, runs))
    opens = [s for s in sig if s.startswith("open")]
    assert len(opens) == len(bodies), f"{len(bodies)} bodies but {len(opens)} open records"
    out = []
    for bi, (idx, n, flipped, runs) in enumerate(bodies):
        poly = polys[idx]
        def left(j):
            return poly[runs[0][1] - j] if flipped else poly[runs[0][0] + j]
        def right(j):
            return poly[runs[1][0] + j] if flipped else poly[runs[1][1] - j]
        for letter, j in (("A", 0), ("B", n - 1)):
            if f" serif{letter}=head" not in opens[bi]:
                continue
            corners = [left(j), right(j)]
            mx = (corners[0][0] + corners[1][0]) / 2
            wedge = None
            for wi in range(idx + 1, len(polys)):
                p = polys[wi]
                if len(runs_all[wi]) != 1 or len(p) != 15:
                    continue
                if min(q[0] for q in p) <= mx <= max(q[0] for q in p):
                    wedge = p
                    break
            out.append({"body": idx, "end": letter, "corners": corners, "wedge": wedge})
    return out


LOWER = ("a b c d e f g h i j k l m n o p q r s t u v w x y z".split())
KERN_KEYS = "".join(LOWER) + "AHOTVW" + ".,-'"


# --- a: the request's adversarial fixture: the Driftwood example, unchanged ---------------------------------------

def test_headsink_buries_the_stem_corner_on_the_driftwood_example():
    """Generator level. The `driftwood` concept of examples/driftwood/concepts.js, unchanged, at the multipliers of the example's
    roman masters (1 and 1.65) and its italic masters (1 and 1.3), every key, headSink absent, 0 and 0.6. Without the key a stem
    stands 2.81 units (mult 1) and 4.11 (mult 1.65) above its wedge at its left edge (measured); at 0.6 every end lies under the
    wedge's top edge, both corners at the end's centre line minus 0.6 h, and still inside the wedge; the glyphs that change are
    exactly the ones with a lowercase head, and only their stem bodies; advances, profiles, point counts, records and kerns are
    untouched; and 0 is the outline with no key."""
    recs = probe({"files": [str(DRIFTWOOD / "concepts.js")], "ids": ["driftwood"], "keys": "all", "spacing": True, "kernKeys": KERN_KEYS,
                  "runs": [{"style": "roman", "mults": [1, 1.65]}, {"style": "italic", "mults": [1, 1.3]}],
                  "headSinks": ["undef", 0, 0.6]})
    romans = [1, 1.65]
    # 1. control: the fixture can observe the defect
    heads = set()
    for mult in romans:
        rec = one(recs, "roman", mult, "undef")
        heads |= {k for k, g in rec["glyphs"].items() if g["ends"]}
        weak = [(k, round(m["left_poke"], 2)) for (k, _, _), m in all_measures(rec, f"mult {mult}").items() if m["left_poke"] <= 1]
        assert not weak, f"the fixture cannot observe the defect: at mult {mult} these ends poke 1 unit or less at the stem's left edge with no headSink: {weak[:5]}"
    missing = set("b d h i j k l m n p r u".split()) - heads
    assert not missing, f"the fixture cannot observe the defect: no lowercase head end found on {sorted(missing)}"
    # 2. the stem end lies under the wedge's top edge at 0.6
    for mult in romans:
        for (k, b, e), m in all_measures(one(recs, "roman", mult, 0.6), f"mult {mult}").items():
            assert m["poke"] <= 0.01, f"HEADSINK-POKE: with headSink 0.6 the stem of {k!r} (end {e}) at mult {mult} still pokes {m['poke']:.2f} units above the wedge"
    # 3. and sits at the centre line minus 0.6 h
    for mult in romans:
        absent, sunk = one(recs, "roman", mult, "undef"), one(recs, "roman", mult, 0.6)
        h, ends_a, ends_s = serif_height(sunk), end_keys(absent), end_keys(sunk)
        assert set(ends_a) == set(ends_s), f"mult {mult}: the set of stem ends under a head changed with headSink: {sorted(set(ends_a) ^ set(ends_s))[:5]}"
        for key, ea in ends_a.items():
            want = centre_y(ea) - 0.6 * h
            for c in ends_s[key]["corners"]:
                assert abs(c[1] - want) < 1e-6, f"mult {mult}: a corner of {key[0]!r} end {key[2]} is at y {c[1]:.6f}, expected the centre line minus 0.6 h = {want:.6f} (h = {h:.4f})"
    # 4. and has not left the serif
    for mult in romans:
        sunk = one(recs, "roman", mult, 0.6)
        h = serif_height(sunk)
        for (k, _, e), m in all_measures(sunk, f"mult {mult}").items():
            assert m["cover"] >= 0.25 * h, f"mult {mult}: {k!r} end {e} keeps {m['cover']:.2f} units over the wedge's lower edge, less than 0.25 h = {0.25 * h:.2f}: the end has left the serif"
    # 5. reach: only the stem bodies under a lowercase head differ
    for style, mults in (("roman", romans), ("italic", [1, 1.3])):
        for mult in mults:
            absent, sunk = one(recs, style, mult, "undef"), one(recs, style, mult, 0.6)
            with_head = {k for k, g in absent["glyphs"].items() if g["ends"]}
            changed = {k for k in absent["glyphs"] if absent["glyphs"][k]["pHash"] != sunk["glyphs"][k]["pHash"]}
            assert changed == with_head, \
                f"HEADSINK-REACH: {style} mult {mult}: glyphs that changed {sorted(changed)} are not the glyphs with a lowercase head {sorted(with_head)}"
            for k in changed:
                body_idx = {e["body"] for e in absent["glyphs"][k]["ends"]}
                moved = {i for i, (a, s) in enumerate(zip(absent["glyphs"][k]["pHash"], sunk["glyphs"][k]["pHash"])) if a != s}
                assert moved <= body_idx, f"HEADSINK-REACH: {style} mult {mult}: in {k!r} polygons {sorted(moved - body_idx)} changed, which are not a stem under a lowercase head"
    italic = {k for k, g in one(recs, "italic", 1, "undef")["glyphs"].items() if g["ends"]}
    assert italic == {"w"}, f"HEADSINK-REACH: the italic's lowercase heads are {sorted(italic)}, expected only w (a narrow concept's first stroke)"
    # 6. spacing: point counts, edge runs, records, advances, profiles and kerns
    for style, mults in (("roman", romans), ("italic", [1, 1.3])):
        for mult in mults:
            absent, sunk = one(recs, style, mult, "undef"), one(recs, style, mult, 0.6)
            for k, ga in absent["glyphs"].items():
                gs = sunk["glyphs"][k]
                for f in ("counts", "runs", "sig", "adv", "L", "R"):
                    assert ga[f] == gs[f], f"HEADSINK-SPACING: {style} mult {mult}: headSink changed {f} of {k!r}"
            bad = [(KERN_KEYS[i // len(KERN_KEYS)] + KERN_KEYS[i % len(KERN_KEYS)], a, s) for i, (a, s) in enumerate(zip(absent["kern"], sunk["kern"])) if a != s]
            assert not bad, f"HEADSINK-SPACING: {style} mult {mult}: headSink changed the kern of {len(bad)} pairs, first {bad[:3]}"
    # 7. headSink 0 is the outline with no key
    for style, mults in (("roman", romans), ("italic", [1, 1.3])):
        for mult in mults:
            absent, zero = one(recs, style, mult, "undef"), one(recs, style, mult, 0)
            for k, ga in absent["glyphs"].items():
                assert ga["pHash"] == zero["glyphs"][k]["pHash"] and ga["adv"] == zero["glyphs"][k]["adv"], \
                    f"HEADSINK-ZERO: {style} mult {mult}: headSink 0 draws {k!r} differently from the concept with no headSink"


# --- b: every serif concept the repository ships, and the partial bracket --------------------------------------------

def shipped_concept_files():
    return sorted(REPO.glob("examples/*/concepts.js")) + [REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]


def test_headsink_buries_the_stem_end_in_every_serif_concept_the_repo_ships():
    """Generator level. Every concept that maps an end to `serif` in examples/*/concepts.js, templates/concepts.example.js and
    templates/concepts.genres.js (27 today), roman and italic, lowercase keys, mult 1.65, headSink absent and 0.6. It covers the
    blended head (`serifBracket` other than 1), `serifGrow` in the depth (Bract's concepts use 0.35, clarendon 0.6), and the italic
    w. Then the partial bracket, which no shipped concept has: the driftwood concept with serifBracket 0.5, whose blended head
    also pokes (measured 1.10 and 1.81 units), and with serifBracket 0, whose top is level so there is nothing to bury."""
    recs = probe({"files": [str(p) for p in shipped_concept_files()], "serifOnly": True, "keys": "lower",
                  "runs": [{"style": "roman", "mults": [1.65]}, {"style": "italic", "mults": [1.65]}], "headSinks": ["undef", 0.6]})
    concepts = {(r["file"], r["concept"]) for r in recs}
    roman_heads = {(r["file"], r["concept"]) for r in recs if r["style"] == "roman" and any(g["ends"] for g in r["glyphs"].values())}
    # 1. the sweep did not shrink silently
    assert len(concepts) >= 20 and len(roman_heads) >= 20, \
        f"the sweep found {len(concepts)} serif concepts, {len(roman_heads)} with a roman lowercase head; at least 20 of each are expected"
    sunk = [r for r in recs if hs_of(r["headSink"]) == 0.6]
    absent = {(r["file"], r["concept"], r["style"]): r for r in recs if hs_of(r["headSink"]) == "undef"}
    # 2. no end pokes out
    pokes = []
    for r in sunk:
        for (k, b, e), m in all_measures(r, f"{r['file']} {r['concept']} {r['style']}").items():
            if m["poke"] > 0.01:
                pokes.append((r["file"], r["concept"], r["style"], k, round(m["poke"], 2)))
    assert not pokes, f"HEADSINK-SWEEP: {len(pokes)} stem ends still poke above the wedge at headSink 0.6; first five (file, concept, style, glyph, figure): {pokes[:5]}"
    # 3. no end has left the serif
    for r in sunk:
        h = serif_height(r)
        for (k, b, e), m in all_measures(r, f"{r['file']} {r['concept']}").items():
            assert m["cover"] >= 0.25 * h, \
                f"{r['file']} {r['concept']} {r['style']}: {k!r} end {e} keeps {m['cover']:.2f} units over the wedge's lower edge, less than 0.25 h = {0.25 * h:.2f}: the end has left the serif"
    # 4. the depth is 0.6 h with serifGrow in h. A corner above the line goes down to it; a corner already below it stays (the italic w of a
    #    slanted end has one corner on each side of the centre line), so each corner is expected at min(its height with no key, the line).
    for r in sunk:
        h, ends_a = serif_height(r), end_keys(absent[(r["file"], r["concept"], r["style"])])
        for key, es in end_keys(r).items():
            line = centre_y(ends_a[key]) - 0.6 * h
            for c, c0 in zip(es["corners"], ends_a[key]["corners"]):
                want = min(c0[1], line)
                assert abs(c[1] - want) < 1e-6, \
                    f"{r['file']} {r['concept']} {r['style']} (serifGrow {r['serifGrow']}): a corner of {key[0]!r} is at y {c[1]:.4f}, expected {want:.4f}, the end's centre line minus 0.6 h = {line:.4f} (h = {h:.4f})"
    # 5. the partial bracket
    part = probe({"files": [str(DRIFTWOOD / "concepts.js")], "ids": ["driftwood"], "keys": "lower", "runs": [{"style": "roman", "mults": [1, 1.65]}],
                  "variants": [{"name": "b0.5", "set": {"serifBracket": 0.5}}, {"name": "b0", "set": {"serifBracket": 0}}], "headSinks": ["undef", 0.6]})
    for mult in (1, 1.65):
        for (k, _, e), m in all_measures(one(part, "roman", mult, "undef", "b0.5"), f"b0.5 mult {mult}").items():
            assert m["left_poke"] > 0.5, f"serifBracket 0.5, mult {mult}: {k!r} end {e} pokes only {m['left_poke']:.2f} with no headSink; the control needs more than 0.5"
        for (k, _, e), m in all_measures(one(part, "roman", mult, 0.6, "b0.5"), f"b0.5 mult {mult}").items():
            assert m["poke"] <= 0.01, f"serifBracket 0.5, mult {mult}: with headSink 0.6 {k!r} end {e} still pokes {m['poke']:.2f} above the blended wedge"
        for (k, _, e), m in all_measures(one(part, "roman", mult, "undef", "b0"), f"b0 mult {mult}").items():
            assert abs(m["poke"]) <= 0.01 and abs(m["left_poke"]) <= 0.01, f"serifBracket 0, mult {mult}: {k!r} end {e} is {m['poke']:.2f} off a level top with no headSink"
        sunk0 = one(part, "roman", mult, 0.6, "b0")
        for (k, _, e), m in all_measures(sunk0, f"b0 mult {mult}").items():
            assert m["cover"] >= 0.25 * serif_height(sunk0), f"serifBracket 0, mult {mult}: with headSink 0.6 {k!r} end {e} keeps {m['cover']:.2f}, which is under 0.25 h: the end has left the slab"


# --- c: a face that sets headSink, through export.js, build.py and the font suite --------------------------------------

def build_face(dest, headsink):
    dest.mkdir(parents=True)
    for name in ("font.json", "concepts.js", "requirements.json"):
        shutil.copyfile(DRIFTWOOD / name, dest / name)
    if headsink:
        text = (dest / "concepts.js").read_text(encoding="utf-8")
        anchor = "serifLen: 0.64, serifH: 0.4,"
        assert text.count(anchor) == 1, f"examples/driftwood/concepts.js: {anchor!r} occurs {text.count(anchor)} times, expected once"
        (dest / "concepts.js").write_text(text.replace(anchor, anchor + " headSink: 0.6,"), encoding="utf-8")
    return run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(dest / "font.json"), "--requirements", str(dest / "requirements.json"),
                "--keep-masters", str(dest / "keep" / "export.json")])


def test_a_face_that_sets_headsink_builds_with_its_spacing_unchanged(tmp_path):
    """Pipeline and whole-tool level: follows the parameter from concepts.js to the woff2. Two copies of examples/driftwood: `plain`,
    and `sunk` with ` headSink: 0.6,` added to the concept. The sunk export holds the sunk ends in the undecimated and in the
    decimated polygons; between the two exports only the glyphs with a lowercase head differ, and no advance, kern, title width
    or word space; between the two fonts the metrics and the GPOS table are equal and the roman outlines differ; and the font
    suite passes on the sunk face."""
    plain, sunk = tmp_path / "plain", tmp_path / "sunk"
    rp, rs = build_face(plain, False), build_face(sunk, True)
    # 1. both builds pass the exporter's compatibility and fold checks and the builder's self-checks
    assert rp.returncode == 0, f"the plain build exited {rp.returncode}:\n{rp.stderr[-2000:]}"
    assert rs.returncode == 0, f"the sunk build exited {rs.returncode}:\n{rs.stderr[-2000:]}"
    exp = {name: {g: json.loads((d / "keep" / f"export-{g}.json").read_text(encoding="utf-8")) for g in ("roman", "italic")} for name, d in (("plain", plain), ("sunk", sunk))}
    # 2. the exported undecimated polygons hold the sunk end (raw is rounded to 0.1)
    for group, keys in (("roman", "nilb"), ("italic", "w")):
        for master, m in exp["sunk"][group]["masters"].items():
            for k in keys:
                ends = ends_from_export(m["glyphs"][k])
                assert ends, f"{group}/{master}: no lowercase head end found on {k!r} in the sunk export"
                for end in ends:
                    poke = measure(end, f"{group}/{master} {k}")["poke"]
                    assert poke <= 0.11, f"HEADSINK-BUILD: the exported {group}/{master} {k!r} still pokes {poke:.2f} units above its wedge although the concept sets headSink 0.6"
                    # 3. decimation kept the sunk end: the decimated body reaches the same height as the undecimated one
                    g = m["glyphs"][k]
                    hi_raw, hi_dec = max(p[1] for p in g["raw"][end["body"]]), max(p[1] for p in g["polys"][end["body"]])
                    assert abs(hi_raw - hi_dec) <= 0.11, f"{group}/{master} {k!r}: the decimated body's highest point is {hi_dec} but the undecimated one's is {hi_raw}"
    # 4. between the exports only the stems under a lowercase head differ
    for group in ("roman", "italic"):
        for master, mp in exp["plain"][group]["masters"].items():
            ms = exp["sunk"][group]["masters"][master]
            where = f"{group}/{master}"
            assert set(mp["glyphs"]) == set(ms["glyphs"]), f"HEADSINK-EXPORT: {where}: the glyph sets differ"
            adv = [k for k in mp["glyphs"] if mp["glyphs"][k]["adv"] != ms["glyphs"][k]["adv"]]
            assert not adv, f"HEADSINK-EXPORT: {where}: headSink changed the advance of {adv[:5]}"
            assert mp["kerns"] == ms["kerns"], f"HEADSINK-EXPORT: {where}: headSink changed the kern list"
            assert mp["titles"] == ms["titles"], f"HEADSINK-EXPORT: {where}: headSink changed a title's laid width"
            assert mp["space"] == ms["space"], f"HEADSINK-EXPORT: {where}: headSink changed the word space"
            changed = {k for k in mp["glyphs"] if any(mp["glyphs"][k][f] != ms["glyphs"][k][f] for f in ("polys", "raw"))}
            with_head = {k for k, g in mp["glyphs"].items() if not UPPERISH.match(k) and any(re.search(r" serif[AB]=head", s) for s in g["sig"])}
            assert changed == with_head, f"HEADSINK-EXPORT: {where}: glyphs that changed {sorted(changed)} are not the glyphs with a lowercase head {sorted(with_head)}"
    # 5. the fonts: same metrics, same GPOS, different roman outlines
    from fontTools.ttLib import TTFont
    fam = json.loads((plain / "font.json").read_text(encoding="utf-8"))["family"].replace(" ", "")
    for group, name in (("roman", f"{fam}-VF.woff2"), ("italic", f"{fam}-Italic-VF.woff2")):
        fp, fs = TTFont(plain / "out" / name), TTFont(sunk / "out" / name)
        assert fp["hmtx"].metrics == fs["hmtx"].metrics, f"{group}: headSink changed the hmtx metrics"
        assert fp.getTableData("GPOS") == fs.getTableData("GPOS"), f"{group}: headSink changed the GPOS table"
        if group == "roman":
            assert fp.getTableData("glyf") != fs.getTableData("glyf"), "headSink 0.6 left the roman glyf table byte for byte as it was"
    # 6. the font suite passes on the sunk face
    r = run([sys.executable, "-m", "pytest", "scripts/tests/test_font.py", "-q", "-p", "no:cacheprovider", "--font", str(sunk / "font.json"),
             "--requirements", str(sunk / "requirements.json"), "--static-dir", "none", f"--scripts={SCRIPTS}"])
    assert r.returncode == 0, f"the font suite failed on the sunk face (exit {r.returncode}):\n{(r.stdout + r.stderr)[-3000:]}"


# --- d: the font suite's own headSink tests, on two examples ---------------------------------------------------------

def test_the_font_suites_headsink_tests_pass_on_two_examples():
    """Whole-tool level. The font suite (scripts/tests/test_font.py, the template a site copies) holds two headSink tests that run
    on any project's concepts file with a synthetic concept: the sink itself, and the range refusal. Neither needs a built font.
    This test runs them by path on the neutral and the Driftwood example, so the workflow's red and green runs see them; they are
    proved separately by the mutations headsink-* in scripts/tests/mutate.py."""
    for example in ("neutral", "driftwood"):
        d = REPO / "examples" / example
        r = run([sys.executable, "-m", "pytest", "scripts/tests/test_font.py", "-q", "-p", "no:cacheprovider", "--font", str(d / "font.json"),
                 "--requirements", str(d / "requirements.json"), "--static-dir", "none", f"--scripts={SCRIPTS}", "-k", "headsink"])
        out = r.stdout + r.stderr
        assert r.returncode == 0 and "2 passed" in out, \
            f"HEADSINK-SUITE: the font suite's headSink tests did not both pass on {example} (exit {r.returncode}):\n{out[-2000:]}"
