"""scripts/compare-shots.py, the cross-platform row comparison, run through its main() on legs built in tmp.

WHAT IT'S FOR: compare-shots.py is what a reviewer reads instead of six full-page PNGs from six runners, so a hole in it
shows a crop of the wrong element, of an unverified PNG, or of a scrolled page as if it were evidence, or hides a leg
that never ran. Each test here builds its legs the way shoot.py --rows --meta leaves them, from the schemas the plan
fixes (docs/plan-platform-shots.md sections 2.2 and 3: the schema is the contract): PNGs drawn with Pillow (a bar at
each row's box, red-fringed in one leg, one leg on a dark surface), `<name>.rows.json` and `meta*.json` written by the
test. The adversarial inputs are a leg missing its meta, a PNG without its rows file, a scrolled shot, the same key
on a different element, and a dark-surface crop for the ink figure. One test (`chrome` in its name, skipped LOUDLY
without Chrome, as in tests/test_shoot.py) feeds a real shoot.py --rows --meta leg in, so the two tools are proved to
agree on the shipped files. Every test was watched red under the mutation named in its docstring.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest
from conftest import REPO

SCRIPT = REPO / "scripts" / "compare-shots.py"
CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/157.0.8103.79 Safari/537.36"
FIREFOX_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0"
MAC = "macOS-26.7.2-arm64-arm-64bit"
WIN = "Windows-2025Server-10.0.26100-SP0"


def load():
    spec = importlib.util.spec_from_file_location("compare_shots_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = load()
Image = pytest.importorskip("PIL.Image")
ImageDraw = pytest.importorskip("PIL.ImageDraw")


def row(key, x=20, y=20, w=100, h=20, text="Harbour", size="16px", weight="400", style="normal", captured=True):
    return {"key": key, "x": x, "y": y, "w": w, "h": h, "text": text, "font_size": size, "font_weight": weight, "font_style": style,
            "captured": captured}


def shot(page="/x.html", rows=(), width=300, height=200, scale=1, scroll_y=0, bg=(255, 255, 255), ink=(0, 0, 0), fringe=False,
         gradient=False, ua=CHROME_UA, with_rows=True):
    return {"page": page, "rows": list(rows), "width": width, "height": height, "scale": scale, "scroll_y": scroll_y, "bg": bg, "ink": ink,
            "fringe": fringe, "gradient": gradient, "ua": ua, "with_rows": with_rows}


def make_leg(root, name, shots, platform=MAC, smoothing=None, browser="chrome", meta_name="meta.json", meta=True):
    """A leg folder as shoot.py --rows --meta leaves it: a PNG per shot (a bar at every row's box, drawn at device scale),
    `<stem>.rows.json` beside it, and one meta file listing the shots. Returns the folder."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    listed = []
    for s in shots:
        sc = s["scale"]
        slug = s["page"].lstrip("/").replace("/", "-").removesuffix(".html")
        png = d / f"{slug}-{s['width']}@{sc:g}x.png"
        im = Image.new("RGB", (int(s["width"] * sc), int(s["height"] * sc)), s["bg"])
        draw = ImageDraw.Draw(im)
        if s["gradient"]:
            for x in range(im.width):
                draw.line((x, 0, x, im.height), fill=(min(255, x * 2),) * 3)
        for r in s["rows"]:
            box = (round(r["x"] * sc), round(r["y"] * sc), round((r["x"] + r["w"]) * sc) - 1, round((r["y"] + r["h"]) * sc) - 1)
            draw.rectangle(box, fill=s["ink"])
            if s["fringe"]:
                draw.rectangle((box[0], box[1], box[0] + 1, box[3]), fill=(255, 0, 0))
        im.save(png)
        rows = {"shot": "t" + slug, "page": s["page"], "width": s["width"], "height": s["height"], "scale": sc, "scroll_x": 0,
                "scroll_y": s["scroll_y"], "viewport_w": s["width"], "viewport_h": s["height"], "ua": s["ua"], "rows": s["rows"]}
        if s["with_rows"]:
            png.with_suffix(".rows.json").write_text(json.dumps(rows), encoding="utf-8")
        listed.append({"png": f"leg/{png.name}", "verified": True, "ua": s["ua"], "rows": len(s["rows"]), "height": s["height"]})
    if meta:
        (d / meta_name).write_text(json.dumps({"platform": platform, "system": platform.split("-")[0], "machine": "x", "python": "3.12.10",
                                               "browser": browser, "launcher": "/chrome", "font_smoothing": smoothing, "args": [],
                                               "shots": listed, "failed": [], "departures": []}), encoding="utf-8")
    return d


def run(out, legs, *extra):
    code = cs.main([str(out), *map(str, legs), *extra])
    md = (out / "compare.md").read_text(encoding="utf-8")
    data = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    return code, md, data


def section(md, title):
    """The lines of one `## title` section of compare.md."""
    part = md.split(f"\n## {title}\n", 1)[1]
    return part.split("\n## ", 1)[0]


THREE = [row("a", y=20, size="16px"), row("b", y=60, size="24px", text="Bay"), row("c", y=100, size="40px", text="Quay")]


def test_compare_writes_one_image_per_row_at_the_zoom_with_every_leg_in_order(tmp_path):
    """Two legs, three rows, shot at scale 2 and compared at --zoom 3: three PNGs `x-<key>@2x.png`, each
    zoom x (w+4) x scale wide and 2 x (zoom x (h+4) x scale + LABEL_H) tall, and leg B's red fringe only in the lower
    half (command-line order). Mutations watched red on 2026-11-17: the zoom ignored (resize to the crop's own size:
    the sheet is 315 px wide, its label's width, not 624); the second leg dropped from the panels (height 160, not
    320); the second leg's panel not pasted (no red in the lower half); the panels reversed (red in the upper half)."""
    a = make_leg(tmp_path, "A", [shot(rows=THREE, scale=2)])
    b = make_leg(tmp_path, "B", [shot(rows=THREE, scale=2, fringe=True)], platform=WIN)
    code, md, data = run(tmp_path / "out", [a, b], "--zoom", "3")
    assert code == 0, md
    names = sorted(p.name for p in (tmp_path / "out").glob("*.png"))
    assert names == ["x-a@2x.png", "x-b@2x.png", "x-c@2x.png"], names
    zoom, w, h, scale = 3, 100, 20, 2
    panel = zoom * (h + 4) * scale
    for n in names:
        im = Image.open(tmp_path / "out" / n).convert("RGB")
        assert im.size == (zoom * (w + 4) * scale, 2 * (panel + cs.LABEL_H)), (n, im.size)
        red = [(x, y) for y in range(im.height) for x in range(0, 60) if im.getpixel((x, y)) == (255, 0, 0)]
        assert red and all(y >= panel + cs.LABEL_H for _x, y in red), f"{n}: leg B's red fringe must be in the lower panel only"


def test_compare_refuses_a_bad_leg_and_still_compares_the_others(tmp_path):
    """Three legs, one with its PNG and rows but no meta file: compare.md lists that folder under Refused, the other two
    are compared, exit 0; with --min-legs 3 exit 1 and compare.md is still written. Mutations watched red on
    2026-11-17: the no-meta refusal raising SystemExit instead of returning None (the run stops, no compare.md); `ok`
    fixed at True (exit 0 under --min-legs 3)."""
    a = make_leg(tmp_path, "A", [shot(rows=THREE)])
    b = make_leg(tmp_path, "B", [shot(rows=THREE)], platform=WIN)
    bad = make_leg(tmp_path, "nometa", [shot(rows=THREE)], meta=False)
    code, md, data = run(tmp_path / "o1", [a, bad, b])
    assert code == 0, md
    assert str(bad) in section(md, "Refused") and "no meta*.json" in section(md, "Refused"), md
    assert len(data["legs"]) == 2 and sorted(r["key"] for r in data["rows"]) == ["a", "b", "c"], data
    out = tmp_path / "o2"
    code, md, _data = run(out, [a, bad, b], "--min-legs", "3")
    assert code == 1 and (out / "compare.md").is_file() and "NOT MET" in md, md


def test_compare_refuses_a_png_without_rows_and_a_scrolled_shot(tmp_path):
    """Leg A's /p2 PNG has no rows file and its /p3 shot scrolled by 300 px; leg B is clean. Both shots are under Refused
    with the reason, neither page is cropped, /p1 is. Mutations watched red on 2026-11-17, each on its own Refused
    assertion: rows_file() returning the first spelling without checking it exists (p2 is refused as "not readable
    JSON", not as a PNG without rows); the scroll check removed (p3 is not refused, and cropped)."""
    def shots(dirty):
        return [shot("/p1.html", [row("k")]), shot("/p2.html", [row("k")], with_rows=not dirty),
                shot("/p3.html", [row("k")], scroll_y=300 if dirty else 0)]
    a = make_leg(tmp_path, "A", shots(True))
    b = make_leg(tmp_path, "B", shots(False))
    code, md, data = run(tmp_path / "out", [a, b])
    assert code == 0, md
    refused = section(md, "Refused")
    assert "p2-300@1x.png: no .rows.json beside it" in refused, refused
    assert "p3-300@1x.png: scrolled by 0,300 px: boxes are not PNG coordinates" in refused, refused
    assert sorted(p.name for p in (tmp_path / "out").glob("*.png")) == ["p1-k@1x.png"]


def test_compare_pairs_rows_by_key_and_fields_not_by_key_alone(tmp_path):
    """`probe-2` is "Title" 48px normal in leg A and "Byline" 16px italic in leg B (a leg with one more visible element
    shifts every later probe key): it is under Mismatched with both field sets and gets no PNG; `probe-1`, equal in
    both, is cropped. Mutation watched red on 2026-11-17: the field comparison dropped (`if False and any(...)`: the
    mismatch is cropped as x-probe-2@1x.png)."""
    a = make_leg(tmp_path, "A", [shot(rows=[row("probe-1", text="Harbour"), row("probe-2", y=60, text="Title", size="48px")])])
    b = make_leg(tmp_path, "B", [shot(rows=[row("probe-1", text="Harbour"), row("probe-2", y=60, text="Byline", size="16px", style="italic")])])
    code, md, data = run(tmp_path / "out", [a, b])
    assert code == 0, md
    mm = section(md, "Mismatched")
    assert "`probe-2`" in mm and '"Title"' in mm and '"Byline"' in mm and '"48px"' in mm and '"italic"' in mm, mm
    assert sorted(p.name for p in (tmp_path / "out").glob("*.png")) == ["x-probe-1@1x.png"]


def test_compare_omits_a_row_a_leg_lacks_and_a_row_below_the_capture_and_says_so(tmp_path):
    """`only-b` is in leg B only and `low` is captured false in leg A: the first is under "Not in every leg" naming leg 1,
    the second under "Below the capture" naming leg 1, and neither gets a PNG. Mutation watched red on 2026-11-17:
    the keys taken from the first leg only (`keys = list(per_leg[0])`: only-b vanishes without a line)."""
    a = make_leg(tmp_path, "A", [shot(rows=[row("k"), row("low", y=60, captured=False)])])
    b = make_leg(tmp_path, "B", [shot(rows=[row("k"), row("low", y=60), row("only-b", y=100)])])
    code, md, data = run(tmp_path / "out", [a, b])
    assert code == 0, md
    assert "`only-b`: not in leg(s) 1" in section(md, "Not in every leg"), md
    assert "`low`" in section(md, "Below the capture") and "captured false in leg(s) 1" in section(md, "Below the capture"), md
    assert sorted(p.name for p in (tmp_path / "out").glob("*.png")) == ["x-k@1x.png"]


def test_compare_ink_is_measured_against_the_crops_own_background(tmp_path):
    """Five legs of one row: a bar of grey 55 on white; the same contrast inverted on a near-black (cloth) surface,
    grey 220 on 20; a red (255,0,0) bar and a grey 76 bar on white (equal luma, 76); and a bar on a horizontal gradient.
    The first two give equal ink, the red and grey give equal ink, the gradient prints `ink n/a`. Mutations watched
    red on 2026-11-17: L_bg fixed at 255 (the cloth leg reads 0.29 against the paper leg's 0.63); `convert("L")`
    replaced by the R channel (`getchannel(0)`: the red bar reads 0.0); the uniform-border check removed (the gradient
    gets a number)."""
    one = [row("k", x=20, y=20, w=100, h=20)]
    legs = [make_leg(tmp_path, "paper", [shot(rows=one, ink=(55, 55, 55))]),
            make_leg(tmp_path, "cloth", [shot(rows=one, bg=(20, 20, 20), ink=(220, 220, 220))]),
            make_leg(tmp_path, "red", [shot(rows=one, ink=(255, 0, 0))]),
            make_leg(tmp_path, "grey", [shot(rows=one, ink=(76, 76, 76))]),
            make_leg(tmp_path, "gradient", [shot(rows=one, gradient=True)])]
    code, md, data = run(tmp_path / "out", legs)
    assert code == 0, md
    (r,) = data["rows"]
    paper, cloth, red, grey, grad = r["ink"]
    assert paper > 0 and cloth == pytest.approx(paper, rel=1e-9), r["ink"]
    assert red > 0 and red == pytest.approx(grey, rel=1e-9), r["ink"]
    assert grad is None and "leg 5 ink n/a" in section(md, "Rows"), md


def test_compare_md_orders_rows_by_font_size_ascending_and_labels_legs_from_meta(tmp_path):
    """Rows at 48px, 9.5px and 16px (in that page order) are listed 9.5, 16, 48: numeric, so neither page order nor a
    string sort passes. Each leg's line carries the platform and the ua's browser token, never the folder name; Windows
    legs read `ClearType, RGB` (FontSmoothingType 2, orientation 1), `grayscale` (type 1) and `smoothing off`
    (FontSmoothing "0"). Mutations watched red on 2026-11-17: the sort removed (48px first); the label built from
    the folder name; the label read from FontSmoothing instead of FontSmoothingType (FontSmoothing "2" everywhere:
    the grayscale leg reads ClearType)."""
    rows = [row("big", y=20, size="48px", text="Big"), row("tiny", y=60, size="9.5px", text="Tiny"), row("mid", y=100, size="16px", text="Mid")]
    legs = [make_leg(tmp_path, "folder-mac-xyz", [shot(rows=rows)]),
            make_leg(tmp_path, "folder-w1-xyz", [shot(rows=rows, ua=FIREFOX_UA)], platform=WIN, browser="firefox",
                     smoothing={"FontSmoothing": "2", "FontSmoothingType": 2, "FontSmoothingGamma": 1000, "FontSmoothingOrientation": 1}),
            make_leg(tmp_path, "folder-w2-xyz", [shot(rows=rows)], platform=WIN,
                     smoothing={"FontSmoothing": "2", "FontSmoothingType": 1, "FontSmoothingGamma": 1000, "FontSmoothingOrientation": 1}),
            make_leg(tmp_path, "folder-w3-xyz", [shot(rows=rows)], platform=WIN,
                     smoothing={"FontSmoothing": "0", "FontSmoothingType": 2, "FontSmoothingGamma": 1000, "FontSmoothingOrientation": 1})]
    code, md, data = run(tmp_path / "out", legs)
    assert code == 0, md
    listed = [ln.split("`")[1] for ln in section(md, "Rows").splitlines() if ln.startswith("- `")]
    assert listed == ["tiny", "mid", "big"], listed
    legs_md = section(md, "Legs")
    assert "folder-" not in legs_md, legs_md
    lines = [ln for ln in legs_md.splitlines() if ln[:2] in ("1.", "2.", "3.", "4.")]
    assert lines[0] == f"1. {MAC} · HeadlessChrome/157.0", lines
    assert lines[1] == f"2. {WIN} · Firefox/160.0 · ClearType, RGB", lines
    assert lines[2] == f"3. {WIN} · HeadlessChrome/157.0 · grayscale", lines
    assert lines[3] == f"4. {WIN} · HeadlessChrome/157.0 · smoothing off", lines


def test_compare_reads_several_meta_files_in_one_leg(tmp_path):
    """Each leg has meta-specimen.json (the specimen invocation) and meta-pages.json (the pages invocation): shots from
    both are compared. Mutation watched red on 2026-11-17: only meta.json read (`d.glob("meta.json")`: both legs refused,
    exit 1)."""
    legs = []
    for name in ("A", "B"):
        make_leg(tmp_path, name, [shot("/review/specimen.html", [row("legibility")])], meta_name="meta-specimen.json")
        legs.append(make_leg(tmp_path, name, [shot("/index.html", [row("probe-1")])], meta_name="meta-pages.json"))
    code, md, data = run(tmp_path / "out", legs)
    assert code == 0, md
    assert sorted(p.name for p in (tmp_path / "out").glob("*.png")) == ["index-probe-1@1x.png", "review-specimen-legibility@1x.png"]


def test_chrome_compare_reads_a_rows_file_shoot_py_wrote(tmp_path):
    """The seam between the two tools on the shipped files: shoot.py --rows --meta, run for real in Chrome twice on a page
    with three data-fd-row elements, writes two legs, and compare-shots.py accepts both, refuses nothing and crops all
    three rows. Skips LOUDLY without Chrome. Mutation to watch red: compare-shots.py's rows_file() looking for one
    spelling only (`<name>.png.rows.json` alone, or `<name>.rows.json` alone): whichever shoot.py does not write
    refuses every shot. NOT YET WATCHED RED on 2026-11-17: shoot.py's --rows and --meta (work item A1) did not exist
    when this test was written; it is to be run, and mutated, at integration."""
    sys.path.insert(0, str(REPO / "tests"))
    from test_shoot import chrome_or_skip, make_font
    chrome = chrome_or_skip()
    site = tmp_path / "site"
    (site / "fonts").mkdir(parents=True)
    make_font(site / "fonts" / "Probe.woff2", italic=False)
    css = ('@font-face { font-family: Probe; src: url(/fonts/Probe.woff2) format("woff2"); }\n'
           "p { font-family: Probe, serif; font-weight: 400; font-synthesis: none; margin: 0 0 24px }")
    body = "".join(f'<p data-fd-row="r{i}" style="font-size:{s}px">Harbour {i}</p>' for i, s in enumerate((12, 24, 48)))
    (site / "rows.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>",
                                    encoding="utf-8")
    legs = []
    for name in ("one", "two"):
        leg = tmp_path / name
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(leg), "--serve", str(site), "--pages", "rows.html",
                            "--widths", "1280", "--scales", "1", "--bands", "none", "--family", "Probe", "--font-url", "/fonts/Probe.woff2",
                            "--rows", "--meta", str(leg / "meta.json")],
                           capture_output=True, text=True, timeout=240, env={**os.environ, "CHROME": chrome})
        assert r.returncode == 0, r.stderr
        legs.append(leg)
    code, md, data = run(tmp_path / "out", legs)
    assert code == 0 and data["refused"] == [] and data["mismatched"] == [], md
    assert sorted(r["key"] for r in data["rows"]) == ["r0", "r1", "r2"], md
    assert all(pathlib.Path(tmp_path / "out" / r["png"]).is_file() for r in data["rows"])
