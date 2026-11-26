"""Holds the Tiki Terminal example (examples/tiki-terminal/) to its approved design, the lean it draws, a minimum gap between outlines and
its font suite.

WHAT IT'S FOR: the example is the skill's fourth fixture and the only one with a skeleton file, cut stem ends and a custom axis (LEAN).
Its parameters are an operator's decisions (axes, instances, names, characters) and measured facts (a gap floor, a list of pairs whose
automatic kern is suppressed). These eight tests fail when the face drifts from either. The plan is .claude/plans/tiki-terminal-example.md
(docs/plan-tiki-terminal.md once released).

The levels, lowest first:
  1. one unit: the two configuration files (font.json, requirements.json) read as data;
  2. across a module boundary: concepts.js through gen.js `loadConcepts`, in node;
  3. the whole tool: sources to woff2 (build.py), read back with fontTools;
  4. 5. the whole tool and HarfBuzz: the data flow from skeleton to shaped text, measured as the distance between outlines;
  6. the same, on a second build whose zero hand pairs are removed;
  7. the software as a whole: the font suite (scripts/tests/test_font.py) run by path on the built copy;
  8. the whole tool again, read as outline coordinates at four instances, so a LEAN axis that draws no lean fails.

How the tests reach the face. Two module-scoped fixtures, and no test opens a face file another way. `face()` returns the two parsed
files, or a record {"missing": path} or {"invalid_json": path, "error": ...}; `built()` copies the folder (without out/) to a temporary
directory, builds it there, and returns the woff2, the manifest and the copy's folder, or {"missing": path} or {"build_failed": stderr}.
Neither raises, so a missing face shows as a failed ASSERTION carrying the record, which is what the red run before the face exists must
show. Each test has exactly one `assert`; its message starts with a marker (TIKI-DESIGN: and so on) that names the test.

Limit of the gap tests, stated: contour distance at the five named locations of tests/pair_gap.py. A glyph lying wholly inside another's
counter, and an axis setting between the five locations, are not seen.
"""
import copy
import importlib.util as _ilu
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

# Load tests/conftest.py and tests/pair_gap.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain import would get the wrong module.
_HERE = pathlib.Path(__file__).resolve().parent


def _load(name, file):
    spec = _ilu.spec_from_file_location(name, _HERE / file)
    mod = _ilu.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_conf = _load("repo_tests_conftest", "conftest.py")
pair_gap = _load("repo_tests_pair_gap", "pair_gap.py")

REPO = _conf.REPO
node = _conf.node
FACE = REPO / "examples" / "tiki-terminal"
FONT_JSON = FACE / "font.json"
REQUIREMENTS_JSON = FACE / "requirements.json"
CONCEPTS_JS = FACE / "concepts.js"
GEN_JS = REPO / "scripts" / "gen.js"

# The font suite's tests that draw the FIRST concept of the face's file (phosphor, a round-1 concept no master uses) and assume it has
# flare or serif ends, or leaves hzThin, xh and crotch unset. -k matches substrings, so each name below also selects any test whose name
# contains it; test 7 asserts that exactly six are deselected.
#   dropamt              two tests: no end of phosphor is a flare, so `tear: true` draws no teardrop.
#   optical_corrections  the fixture's "no knob" variant keeps phosphor's own hzThin 0.92 (bar 88.32, expected 96.0).
#   open_curve_extremes  the same fixture.
#   unbracketed_serif    the fixture keeps phosphor's xh 560 and looks for the serif at 500.
#   unset_crotch         every master of the face sets crotch, so the fixture reads 0 records and its floor of 1,000 fails.
SUITE_EXCLUSIONS = "not dropamt and not optical_corrections and not unbracketed_serif and not open_curve_extremes and not unset_crotch"

# The two hand pairs with a real (non-zero) value: they are kerned in the second build of test 6 as in the face, so they do not appear
# in its measurement and are the one named exception to "every pair under 15 units is a zero pair".
NONZERO_HAND = {"r|r": -90, "E|O": -60}

