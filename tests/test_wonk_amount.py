"""wonkAmount sets how far the `wonk` letters lean back, is refused outside 0 to 0.2, and is honoured end to end (0.12.0).

WHAT IT'S FOR: `scripts/gen.js` leans every letter a concept names in `wonk` by a fixed `x -= 0.045 * y` (about 2.6 degrees). A face
that wants a range of lean on a variable-font axis needs that number per master, so a concept setting, `wonkAmount`, carries it
(default 0.045, refused outside 0 to 0.2). These six tests hold the setting from the outside, at six levels: the drawn lean of a stem
(across params(), xf() and glyph()), the refusal of a bad value (params()), two masters that differ only in the amount through the
exporter, the exporter's refusal of a serif concept whose masters stand either side of the serif threshold (the limit the
documentation states), a face built to woff2 with a weight axis and a lean axis, and the font suite's own headSink fixture on a face
whose first concept sets a steep lean. The plan is .claude/plans/wonk-amount-setting.md (docs/plan-wonk-amount.md once released).

How the measures work. Nothing is computed from the generator's source. tests/wonk_amount_probe.js (its header defines every
figure) draws glyphs and reports each one; the lean of a stem is `(x1 - x0) / (y1 - y0)` of two points of its centre line, found from
the output polygons. The expected lean, `-amount x xs x (1 + 0.16 (mult - 1))`, is restated from references/generator.md section 4,
and the default 0.045 is restated here, not imported, so a change to the constant fails a test instead of following it.

FONT_DESIGN_WONK_SCRIPTS names another copy of the whole scripts/ folder, with a copy of VERSION beside it (a scratch copy carrying
one mutation, for the watches in the plan's Verification section); unset, the real one.
"""
import importlib.util as _ilu
import json
import os
import pathlib
import pathlib as _pl
import shutil
import subprocess
import sys

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
node = _mod.node
run = _mod.run

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_WONK_SCRIPTS", REPO / "scripts"))
GEN = SCRIPTS / "gen.js"
PROBE = REPO / "tests" / "wonk_amount_probe.js"
NEUTRAL = REPO / "examples" / "neutral"
BRACT = REPO / "examples" / "bract"
DRIFTWOOD = REPO / "examples" / "driftwood"
DEFAULT_LEAN = 0.045  # restated, not imported: the lean every version up to 0.11.0 drew


def probe(mode, spec):
    r = run([node(), str(PROBE), str(GEN), mode, json.dumps(spec)])
    assert r.returncode == 0, f"wonk_amount_probe.js {mode} exited {r.returncode}:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout)


def lean_of(rec):
    """The lean of the stem the record's centre line describes: dx / dy between its two centre points."""
    (x0, y0), (x1, y1) = rec["centre"]
    return (x1 - x0) / (y1 - y0)


def expected_lean(amount, xs, mult):
    return -amount * xs * (1 + 0.16 * (mult - 1))


def pick(draws, key, mult, amount):
    found = [d for d in draws if d["key"] == key and float(d["mult"]) == mult and d["amount"] == amount]
    assert len(found) == 1, f"expected one draw of {key!r} at mult {mult}, amount {amount!r}; found {len(found)}"
    return found[0]


def concept_xs(file, cid):
    for c in probe("concepts", {"files": [str(file)]}):
        if c["id"] == cid:
            return c["xs"]
    raise AssertionError(f"no concept {cid} in {file}")


def mean_spread(poly):
    """Mean x of the points above y 700 minus the mean x of the points below y 40: the lean of a tall stem as a displacement."""
    hi = [p[0] for p in poly if p[1] > 700]
    lo = [p[0] for p in poly if p[1] < 40]
    assert hi and lo, f"no points above y 700 ({len(hi)}) or below y 40 ({len(lo)}) in the polygon"
    return sum(hi) / len(hi) - sum(lo) / len(lo)


