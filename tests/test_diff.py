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


# ---------------------------------------------------------------------------------------------------------------------------
# 0.8.0: the file-name lookup (issue 17), the shared-name refusal and the by-value section. Each test below fails on the 0.7.1
# tree on the assertion named by its message prefix; the weakest mutations to watch go red are named in each docstring.
# ---------------------------------------------------------------------------------------------------------------------------

EXAMPLES = REPO / "examples"


def site_face(tmp_path, files):
    """A face inside a sample site: tmp_path/site/tools/face/font.json is the neutral font.json with out_dir "." and only the
    groups named in `files` ({group: file key}); returns the font.json path. The woff2 files are the caller's to place."""
    face = tmp_path / "site" / "tools" / "face"
    face.mkdir(parents=True)
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["out_dir"] = "."
    cfg["groups"] = {g: dict(cfg["groups"][g], file=f) for g, f in files.items()}
    (face / "font.json").write_text(json.dumps(cfg), encoding="utf-8")
    shutil.copyfile(NEUTRAL / "concepts.js", face / "concepts.js")
    return face / "font.json"


def run_diff(out, font, *extra):
    r = run([sys.executable, str(DIFF), str(out), "--font", str(font), *extra])
    data = json.loads((out / "diff.json").read_text(encoding="utf-8")) if (out / "diff.json").is_file() else None
    return r, data


def test_diff_finds_a_group_file_by_its_name_under_before_and_after(tmp_path, built):
    """Issue 17: a group whose `file` is `../../static/F-VF.woff2` (a site that ships its font outside the face folder) is looked
    up as `F-VF.woff2` under --before and --after, which is what `build.py --out-dir` writes, instead of walking out of the folder.
    Second run, no --after: the after side is the shipped file where font.json puts it (resolved), recorded in diff.json. The
    expected entry count is groups x instances x titles x sizes counted from font.json. Weakest mutation to watch red: `group_files()`
    keeping the relative path under --before (the run exits 2 naming a path outside the folder)."""
    font = site_face(tmp_path, {"roman": "../../static/F-VF.woff2"})
    for d in ("site/static", "before", "after"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built[0], tmp_path / d / "F-VF.woff2")
    r, data = run_diff(tmp_path / "o1", font, "--before", str(tmp_path / "before"), "--after", str(tmp_path / "after"), "--sizes", "16")
    assert r.returncode == 0, f"issue-17 basename lookup: diff.py exited {r.returncode} on a group whose file is ../../static/F-VF.woff2: {r.stderr}"
    assert len(data["entries"]) == len(CFG["groups"]["roman"]["instances"]) * len(CFG["titles"]) * 1, len(data["entries"])
    r2, data2 = run_diff(tmp_path / "o2", font, "--before", str(tmp_path / "before"), "--sizes", "16")
    assert r2.returncode == 0, f"issue-17 basename lookup, default after side: diff.py exited {r2.returncode}: {r2.stderr}"
    assert data2["files"]["roman"]["after"].endswith("static/F-VF.woff2"), data2["files"]
    assert data2["files"]["roman"]["before"].endswith("before/F-VF.woff2"), data2["files"]


def test_diff_refuses_two_groups_whose_files_share_a_name(tmp_path, built):
    """Two groups whose `file` keys end in the same name would be one file under --before and --after, so one group would be compared
    with the other's font and the run would read as 'unchanged'. Exit 2, both groups and the name in stderr, nothing written. The
    files exist under both folders, so the missing-file refusal cannot be what answers. Weakest mutation to watch red: the
    shared-name check removed (the run compares roman with itself and exits 0)."""
    font = site_face(tmp_path, {"roman": "a/F-VF.woff2", "italic": "b/F-VF.woff2"})
    for d in ("before", "after"):
        (tmp_path / d).mkdir()
        shutil.copyfile(built[0], tmp_path / d / "F-VF.woff2")
    r, data = run_diff(tmp_path / "o", font, "--before", str(tmp_path / "before"), "--after", str(tmp_path / "after"), "--sizes", "16")
    assert r.returncode == 2 and "share the file name F-VF.woff2" in r.stderr, f"same-name groups: exit {r.returncode}: {r.stderr}"
    assert "roman" in r.stderr and "italic" in r.stderr, r.stderr
    assert data is None and not (tmp_path / "o" / "diff.md").exists()