BAND_HIGH = 17  # every zero pair measures under this many units without its zero entry
BAND_LOW = 15  # every pair under this many units without the zero list is a zero pair

# Set from the first build of the face at half the smallest value measured over the ten wonk letters and the two weights (plan, test 8).
# PROVISIONAL until that build is measured: the lean is 0.158 x height in units, so a lowercase letter tips by about 80, and these
# are far below it.
MIN_TIP = 20
MIN_SPREAD = 20

LOCS = pair_gap.LOCATIONS
CONTROL_LETTERS = "nHmTxz"
WONK_LETTERS = "aeiokrAEIO"


def _read_json(path):
    path = pathlib.Path(path)
    if not path.exists():
        return {"missing": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"invalid_json": str(path), "error": str(exc).splitlines()[0]}


@pytest.fixture(scope="module")
def face():
    """The face's two files as dictionaries, or one record naming what is wrong. Never raises."""
    font = _read_json(FONT_JSON)
    req = _read_json(REQUIREMENTS_JSON)
    return {"font": font, "requirements": req}


def _build_copy(mutate_font=None):
    """Copies the face folder (without out/) to a temporary directory, optionally edits the copy's font.json, builds it there.
    Returns {"woff2", "manifest", "dir", "font_json"} or {"missing": path} or {"build_failed": last 2,000 characters of stderr}."""
    if not FONT_JSON.exists():
        return {"missing": str(FONT_JSON)}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="tiki-"))
    dest = tmp / "tiki-terminal"
    shutil.copytree(FACE, dest, ignore=shutil.ignore_patterns("out"))
    fj = dest / "font.json"
    if mutate_font is not None:
        cfg = json.loads(fj.read_text(encoding="utf-8"))
        mutate_font(cfg)
        fj.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    done = subprocess.run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(fj)], capture_output=True, text=True, cwd=REPO, timeout=900)
    if done.returncode != 0:
        return {"build_failed": (done.stderr or done.stdout)[-2000:]}
    manifest = json.loads((dest / "out" / "manifest.json").read_text(encoding="utf-8"))
    woff2 = dest / manifest["groups"]["roman"]["file"]
    return {"woff2": woff2, "manifest": manifest, "dir": dest, "font_json": fj}


@pytest.fixture(scope="module")
def built():
    """The face built in a temporary copy, or a record naming why not. Never raises."""
    return _build_copy()


def _usable(record):
    return "woff2" in record


def _concept_facts():
    """What `loadConcepts` makes of the face's concepts.js, read in node: the ids, the keys in which canelean differs from cane, and the
    values of the lean letters. A record {"missing": path} or {"node_failed": stderr} when it cannot."""
    script = """
var fs = require("fs"), gen = process.argv[1], file = process.argv[2];
if (!fs.existsSync(file)) { console.log(JSON.stringify({missing: file})); process.exit(0); }
var G = require(gen), list = G.loadConcepts(file), by = {};
list.forEach(function (c) { by[c.id] = c; });
var out = {ids: list.map(function (c) { return c.id; })};
if (by.cane && by.canelean) {
  var keys = {};
  Object.keys(by.cane).concat(Object.keys(by.canelean)).forEach(function (k) { keys[k] = 1; });
  out.differ = Object.keys(keys).filter(function (k) { return JSON.stringify(by.cane[k]) !== JSON.stringify(by.canelean[k]); });
  out.wonk = by.canelean.wonk;
  out.wonkAmount = by.canelean.wonkAmount;
  out.cane_wonk = by.cane.wonk;
}
console.log(JSON.stringify(out));
"""
    done = subprocess.run([node(), "-e", script, str(GEN_JS), str(CONCEPTS_JS)], capture_output=True, text=True, cwd=REPO, timeout=120)
    if done.returncode != 0:
        return {"node_failed": done.stderr[-2000:]}
    return json.loads(done.stdout)


def _fmt(observed, expected):
    return f"observed {json.dumps(observed, ensure_ascii=False, default=str, sort_keys=True)} expected {json.dumps(expected, ensure_ascii=False, default=str, sort_keys=True)}"  # noqa: E501