def write_face(tmp_path, example, concept_id, wonk_all, masters, axes, instances=None, **font_extra):
    """A one-group face in tmp_path: the example's font.json with `groups` replaced by one group `roman`, and a concepts.js that
    requires the example's concepts file and exports two copies of one concept, ids `lo` and `hi`, both leaning every key, with
    wonkAmount 0 and 0.2. `masters` is {name: (concept, mult, location)}; `axes` the group's axes."""
    face = tmp_path / "face"
    face.mkdir()
    cfg = json.loads((example / "font.json").read_text(encoding="utf-8"))
    cfg["groups"] = {"roman": {
        "italic": False,
        "axes": axes,
        "masters": {n: {"concept": c, "mult": m, "location": loc} for n, (c, m, loc) in masters.items()},
        "instances": instances or [{"name": "Regular", "location": next(iter(masters.values()))[2]}],
        "hairline_floors": {n: 20 for n in masters},
    }}
    for k, v in font_extra.items():
        cfg[k] = v
    cfg["concepts"] = "concepts.js"
    (face / "font.json").write_text(json.dumps(cfg), encoding="utf-8")
    (face / "concepts.js").write_text(
        "var base = require(" + json.dumps(str(example / "concepts.js")) + ");\n"
        "var src = base.filter(function (c) { return c.id === " + json.dumps(concept_id) + "; })[0];\n"
        "function copy(id, amount) { return Object.assign({}, src, { id: id, wonk: " + json.dumps(wonk_all) + ", wonkAmount: amount }); }\n"
        "module.exports = [copy('lo', 0), copy('hi', 0.2)];\n", encoding="utf-8")
    return face


def all_keys():
    return "".join(probe("keys", {}))


LEAN_AXIS = [{"tag": "LEAN", "name": "Lean", "min": 0, "default": 0, "max": 100}]
LEAN_MASTERS = {"Upright": ("lo", 1, {"LEAN": 0}), "Leaning": ("hi", 1, {"LEAN": 100})}


def export_pair(tmp_path, example, concept_id):
    face = write_face(tmp_path, example, concept_id, all_keys(), LEAN_MASTERS, LEAN_AXIS)
    out = face / "export.json"
    r = run([node(), str(SCRIPTS / "export.js"), "--font", str(face / "font.json"), str(out)])
    return r, out


def test_wonkamount_sets_how_far_a_named_glyph_leans():
    """Across functions (params(), xf(), glyph()): Bract `bine` (no serif end, no swell, xs 0.98) with wonk "lIH", amounts unset, 0,
    0.045, 0.1, 0.158 and 0.2 at mult 1 and 1.5. The lean of `l`, `I` and `H` is -amount x xs x (1 + 0.16 (mult - 1)) within 1e-9,
    and `o` and `n`, which wonk does not name, are drawn as with wonk empty at every amount."""
    file = BRACT / "concepts.js"
    amounts = ["undef", 0, 0.045, 0.1, 0.158, 0.2]
    spec = {"file": str(file), "id": "bine", "set": {"wonk": "lIH"}, "amounts": amounts, "styles": ["roman"], "mults": [1, 1.5],
            "keys": ["l", "I", "H", "o", "n"]}
    draws = probe("draw", spec)
    plain = probe("draw", dict(spec, set={"wonk": ""}))
    xs = concept_xs(file, "bine")
    assert xs == 0.98, f"the bine concept's xs is {xs}, not the 0.98 this test restates"
    for mult in (1, 1.5):
        for k in ("l", "I", "H"):
            assert pick(draws, k, mult, "undef")["centre"] is not None, f"{k!r} at mult {mult} reports no stroke body, so its lean cannot be read"
        got = lean_of(pick(draws, "l", mult, "undef"))
        want = -DEFAULT_LEAN * xs * (1 + 0.16 * (mult - 1))
        assert abs(got - want) < 1e-9, f"WONK-MEASURE-CONTROL: with no wonkAmount, `l` at mult {mult} leans {got}, not {want}"
    for amount in (0.158, 0, 0.1, 0.2, 0.045):
        for mult in (1, 1.5):
            for k in ("l", "I", "H"):
                got = lean_of(pick(draws, k, mult, amount))
                want = expected_lean(amount, xs, mult)
                assert abs(got - want) < 1e-9, f"WONK-AMOUNT-LEAN: {k!r} at wonkAmount {amount}, mult {mult} leans {got}, not {want}"
    for amount in amounts:
        for mult in (1, 1.5):
            for k in ("o", "n"):
                a, b = pick(draws, k, mult, amount), pick(plain, k, mult, "undef")
                for f in ("pHash", "adv", "L", "R"):
                    assert a[f] == b[f], f"WONK-SCOPE: {k!r} (not named in wonk) at wonkAmount {amount}, mult {mult} differs from the same concept with wonk empty in {f}"


