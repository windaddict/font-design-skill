"""The configuration contracts hold for every example, and every concept the repo ships is one the
generator accepts.

WHAT IT'S FOR: font.json and the export JSON are the two contracts between the scripts (review
finding F014 fixed them before anything else was written). An example that drifts from the schema
would teach a new project a shape the scripts reject. A concept that params() refuses (the dead
flareAmt beside tear:true) would fail the first build a user runs from the example. Each is checked
by executing the real code: jsonschema over the files, node over the concepts, and export.js over
every group of every example.
"""
import json
import pathlib
import shutil

import jsonschema
import pytest
from conftest import REPO, node, run

EXAMPLES = sorted(p for p in (REPO / "examples").iterdir() if p.is_dir())
FONT_SCHEMA = json.loads((REPO / "templates" / "font.schema.json").read_text())
EXPORT_SCHEMA = json.loads((REPO / "templates" / "export.schema.json").read_text())


def test_the_schemas_are_valid_schemas():
    jsonschema.Draft202012Validator.check_schema(FONT_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(EXPORT_SCHEMA)


@pytest.mark.parametrize("font_json", [p / "font.json" for p in EXAMPLES] + [REPO / "templates" / "font.example.json"],
                         ids=lambda p: p.parent.name + "/" + p.name)
def test_every_font_json_validates(font_json):
    jsonschema.validate(json.loads(font_json.read_text()), FONT_SCHEMA)


def test_the_font_schema_rejects_a_group_with_one_master(tmp_path):
    """A negative fixture: a variable font needs two masters; the schema must refuse one."""
    cfg = json.loads((REPO / "examples" / "neutral" / "font.json").read_text())
    cfg["groups"]["roman"]["masters"] = {"Only": cfg["groups"]["roman"]["masters"]["TextRegular"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(cfg, FONT_SCHEMA)
    cfg2 = json.loads((REPO / "examples" / "neutral" / "font.json").read_text())
    cfg2["unexpected_key"] = 1
    with pytest.raises(jsonschema.ValidationError, match="unexpected_key"):
        jsonschema.validate(cfg2, FONT_SCHEMA)


def concepts_files():
    return sorted((REPO / "examples").glob("*/concepts.js")) + [REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]


@pytest.mark.parametrize("concepts", concepts_files(), ids=lambda p: p.parent.name + "/" + p.name)
def test_every_concept_passes_params(concepts):
    script = (
        "const m = require(process.argv[1]); const list = m.loadConcepts(process.argv[2]);"
        "for (const c of list) { m.params(c, 1); m.params(c, 1.5); if (c.ends && c.ends.x) m.params(c, 1, true); }"
        "console.log(list.length);"
    )
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(concepts)])
    assert r.returncode == 0, r.stderr
    assert int(r.stdout.strip()) >= 1


def test_params_refuses_the_dead_flare_knob_and_names_the_fix():
    """Issue 24 on Driftwood: flareAmt did nothing with teardrop terminals and a review round tuned
    it for no effect. The generator now refuses the combination and names dropAmt."""
    script = (
        "const m = require(process.argv[1]); const c = m.loadConcepts(process.argv[2])[0];"
        "try { m.params(Object.assign({}, c, { tear: true, flareAmt: 0.3 }), 1); console.log('no throw'); }"
        "catch (e) { console.log(e.message); }"
    )
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    assert "flareAmt" in r.stdout and "dropAmt" in r.stdout and "no throw" not in r.stdout, r.stdout


def test_drop_amt_changes_the_teardrop_and_flare_amt_changes_the_flare():
    """The two terminal knobs each do something: dropAmt moves outline points of a tear:true cut,
    flareAmt moves points of a tear:false cut. A knob that moves nothing is the defect issue 24 named."""
    script = r"""
const m = require(process.argv[1]);
const base = { id: "b", W: 96, nib: 0.2, thin: 0.44, pow: 1.5, xs: 0.9, swell: 0.03, track: 0,
  ends: { s: "serif", t: "flare", u: "flareS", "": "disk", x: "exit" }, flareLen: 90, serifLen: 0.75, serifH: 0.5, dot: 0.5, overshoot: 10, beak: true };
function pts(c) { const g = m.glyph("c", m.params(c, 1)); return g.polys.flat().map(p => p.join(",")).join(";"); }
const tearA = pts(Object.assign({}, base, { id: "t1", tear: true })), tearB = pts(Object.assign({}, base, { id: "t2", tear: true, dropAmt: 0.9 }));
const flareA = pts(Object.assign({}, base, { id: "f1", tear: false, flareAmt: 0.1 })), flareB = pts(Object.assign({}, base, { id: "f2", tear: false, flareAmt: 0.4 }));
console.log(JSON.stringify({ drop: tearA !== tearB, flare: flareA !== flareB }));
"""
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js")])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out == {"drop": True, "flare": True}, out


TEARDROP_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { tear: true }); delete base.flareAmt; delete base.dropAmt;
function draw(drop) {
  const P = m.params(Object.assign({}, base, { id: base.id + "|drop" + drop, dropAmt: drop }), 1), out = {};
  for (const k of Object.keys(m.G)) { const g = m.glyph(k, P); if (g) out[k] = g; }
  return out;
}
const G = [draw(0), draw(0.55), draw(1.1)];
// one stroke per teardrop kind, found from the branch record "tear=A/B" (A, B in L, R, S or null)
const want = {};
for (const k of Object.keys(G[0])) {
  let open = 0;
  G[0][k].sig.forEach(s => {
    if (!s.startsWith("open")) return;
    const mm = s.match(/tear=(\w+)\/(\w+)/);
    if (mm) for (const [end, kind] of [["A", mm[1]], ["B", mm[2]]]) {
      if ("LRS".includes(kind) && kind.length === 1 && !want[kind]) want[kind] = { glyph: k, open, end, other: end === "A" ? mm[2] : mm[1] };
    }
    open++;
  });
}
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function edges(g, open) {
  // the open-th polygon with two edge runs is that stroke's body; runs[0] is always the left edge's run
  let seen = 0, pi = -1;
  for (let i = 0; i < g.polys.length; i++) if (g.runs[i].length === 2) { if (seen === open) { pi = i; break; } seen++; }
  const poly = g.polys[pi], runs = g.runs[pi], n = runs[0][1] - runs[0][0] + 1, flipped = runs[0][0] !== 0;
  return { n, L: i => flipped ? poly[runs[0][1] - i] : poly[runs[0][0] + i], R: i => flipped ? poly[runs[1][0] + i] : poly[runs[1][1] - i] };
}
const out = {};
for (const kind of ["L", "R", "S"]) {
  const w = want[kind];
  if (!w) { out[kind] = null; continue; }
  const e = G.map(g => edges(g[w.glyph], w.open)), n = e[0].n;
  // the glyph's sidebearing shifts with its extents, so every build is re-aligned on a reference sample
  // that no teardrop reaches: the far end when it has none, else the middle of the stroke
  const r = w.other === "null" ? (w.end === "A" ? n - 1 : 0) : Math.floor(n / 2);
  const shift = e.map(ed => [ed.L(r)[0] - e[0].L(r)[0], ed.L(r)[1] - e[0].L(r)[1]]);
  const refWidths = e.map(ed => dist(ed.L(r), ed.R(r)));
  // eight samples in from the end: inside the teardrop zone, clear of the cap; skip a sample the fold pin
  // touched (a pinned point equals its predecessor) in any build
  let s = w.end === "A" ? 8 : n - 1 - 8;
  const pinned = i => e.some(ed => dist(ed.L(i), ed.L(i - 1)) < 1e-9 || dist(ed.R(i), ed.R(i - 1)) < 1e-9);
  for (let tries = 0; tries < 12 && pinned(s); tries++) s += w.end === "A" ? 1 : -1;
  const al = (d, p) => [p[0] - shift[d][0], p[1] - shift[d][1]];
  const C = [(e[0].L(s)[0] + e[0].R(s)[0]) / 2, (e[0].L(s)[1] + e[0].R(s)[1]) / 2];
  const dL = d => dist(al(d, e[d].L(s)), C) - dist(e[0].L(s), C), dR = d => dist(al(d, e[d].R(s)), C) - dist(e[0].R(s), C);
  out[kind] = { glyph: w.glyph, end: w.end, sample: s, n, refWidths, width0: dist(e[0].L(s), e[0].R(s)),
    dL55: dL(1), dL110: dL(2), dR55: dR(1), dR110: dR(2), pinned: pinned(s) };
}
console.log(JSON.stringify(out));
"""

def check_teardrop_scaling(out):
    """Shared assertions for the L, R and S teardrop cases (review finding F005 of the skill plan). At a
    sample eight steps inside the teardrop zone, re-aligned for the sidebearing shift and clear of the
    fold pin: the outer edge swells by 0.55 and the inner edge thins by 0.28 of the stroke's half-width
    times the same smoothstep, so outer/inner = 55/28; the symmetric (S) case moves both edges equally;
    and every displacement doubles from dropAmt 0.55 to 1.1, because the knob is linear. Measured in
    the test from the polygons, not from the generator's formula."""
    for kind in "LRS":
        assert out[kind], f"no stroke with a {kind} teardrop end in the branch records"
    L, R, S = out["L"], out["R"], out["S"]
    for d in (L, R, S):
        assert not d["pinned"], f"{d['glyph']}: the sample is on a pinned point"
        assert max(d["refWidths"]) - min(d["refWidths"]) < 1e-6, f"{d['glyph']}: the reference sample moved; the re-alignment is wrong"
    want = 55 / 28
    assert L["dL55"] > 0 and L["dR55"] < 0, f"L case ({L['glyph']}): outer {L['dL55']:.3f} must swell and inner {L['dR55']:.3f} must thin"
    assert abs(L["dL55"] / -L["dR55"] - want) < 0.02 * want, f"L case: outer/inner is {L['dL55'] / -L['dR55']:.3f}, expected {want:.3f}"
    assert R["dR55"] > 0 and R["dL55"] < 0, f"R case ({R['glyph']}): outer {R['dR55']:.3f} must swell and inner {R['dL55']:.3f} must thin"
    assert abs(R["dR55"] / -R["dL55"] - want) < 0.02 * want, f"R case: outer/inner is {R['dR55'] / -R['dL55']:.3f}, expected {want:.3f}"
    assert S["dL55"] > 0 and S["dR55"] > 0, f"S case ({S['glyph']}): both edges must swell, got {S['dL55']:.3f} / {S['dR55']:.3f}"
    assert abs(S["dL55"] - S["dR55"]) < 1e-6 + 0.005 * S["dL55"], f"S case: the swell is not symmetric: {S['dL55']:.3f} / {S['dR55']:.3f}"
    for d in (L, R, S):
        for edge in ("dL", "dR"):
            assert abs(d[edge + "110"] - 2 * d[edge + "55"]) < 1e-6 + 0.005 * abs(d[edge + "110"]), \
                f"{d['glyph']} {edge}: {d[edge + '55']:.3f} at dropAmt 0.55 but {d[edge + '110']:.3f} at 1.1; the knob is not linear"


