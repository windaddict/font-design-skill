"""scripts/diff.py, the per-round visual diff, executed on the neutral example and on copies of it that were changed on purpose.

WHAT IT'S FOR: diff.py tells a fresh design-round reviewer which of the project's title renders moved since the previous
build. A diff tool that reports "nothing changed" because it compared a file with itself, or "everything changed" because
the two sides were drawn differently, is worse than none: the reviewer stops looking where the words moved. Each test
builds its own changed font (a glyph shifted, one kern value moved, one master's deltas enlarged), states what must
change from the font.json titles and from fontTools reads of its own, never from a figure diff.py printed, and was
watched red under the weakest by-hand mutation named in its docstring (Pillow 13.0.0, FreeType 2.14.3, 2026-11-16).
The neutral example's `out/` is built by `smoke.sh` / `build.py`; it is untracked, so a missing one SKIPS LOUDLY here (the
same convention as tests/test_tools_and_templates.py), and CI builds it first.
"""
import importlib.util
import json
import re
import shutil
import sys

import pytest
from conftest import REPO, run

NEUTRAL = REPO / "examples" / "neutral"
DIFF = REPO / "scripts" / "diff.py"
CFG = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
SIZES = ["16", "24", "40"]


@pytest.fixture(scope="module")
def built():
    """The neutral example's two built woff2 files, or a loud skip."""
    files = [NEUTRAL / "out" / "Sampler-VF.woff2", NEUTRAL / "out" / "Sampler-Italic-VF.woff2"]
    if not all(f.is_file() for f in files):
        pytest.skip("SKIPPED, NOT PASSED: examples/neutral/out is not built (build the neutral example first)")
    return files


@pytest.fixture
def folders(tmp_path, built):
    """(before, after): two folders each holding a copy of the neutral build's two files, so a test changes `after` only."""
    out = {}
    for side in ("before", "after"):
        d = tmp_path / side
        d.mkdir()
        for f in built:
            shutil.copyfile(f, d / f.name)
        out[side] = d
    return out["before"], out["after"]


def diff(tmp_path, before, after, *extra, name="d", font=None):
    """Runs scripts/diff.py as a subprocess; returns (CompletedProcess, out dir, parsed diff.json or None)."""
    out = tmp_path / name
    r = run([sys.executable, str(DIFF), str(out), "--font", str(font or NEUTRAL / "font.json"), "--before", str(before), "--after", str(after), *extra])
    data = json.loads((out / "diff.json").read_text(encoding="utf-8")) if (out / "diff.json").is_file() else None
    return r, out, data


def load_diff_module():
    spec = importlib.util.spec_from_file_location("diff_under_test", DIFF)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def save_woff2(font, path):
    font.flavor = "woff2"
    font.save(str(path))


def panels(png, entry):
    """(before, after) as flat lists of grey levels, read from a changed entry's PNG: three panels of entry['panel'] size stacked
    with a gap the test derives from the image height."""
    from PIL import Image
    w, h = entry["panel"]
    with Image.open(png) as im:
        im = im.convert("L")
        gap = (im.height - 3 * h) // 2
        assert im.width == w and im.height == 3 * h + 2 * gap and gap > 0, (im.size, entry["panel"])
        return (list(im.crop((0, 0, w, h)).tobytes()), list(im.crop((0, h + gap, w, 2 * h + gap)).tobytes()))


def titles_with(text):
    return [t for t in CFG["titles"] if text in t]


def test_diff_reports_no_change_between_a_font_and_itself(tmp_path, folders):
    """The neutral `out/` against a copy of itself: every entry has changed_px 0, diff.md says "0 of M renders changed",
    no PNG is written, the exit is 0. M is counted here from font.json (groups x instances x titles x sizes), not read from
    the output. Weakest mutation, by hand 2026-11-16: the BEFORE font loaded at `px + 1` pixels in `run()` (the two sides then
    differ in canvas and in every glyph, so every entry reports a change) turned it red on 'renders changed'."""
    before, after = folders
    r, out, data = diff(tmp_path, before, after)
    assert r.returncode == 0, r.stderr
    sizes = CFG["review"]["sizes"]
    m = sum(len(g["instances"]) for g in CFG["groups"].values()) * len(CFG["titles"]) * len(sizes)
    assert len(data["entries"]) == m and m > 100, (len(data["entries"]), m)
    assert [e for e in data["entries"] if e["changed_px"]] == [], "a font diffed against a copy of itself changed"
    assert f"0 of {m} renders changed" in (out / "diff.md").read_text(encoding="utf-8")
    assert list(out.glob("*.png")) == []