# ---------------------------------------------------------------------------------------------------------------------------------
# 1. the two configuration files
# ---------------------------------------------------------------------------------------------------------------------------------

EXPECTED_AXES = [["wght", 400, 400, 700], ["LEAN", 0, 0, 100]]
EXPECTED_MASTERS = {
    "Reg": ["cane", 1, {"wght": 400, "LEAN": 0}],
    "Bold": ["cane", 1.5, {"wght": 700, "LEAN": 0}],
    "RegLean": ["canelean", 1, {"wght": 400, "LEAN": 100}],
    "BoldLean": ["canelean", 1.5, {"wght": 700, "LEAN": 100}],
}
EXPECTED_INSTANCES = [
    ["Regular", {"wght": 400, "LEAN": 0}],
    ["Bold", {"wght": 700, "LEAN": 0}],
    ["Lean", {"wght": 400, "LEAN": 100}],
    ["Bold Lean", {"wght": 700, "LEAN": 100}],
]
OFL_SENTENCE = "SIL Open Font License, Version 1.1"


def _bad(record):
    return isinstance(record, dict) and ("missing" in record or "invalid_json" in record)


def test_font_json_and_requirements_state_the_approved_design(face):
    font, req = face["font"], face["requirements"]
    expected = {
        "font": {
            "family": "Tiki Terminal",
            "groups": ["roman"],
            "italic": False,
            "axes": EXPECTED_AXES,
            "masters": EXPECTED_MASTERS,
            "instances": EXPECTED_INSTANCES,
            "concepts": "concepts.js",
            "skeletons": "skeletons.js",
            "fold_units": {"raw": 4, "decimated": 10},
            "fs_type": 0,
            "designer": "John M. P. Knox",
            "manufacturer": "John M. P. Knox",
            "copyright": "Copyright 2026 John M. P. Knox",
            "licence_url": "https://openfontlicense.org",
            "licence_has_ofl": True,
            "required_has_gt": True,
            "required_has_underscore": True,
            "required_has_lt": False,
        },
        "requirements": {
            "family": "Tiki Terminal",
            "axes": {"wght": [400, 400, 700], "LEAN": [0, 0, 100]},
            "masters": {n: m[2] for n, m in EXPECTED_MASTERS.items()},
            "instances": {n: loc for n, loc in EXPECTED_INSTANCES},
            "fs_type": 0,
            "designer": "John M. P. Knox",
            "required_has_gt": True,
            "required_has_underscore": True,
            "required_has_lt": False,
            "floors_at_least_18_75": True,
            "floors_agree": True,
            "titles_agree": True,
        },
    }
    if _bad(font) or _bad(req):
        observed = {"font": font, "requirements": req}
    else:
        g = font.get("groups", {})
        grp = g.get("roman", {})
        rg = req.get("groups", {}).get("roman", {})
        floors = rg.get("hairline_floors", {})
        req_chars = req.get("required_characters", "")
        font_chars = font.get("charset", {}).get("required", "")
        observed = {
            "font": {
                "family": font.get("family"),
                "groups": sorted(g),
                "italic": grp.get("italic"),
                "axes": [[a.get("tag"), a.get("min"), a.get("default"), a.get("max")] for a in grp.get("axes", [])],
                "masters": {n: [m.get("concept"), m.get("mult"), m.get("location")] for n, m in grp.get("masters", {}).items()},
                "instances": [[i.get("name"), i.get("location")] for i in grp.get("instances", [])],
                "concepts": font.get("concepts"),
                "skeletons": font.get("skeletons"),
                "fold_units": font.get("fold_units"),
                "fs_type": font.get("names", {}).get("fs_type"),
                "designer": font.get("names", {}).get("designer"),
                "manufacturer": font.get("names", {}).get("manufacturer"),
                "copyright": font.get("names", {}).get("copyright"),
                "licence_url": font.get("names", {}).get("licence_url"),
                "licence_has_ofl": OFL_SENTENCE in font.get("names", {}).get("licence", ""),
                "required_has_gt": ">" in font_chars,
                "required_has_underscore": "_" in font_chars,
                "required_has_lt": "<" in font_chars,
            },
            "requirements": {
                "family": req.get("family"),
                "axes": rg.get("axes"),
                "masters": rg.get("masters"),
                "instances": rg.get("instances"),
                "fs_type": req.get("names", {}).get("fs_type"),
                "designer": req.get("names", {}).get("designer"),
                "required_has_gt": ">" in req_chars,
                "required_has_underscore": "_" in req_chars,
                "required_has_lt": "<" in req_chars,
                "floors_at_least_18_75": bool(floors) and all(v >= 1000 * 0.75 / 40 for v in floors.values()),
                "floors_agree": floors == grp.get("hairline_floors") and bool(floors),
                "titles_agree": req.get("titles") == font.get("titles") and bool(font.get("titles")),
            },
        }
    assert observed == expected, "TIKI-DESIGN: the configuration files differ from the approved design: " + _fmt(observed, expected)


