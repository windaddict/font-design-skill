"""A stroke shorter than its cut's reach pins only the near half of its edge (0.13.0, finding F001).

WHAT IT'S FOR: the corner a cut shortens is placed by walking back along the edge, as far as the cut's reach. On a stroke shorter than that
reach (the acute and grave accents at multiplier 1.5 and above: reach 80 to 99 units on a stroke about 142 long) an unbounded walk would
end at the last sample of the whole edge and pin the whole edge, the other end's corner included, to one point. The generator bounds
the walk to the near half (`lim`), so the pins of the two ends of one stroke never meet and the middle of the edge keeps its points.
The three tests hold behaviour the fix adds, so each is red on 0.12.0, on the marker named in its docstring (CUT-RUN:, CUT-RUN-ACCENT:,
CUT-RUN-BUILD:); the mutation `var lim = 80;` (the unbounded walk) is a watch of the fix, not the proof of these tests.

How the measure works (tests/cut_end_probe.js defines every figure). `exhaustedEdge`: the first `lim` segments of the row's uncut edge are shorter
than the cut asks (`exhausted` is the same for either edge of the end, and an end can be exhausted on one edge
only: the row's own edge is the one whose walk is measured), so the walk cannot reach the line or the reach.
`pinRun`: how many samples from the end sit on the corner. `lim`:
min(80, floor((n - 2) / 2)). The accents below were found from the rows (2026-11-25, with the fix applied to a scratch copy of gen.js): the moved-back edges
whose own edge is exhausted, at multiplier 1.5 and 1.65 in the roman, of the genres `grot`: stroke 2 of the lowercase grave and acute
vowels `à á è é ù ú`. The genres `geometric` has the short strokes `'`, `,` and `;` exhausted on an end, but on no moved-back edge, so
the plan's expectation that its accents are covered holds only by the end-level measure `exhausted`, not by the row's own edge.
"""
import json
import re

import test_cut_step as cs

GENRES_FILE = "templates/concepts.genres.js"
# (concept, key, stroke) of the short strokes the rows found
SHORT_STROKES = [("grot", "à", 2), ("grot", "á", 2), ("grot", "è", 2), ("grot", "é", 2), ("grot", "ù", 2), ("grot", "ú", 2)]


def _short_rows():
    return [r for r in cs.all_rows() if r["set"] == "shipped" and r["back"] and r["exhaustedEdge"] and not r["stacked"]]


def test_a_stroke_shorter_than_its_cut_reach_pins_only_its_near_half():
    """Across functions: `cutBack` against the edge's own length, on the contour the generator draws. Every edge whose corner the cut
    moved back, whose own edge is `exhaustedEdge` and that is not stacked has `pinRun` at most `lim + 1`, so the pins at one end stop inside the
    near half and the middle is never pinned. Red on 0.12.0 at CUT-RUN: (106 of 172 short edges, worst 15.00)."""
    rows = _short_rows()
    assert len(rows) >= 1, "no edge is moved back, exhausted and not stacked: the fixture holds no stroke shorter than its cut's reach"
    for cid, key, stroke in SHORT_STROKES:
        for mult in (1.5, 1.65):
            hit = [r for r in rows if r["file"] == GENRES_FILE and r["concept"] == cid and r["key"] == key and r["stroke"] == stroke
                   and r["style"] == "roman" and r["mult"] == mult]
            assert hit, f"{cid} {key} stroke {stroke} at mult {mult} has no moved-back exhausted edge"
    over = [dict(r, excess=r["pinRun"] - r["lim"] - 1) for r in rows if r["pinRun"] > r["lim"] + 1]
    assert not over, f"CUT-RUN: {len(over)} of {len(rows)} short edges pin more than the near half of their samples; worst {cs.ce.worst(over, 'excess')}"


ACCENTED = "áàâäéèêëíìîïóòôöúùûüÁÀÂÄÉÈÊËÍÏÓÔÖÚÜ"
# The accents whose stroke ends in `t`, so the fixture draws its ends `cut`. The fold check reads only these. The circumflex and
# diaeresis strokes do not end in `t`; on this fixture the circumflexes of Â Ê Ô fold (raw 3.2 to 4.1, decimated up to 11.6) by the
# same figures on 0.12.0 and 0.13.0, from `swell: 0.35` on a very short stroke. That is the face problem the issue #27 request
# put outside this change (the Cane circumflex), so it is not this test's subject (operator's standing ruling, 2026-11-25).
CUT_ACCENTS = "áàéèíìóòúùÁÀÉÈÍÓÚ"
FOLD_SCRIPT = """
const ex = require(process.argv[2] + "/export.js");
const data = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const bad = [], seen = {};
for (const [name, m] of Object.entries(data.masters)) for (const k of process.argv[4]) {
  const g = m.glyphs[k]; if (!g) { bad.push(name + ":" + k + ":missing"); continue; }
  g.raw.forEach((poly, pi) => {
    // the accent stroke's own polygon: every point above y 540. The lowercase accents start at 576 over an x-height of 511;
    // until the build review (F005) the filter was 600 and read only the capitals
    if (!poly.every(q => q[1] > 540)) return;
    seen[name + ":" + k] = (seen[name + ":" + k] || 0) + 1;
    const e = ex.backwardExcursion(poly, g.runs[pi], g.polys[pi], g.keptIdx[pi]);
    if (e.raw > data.foldUnits.raw || e.decimated > data.foldUnits.decimated)
      bad.push(name + ":" + k + " poly " + pi + " raw " + e.raw.toFixed(2) + " dec " + e.decimated.toFixed(2));
  });
}
console.log(JSON.stringify({ bad, seen }));
"""