REFUSAL_BAD = [
    ("-0.01", {"value": -0.01}, "number:-0.01"), ("0.2000001", {"value": 0.2000001}, "number:0.2000001"),
    ("0.21", {"value": 0.21}, "number:0.21"), ("1", {"value": 1}, "number:1"), ("string 0.1", {"value": "0.1"}, "string:0.1"),
    ("null", {"value": None}, "object:null"), ("true", {"value": True}, "boolean:true"), ("false", {"value": False}, "boolean:false"),
    ("[0.1]", {"value": [0.1]}, "object:0.1"), ("{}", {"value": {}}, "object:[object Object]"),
    ("NaN", {"token": "NaN"}, "number:NaN"), ("Infinity", {"token": "Infinity"}, "number:Infinity"),
    ("-Infinity", {"token": "-Infinity"}, "number:-Infinity"),
]
REFUSAL_GOOD = [
    ("0", {"value": 0}, "number:0"), ("0.045", {"value": 0.045}, "number:0.045"), ("0.1", {"value": 0.1}, "number:0.1"),
    ("0.2", {"value": 0.2}, "number:0.2"), ("undefined", {"token": "undefined"}, "undefined:undefined"),
    ("absent", {"token": "absent"}, "absent"),
]


def test_wonkamount_outside_its_range_is_refused():
    """Unit (params()): -0.01, 0.2000001, 0.21, 1, "0.1", null, true, false, [0.1], {}, NaN, Infinity and -Infinity are refused with a
    message that names wonkAmount, the concept, the range and the documentation section; 0, 0.045, 0.1, 0.2, undefined and an absent
    key are accepted. The cases are written here, not read from the generator, and each is shown delivered as meant."""
    cases = [dict(label=lab, **body) for lab, body, _ in REFUSAL_BAD + REFUSAL_GOOD]
    out = {r["label"]: r for r in probe("refusals", {"file": str(BRACT / "concepts.js"), "id": "bine", "cases": cases})}
    for lab, _, delivered in REFUSAL_BAD + REFUSAL_GOOD:
        assert out[lab]["delivered"] == delivered, f"WONK-DELIVERED: case {lab!r} reached params() as {out[lab]['delivered']!r}, not {delivered!r}"
    for lab, _, _ in REFUSAL_BAD:
        assert out[lab]["message"] is not None, f"WONK-AMOUNT-REFUSED: params() accepted wonkAmount {lab} (delivered {out[lab]['delivered']})"
    for lab, _, _ in REFUSAL_BAD:
        msg = out[lab]["message"]
        for part in ("wonkAmount", "bine", "it must be a number from 0 to 0.2", "references/generator.md, section 4"):
            assert part in msg, f"WONK-REFUSAL-MESSAGE: the refusal of {lab} lacks {part!r}: {msg}"
    for lab, word in (("NaN", "NaN"), ("Infinity", "Infinity"), ("-Infinity", "Infinity")):
        assert word in out[lab]["message"], f"WONK-REFUSAL-MESSAGE: the refusal of {lab} does not name the value {word}: {out[lab]['message']}"
    for lab, _, _ in REFUSAL_GOOD:
        assert out[lab]["message"] is None, f"WONK-AMOUNT-ALLOWED: params() refused wonkAmount {lab}: {out[lab]['message']}"


NO_SERIF = [(BRACT, "bine"), (DRIFTWOOD, "tideline"), (DRIFTWOOD, "dune")]