# ---------------------------------------------------------------------------------------------------------------------------------
# 2. concepts.js through loadConcepts
# ---------------------------------------------------------------------------------------------------------------------------------


def test_the_lean_masters_draw_cane_with_the_leaning_letters():
    facts = _concept_facts()
    if "missing" in facts or "node_failed" in facts:
        observed = facts
    else:
        observed = {
            "ids_have_cane_and_canelean": "cane" in facts.get("ids", []) and "canelean" in facts.get("ids", []),
            "differ": sorted(facts["differ"]) if "differ" in facts else None,
            "wonk": facts.get("wonk"),
            "wonkAmount": facts.get("wonkAmount"),
            "cane_wonk_absent": "differ" in facts and "cane_wonk" not in facts,
        }
    expected = {
        "ids_have_cane_and_canelean": True,
        "differ": ["from", "id", "name", "wonk", "wonkAmount"],
        "wonk": "aeiokrAEIO",
        "wonkAmount": 0.158,
        "cane_wonk_absent": True,
    }
    assert observed == expected, "TIKI-CONCEPTS: canelean must be cane with only the leaning letters and their amount changed: " + _fmt(observed, expected)


# ---------------------------------------------------------------------------------------------------------------------------------
# 3. the built font
# ---------------------------------------------------------------------------------------------------------------------------------


def test_the_built_font_carries_the_approved_axes_names_and_characters(built):
    expected = {
        "axes": EXPECTED_AXES,
        "instances": EXPECTED_INSTANCES,
        "name_1": "Tiki Terminal",
        "name_9": "John M. P. Knox",
        "name_0": "Copyright 2026 John M. P. Knox",
        "name_14": "https://openfontlicense.org",
        "name_13_has_ofl": True,
        "fs_type": 0,
        "cmap_gt": True,
        "cmap_underscore": True,
        "cmap_lt": False,
        "zero_has_three_contours_or_more": True,
        "manifest_skeletons": "skeletons.js",
    }
    if not _usable(built):
        observed = built
    else:
        from fontTools.ttLib import TTFont

        font = TTFont(built["woff2"])
        name = font["name"]
        cmap = font.getBestCmap()
        zero = font["glyf"][cmap[0x30]]
        observed = {
            "axes": [[a.axisTag, a.minValue, a.defaultValue, a.maxValue] for a in font["fvar"].axes],
            "instances": [[name.getDebugName(i.subfamilyNameID), dict(i.coordinates)] for i in font["fvar"].instances],
            "name_1": name.getDebugName(1),
            "name_9": name.getDebugName(9),
            "name_0": name.getDebugName(0),
            "name_14": name.getDebugName(14),
            "name_13_has_ofl": OFL_SENTENCE in (name.getDebugName(13) or ""),
            "fs_type": font["OS/2"].fsType,
            "cmap_gt": 0x3E in cmap,
            "cmap_underscore": 0x5F in cmap,
            "cmap_lt": 0x3C in cmap,
            "zero_has_three_contours_or_more": zero.numberOfContours >= 3,
            "manifest_skeletons": built["manifest"].get("skeletons"),
        }
    assert observed == expected, "TIKI-FONT: the built font differs from the approved design: " + _fmt(observed, expected)


