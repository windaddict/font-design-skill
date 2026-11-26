"""A `cut` end puts the corner it shortens on the stroke's own edge (0.13.0, issue #27).

WHAT IT'S FOR: scripts/gen.js 0.12.0 draws a `cut` end by moving each of the end's two corners along the end tangent onto the cut
line. That is the stroke's edge only on a straight stroke of even width. On a curved terminal, and on a straight stroke whose edges a
large `swell` curves, the corner that moves back stands off the edge and the outline jumps from the edge to the corner: a step. On a
swelled stem the exporter counts the step as a folded edge, so build.py refuses the face. These tests hold the fix to what a reader of
the outlines would check. The plan is docs/plan-cut-curved-step.md; each test names its first assertion about the new behaviour by a
marker in capitals (CUT-STEP:, CUT-STEP-SWELL:, CUT-SWELL-FOLD:, CUT-SWELL-BUILD:), the message that test fails on against the 0.12.0
generator. The assertions before a marker are coverage checks, so a probe that measures nothing cannot pass.

How the measure works. tests/cut_end_probe.js (its header defines every figure) draws every glyph twice, with the concept's `cut` ends
and with every `cut` end replaced by `butt`, and reports one row per EDGE of each stroke end that stayed a `cut` end. Used here:
`back` (the cut moved the corner back along the stroke) and `off` (the distance from that corner to the edge the uncut stroke draws;
0 means the corner is on the edge). The helpers `all_rows`, `swell_rows` and `make_swelled_face` are shared with the other cut test
files. The swelled fixture is the `grot` recipe of templates/concepts.genres.js drawn with `swell` 0.35 and `cut` ends at 32 degrees,
passed to the probe as `spec.patch`.

FONT_DESIGN_CUT_SCRIPTS names another copy of the whole scripts/ folder (see tests/test_cut_ends.py); unset, the real one.
"""
import functools
import json
import re

import test_cut_ends as ce  # the probe runner, the Cane concept, the shipped rows and the face helper

TOL = ce.TOL
GENRES = ce.REPO / "templates" / "concepts.genres.js"
SWELL_PATCH = {"swell": 0.35, "cut": 32 * ce.DEG, "ends": {"s": "cut", "t": "cut", "u": "cut", "": "disk", "x": "exit"}}


@functools.lru_cache(maxsize=None)
def swell_rows():
    """The `ends` rows of the swelled fixture: the genres `grot` recipe with `SWELL_PATCH`, roman and italic, four multipliers."""
    return ce._probe("ends", ce.spec_json(files=[str(GENRES)], only="grot", patch=SWELL_PATCH, mults=ce.MULTS, styles=ce.STYLES))


@functools.lru_cache(maxsize=None)
def all_rows():
    """Every row of the shipped concepts, the Cane concept and the swelled fixture, each copy tagged with `set`: "shipped", "cane" or
    "swell" (the swelled fixture and the genres `grot` share a file and a concept id, so a test that groups rows needs it)."""
    out = []
    for name, rows in (("shipped", ce.shipped_rows()), ("cane", ce.cane_rows()), ("swell", swell_rows())):
        out.extend(dict(r, set=name) for r in rows)
    return out