def test_two_masters_that_differ_only_in_wonkamount_export_together_without_a_serif_end(tmp_path):
    """Integration across modules (a concepts file, gen.js, the export.js command, the JSON read back): for Bract `bine` and Driftwood
    `tideline` and `dune`, two masters that differ only in wonkAmount, 0 and 0.2, with every key leaning, export without complaint,
    draw `l` leaning by -0.2 x xs x 740 units between its top and its foot, and differ in coordinates only."""
    listing = probe("concepts", {"files": [str(e / "concepts.js") for e in (NEUTRAL, BRACT, DRIFTWOOD)]})
    plain = sorted(c["id"] for c in listing if not c["serif"] and not c["shear"] and not c["bend"])
    assert plain == sorted(cid for _, cid in NO_SERIF), (
        f"WONK-NO-SERIF-SET: the shipped concepts with no serif end, no shear and no bend are {plain}, not {sorted(c for _, c in NO_SERIF)}; "
        "a new shipped concept of that kind needs a case here")
    for example, cid in NO_SERIF:
        sub = tmp_path / cid
        sub.mkdir()
        r, out = export_pair(sub, example, cid)
        assert r.returncode == 0, f"WONK-EXPORT-EXIT: export.js exited {r.returncode} for {cid}:\n{r.stderr[-1500:]}"
        masters = json.loads(out.read_text(encoding="utf-8"))["masters"]
        up, lean = masters["Upright"]["glyphs"], masters["Leaning"]["glyphs"]
        assert up["l"]["polys"] != lean["l"]["polys"], f"WONK-EXPORT-LEAN: {cid}: `l` is drawn the same in the wonkAmount 0 and the wonkAmount 0.2 master"
        xs = next(c["xs"] for c in listing if c["id"] == cid)
        want = -0.2 * xs * 740
        got = mean_spread(lean["l"]["polys"][0])
        assert abs(got - want) <= 0.5, f"{cid}: in the wonkAmount 0.2 master the top of `l` is {got} units from its foot, not {want}"
        assert abs(mean_spread(up["l"]["polys"][0])) <= 0.5, f"{cid}: in the wonkAmount 0 master `l` is not plumb"
        differ = [k for k in up if up[k]["polys"] != lean[k]["polys"]]
        assert len(differ) >= 120 and len(up) == 131, f"{cid}: {len(differ)} of {len(up)} glyphs differ between the masters, expected at least 120 of 131"
        for k in up:
            assert [len(p) for p in up[k]["polys"]] == [len(p) for p in lean[k]["polys"]], f"{cid}: {k!r} has different point counts in the two masters"
            assert up[k]["runs"] == lean[k]["runs"] and up[k]["sig"] == lean[k]["sig"], f"{cid}: {k!r} has different runs or branch records in the two masters"


def test_a_serif_concept_is_refused_when_its_masters_stand_either_side_of_the_serif_threshold(tmp_path):
    """Integration across modules: on the neutral `text` concept (serif ends), masters at wonkAmount 0 and 0.2 are refused by
    export.js, which exits 1 and names the glyphs: the serif kind is decided on the leaned skeleton, so a plumb stem's serifs turn
    from foot to diag as the lean passes the threshold. This pins the limit the documentation states (references/generator.md
    section 12)."""
    r, _ = export_pair(tmp_path, NEUTRAL, "text")
    assert r.returncode == 1, f"WONK-SERIF-REFUSED: export.js exited {r.returncode} on masters at wonkAmount 0 and 0.2 of a serif concept, not 1:\n{r.stderr[-800:]}"
    marker = "differ in structure or branch outcome between masters of group roman"
    assert marker in r.stderr, f"the refusal does not say {marker!r}:\n{r.stderr[-800:]}"
    line = next(ln for ln in r.stderr.splitlines() if marker in ln)
    glyphs = line.split(marker + ":", 1)[1].split()
    for k in ("l", "H", "n", "i", "I"):
        assert k in glyphs, f"the refusal does not list {k!r}: {glyphs}"
    assert len(glyphs) >= 50, f"the refusal lists {len(glyphs)} glyphs, expected at least 50: {glyphs}"
    assert any("Upright" in ln and "serifB=foot" in ln for ln in r.stderr.splitlines()), f"no Upright record line holds serifB=foot:\n{r.stderr[-1500:]}"
    assert any("Leaning" in ln and "serifB=diag" in ln for ln in r.stderr.splitlines()), f"no Leaning record line holds serifB=diag:\n{r.stderr[-1500:]}"