# ---------------------------------------------------------------------------------------------------------------------------------
# 4. 5. the minimum gap
# ---------------------------------------------------------------------------------------------------------------------------------

UNDER_16_COMMAND = ".venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --under 16"


def test_no_two_mapped_characters_come_closer_than_12_units(built):
    expected = {name: {"measured_at_least_18000": True, "close": {}} for name in LOCS}
    close_all = {}
    if not _usable(built):
        observed = built
    else:
        observed = {}
        for name, loc in LOCS.items():
            r = pair_gap.scan(built["woff2"], loc, 12)
            observed[name] = {"measured_at_least_18000": r["measured"] >= 18000, "close": r["close"]}
            for k, v in r["close"].items():
                close_all[f"{k} at {name}"] = v
    worst = sorted(close_all.items(), key=lambda kv: kv[1])[:40]
    assert observed == expected, (
        "TIKI-PAIR-GAP: outlines come closer than 12 units (contour distance at the five named locations, not containment; worst first, "
        f"at most 40 of {len(close_all)}): {worst}; the pairs to suppress are listed by `{UNDER_16_COMMAND}`; observed {json.dumps(observed, default=str)[:600]}"
    )


def test_the_five_reported_pairs_keep_30_units_at_weight_700(built):
    pairs = ["r|r", "r|o", "e|r", "R|E", "E|O"]
    expected = {name: {"measured_at_least_18000": True, "under_30": {}} for name in ("Bold", "Bold Lean")}
    if not _usable(built):
        observed = built
    else:
        observed = {}
        for name in ("Bold", "Bold Lean"):
            r = pair_gap.scan(built["woff2"], LOCS[name], 30)
            observed[name] = {"measured_at_least_18000": r["measured"] >= 18000, "under_30": {p: g for p, g in r["close"].items() if p in pairs}}
    assert observed == expected, "TIKI-BOLD-PAIRS: rr, ro, er, RE and EO must keep 30 units at weight 700 (contour distance at the named locations): " + _fmt(observed, expected)  # noqa: E501


# ---------------------------------------------------------------------------------------------------------------------------------
# 6. the zero list against a build without it
# ---------------------------------------------------------------------------------------------------------------------------------


def _union_scan(woff2, limit, kern_set):
    union = {}
    for loc in LOCS.values():
        r = pair_gap.scan(woff2, loc, limit)
        for k, v in pair_gap.kern_set_filter(r["close"], kern_set).items():
            union[k] = min(v, union.get(k, v))
    return union


def test_every_suppressed_pair_is_one_the_measurement_found(face, built):
    expected = {"zero_pairs_at_least_400": True, "not_found_under_17": [], "under_15_not_suppressed": [], "not_kern_set_keys": [], "kern_pairs_at_least_4000": True}
    font = face["font"]
    if _bad(font):
        observed = font
    elif not _usable(built):
        observed = built
    else:
        hand = font.get("kerning", {}).get("hand", {})
        zero = sorted(k for k, v in hand.items() if "|" in k and v == 0)
        kern_set = font["kerning"]["set"]

        def drop_zero(cfg):
            cfg["kerning"]["hand"] = {k: v for k, v in cfg["kerning"]["hand"].items() if v != 0}

        second = _build_copy(drop_zero)
        if not _usable(second):
            observed = second
        else:
            high = _union_scan(second["woff2"], BAND_HIGH, kern_set)
            low = _union_scan(second["woff2"], BAND_LOW, kern_set)
            rx_ok = pair_gap.kern_set_filter({z: 0 for z in zero}, kern_set)
            observed = {
                "zero_pairs_at_least_400": len(zero) >= 400,
                "not_found_under_17": sorted(z for z in zero if z not in high),
                "under_15_not_suppressed": sorted(p for p in low if p not in zero and p not in NONZERO_HAND),
                "not_kern_set_keys": sorted(z for z in zero if z not in rx_ok),
                "kern_pairs_at_least_4000": built["manifest"]["groups"]["roman"]["kern_pairs"] >= 4000,
            }
    assert observed == expected, "TIKI-ZERO-LIST: the zero hand pairs must be pairs the unsuppressed build puts under 17 units, and cover every pair under 15: " + _fmt(observed, expected)  # noqa: E501