def test_diff_sees_a_moved_glyph_in_the_titles_that_use_it_only(tmp_path, folders):
    """A copy of the neutral roman with the default outline of `o` shifted +30 units in x (the gvar deltas untouched, so every
    instance moves): every roman entry whose title contains a lowercase o changes at every instance and size, `SIX WAYS OUT`
    and `Bracket's Last Stand` (no lowercase o, by the test's own `in` check) do not, and the italic group, whose file was not
    touched, does not. The PNG of one changed entry stacks three panels; the third holds red or blue pixels inside the reported
    bbox and none outside it, and red means the after panel is darker there. Weakest mutation, by hand 2026-11-16: `after`
    rendered from the before path in `group_files()` (nothing changes) turned it red on 'did not change'."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    glyph = font["glyf"]["o"]
    glyph.coordinates.translate((30, 0))
    # FreeType places a TrueType glyph so that its xMin equals the hmtx left side bearing; a shift that leaves hmtx alone is undone
    # at draw time (seen 2026-11-16: 0 changed pixels). So the bounds and the lsb follow the outline.
    glyph.recalcBounds(font["glyf"])
    font["hmtx"].metrics["o"] = (font["hmtx"].metrics["o"][0], glyph.xMin)
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", *SIZES)
    assert r.returncode == 0, r.stderr
    uses_o = set(titles_with("o"))
    assert uses_o and uses_o != set(CFG["titles"]), "the fixture titles must split on a lowercase o"
    seen = 0
    for e in data["entries"]:
        expect_change = e["group"] == "roman" and e["title"] in uses_o
        where = f"{e['group']} {e['instance']} {e['size']}px {e['title']!r}"
        assert (e["changed_px"] > 0) == expect_change, f"{where}: changed_px {e['changed_px']}, expected change {expect_change}"
        seen += expect_change
    assert seen == len(uses_o) * len(CFG["groups"]["roman"]["instances"]) * len(SIZES)
    from PIL import Image
    entry = max((e for e in data["entries"] if e["png"]), key=lambda e: e["changed_px"])
    w, h = entry["panel"]
    with Image.open(out / entry["png"]) as im:
        im = im.convert("RGB")
        gap, rem = divmod(im.height - 3 * h, 2)
        assert im.width == w and rem == 0 and gap > 0, (im.size, entry["panel"])
        left, top, right, bottom = entry["bbox"]
        n_in = n_out = 0
        y0 = 2 * (h + gap)
        for y in range(h):
            for x in range(w):
                pr, pg, pb = im.getpixel((x, y0 + y))
                red, blue = pr > 200 and pg < 80 and pb < 80, pb > 200 and pr < 80 and pg < 120
                if not (red or blue):
                    continue
                if left <= x < right and top <= y < bottom:
                    n_in += 1
                    after_px, before_px = im.getpixel((x, h + gap + y))[0], im.getpixel((x, y))[0]
                    assert (after_px < before_px) if red else (after_px > before_px), "red must mean more ink in the after panel, blue less"
                else:
                    n_out += 1
        assert n_in > 0 and n_out == 0, (n_in, n_out)
        assert im.getpixel((0, 0)) == (255, 255, 255) and im.getpixel((0, h + gap))[0] == 255, "the before and after panels are black on white"


def test_diff_lays_out_with_kerning_so_a_kern_change_shows(tmp_path, folders):
    """A copy of the neutral roman with one GPOS pair value raised by +80: the pair is a PairValueRecord the test finds by reading
    the font's PairPos for two glyphs adjacent in exactly ONE title. That title changes, the other five do not, and diff.json
    records `layout: raqm`. Weakest mutation, by hand 2026-11-16: `load_pil_font` using `ImageFont.Layout.BASIC` (GPOS ignored, so
    the changed pair draws as before) turned it red on 'the title with the pair did not change'."""
    from fontTools.ttLib import TTFont
    from PIL import features
    if not features.check("raqm"):
        pytest.fail("this Pillow has no raqm layout engine; diff.py refuses to run without it, so this test cannot (NOT skipped: install requirements.txt)")
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    cmap = font.getBestCmap()
    pairpos = font["GPOS"].table.LookupList.Lookup[0].SubTable[0]
    assert pairpos.Format == 1
    records = {}
    for first, pset in zip(pairpos.Coverage.glyphs, pairpos.PairSet):
        for rec in pset.PairValueRecord:
            records[(first, rec.SecondGlyph)] = rec
    pair = None
    for title in CFG["titles"]:
        for a, b in zip(title, title[1:]):
            key = (cmap.get(ord(a)), cmap.get(ord(b)))
            if key in records and sum(a + b in t for t in CFG["titles"]) == 1:
                pair = (a + b, key)
                break
        if pair:
            break
    assert pair, "no title holds a kerned pair that no other title holds"
    records[pair[1]].Value1.XAdvance += 80
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", *SIZES)
    assert r.returncode == 0, r.stderr
    assert data["layout"] == "raqm"
    with_pair = [t for t in CFG["titles"] if pair[0] in t]
    assert len(with_pair) == 1
    for e in data["entries"]:
        expect = e["group"] == "roman" and e["title"] in with_pair
        where = f"{e['group']} {e['instance']} {e['size']}px {e['title']!r}"
        assert (e["changed_px"] > 0) == expect, f"{where}: the pair title {'did not change' if expect else 'changed but lacks the pair'} (pair {pair[0]!r})"


def test_diff_renders_every_instance_at_every_size(tmp_path, folders):
    """The entry count equals the sum over groups of instances x titles x sizes, counted from font.json. A copy whose gvar deltas
    for `o` that peak at the wght maximum are enlarged by +60 in x changes the Bold and Display Bold entries and leaves the
    Regular and Display ones (wght 400, where those tuples have no weight) alone. Weakest mutation, by hand 2026-11-16: the instance
    loop in `run()` reduced to the group's first instance location (every instance rendered at Regular) turned it red on the
    Bold entry 'did not change'."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    g = font["glyf"]["o"]
    n_points = len(g.coordinates)
    tuples = [v for v in font["gvar"].variations["o"] if v.axes.get("wght", (0, 0, 0))[1] == 1.0]
    assert tuples, "the neutral roman's `o` has no gvar tuple peaking at the weight maximum"
    for v in tuples:
        v.coordinates = [(dx + 60, dy) if i < n_points else (dx, dy) for i, (dx, dy) in enumerate(v.coordinates)]
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", *SIZES)
    assert r.returncode == 0, r.stderr
    per_group = {name: len(g["instances"]) for name, g in CFG["groups"].items()}
    assert len(data["entries"]) == sum(per_group.values()) * len(CFG["titles"]) * len(SIZES)
    uses_o = set(titles_with("o"))
    by = {}
    for e in data["entries"]:
        if e["group"] == "roman" and e["title"] in uses_o:
            by.setdefault(e["instance"], []).append(e["changed_px"] > 0)
    assert set(by) == {i["name"] for i in CFG["groups"]["roman"]["instances"]}, sorted(by)
    for name in ("Bold", "Display Bold"):
        assert all(by[name]) and len(by[name]) == len(uses_o) * len(SIZES), f"the {name} entries did not change: {by[name]}"
    for name in ("Regular", "Display"):
        assert not any(by[name]), f"the {name} entries changed, but the enlarged deltas have no weight at wght 400: {by[name]}"
    assert not any(e["changed_px"] for e in data["entries"] if e["group"] == "italic")