def test_a_face_with_a_weight_and_a_lean_axis_builds(tmp_path):
    """The software as a whole (concepts file to woff2, through build.py and every self-check): Driftwood `tideline` with a weight
    axis and a lean axis, four masters, builds, and the instance at wght 400, LEAN 100 leans `l` by -0.2 x xs x 740 units from top to
    foot, half of it at LEAN 50, none at LEAN 0."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    axes = [{"tag": "wght", "name": "Weight", "min": 400, "default": 400, "max": 700}] + LEAN_AXIS
    masters = {"Regular": ("lo", 1, {"wght": 400, "LEAN": 0}), "Bold": ("lo", 1.5, {"wght": 700, "LEAN": 0}),
               "LeanRegular": ("hi", 1, {"wght": 400, "LEAN": 100}), "LeanBold": ("hi", 1.5, {"wght": 700, "LEAN": 100})}
    instances = [{"name": "Regular", "location": {"wght": 400, "LEAN": 0}}, {"name": "Bold", "location": {"wght": 700, "LEAN": 0}},
                 {"name": "Lean Regular", "location": {"wght": 400, "LEAN": 100}}]
    face = write_face(tmp_path, DRIFTWOOD, "tideline", all_keys(), masters, axes, instances, size_budget_bytes=204800)
    r = run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(face / "font.json"), "--no-requirements", "--keep-masters", str(face / "keep" / "export.json")])
    assert r.returncode == 0, f"WONK-BUILD-EXIT: build.py exited {r.returncode}:\n{(r.stdout + r.stderr)[-2500:]}"
    built = sorted((face / "out").rglob("*.woff2"))
    assert len(built) == 1, f"expected one woff2 under {face / 'out'}, found {[str(p) for p in built]}"
    fvar = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in TTFont(str(built[0]))["fvar"].axes}
    assert fvar == {"wght": (400, 400, 700), "LEAN": (0, 0, 100)}, f"the built font's axes are {fvar}"
    xs = concept_xs(DRIFTWOOD / "concepts.js", "tideline")

    def spread_at(lean):
        inst = instancer.instantiateVariableFont(TTFont(str(built[0])), {"wght": 400, "LEAN": lean})
        coords = inst["glyf"]["l"].getCoordinates(inst["glyf"])[0]
        return mean_spread(list(coords))

    full = -0.2 * xs * 740
    got = spread_at(100)
    assert abs(got - full) <= 1.5, f"WONK-BUILD-LEAN: at wght 400, LEAN 100 the top of `l` is {got} units from its foot, not {full}"
    assert abs(spread_at(0)) <= 1.5, f"at LEAN 0 `l` is {spread_at(0)} units from plumb"
    assert abs(spread_at(50) - full / 2) <= 1.5, f"at LEAN 50 the top of `l` is {spread_at(50)} units from its foot, not half of {full}"


def test_the_font_suites_headsink_fixture_keeps_its_own_lean(tmp_path):
    """Across tools (a face, the generator, the font suite run by path): a copy of the neutral example whose first concept sets
    wonkAmount 0.2 would give the suite's headSink fixture (its `l` leans through wonk "l") a steep lean and turn the `l`'s head
    serif diagonal, so two of the three headSink tests would fail. The suite's fixture pins its own amount, so all three pass."""
    face = tmp_path / "neutral"
    shutil.copytree(NEUTRAL, face, ignore=shutil.ignore_patterns("out"))
    anchor = "beak: true, tear: false, serifGrow: 0.4 },"
    text = (face / "concepts.js").read_text(encoding="utf-8")
    assert text.count(anchor) == 1, f"the anchor {anchor!r} occurs {text.count(anchor)} times in the neutral concepts, not once (the first concept)"
    (face / "concepts.js").write_text(text.replace(anchor, "beak: true, tear: false, serifGrow: 0.4, wonkAmount: 0.2 },"), encoding="utf-8")
    xs = concept_xs(face / "concepts.js", "text")
    draws = probe("draw", {"file": str(face / "concepts.js"), "id": "text", "set": {"wonk": "l", "shear": 0, "bend": 0},
                           "styles": ["roman"], "mults": [1], "keys": ["l"]})
    assert len(draws) == 1 and draws[0]["centre"] is not None, f"the probe drew {len(draws)} glyphs, or `l` has no stroke body"
    got, want = lean_of(draws[0]), -0.2 * xs
    assert abs(got - want) < 1e-9, f"WONK-SUITE-FACE: the face's first concept sets wonkAmount 0.2 and the fixture's `l` leans {got}, not {want}"
    r = subprocess.run([sys.executable, "-m", "pytest", str(SCRIPTS / "tests" / "test_font.py"), "-q", "-p", "no:cacheprovider", "-k", "headsink",
                        "--font", str(face / "font.json"), "--requirements", str(face / "requirements.json"), "--static-dir", "none", f"--scripts={SCRIPTS}"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0 and "3 passed" in r.stdout, f"WONK-SUITE-FIXTURE: the font suite's headSink tests on the face exited {r.returncode}:\n{r.stdout[-2500:]}"