def make_swelled_face(dest):
    """`ce.make_face(dest)` (a copy of examples/neutral with `cut` stem ends at 32 degrees) with `swell: 0.35` in both concepts. The
    swell thins the middle of a stroke to 44.5 to 63.1 units, under the neutral hairline floors, and the woff2 grows to 106,396 bytes,
    over the neutral size budget of 102,400. Neither is the defect under test, and on 0.12.0 the build stops at the fold check before
    either, so the floors drop to 75 percent and the budget rises to 131072 in both files that carry them."""
    ce.make_face(dest)
    text = (dest / "concepts.js").read_text(encoding="utf-8")
    assert text.count("swell: 0.02,") == 2, f"examples/neutral/concepts.js: 'swell: 0.02,' occurs {text.count('swell: 0.02,')} times, expected twice"
    (dest / "concepts.js").write_text(text.replace("swell: 0.02,", "swell: 0.35,"), encoding="utf-8")

    def relax(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "hairline_floors":
                    node[k] = {n: int(x * 0.75) for n, x in v.items()}
                elif k == "size_budget_bytes":
                    node[k] = 131072
                else:
                    relax(v)
        elif isinstance(node, list):
            for v in node:
                relax(v)
    for name in ("font.json", "requirements.json"):
        data = json.loads((dest / name).read_text(encoding="utf-8"))
        relax(data)
        (dest / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _off(rows):
    return [r for r in rows if r["back"] and r["off"] > TOL]


# --- 1 and 2: the corner is on the edge --------------------------------------------------------------------------------------------

def test_a_cut_corner_that_moved_back_lies_on_the_strokes_edge_in_every_shipped_concept():
    """One module (`glyph()` of gen.js): the six shipped concepts with a `cut` end, roman and italic, four multipliers. No edge whose
    corner the cut moved back has that corner more than 0.05 units off the edge the uncut stroke draws. Red on 0.12.0 at CUT-STEP:
    2,879 of 3,952, worst 113.42 units (`grot` roman `f` at 1.65)."""
    rows = ce.shipped_rows()
    assert len(rows) >= 9000, f"only {len(rows)} edge rows were measured in the shipped concepts"
    back = [r for r in rows if r["back"]]
    assert len(back) >= 3500, f"only {len(back)} shipped edges have a corner the cut moved back"
    for fl, cid in sorted(ce.shipped_pairs()):
        n = len([r for r in back if r["file"] == fl and r["concept"] == cid])
        assert n >= 500, f"{fl} {cid}: only {n} edges with a corner the cut moved back"
    for cid in ("grot", "geometric"):
        for style, keys in (("roman", "csea" + "ftr9"), ("italic", "csef" + "tr9")):
            for key in keys:
                for mult in (1, 1.5, 1.65):
                    hit = [r for r in back if r["file"] == "templates/concepts.genres.js" and r["concept"] == cid
                           and r["style"] == style and r["key"] == key and r["mult"] == mult]
                    assert hit, f"{cid} {style} {key} at mult {mult} has no edge with a corner the cut moved back"
    bad = _off(rows)
    assert not bad, (f"CUT-STEP: {len(bad)} of {len(back)} corners the cut moved back stand more than {TOL} off the stroke's edge; "
                     f"worst {ce.worst(bad, 'off')}")


def test_a_cut_corner_lies_on_the_edge_of_a_swelled_straight_stroke():
    """One module: the Cane concept and the swelled fixture (`SWELL_PATCH`), which draw straight stems whose edges a large swell curves.
    The same measure. Red on 0.12.0 at CUT-STEP-SWELL: 2,623 of 2,635, worst 150.73 (swelled fixture, italic `?` at 1.65)."""
    cane, swell = ce.cane_rows(), swell_rows()
    cane_back = [r for r in cane if r["back"]]
    swell_back = [r for r in swell if r["back"]]
    assert len(cane_back) >= 850, f"only {len(cane_back)} Cane edges have a corner the cut moved back"
    assert len(swell_back) >= 1500, f"only {len(swell_back)} swelled edges have a corner the cut moved back"
    for key in "xXY7k":
        hit = [r for r in swell_back if r["style"] == "roman" and r["mult"] == 1 and r["key"] == key and r["reach"] > 20]
        assert hit, f"the swelled roman {key} at mult 1 has no moved-back edge with a reach over 20 units"
    rows = cane_back + swell_back
    bad = _off(rows)
    assert not bad, (f"CUT-STEP-SWELL: {len(bad)} of {len(rows)} corners the cut moved back stand more than {TOL} off the stroke's edge "
                     f"on a swelled or Cane stroke; worst {ce.worst(bad, 'off')}")


# --- 3 and 4: a face with swelled cut stems ----------------------------------------------------------------------------------------

def test_a_face_with_swelled_cut_stem_ends_exports_without_a_folded_edge(tmp_path):
    """Two modules, `gen.js` into `export.js` (the exporter's own fold measure, master compatibility and decimation): the swelled
    face. The roman group has 4 masters and the italic group 2, each draws at least 50 glyphs with a cut end, and none has a folded
    edge. Red on 0.12.0 at CUT-SWELL-FOLD: 7, 4, 3 and 4 folded edges in the roman masters, 3 and 14 in the italic ones."""
    face = tmp_path / "face"
    make_swelled_face(face)
    exports = {}
    for group, n_masters in (("roman", 4), ("italic", 2)):
        out = face / "keep" / f"export-{group}.json"
        r = ce.run([ce.node(), str(ce.SCRIPTS / "export.js"), "--font", str(face / "font.json"), "--group", group, str(out)])
        assert r.returncode == 0, f"export.js --group {group} exited {r.returncode}:\n{r.stderr[-2000:]}"
        exports[group] = json.loads(out.read_text(encoding="utf-8"))["masters"]
        assert len(exports[group]) == n_masters, f"the {group} export has {len(exports[group])} masters, expected {n_masters}"
        for name, m in exports[group].items():
            with_cut = [k for k, g in m["glyphs"].items() if any(re.search(r" ends=(cut/|\S*/cut\b)", s) for s in g["sig"])]
            assert len(with_cut) >= 50, f"{group}/{name}: only {len(with_cut)} glyphs hold an end drawn cut"
    folded = [(g, n, m["foldedEdges"], m["worstFoldAt"]) for g, ms in exports.items() for n, m in ms.items() if m["foldedEdges"] != 0]
    assert not folded, "CUT-SWELL-FOLD: " + "; ".join(f"{g}/{n}: {c} folded edges, worst at {w}" for g, n, c, w in folded)


def test_a_face_with_swelled_cut_stem_ends_builds(tmp_path):
    """The whole tool: concepts.js to export.js to build.py to the woff2 files, with the builder's self-checks, for the swelled face.
    Red on 0.12.0 at CUT-SWELL-BUILD: build.py exits 1 with `SELF-CHECK FAILED: TextRegular: 7 stroke edge(s) fold back`."""
    face = tmp_path / "face"
    make_swelled_face(face)
    r = ce.run([ce.sys.executable, str(ce.SCRIPTS / "build.py"), "--font", str(face / "font.json"), "--requirements", str(face / "requirements.json"),
                "--keep-masters", str(face / "keep" / "export.json")])
    assert r.returncode == 0, f"CUT-SWELL-BUILD: build.py exited {r.returncode}:\n{r.stderr[-2000:]}"
    out = face / "out"
    woff2 = sorted(p.name for p in out.rglob("*.woff2"))
    assert len(woff2) >= 2, f"build.py wrote {len(woff2)} woff2 files under {out}: {woff2}"
    assert any(p.name == "manifest.json" for p in out.rglob("manifest.json")), f"no manifest.json under {out}"