def test_diff_renders_without_the_autohinter(tmp_path, built, monkeypatch):
    """FreeType autohints a TrueType font with no font program (measured 2026-11-16: the neutral roman, `B` at 16 px, differs by
    212 grey levels once a one-instruction fpgm is added, and renders the same with its `prep` deleted). Two checks. (1) diff.py's
    own instance file, drawn through its own `draw`, differs from plain Pillow on the same instance (this test's own instancer run,
    no fpgm) by more than 100 grey levels at 16 px, scale 1. (2) Every font `main()` draws carries an `fpgm` table (read back from
    the file Pillow was given), and diff.json carries the hinting line. Weakest mutation, by hand 2026-11-16: the `with_fpgm(static)`
    call in `instance_file()` removed turned both red (max difference 0; no fpgm table)."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from PIL import Image, ImageChops, ImageDraw, ImageFont
    mod = load_diff_module()
    loc = dict(next(i for i in CFG["groups"]["roman"]["instances"] if i["name"] == "Regular")["location"])
    ours = mod.instance_file(built[0], loc, tmp_path / "ours.ttf")
    plain = instancer.instantiateVariableFont(TTFont(str(built[0])), loc, inplace=False)
    plain.flavor = None
    plain.save(str(tmp_path / "plain.ttf"))
    assert "fpgm" not in TTFont(str(tmp_path / "plain.ttf")), "the plain control must have no font program"

    def draw_b(font):
        im = Image.new("L", (60, 40), 255)
        ImageDraw.Draw(im).text((8, 30), "B", font=font, fill=0, anchor="ls")
        return im
    ours_im = draw_b(mod.load_pil_font(ours, 16))
    plain_im = draw_b(ImageFont.truetype(str(tmp_path / "plain.ttf"), 16, layout_engine=ImageFont.Layout.RAQM))
    assert ImageChops.difference(ours_im, plain_im).getextrema()[1] > 100, "diff.py's render equals plain Pillow's: the autohinter is not suppressed"
    seen = []
    real = mod.draw

    def spy(font, text, size, baseline, margin):
        seen.append("fpgm" in TTFont(font.path))
        return real(font, text, size, baseline, margin)
    monkeypatch.setattr(mod, "draw", spy)
    before = tmp_path / "before"
    before.mkdir()
    for f in built:
        shutil.copyfile(f, before / f.name)
    rc = mod.main([str(tmp_path / "o"), "--font", str(NEUTRAL / "font.json"), "--before", str(before), "--sizes", "16", "--scale", "1"])
    assert rc == 0 and len(seen) > 20 and all(seen), f"{seen.count(False)} of {len(seen)} fonts drawn had no fpgm"
    data = json.loads((tmp_path / "o" / "diff.json").read_text(encoding="utf-8"))
    assert "fpgm" in data["hinting"] and "autohint" in data["hinting"], data["hinting"]


def test_diff_refuses_a_missing_group_file_naming_it(tmp_path, folders):
    """Exit 2 and the missing path named when --before lacks a group's file; nothing is written. Weakest mutation, by hand 2026-11-16:
    the `missing` check in `run()` removed (the run then crashes in fontTools with a different exit code and no path)."""
    before, after = folders
    (before / "Sampler-Italic-VF.woff2").unlink()
    r, out, data = diff(tmp_path, before, after, "--sizes", "16")
    assert r.returncode == 2 and str(before / "Sampler-Italic-VF.woff2") in r.stderr, (r.returncode, r.stderr[-300:])
    assert data is None


def test_diff_imports_name_the_install_command_on_the_wrong_interpreter():
    """A wrong interpreter (no fontTools) exits 1 with the script's name, the module, and the venv command, not a traceback, as every
    other script does (tests/test_check_env.py). The real `instance_file` is called with fontTools blocked. Weakest mutation, by hand
    2026-11-16: the `except ImportError` in `need()` narrowed to `except KeyError`."""
    import subprocess
    code = ("import runpy, sys\nsys.modules['fontTools'] = None\n"
            f"g = runpy.run_path({str(DIFF)!r}, run_name='not_main')\ng['instance_file']('x.woff2', {{}}, 'y.ttf')\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 1 and "diff.py cannot import fontTools" in r.stderr and ".venv/bin/pip install -r requirements.txt" in r.stderr, r.stderr[-400:]
    assert "Traceback" not in r.stderr



def test_diff_counts_an_advance_change_with_no_ink_change_as_changed(tmp_path, folders):
    """Review finding T1: the advance width of the LAST glyph of a title can change while no pixel does (the ink is the same, the
    line is longer). The test raises the hmtx advance of `4` by 60 units (outline untouched; `4` is only the last glyph of one title,
    "Notes from the Third Floor #4", and no title has another digit). That title at every roman instance and size must be reported
    changed with changed_px 0 and different advances, diff.md must say so and count it, and nothing else is changed. Weakest mutation,
    by hand 2026-11-16: `or e["advance_changed"]` removed from the `changed` list in `run()` (a changed advance reported as unchanged)."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    adv, lsb = font["hmtx"].metrics["four"]
    font["hmtx"].metrics["four"] = (adv + 60, lsb)
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", *SIZES)
    assert r.returncode == 0, r.stderr
    title = next(t for t in CFG["titles"] if t.endswith("4"))
    expect = len(CFG["groups"]["roman"]["instances"]) * len(SIZES)
    moved = [e for e in data["entries"] if e["advance_before"] != e["advance_after"]]
    assert len(moved) == expect and {e["title"] for e in moved} == {title} and {e["group"] for e in moved} == {"roman"}, [(e["title"], e["group"]) for e in moved][:4]
    for e in moved:
        assert e["changed_px"] == 0, "the fixture must move the advance and no ink"
        assert e["advance_after"] - e["advance_before"] > 0.5, e
    assert data["changed"] == expect, data["changed"]
    md = (out / "diff.md").read_text(encoding="utf-8")
    assert f"{expect} of {len(data['entries'])} renders changed" in md and "Notes from the Third Floor #4" in md


