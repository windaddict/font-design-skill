"""scripts/fallback-metrics.py: the numbers behind a metric-matched fallback face, checked against arithmetic done here.

WHAT IT'S FOR: `size-adjust` and the three overrides come from two fonts, so a person cannot type them, and a
wrong one makes the swap move the page more than no fallback face at all. The script is run on the built neutral
font and a fallback font made in the test (every glyph 500 units wide on a 1000-unit em, ascent 800, descent 200),
so the expected size-adjust is the web font's mean title advance divided by exactly 0.5, computed here with
fontTools from the same titles; the overrides are the web font's own hhea metrics divided by that. Needs the built
Sampler (examples/neutral/out), which smoke.sh and the font suite build.
"""
import json
import re
import subprocess
import sys

import pytest
from conftest import REPO

SCRIPT = REPO / "scripts" / "fallback-metrics.py"
NEUTRAL = REPO / "examples" / "neutral"


def make_fallback(path, width=500, ascent=800, descent=200, chars="".join(chr(c) for c in range(32, 127)) + "’“”‘–—…"):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    names = {".notdef": 0x0, **{f"u{ord(c):04X}": ord(c) for c in chars}}
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(list(names))
    fb.setupCharacterMap({cp: n for n, cp in names.items() if cp})
    pen = TTGlyphPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 100))
    pen.lineTo((100, 100))
    pen.closePath()
    fb.setupGlyf({n: pen.glyph() for n in names})
    fb.setupHorizontalMetrics({n: (width, 0) for n in names})
    fb.setupHorizontalHeader(ascent=ascent, descent=-descent)
    fb.setupNameTable({"familyName": "Fb", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=ascent, sTypoDescender=-descent, usWinAscent=ascent, usWinDescent=descent)
    fb.setupPost()
    fb.save(str(path))
    return path


def web_mean(location=None, titles=None):
    """The mean advance in em of the titles' characters (every occurrence, no-break space as space) in the built
    roman, with the axes at `location` and the rest at their defaults; fontTools only, no script code."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    font = TTFont(NEUTRAL / "out" / "Sampler-VF.woff2")
    loc = {a.axisTag: a.defaultValue for a in font["fvar"].axes} | (location or {})
    font = instancer.instantiateVariableFont(font, loc, inplace=True)
    cmap, hm = font.getBestCmap(), font["hmtx"].metrics
    text = "\n".join(titles if titles is not None else json.loads((NEUTRAL / "font.json").read_text())["titles"]).replace(" ", " ")
    advs = [hm[cmap[ord(c)]][0] / 1000 for c in text if not c.isspace() or c == " "]
    return sum(advs) / len(advs), font["hhea"]


def run(tmp_path, *extra, fallback=None):
    fb = fallback or make_fallback(tmp_path / "Fb.ttf")
    cmd = [sys.executable, str(SCRIPT), "--font", str(NEUTRAL / "font.json"), "--group", "roman", "--fallback", f"Georgia={fb}", *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def value(out, prop):
    m = re.search(rf"{prop}: ([\d.]+)%", out)
    assert m, f"{prop} missing from:\n{out}"
    return float(m.group(1))


def test_size_adjust_and_overrides_are_the_arithmetic_of_the_two_fonts(tmp_path):
    """size-adjust = mean web advance / mean fallback advance (0.5 em here); each override = the web font's hhea
    metric over its em, divided by size-adjust. Mutations watched red: the ratio inverted; the ascent override not
    divided by size-adjust; the descent sign flipped. Not caught, and said so: reading the metrics from OS/2 typo
    instead of hhea, because the neutral font writes the same numbers to both (build.py makes them equal by
    design), so no fixture here can tell the tables apart."""
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    mean, hhea = web_mean()
    size = mean / 0.5
    assert abs(value(r.stdout, "size-adjust") - 100 * size) < 0.006, (value(r.stdout, "size-adjust"), 100 * size)
    assert abs(value(r.stdout, "ascent-override") - 100 * hhea.ascent / 1000 / size) < 0.006
    assert abs(value(r.stdout, "descent-override") - 100 * -hhea.descent / 1000 / size) < 0.006
    assert abs(value(r.stdout, "line-gap-override") - 100 * hhea.lineGap / 1000 / size) < 0.006
    assert 'font-family: "Sampler Fallback";' in r.stdout and 'src: local("Georgia");' in r.stdout, r.stdout


def test_the_location_moves_the_measurement_to_the_cut_the_headlines_use(tmp_path):
    """At wght=700,opsz=72 the web font's advances are other numbers than at its defaults, and size-adjust follows.
    Mutation watched red: --location parsed and then ignored (the default location always measured)."""
    r = run(tmp_path, "--location", "wght=700,opsz=72")
    assert r.returncode == 0, r.stderr
    mean, _hhea = web_mean({"wght": 700, "opsz": 72})
    default_mean, _ = web_mean()
    assert abs(mean - default_mean) > 0.01, "the fixture's cuts must differ in width for this test to mean anything"
    assert abs(value(r.stdout, "size-adjust") - 100 * mean / 0.5) < 0.006, (value(r.stdout, "size-adjust"), 100 * mean / 0.5)
    assert "wght=700,opsz=72" in r.stdout


def test_a_character_the_fallback_lacks_does_not_tilt_the_ratio(tmp_path):
    """The mean is over characters BOTH fonts map. A fallback lacking `#` (in the title 'Notes from the Third
    Floor #4') must give the same size-adjust as the web font's mean over the titles without that character.
    Mutation watched red: the mean taken over every character the web font maps."""
    fb = make_fallback(tmp_path / "NoHash.ttf", chars="".join(chr(c) for c in range(32, 127) if chr(c) != "#"))
    r = run(tmp_path, fallback=fb)
    assert r.returncode == 0, r.stderr
    titles = json.loads((NEUTRAL / "font.json").read_text())["titles"]
    mean, _ = web_mean(titles=[t.replace("#", "") for t in titles])
    assert abs(value(r.stdout, "size-adjust") - 100 * mean / 0.5) < 0.006, (value(r.stdout, "size-adjust"), 100 * mean / 0.5)


@pytest.mark.parametrize("args,why", [(["--location", "wght"], "TAG=VALUE"), (["--location", "slnt=4"], "no axis"),
                                      (["--fallback", "X=/nonexistent.ttf"], "NAME=PATH")])
def test_bad_input_exits_naming_the_problem(tmp_path, args, why):
    fb = make_fallback(tmp_path / "Fb.ttf")
    cmd = [sys.executable, str(SCRIPT), "--font", str(NEUTRAL / "font.json"), "--group", "roman", "--fallback", f"Georgia={fb}", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode != 0 and why in r.stderr, r.stderr