def test_dropamt_scales_the_outer_inner_and_symmetric_teardrop():
    """Review finding F005: the three teardrop constants (outer 0.55, inner 0.28, symmetric 0.30) must
    all follow dropAmt. The existing "changes outlines" test above stayed green with dropAmt removed
    from the inner and symmetric cases; this measures each case on the neutral concept with teardrops
    forced on."""
    r = run([node(), "-e", TEARDROP_FIXTURE, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    check_teardrop_scaling(json.loads(r.stdout))


def test_flareamt_scales_the_flare_in_proportion():
    """The flare swell is 1 + flareAmt * u^2 along the stroke's own width, so at one sample the width
    gain at flareAmt 0.4 is four times the gain at 0.1. A knob that moves "something" is not enough
    (the dropAmt mutation above showed why); the proportion is checked, from the polygons."""
    script = r"""
const m = require(process.argv[1]);
const c = Object.assign({}, m.loadConcepts(process.argv[2])[0], { tear: false }); delete c.dropAmt; delete c.flareAmt;
function widths(fa) {
  const P = m.params(Object.assign({}, c, { id: "fl" + fa, flareAmt: fa }), 1);
  for (const k of Object.keys(m.G)) {
    const g = m.glyph(k, P); if (!g) continue;
    let open = 0;
    for (const s of g.sig) {
      if (!s.startsWith("open")) continue;
      if (/ A=flare /.test(s) && / curved=true /.test(s)) {
        let seen = 0, pi = -1;
        for (let i = 0; i < g.polys.length; i++) if (g.runs[i].length === 2) { if (seen === open) { pi = i; break; } seen++; }
        const poly = g.polys[pi], runs = g.runs[pi], fl = runs[0][0] !== 0;
        const L = i => fl ? poly[runs[0][1] - i] : poly[runs[0][0] + i], R = i => fl ? poly[runs[1][0] + i] : poly[runs[1][1] - i];
        return { glyph: k, w: Math.hypot(L(8)[0] - R(8)[0], L(8)[1] - R(8)[1]) };
      }
      open++;
    }
  }
  return null;
}
console.log(JSON.stringify({ w0: widths(0), w1: widths(0.1), w4: widths(0.4) }));
"""
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["w0"] and out["w1"]["glyph"] == out["w0"]["glyph"] == out["w4"]["glyph"], out
    g1, g4 = out["w1"]["w"] - out["w0"]["w"], out["w4"]["w"] - out["w0"]["w"]
    assert g1 > 0.5, f"flareAmt 0.1 widened the end of {out['w0']['glyph']} by only {g1:.3f} units"
    assert abs(g4 / g1 - 4) < 0.02, f"flareAmt 0.4 widened by {g4:.3f}, 0.1 by {g1:.3f}: ratio {g4 / g1:.3f}, expected 4"


def test_editing_a_concept_in_place_redraws_its_glyphs():
    """Review finding C3: the glyph cache was keyed by concept id and a two-decimal multiplier, so a
    concept edited without a new id (the normal way to tune one) and multipliers that round alike
    (1.001 vs 1.004) reused stale outlines inside one process. Draws, edits the same object, draws
    again: the outlines must differ, in the same process, for a W change, an ends change and a
    nearby multiplier."""
    script = r"""
const m = require(process.argv[1]);
const c = JSON.parse(JSON.stringify(m.loadConcepts(process.argv[2])[0]));
const draw = (concept, mult) => JSON.stringify(m.glyph("n", m.params(concept, mult)).polys);
const a = draw(c, 1);
c.W = c.W + 7;                       // same id, same object, one knob changed
const b = draw(c, 1);
c.ends = Object.assign({}, c.ends, { s: "flare" });
const d = draw(c, 1);
const e = draw(c, 1.001), f = draw(c, 1.004);
console.log(JSON.stringify({ w: a !== b, ends: b !== d, mult: e !== f }));
"""
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"w": True, "ends": True, "mult": True}, r.stdout


def test_a_parameter_set_to_null_does_not_share_the_cache_of_one_left_undefined():
    """Re-review finding code-a F001: stable() serialised `undefined` as null, so a concept with
    `dropAmt: undefined` (the default 0.55 applies) and the same concept with `dropAmt: null` (no default:
    dk becomes 0 and the teardrop vanishes) shared one cache key, and the second drew the first's glyphs.
    The keys must differ and a glyph with a teardrop must draw differently. Mutation watched red: stable()
    serialising undefined as null again (the keys are then equal and the glyph objects identical)."""
    fixture = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { tear: true }); delete base.flareAmt;