# ---------------------------------------------------------------------------------------------------------------------------------
# 7. the font suite
# ---------------------------------------------------------------------------------------------------------------------------------


def test_the_font_suite_passes_on_the_face_with_six_first_concept_tests_excluded(built):
    expected = {"exit": 0, "six_deselected": True, "failed": False}
    if not _usable(built):
        observed = built
        tail = ""
    else:
        d = built["dir"]
        cmd = [sys.executable, "-m", "pytest", str(REPO / "scripts" / "tests" / "test_font.py"), "-q", "-p", "no:cacheprovider",
               "--font", str(d / "font.json"), "--requirements", str(d / "requirements.json"), "--static-dir", "none",
               f"--scripts={REPO / 'scripts'}", "-k", SUITE_EXCLUSIONS]
        done = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=3000)
        out = done.stdout + done.stderr
        lines = [ln for ln in out.splitlines() if ln.strip()]
        summary = lines[-1] if lines else ""
        observed = {"exit": done.returncode, "six_deselected": "6 deselected" in out, "failed": "failed" in summary}
        tail = "\n".join(lines[-15:])
    assert observed == expected, "TIKI-SUITE: the font suite must pass on the face with exactly six tests deselected: " + _fmt(observed, expected) + "\n" + tail


# ---------------------------------------------------------------------------------------------------------------------------------
# 8. the lean the LEAN axis draws
# ---------------------------------------------------------------------------------------------------------------------------------


def _outlines(woff2, location, letters):
    """{letter: [(x, y), ...]} of the instanced font at the location; every point of every contour, in glyph order."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    inst = instancer.instantiateVariableFont(TTFont(woff2), dict(location))
    cmap = inst.getBestCmap()
    glyf = inst["glyf"]
    out = {}
    for ch in letters:
        coords = glyf[cmap[ord(ch)]].getCoordinates(glyf)[0]
        out[ch] = [tuple(p) for p in coords]
    return out


def test_the_lean_axis_tips_the_wonk_letters_and_leaves_the_others_alone(built):
    expected = {w: {"wonk_letters": sorted(WONK_LETTERS), "wonk_not_tipped": [], "wonk_only_shifted": [], "others_moved": [], "count_mismatch": []} for w in (400, 700)}
    if not _usable(built):
        observed = built
    else:
        facts = _concept_facts()
        wonk = sorted(facts.get("wonk") or "")
        letters = sorted(set(wonk) | set(CONTROL_LETTERS))
        observed = {}
        for w in (400, 700):
            a = _outlines(built["woff2"], {"wght": w, "LEAN": 0}, letters)
            b = _outlines(built["woff2"], {"wght": w, "LEAN": 100}, letters)
            rec = {"wonk_letters": wonk, "wonk_not_tipped": [], "wonk_only_shifted": [], "others_moved": [], "count_mismatch": []}
            for ch in letters:
                if len(a[ch]) != len(b[ch]):
                    rec["count_mismatch"].append(ch)
                    continue
                dx = [q[0] - p[0] for p, q in zip(a[ch], b[ch])]
                dy = [q[1] - p[1] for p, q in zip(a[ch], b[ch])]
                if ch in wonk:
                    largest = max((x * x + y * y) ** 0.5 for x, y in zip(dx, dy)) if dx else 0
                    if largest < MIN_TIP:
                        rec["wonk_not_tipped"].append(ch)
                    if (max(dx) - min(dx) if dx else 0) < MIN_SPREAD:
                        rec["wonk_only_shifted"].append(ch)
                elif a[ch] != b[ch]:
                    rec["others_moved"].append(ch)
            observed[w] = rec
    assert observed == copy.deepcopy(expected), "TIKI-LEAN-GEOMETRY: LEAN 100 must tip exactly the ten wonk letters, as a lean and not a shift: " + _fmt(observed, expected)  # noqa: E501