@pytest.mark.parametrize("how", ["empty list", "key omitted"])
def test_diff_refuses_a_group_with_no_instances_naming_it(tmp_path, folders, how):
    """Review finding T2: a group whose `instances` is an empty list used to produce a successful empty diff (which reads as
    "unchanged"), and an omitted key raised a KeyError. Both now exit 2 naming the group, and nothing is written. Weakest mutation,
    by hand 2026-11-16: the `bad` check in `run()` removed (the empty list then exits 0; the omitted key exits 1)."""
    before, after = folders
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    if how == "empty list":
        cfg["groups"]["italic"]["instances"] = []
    else:
        del cfg["groups"]["italic"]["instances"]
    font = tmp_path / "font.json"
    font.write_text(json.dumps(cfg), encoding="utf-8")
    r, out, data = diff(tmp_path, before, after, "--sizes", "16", font=font)
    assert r.returncode == 2 and "italic" in r.stderr and "instances" in r.stderr, (r.returncode, r.stderr[-300:])
    assert data is None


def test_diff_does_not_clip_a_contour_moved_outside_the_line_box(tmp_path, folders):
    """Review finding T3: the canvas was sized from the advance and the line's ascent and descent, so a contour moved far above the
    ascender was cut off before the comparison saw it. The test sets the title to `o`, moves the after font's `o` up by 1500 units
    (48 px at 32 px, an integer, so the moved glyph has exactly the same pixels), and reads the PNG: the after panel holds exactly as
    much ink as the before panel, and changed_px is the sum of the two (the glyphs are far apart, so no pixel is shared). Weakest
    mutation, by hand 2026-11-16: `canvas_for` sized from `getlength` and `getmetrics` only (the after panel then holds 0 ink)."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    glyph = font["glyf"]["o"]
    glyph.coordinates.translate((0, 1500))
    glyph.recalcBounds(font["glyf"])
    save_woff2(font, after / "Sampler-VF.woff2")
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["titles"] = ["o"]
    cfgfile = tmp_path / "font.json"
    cfgfile.write_text(json.dumps(cfg), encoding="utf-8")
    r, out, data = diff(tmp_path, before, after, "--sizes", "16", font=cfgfile)
    assert r.returncode == 0, r.stderr
    entry = next(e for e in data["entries"] if e["group"] == "roman" and e["instance"] == "Regular")
    pb, pa = panels(out / entry["png"], entry)
    ink_b, ink_a = sum(v < 247 for v in pb), sum(v < 247 for v in pa)
    assert ink_b > 20 and ink_a == ink_b, f"the moved glyph was clipped: {ink_a} inked pixels after, {ink_b} before"
    assert entry["changed_px"] == ink_a + ink_b, (entry["changed_px"], ink_a, ink_b)


def test_diff_share_and_the_order_of_diff_md(tmp_path, folders):
    """Review finding T4: nothing asserted `share` or the sort, so `share = 0` and a reversed sort passed. With `o` shifted +30 units
    (as in the moved-glyph test), the three entries with the most changed pixels are read back from their PNGs and `share` is
    recomputed here as changed pixels (grey levels differing by more than 8) over pixels where either panel has ink (under 247),
    to the 6 decimals diff.json keeps. The shares in diff.md's table must be non-increasing and equal the changed entries'. Weakest
    mutations, by hand 2026-11-16: `share` forced to 0; the sort key reversed (`-e["share"]` to `e["share"]`)."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    glyph = font["glyf"]["o"]
    glyph.coordinates.translate((30, 0))
    glyph.recalcBounds(font["glyf"])
    font["hmtx"].metrics["o"] = (font["hmtx"].metrics["o"][0], glyph.xMin)
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", *SIZES)
    assert r.returncode == 0, r.stderr
    changed = [e for e in data["entries"] if e["png"]]
    assert len(changed) > 10
    for e in sorted(changed, key=lambda e: -e["changed_px"])[:3] + changed[:2]:
        pb, pa = panels(out / e["png"], e)
        n_changed = sum(abs(x - y) > 8 for x, y in zip(pb, pa))
        n_ink = sum(min(x, y) < 247 for x, y in zip(pb, pa))
        assert n_changed == e["changed_px"] and n_changed > 0
        assert e["share"] > 0 and abs(e["share"] - n_changed / n_ink) < 1e-6, (e["share"], n_changed / n_ink)
    md = (out / "diff.md").read_text(encoding="utf-8")
    shares = [float(m.group(1)) for m in re.finditer(r"^\| (\d\.\d{4}) \|", md, re.M)]
    assert len(shares) == len(changed) == data["changed"], (len(shares), len(changed))
    assert shares == sorted(shares, reverse=True) and shares[0] > shares[-1], "diff.md must list the largest share first"
    assert shares[0] == float(f"{max(e['share'] for e in changed):.4f}")