const Pa = m.params(Object.assign({}, base, { dropAmt: undefined }), 1), Pb = m.params(Object.assign({}, base, { dropAmt: null }), 1);
const differ = Object.keys(m.G).filter(k => { const a = m.glyph(k, Pa), b = m.glyph(k, Pb); return a && b && JSON.stringify(a.polys) !== JSON.stringify(b.polys); });
console.log(JSON.stringify({ sameKey: Pa.key === Pb.key, differ: differ.length, dropA: Pa.dropAmt, dropB: Pb.dropAmt }));
"""
    r = run([node(), "-e", fixture, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")], cwd=REPO / "scripts")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["dropA"] == 0.55 and out["dropB"] is None, out
    assert not out["sameKey"], "dropAmt: undefined and dropAmt: null share a glyph-cache key"
    assert out["differ"] > 0, "no glyph drew differently with dropAmt null (dk 0) than with the default; the cache served stale glyphs"


def test_a_sparse_glyph_does_not_take_the_full_kern_clamp():
    """A cold dry run of the skill saw the hyphen crowd the S in "Eighty-Seventh": the automatic kern
    measures the gap only where both glyphs have ink, and a hyphen has ink at one height, so the
    pair hit the -170 clamp. kern() now caps pairs where either glyph covers under 35 % of the band
    at -50. A pair of full-height glyphs (t y) keeps its full automatic value."""
    script = r"""