def test_diff_by_value_reports_no_difference_between_a_font_and_itself(tmp_path, folders):
    """The identity run: the neutral build against a copy of itself. diff.json has a `values` entry per group with no differences,
    some strings shaped, and the group's named-instance locations from font.json; diff.md says `<group>: no difference by value`
    for each group. Weakest mutation to watch red: `value_diff` returning one fixed difference line for every pair."""
    before, after = folders
    r, out, data = diff(tmp_path, before, after, "--sizes", "16")
    assert r.returncode == 0, r.stderr
    assert data.get("values"), "by-value section missing from diff.json (identity)"
    assert set(data["values"]) == set(CFG["groups"]), sorted(data["values"])
    for g, v in data["values"].items():
        assert v["differences"] == [], (g, v["differences"][:3])
        assert v["strings_shaped"] > 0, (g, v["strings_shaped"])
        assert v["locations"] == [i["location"] for i in CFG["groups"][g]["instances"]], (g, v["locations"])
    md = (out / "diff.md").read_text(encoding="utf-8")
    assert "## By value" in md
    for g in CFG["groups"]:
        assert f"{g}: no difference by value" in md, g


def test_diff_by_value_names_what_moved_in_the_roman_and_nothing_in_the_italic(tmp_path, folders):
    """The after roman is doctored here with fontTools: `o` shifted +30 in x with its lsb, the advance of `four` raised by 60, one
    GPOS PairValueRecord raised by 80 (a pair of two letters the cmap maps), name ID 5 rewritten. diff.json's roman differences hold
    a line for each (the outline, the hmtx record, the GPOS pair, HarfBuzz shaping of the pair, the instanced outline, the name),
    the italic holds none, and diff.md lists them under `## By value`. Weakest mutation to watch red: the roman compared with
    itself in `run()`'s value pass (every line vanishes)."""
    from fontTools.ttLib import TTFont
    before, after = folders
    font = TTFont(str(after / "Sampler-VF.woff2"))
    glyph = font["glyf"]["o"]
    glyph.coordinates.translate((30, 0))
    glyph.recalcBounds(font["glyf"])
    font["hmtx"].metrics["o"] = (font["hmtx"].metrics["o"][0], glyph.xMin)
    adv, lsb = font["hmtx"].metrics["four"]
    font["hmtx"].metrics["four"] = (adv + 60, lsb)
    reverse = {g: c for c, g in font.getBestCmap().items()}
    pairpos = font["GPOS"].table.LookupList.Lookup[0].SubTable[0]
    assert pairpos.Format == 1
    moved = None
    for first, pset in zip(pairpos.Coverage.glyphs, pairpos.PairSet):
        for rec in pset.PairValueRecord:
            if first in reverse and rec.SecondGlyph in reverse and rec.Value1 is not None and getattr(rec.Value1, "XAdvance", 0):
                moved = rec
                break
        if moved:
            break
    assert moved, "the fixture has no kerned pair of two mapped glyphs"
    moved.Value1.XAdvance += 80
    font["name"].setName("Version 9.99 doctored by the test", 5, 3, 1, 0x409)
    save_woff2(font, after / "Sampler-VF.woff2")
    r, out, data = diff(tmp_path, before, after, "--sizes", "16")
    assert r.returncode == 0, r.stderr
    assert data.get("values"), "by-value section missing from diff.json (moved)"
    lines = data["values"]["roman"]["differences"]
    assert any(line.startswith("glyph o: default outline differs") for line in lines), lines[:12]
    assert any(re.match(r"glyph four: hmtx", line) for line in lines), lines[:12]
    assert any(line.startswith("GPOS pair") for line in lines), lines[:12]
    assert any(line.startswith("shaped '") for line in lines), lines[:12]
    assert any("glyph o @ (" in line for line in lines), lines[:12]
    assert any(line.startswith("name 5 (") for line in lines), lines[:12]
    assert data["values"]["italic"]["differences"] == []
    md = (out / "diff.md").read_text(encoding="utf-8")
    assert "## By value" in md and md.index("## By value") < md.index("glyph o: default outline differs")
    assert "italic: no difference by value" in md


@pytest.fixture(scope="module")
def example_builds(tmp_path_factory):
    """{name: build folder}: examples/<name> built by `build.py --out-dir` into a temp folder, once per module."""
    cache = {}

    def get(name):
        if name not in cache:
            out = tmp_path_factory.mktemp(f"build-{name}") / "out"
            extra = ["--no-requirements"] if name == "bract" else []
            r = run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(EXAMPLES / name / "font.json"), "--out-dir", str(out), *extra])
            assert r.returncode == 0, f"the {name} example did not build:\n{r.stderr[-1500:]}"
            cache[name] = out
        return cache[name]
    return get