def make_accent_face(dest):
    """The swelled face (`cs.make_swelled_face`) whose stems draw `serif` ends and whose `t` ends (the acute and grave strokes, and
    every other stroke that ends in `t`) draw `cut` at 32 degrees. The fold of a stem or of `c` or `S` cannot make the accent test red:
    it reads the accent strokes' own contours."""
    cs.make_swelled_face(dest)
    anchor = 'ends: { s: "cut", t: "flare", u: "flare", "": "disk", x: "exit" }, cut: 32 * DEG,'
    text = (dest / "concepts.js").read_text(encoding="utf-8")
    assert text.count(anchor) == 2, f"the face's concepts.js holds {anchor!r} {text.count(anchor)} times, expected twice"
    (dest / "concepts.js").write_text(text.replace(anchor, 'ends: { s: "serif", t: "cut", u: "flare", "": "disk", x: "exit" }, cut: 32 * DEG,'), encoding="utf-8")


def test_a_face_with_cut_accents_exports_without_a_folded_edge(tmp_path):
    """Two modules, `gen.js` into `export.js` (the exporter's own fold function, reused through its module.exports): the accent fixture.
    The roman group has 4 masters, the acute and grave accents hold an end drawn cut, and the contour of no cut accent stroke has a
    folded edge. Fails on the accent contours at CUT-RUN-ACCENT: before the fix. The master as a whole is not held to zero folded edges
    here: the circumflexes fold for a reason outside this change (see CUT_ACCENTS). The whole-face fold count of a face with cut
    accents is held by test_a_face_with_cut_accents_and_swelled_stems_builds."""
    face = tmp_path / "face"
    make_accent_face(face)
    out = face / "keep" / "export-roman.json"
    r = cs.ce.run([cs.ce.node(), str(cs.ce.SCRIPTS / "export.js"), "--font", str(face / "font.json"), "--group", "roman", str(out)])
    assert r.returncode == 0, f"export.js --group roman exited {r.returncode}:\n{r.stderr[-2000:]}"
    masters = json.loads(out.read_text(encoding="utf-8"))["masters"]
    assert len(masters) == 4, f"the roman export has {len(masters)} masters, expected 4"
    for name, m in masters.items():
        for key in ACCENTED:
            assert key in m["glyphs"], f"{name} has no glyph {key}"
        # the acute and grave accents end in `t`; the circumflex and diaeresis strokes do not, so only some accented glyphs hold a cut end
        cut = [k for k in ACCENTED if any(re.search(r" ends=(cut/|\S*/cut\b)", s) for s in m["glyphs"][k]["sig"])]
        assert len(cut) >= 15 and all(k in cut for k in "áàéèóòúùÁÉ"), f"{name}: only {len(cut)} accented glyphs hold an end drawn cut: {cut}"
    script = tmp_path / "accent_fold.js"
    script.write_text(FOLD_SCRIPT, encoding="utf-8")
    p = cs.ce.run([cs.ce.node(), str(script), str(cs.ce.SCRIPTS), str(out), CUT_ACCENTS])
    assert p.returncode == 0, f"the accent fold script exited {p.returncode}:\n{p.stderr[-2000:]}"
    report = json.loads(p.stdout)
    # the filter above y 540 must find the accent stroke of every cut accent in every master, or the check reads nothing (build review F005)
    unseen = [f"{n}:{k}" for n in masters for k in CUT_ACCENTS if report["seen"].get(f"{n}:{k}", 0) == 0]
    assert not unseen, f"the accent fold script examined no contour of {len(unseen)} cut accents: {unseen[:8]}"
    bad = report["bad"]
    assert not bad, f"CUT-RUN-ACCENT: {len(bad)} accent contours fold back: {bad[:8]}"


def test_a_face_with_cut_accents_and_swelled_stems_builds(tmp_path):
    """The whole tool: `concepts.js` to `export.js` to `build.py`. The swelled face of tests/test_cut_step.py with the `t` end (the end
    the acute and grave strokes use) drawn `cut` too, at the heaviest multiplier the face reaches (1.5). build.py exits 0, every master
    has `foldedEdges` 0 and the accents `á` and `à` hold an end drawn cut. Red on 0.12.0 at CUT-RUN-BUILD: (build.py exits 1, 25 to 29 folded edges per master)."""
    face = tmp_path / "face"
    cs.make_swelled_face(face)
    text = (face / "concepts.js").read_text(encoding="utf-8")
    anchor = 't: "flare"'
    assert text.count(anchor) == 2, f"the face's concepts.js holds {anchor!r} {text.count(anchor)} times, expected twice"
    (face / "concepts.js").write_text(text.replace(anchor, 't: "cut"'), encoding="utf-8")
    r = cs.ce.run([cs.ce.sys.executable, str(cs.ce.SCRIPTS / "build.py"), "--font", str(face / "font.json"), "--requirements", str(face / "requirements.json"),
                   "--keep-masters", str(face / "keep" / "export.json")])
    assert r.returncode == 0, f"CUT-RUN-BUILD: build.py exited {r.returncode}:\n{r.stderr[-2000:]}"
    kept = sorted((face / "keep").glob("export-*.json"))
    assert kept, f"build.py kept no export under {face / 'keep'}"
    for path in kept:
        for name, m in json.loads(path.read_text(encoding="utf-8"))["masters"].items():
            assert m["foldedEdges"] == 0, f"CUT-RUN-BUILD: {path.name}/{name} has {m['foldedEdges']} folded edges, worst at {m['worstFoldAt']}"
            for key in "áà":
                sigs = m["glyphs"][key]["sig"]
                assert any(re.search(r" ends=(cut/|\S*/cut\b)", s) for s in sigs), f"CUT-RUN-BUILD: {path.name}/{name} {key} holds no end drawn cut: {sigs}"