@pytest.mark.parametrize("delta,flagged", [(0.0204, True), (0.0196, False)])
def test_diff_advance_tolerance_is_compared_before_rounding(tmp_path, folders, monkeypatch, delta, flagged):
    """Review re-check: the advance tolerance (0.02 CSS px) was applied to advances already rounded to 3 places, so a raw change of
    0.0204 (advances 100.0006 to 100.0210, which round to 100.001 and 100.021) could land on the tolerance and read as unchanged. The
    renderer's advance is replaced by fixed numbers (real fonts still draw): the after file's title is `delta` CSS px wider than the
    before file's, at scale 2. Just over 0.02 must be flagged and just under must not, whatever the rounding. Weakest mutation, by
    hand 2026-11-16: `moved` computed from the rounded `adv_b`, `adv_a` in `run()` (the 0.0204 case then reads unchanged)."""
    mod = load_diff_module()
    before, after = folders
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["titles"] = ["o"]
    cfgfile = tmp_path / "font.json"
    cfgfile.write_text(json.dumps(cfg), encoding="utf-8")
    real_load, real_draw = mod.load_pil_font, mod.draw

    class Wide:
        def __init__(self, font, length):
            self.font, self.length = font, length

        def getlength(self, text):
            return self.length

        def __getattr__(self, name):
            return getattr(self.font, name)

    def load(path, px):
        base = 2 * 100.0006
        return Wide(real_load(path, px), base + (2 * delta if path.name.startswith("a-") else 0))
    monkeypatch.setattr(mod, "load_pil_font", load)
    monkeypatch.setattr(mod, "draw", lambda font, *a: real_draw(font.font, *a))
    rc = mod.main([str(tmp_path / "o"), "--font", str(cfgfile), "--before", str(before), "--after", str(after), "--sizes", "16"])
    assert rc == 0
    data = json.loads((tmp_path / "o" / "diff.json").read_text(encoding="utf-8"))
    assert len(data["entries"]) == 8 and all(e["advance_changed"] is flagged for e in data["entries"]), [e["advance_changed"] for e in data["entries"]]
    assert all(e["changed_px"] == 0 for e in data["entries"]), "the fixture changes the reported advance only"