const m = require(process.argv[1]); const P = m.params(m.loadConcepts(process.argv[2])[0], 1);
const k = (a, b) => m.kern(m.glyph(a, P), m.glyph(b, P), P);
console.log(JSON.stringify({ hyphenS: k("-", "S"), hyphenY: k("y", "-"), periodT: k(".", "T"), ty: k("t", "y") }));
"""
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(REPO / "examples" / "neutral" / "concepts.js")])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["hyphenS"] >= -50 and out["periodT"] >= -50, out
    assert out["hyphenS"] < 0, "the hyphen still gets some kern toward S"
    assert out["ty"] < -60, f"a full-height pair must keep its automatic kern: {out}"


def all_groups():
    out = []
    for ex in EXAMPLES:
        cfg = json.loads((ex / "font.json").read_text())
        for g in cfg["groups"]:
            out.append((ex, g))
    return out


@pytest.mark.parametrize("example,group", all_groups(), ids=lambda v: v.name if isinstance(v, pathlib.Path) else v)
def test_every_example_group_exports_and_matches_the_export_schema(example, group, tmp_path):
    """Executes export.js: the masters of every group of every example must be interpolation-
    compatible (the exporter exits 1 otherwise) and the JSON must match the contract build.py reads."""
    out = tmp_path / f"{example.name}-{group}.json"
    req = example / "requirements.json"
    cmd = [node(), str(REPO / "scripts" / "export.js"), "--font", str(example / "font.json"), "--group", group, str(out)]
    if req.exists():
        cmd[-1:-1] = ["--requirements", str(req)]
    r = run(cmd)
    assert r.returncode == 0, r.stderr[-2000:]
    data = json.loads(out.read_text())
    jsonschema.validate(data, EXPORT_SCHEMA)
    assert data["group"] == group and data["family"] == json.loads((example / "font.json").read_text())["family"]
    for name, master in data["masters"].items():
        assert master["foldedEdges"] == 0, f"{example.name}/{group}/{name}: {master['worstFoldAt']}"
    assert "folded edges" in r.stderr


def test_export_fails_early_naming_a_required_character_the_generator_lacks(tmp_path):
    """Review finding F011: a character the skeleton table lacks used to surface only as a missing
    glyph in the built font. The exporter now refuses before drawing, naming the code point."""
    req = tmp_path / "req.json"
    req.write_text(json.dumps({"required_characters": "Abc@"}))
    r = run([node(), str(REPO / "scripts" / "export.js"), "--font", str(REPO / "examples" / "neutral" / "font.json"), "--group", "roman",
             "--requirements", str(req), str(tmp_path / "out.json")])
    assert r.returncode == 1, r.stderr
    assert "U+0040" in r.stderr and '"@"' in r.stderr, r.stderr
    assert not (tmp_path / "out.json").exists(), "nothing may be written when a required character is missing"


# ---- kerning.sparse_cap (0.3.1): a face reviewed without the sparse-glyph cap can switch it off ---------------

BRACT = REPO / "examples" / "bract"


def bract_kerns(tmp_path, name, **kerning):
    """Exports a copy of the Bract example's roman group with `kerning` keys overridden (a value of the
    sentinel "DELETE" removes the key) and returns {master: {"a|b": v}}. Executes the real export.js."""
    d = tmp_path / name
    d.mkdir()
    cfg = json.loads((BRACT / "font.json").read_text())
    for k, v in kerning.items():
        if v == "DELETE":
            cfg["kerning"].pop(k, None)
        else:
            cfg["kerning"][k] = v
    shutil.copyfile(BRACT / "concepts.js", d / "concepts.js")
    (d / "font.json").write_text(json.dumps(cfg))
    r = run([node(), str(REPO / "scripts" / "export.js"), "--font", str(d / "font.json"), "--group", "roman", str(d / "out.json")])
    assert r.returncode == 0, r.stderr[-1500:]
    data = json.loads((d / "out.json").read_text())
    return {n: {f"{a}|{b}": v for a, b, v in m["kerns"]} for n, m in data["masters"].items()}


def test_sparse_cap_null_lets_a_sparse_pair_pass_minus_fifty(tmp_path):
    """Bract's kerning was reviewed before the cap existed: at Bold its `.|Y` is -149 and `-|S` -170. With
    kerning.sparse_cap null the export must give exactly those; with the key absent (the default) both sit at
    -50. Two exports in one test, so it is the parameter that is observed, not the default. Mutations watched
    red: export.js stops passing the cap to m.kern; kern() ignores its fourth argument; the default changed
    to null (the absent-key export then reads -149)."""
    off = bract_kerns(tmp_path, "off", sparse_cap=None)["TextBold"]
    default = bract_kerns(tmp_path, "default", sparse_cap="DELETE")["TextBold"]
    assert off[".|Y"] == -149 and off["-|S"] == -170, {k: off[k] for k in (".|Y", "-|S")}
    assert default[".|Y"] == -50 and default["-|S"] == -50, {k: default[k] for k in (".|Y", "-|S")}


def test_the_kern_cache_keys_on_the_cap():
    """kern() caches by glyph pair per parameter set; a cap passed as an argument must be part of that id, or the
    second call in one process returns the first call's value (the class of defect the null-vs-undefined test
    above was written for). Called default, null, default in one process: -50, below -50, -50. Mutation watched
    red: the cap dropped from the cache id (the second call then returns the cached -50). The pair is `.|Y` in
    Bract's text cut, which is -102 uncapped."""
    script = r"""
const m = require(process.argv[1]); const P = m.params(m.loadConcepts(process.argv[2])[0], 1);
const a = m.glyph(".", P), b = m.glyph("Y", P);
console.log(JSON.stringify([m.kern(a, b, P), m.kern(a, b, P, null), m.kern(a, b, P), m.kern(a, b, P, -20)]));
"""
    r = run([node(), "-e", script, str(REPO / "scripts" / "gen.js"), str(BRACT / "concepts.js")])
    assert r.returncode == 0, r.stderr
    first, off, again, tighter = json.loads(r.stdout)
    assert first == -50 and again == -50, (first, again)
    assert off < -50, f"kern(..., null) returned {off}; the cap still applied or the cache answered"
    assert -20 <= tighter < 0, f"kern(..., -20) returned {tighter}"