@pytest.mark.parametrize("name", ["bract", "driftwood"])
def test_diff_by_value_runs_on_the_bract_and_driftwood_examples_against_copies_of_themselves(tmp_path, example_builds, name):
    """Bract has two axes (wght and opsz) and Driftwood's roman and italic each have one avar-mapped axis, which the group's own
    named-instance locations must handle: each example's build is compared with a copy of itself and every group reports no
    difference by value and no render changed. Weakest mutation to watch red: the instance locations fixed to `wght` and `opsz`
    (a one-axis group then fails to instance)."""
    built_dir = example_builds(name)
    before = tmp_path / "before"
    shutil.copytree(built_dir, before)
    cfg = json.loads((EXAMPLES / name / "font.json").read_text(encoding="utf-8"))
    r, data = run_diff(tmp_path / "o", EXAMPLES / name / "font.json", "--before", str(before), "--after", str(built_dir), "--sizes", "16")
    assert r.returncode == 0, r.stderr
    assert data.get("values"), "by-value section missing from diff.json (examples)"
    assert set(data["values"]) == set(cfg["groups"]), sorted(data["values"])
    for g, v in data["values"].items():
        assert v["differences"] == [], (name, g, v["differences"][:3])
        assert v["locations"] == [i["location"] for i in cfg["groups"][g]["instances"]], (name, g)
    assert f"0 of {len(data['entries'])} renders changed" in (tmp_path / "o" / "diff.md").read_text(encoding="utf-8")


def test_diff_by_value_sees_a_change_that_shows_only_at_a_named_instance(tmp_path, folders):
    """The instanced check exists for a difference the default outline does not show. Here one gvar delta of `o` is moved in the
    after roman, so the default outline is unchanged and only the instanced outline differs. value_diff, at the axis maximum,
    must report `glyph o @ (...): instanced outline differs` at the axis maximum, must NOT report it at the axis default (where
    every delta is scaled by zero), and must NOT report the default outline. Weakest mutation to watch red: the instanced
    comparison replaced by an echo of the default comparison, or by a line per location whenever the gvar tuples differ."""
    from fontTools.ttLib import TTFont
    before, after = folders
    path = after / "Sampler-VF.woff2"
    font = TTFont(str(path))
    axis = font["fvar"].axes[0]
    tv = next(v for v in font["gvar"].variations["o"] if any(c is not None for c in v.coordinates))
    i = next(k for k, c in enumerate(tv.coordinates) if c is not None)
    tv.coordinates[i] = (tv.coordinates[i][0] + 40, tv.coordinates[i][1])
    save_woff2(font, path)
    mod = load_diff_module()
    rest, peak = {axis.axisTag: axis.defaultValue}, {axis.axisTag: axis.maxValue}
    lines, _ = mod.value_diff(before / "Sampler-VF.woff2", path, [rest, peak])
    assert f"glyph o @ {mod.where_text(peak)}: instanced outline differs" in lines, lines[:12]
    # At the default location every delta is scaled by zero, so the outline there is the same: a line there would mean the
    # check reports the changed tuple, not the instanced outline.
    assert f"glyph o @ {mod.where_text(rest)}: instanced outline differs" not in lines, lines[:12]
    assert not any(ln.startswith("glyph o: default outline differs") for ln in lines), lines[:12]


def test_diff_by_value_keeps_name_records_that_share_an_id_and_language_apart(tmp_path, folders):
    """Two platform-3 name records can share a name ID and a language and differ only in encoding (Unicode BMP, encoding 1, and
    full repertoire, encoding 10). Both fonts get the same encoding-10 record for name ID 5; the after font's encoding-1 record is
    then rewritten. The difference must be reported. Weakest mutation to watch red: name records keyed by (name ID, language)
    only, so the encoding-10 record overwrites the changed encoding-1 one in both fonts and the change vanishes."""
    from fontTools.ttLib import TTFont
    before, after = folders
    paths = []
    for folder, v1 in ((before, None), (after, "Version 9.99 rewritten by the test")):
        p = folder / "Sampler-VF.woff2"
        font = TTFont(str(p))
        font["name"].setName("Version full repertoire", 5, 3, 10, 0x409)
        if v1:
            font["name"].setName(v1, 5, 3, 1, 0x409)
        save_woff2(font, p)
        paths.append(p)
    lines, _ = load_diff_module().value_diff(paths[0], paths[1], [])
    assert any(ln.startswith("name 5") and "rewritten by the test" in ln for ln in lines), lines[:12]