@pytest.mark.parametrize("value", [10, "off", -50.5, True])
def test_export_refuses_a_malformed_sparse_cap(tmp_path, value):
    """Nothing enforces the schema at run time, so export.js checks the value before drawing: a positive cap would
    quietly clamp every sparse pair to a positive kern. Mutation watched red: the check removed (10 then exports)."""
    cfg = json.loads((REPO / "examples" / "neutral" / "font.json").read_text())
    cfg["kerning"]["sparse_cap"] = value
    shutil.copyfile(REPO / "examples" / "neutral" / "concepts.js", tmp_path / "concepts.js")
    (tmp_path / "font.json").write_text(json.dumps(cfg))
    r = run([node(), str(REPO / "scripts" / "export.js"), "--font", str(tmp_path / "font.json"), "--group", "roman", str(tmp_path / "o.json")])
    assert r.returncode != 0, f"sparse_cap {value!r} exported"
    assert "kerning.sparse_cap" in r.stderr, r.stderr[-500:]
    assert not (tmp_path / "o.json").exists()


def test_the_schema_accepts_null_and_rejects_a_positive_sparse_cap():
    """The schema says what export.js enforces. Mutation watched red: `maximum` removed (10 then validates)."""
    cfg = json.loads((REPO / "examples" / "neutral" / "font.json").read_text())
    for ok in (None, -50, 0):
        cfg["kerning"]["sparse_cap"] = ok
        jsonschema.validate(cfg, FONT_SCHEMA)
    for bad in (10, "off", -50.5):
        cfg["kerning"]["sparse_cap"] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(cfg, FONT_SCHEMA)
