#!/usr/bin/env python3
"""Puts the same row of the same page, shot on several platforms, side by side at a fixed zoom: one image per row.

WHAT IT'S FOR: the platform-shots workflow runs shoot.py on a Windows, a macOS and a Linux runner, in Chrome and in
Firefox, and each run (a "leg": one OS x one browser) leaves a folder of full-page PNGs. Finding the same title in six
6000 px PNGs by eye and cropping it at 7x is how the first Windows check was read, and it does not scale past one row.
Every verified shot made with `shoot.py --rows --meta` also carries the box of every marked row in the page (the
specimen's `data-fd-row` keys, or `probe-<n>` for the elements the probe counted on a real page), so this tool crops
each row from each leg's own PNG at its own box, scales the crop with nearest-neighbour resampling so pixels stay
pixels, labels each crop with the platform and browser the leg's meta file recorded, and stacks the legs in
command-line order. The reader opens `compare.md`, reads Refused and Mismatched first, then the smallest sizes.

    compare-shots.py OUT_DIR LEG_DIR [LEG_DIR ...] [--zoom N] [--rows KEY ...] [--min-legs N]

A LEG_DIR holds one or more `meta*.json` files (`shoot.py --meta`, one per invocation) and, for each verified shot they
list, the PNG and its `.rows.json` (`<name>.rows.json` or `<name>.png.rows.json`; both spellings are read). OUT_DIR gets
one PNG per compared row, `<page>-<key>@<scale>x.png` (`<page>-<width>-<key>@<scale>x.png` when a page was shot at more
than one width), plus `compare.md` and `compare.json`; the path of `compare.md` is printed.

What is refused, each one listed under "Refused" in compare.md and the comparison going on without it: a leg folder
with no `meta*.json`, a meta file that is not JSON, a leg whose meta files name no verified shot; a shot whose PNG is
not in the leg, whose rows file is missing (shoot.py writes it only after every proof passed, so its absence means an
unverified or hand-copied PNG), whose page had scrolled (the boxes are viewport coordinates, which are PNG coordinates
only at scroll 0), or whose page was laid out more than 2 px narrower or wider than the shot (`viewport_w` against
`width`: the boxes then belong to another layout; Chrome's command line on a Windows runner measured 1264 px for a
1280 shot, and every row under a line that wrapped differently was cropped from the wrong place). A row is cropped
only when its key is in every accepted leg's shot of that page, width and scale, `captured` is true in every one, its
`text`, `font_weight` and `font_style` are equal in every one and its `font_size` agrees to 1/16 px (Firefox reports
computed sizes rounded to 1/16 px: 16.8125px where Chrome says 16.8px); otherwise it goes under "Not in every leg",
"Below the capture" or "Mismatched" with the reason, and no PNG is written for it. Exit 0 when at least --min-legs
legs (default 2) were accepted, whatever else was refused;
exit 1 below that, with compare.md still written so the reasons can be read; exit 1 also when Pillow is missing.

The ink figure. For each crop, L_bg is the median luminance (Pillow's "L", ITU-R 601 luma) of the crop's one-pixel
border, which is the row's margin, so the background is measured on a light and a dark surface alike; ink is the mean
of |L - L_bg| over the crop, divided by 255. compare.md prints each leg's figure as a share of the first leg's. A crop
whose border spans more than 32 levels has no single background and prints `ink n/a`. The figure is a hint for where
to look and nothing more: a lighter stroke, a coloured fringe and a stroke that has broken up can give the same
number. The PNG is the evidence.

Exact guarantee: each crop is the pixels of that leg's own verified PNG inside the box that leg's own browser
reported for the element, plus 2 CSS px, unconverted (subpixel colour is kept); the label is what that leg's meta
recorded. It says nothing about a platform no leg ran on, it does not judge whether two legs differ acceptably (they
are expected to differ), and a box can be compared only when every leg marked the same element under the same key.
Copyright 2026 John Knox. MIT licence.
"""
import argparse
import json
import pathlib
import re
import statistics
import sys

if sys.version_info < (3, 10):
    sys.exit(f"compare-shots.py needs Python >= 3.10 and this is {sys.version_info[0]}.{sys.version_info[1]}; make the skill's venv with a newer "
             "one: python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt, then run .venv/bin/python3 scripts/compare-shots.py ...")

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from diff import slug  # noqa: E402  (diff.py's file-name slug, kept in one place)

MARGIN = 2  # CSS px added round every box
LABEL_H = 16  # px of the label strip above each leg's crop
BORDER_SPREAD = 32  # luminance levels: a crop border wider than this has no single background, so ink is n/a
MATCH_FIELDS = ("text", "font_size", "font_weight", "font_style")
SIZE_SLACK = 1 / 16 + 1e-6  # px: Firefox rounds a computed font-size to 1/16 px (16.8125 for Chrome's 16.8)
WIDTH_SLACK = 2  # CSS px between the page's innerWidth and the shot's width (rounding; Linux Chrome at 1.25x read 1282)
SMOOTHING_TYPE = {"2": "ClearType", "1": "grayscale"}
ORIENTATION = {"1": "RGB", "0": "BGR"}


def need(*names):
    """diff.py's lazy import guard: a wrong interpreter names the install command, not a traceback."""
    try:
        import importlib
        return [importlib.import_module(n) for n in names]
    except ImportError as exc:
        sys.exit(f"compare-shots.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the "
                 "skill's venv. Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/compare-shots.py ... (on a runner: pip install pillow)")


def fmt_scale(scale):
    return f"{float(scale):g}"


def browser_token(ua):
    """'Mozilla/5.0 ... HeadlessChrome/157.0.8103.79 ...' -> 'HeadlessChrome/157.0'; Firefox likewise; the raw ua otherwise."""
    m = re.search(r"\b(HeadlessChrome|Chrome|Firefox)/(\d+(?:\.\d+)?)", ua or "")
    return f"{m.group(1)}/{m.group(2)}" if m else (ua or "browser unknown")


def smoothing_label(fs):
    """The Windows font-smoothing summary, from FontSmoothingType and FontSmoothingOrientation (FontSmoothing is only the
    on/off flag, printed when it is "0"). None off Windows (meta records null there)."""
    if not fs:
        return None
    val = {k: (None if v is None else str(v).strip()) for k, v in fs.items()}
    if val.get("FontSmoothing") == "0":
        return "smoothing off"
    kind = SMOOTHING_TYPE.get(val.get("FontSmoothingType"))
    if kind == "ClearType":
        orient = ORIENTATION.get(val.get("FontSmoothingOrientation"), f"orientation {val.get('FontSmoothingOrientation')}")
        return f"ClearType, {orient}"
    if kind:
        return kind
    return f"smoothing type {val.get('FontSmoothingType')}"


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rows_file(png):
    for cand in (png.with_suffix(".rows.json"), png.parent / (png.name + ".rows.json")):
        if cand.is_file():
            return cand
    return None


def page_token(page):
    return slug(str(page).lstrip("/").replace("/", "-").removesuffix(".html"))


def load_leg(leg_dir, refused):
    """One leg: {dir, platform, ua, smoothing, label, metas, shots: {(page, width, scale): {png, rows}}}, or None when
    the whole leg is refused. Every refusal is appended to `refused`."""
    d = pathlib.Path(leg_dir)

    def refuse(reason, shot=None):
        refused.append({"leg": str(d), "shot": shot, "reason": reason})

    if not d.is_dir():
        refuse("not a directory")
        return None
    meta_files = sorted(d.glob("meta*.json"))
    if not meta_files:
        refuse("no meta*.json in the leg (shoot.py --meta writes it): no platform to label it with and no list of verified shots")
        return None
    metas, listed = [], []
    for mf in meta_files:
        try:
            meta = read_json(mf)
        except (OSError, ValueError) as exc:
            refuse(f"{mf.name} is not readable JSON ({exc})")
            continue
        if not isinstance(meta, dict):
            refuse(f"{mf.name} is JSON but not an object")
            continue
        bad = [k for k in ("shots", "failed") if not isinstance(meta.get(k) or [], list)]
        if bad:
            refuse(f"{mf.name} is JSON but not a meta object: its {' and '.join(bad)} is not a list")
            continue
        metas.append((mf.name, meta))
        for shot in meta.get("shots") or []:
            if not isinstance(shot, dict):
                refuse(f"{mf.name} lists a shot that is not an object ({str(shot)[:60]})")
                continue
            listed.append((mf.name, shot))
    if not metas:
        return None
    if not listed:
        refuse("its meta files name no verified shot" + _failed_note(metas))
        return None
    shots = {}
    for mf_name, shot in listed:
        # the last part after / or \: a Windows leg records leg\x.png, which pathlib on this Linux job reads as one name
        png_name = re.split(r"[\\/]", str(shot.get("png") or ""))[-1]
        if not png_name:
            refuse(f"a shot in {mf_name} has no PNG", shot=None)
            continue
        if shot.get("verified") is False:
            refuse("listed with verified false: not evidence", shot=png_name)
            continue
        png = d / png_name
        if not png.is_file():
            refuse(f"named in {mf_name} but the PNG is not in the leg", shot=png_name)
            continue
        rf = rows_file(png)
        if rf is None:
            refuse("no .rows.json beside it (shoot.py writes one only after every proof passed, so this PNG is unverified or hand-copied)",
                   shot=png_name)
            continue
        try:
            rows = read_json(rf)
        except (OSError, ValueError) as exc:
            refuse(f"{rf.name} is not readable JSON ({exc})", shot=png_name)
            continue
        if not isinstance(rows, dict) or not isinstance(rows.get("rows", []), list):
            refuse(f"{rf.name} is JSON but not a rows object", shot=png_name)
            continue
        sx, sy = rows.get("scroll_x", 0) or 0, rows.get("scroll_y", 0) or 0
        if sx or sy:
            refuse(f"scrolled by {sx},{sy} px: boxes are not PNG coordinates", shot=png_name)
            continue
        vw = rows.get("viewport_w")
        if not isinstance(vw, (int, float)) or not isinstance(rows.get("width"), (int, float)) or abs(vw - rows["width"]) > WIDTH_SLACK:
            refuse(f"laid out {vw} px wide for a {rows.get('width')} px shot: the boxes belong to another layout", shot=png_name)
            continue
        size, want = png_size(png), None
        if isinstance(rows.get("height"), (int, float)) and isinstance(rows.get("scale"), (int, float)):
            want = (round(rows["width"] * rows["scale"]), round(rows["height"] * rows["scale"]))
        if size is None or want is None or abs(size[0] - want[0]) > 1 or abs(size[1] - want[1]) > 1:
            refuse(f"the PNG is {size} px and the rows file describes a {want} px shot: the boxes are not its coordinates",
                   shot=png_name)
            continue
        try:
            unit = (str(rows["page"]), int(rows["width"]), float(rows["scale"]))
        except (KeyError, TypeError, ValueError) as exc:
            refuse(f"{rf.name} lacks page, width or scale ({exc})", shot=png_name)
            continue
        if unit in shots:
            refuse(f"a second shot of {unit[0]} at {unit[1]}@{fmt_scale(unit[2])}x in the same leg; the first ({shots[unit]['png'].name}) is kept",
                   shot=png_name)
            continue
        shots[unit] = {"png": png, "rows": rows, "ua": rows.get("ua") or shot.get("ua")}
    if not shots:
        refuse("no shot of the leg survived the checks above")
        return None
    meta = next((m for _n, m in metas if m.get("platform")), metas[0][1])
    ua = next((s["ua"] for s in shots.values() if s["ua"]), None)
    smoothing = smoothing_label(meta.get("font_smoothing"))
    label = " · ".join(x for x in (meta.get("platform") or "platform unknown", browser_token(ua), smoothing) if x)
    return {"dir": d, "platform": meta.get("platform"), "browser": meta.get("browser"), "launcher": meta.get("launcher"),
            "python": meta.get("python"), "ua": ua, "font_smoothing": meta.get("font_smoothing"), "smoothing": smoothing, "label": label,
            "metas": [n for n, _m in metas], "shots": shots, "failed": [f for _n, m in metas for f in (m.get("failed") or [])]}


def _failed_note(metas):
    failed = [f for _n, m in metas for f in (m.get("failed") or [])]
    return f" ({len(failed)} failed: {failed[0][:200]})" if failed else ""


def crop_box(row, scale, size):
    """The row's box plus MARGIN, in PNG px, clamped to the PNG; (box, clipped)."""
    left = round((float(row["x"]) - MARGIN) * scale)
    top = round((float(row["y"]) - MARGIN) * scale)
    right = round((float(row["x"]) + float(row["w"]) + MARGIN) * scale)
    bottom = round((float(row["y"]) + float(row["h"]) + MARGIN) * scale)
    box = (max(0, left), max(0, top), min(size[0], right), min(size[1], bottom))
    return box, box != (left, top, right, bottom)


def ink(crop):
    """Mean |L - L_bg| / 255 over the crop, L_bg the median luminance of its one-pixel border; None when the border is not
    uniform (spread over BORDER_SPREAD levels) or the crop is empty."""
    lum = crop.convert("L")
    w, h = lum.size
    if w < 1 or h < 1:
        return None
    px = lum.load()
    border = [px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)] + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)]
    if max(border) - min(border) > BORDER_SPREAD:
        return None
    bg = statistics.median(border)
    return sum(n * abs(v - bg) for v, n in enumerate(lum.histogram())) / (w * h) / 255


def sheet(panels, zoom):
    """The legs' crops stacked in order, each under a LABEL_H label strip; nearest-neighbour zoom."""
    image, image_draw, image_font = need("PIL.Image", "PIL.ImageDraw", "PIL.ImageFont")
    font = image_font.load_default()
    zoomed = [(label, crop.convert("RGB").resize((crop.width * zoom, crop.height * zoom), image.Resampling.NEAREST)) for label, crop in panels]
    probe = image_draw.Draw(image.new("RGB", (1, 1)))
    width = max(max(z.width for _l, z in zoomed), max(int(probe.textlength(label, font=font)) + 8 for label, _z in zoomed))
    height = sum(LABEL_H + z.height for _l, z in zoomed)
    out = image.new("RGB", (width, height), (128, 128, 128))
    draw = image_draw.Draw(out)
    y = 0
    for label, z in zoomed:
        draw.rectangle((0, y, width - 1, y + LABEL_H - 1), fill=(32, 32, 32))
        draw.text((4, y + 2), label, fill=(255, 255, 255), font=font)
        out.paste(z, (0, y + LABEL_H))
        y += LABEL_H + z.height
    return out


def px_of(size):
    try:
        return float(str(size).removesuffix("px"))
    except ValueError:
        return float("inf")


def same_element(rows):
    """Whether every leg's row describes the same element: equal text, weight and style, and all sizes within SIZE_SLACK
    of each other (the largest minus the smallest, so three legs cannot drift apart while each stays near the first)."""
    sizes = [px_of(r.get("font_size")) for r in rows]
    return (all(r.get(f) == rows[0].get(f) for r in rows for f in ("text", "font_weight", "font_style"))
            and max(sizes) - min(sizes) <= SIZE_SLACK)


def png_size(path):
    """(width, height) from a PNG's IHDR chunk, or None for a file that is not a PNG. Read without Pillow, so the loader
    can check a shot before any image library is needed."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def compare(out_dir, legs, zoom, only_keys):
    """Crops and writes every comparable row; returns (rows, mismatched, not_in_every_leg, below_capture)."""
    (image,) = need("PIL.Image")
    units = sorted({u for leg in legs for u in leg["shots"]}, key=lambda u: (u[0], u[1], u[2]))
    widths_per_page = {}
    for page, width, _s in units:
        widths_per_page.setdefault(page, set()).add(width)
    rows_out, mismatched, missing, below = [], [], [], []
    opened = {}
    for unit in units:
        page, width, scale = unit
        where = f"{page} {width}@{fmt_scale(scale)}x"
        lacking = [i + 1 for i, leg in enumerate(legs) if unit not in leg["shots"]]
        if lacking:
            missing.append({"page": page, "width": width, "scale": scale, "key": None, "missing_from": lacking,
                            "reason": f"the shot {where} is missing from leg(s) {', '.join(map(str, lacking))}: none of its rows is compared"})
            continue
        per_leg = []
        for i, leg in enumerate(legs):
            by_key = {}
            for r in leg["shots"][unit]["rows"].get("rows") or []:
                by_key.setdefault(str(r.get("key")), []).append(r)
            per_leg.append(by_key)
        keys = []
        for by_key in per_leg:
            keys += [k for k in by_key if k not in keys]
        for key in keys:
            if only_keys and key not in only_keys:
                continue
            entry = {"page": page, "width": width, "scale": scale, "key": key}
            lacking = [i + 1 for i, bk in enumerate(per_leg) if key not in bk]
            if lacking:
                missing.append({**entry, "missing_from": lacking, "reason": f"not in leg(s) {', '.join(map(str, lacking))}"})
                continue
            dupes = [i + 1 for i, bk in enumerate(per_leg) if len(bk[key]) > 1]
            if dupes:
                mismatched.append({**entry, "fields": None, "reason": f"the key appears more than once in leg(s) {', '.join(map(str, dupes))}"})
                continue
            rows = [bk[key][0] for bk in per_leg]
            uncaptured = [i + 1 for i, r in enumerate(rows) if r.get("captured") is not True]
            if uncaptured:
                below.append({**entry, "legs": uncaptured, "font_size": rows[0].get("font_size"), "text": rows[0].get("text")})
                continue
            if not same_element(rows):
                mismatched.append({**entry, "fields": [{f: r.get(f) for f in MATCH_FIELDS} for r in rows],
                                   "reason": "text or computed style differs: not the same element in every leg"})
                continue
            panels, inks, clipped = [], [], []
            for i, (leg, r) in enumerate(zip(legs, rows)):
                png = leg["shots"][unit]["png"]
                if png not in opened:
                    opened[png] = image.open(png)
                    opened[png].load()
                im = opened[png]
                box, was_clipped = crop_box(r, scale, im.size)
                if was_clipped:
                    clipped.append(i + 1)
                crop = im.crop(box)
                inks.append(ink(crop))
                panels.append((f"{leg['platform'] or 'platform unknown'} · {browser_token(leg['shots'][unit]['ua'])} · {fmt_scale(scale)}x"
                               + (f" · {leg['smoothing']}" if leg["smoothing"] else ""), crop))
            stem = page_token(page) + (f"-{width}" if len(widths_per_page[page]) > 1 else "")
            name = f"{stem}-{slug(key)}@{fmt_scale(scale)}x.png"
            sheet(panels, zoom).save(out_dir / name)
            first = inks[0]
            shares = [None if (v is None or not first) else v / first for v in inks]
            rows_out.append({**entry, **{f: rows[0].get(f) for f in MATCH_FIELDS}, "png": name, "ink": inks, "ink_share": shares,
                             "clipped_in_legs": clipped})
    rows_out.sort(key=lambda r: (r["page"], px_of(r["font_size"]), r["scale"], r["key"]))
    return rows_out, mismatched, missing, below


def markdown(legs, rows, mismatched, missing, below, refused, zoom, min_legs, ok):
    lines = ["# Platform comparison", "",
             f"{len(legs)} leg(s) accepted (at least {min_legs} needed: {'met' if ok else 'NOT MET, exit 1'}), {len(refused)} refusal(s). "
             f"Each PNG stacks the legs in the order below at {zoom}x, nearest-neighbour, colour unconverted. Read Refused and Mismatched "
             "first, then the smallest sizes. Ink is mean |L - L_bg| / 255 against the crop's own border, shown as a share of leg 1's: a "
             "hint for where to look, not a verdict; the PNG is the evidence.", "", "## Legs", ""]
    lines += [f"{i}. {leg['label']}" for i, leg in enumerate(legs, 1)] or ["(none accepted)"]
    lines += ["", "## Rows", ""]
    if not rows:
        lines.append("(no row was compared)")
    page = None
    for r in rows:
        if r["page"] != page:
            page = r["page"]
            lines += ["", f"### {page}", ""]
        inks = ", ".join(f"leg {i} ink n/a" if v is None else f"leg {i} ink " + ("n/a" if s is None else f"{s:.2f}") + f" ({v:.4f})"
                         for i, (v, s) in enumerate(zip(r["ink"], r["ink_share"]), 1))
        clip = f"; clipped to the PNG edge in leg(s) {', '.join(map(str, r['clipped_in_legs']))}" if r["clipped_in_legs"] else ""
        lines.append(f"- `{r['key']}` {r['font_size']} {r['font_weight']} {r['font_style']} at {r['width']}@{fmt_scale(r['scale'])}x: "
                     f"`{r['png']}`, text {json.dumps(r['text'], ensure_ascii=False)}; {inks}{clip}")

    def where(e):
        return f"{e['page']} {e['width']}@{fmt_scale(e['scale'])}x" + (f" `{e['key']}`" if e.get("key") else "")

    lines += ["", "## Mismatched", ""]
    for e in mismatched:
        lines.append(f"- {where(e)}: {e['reason']}")
        for i, f in enumerate(e["fields"] or [], 1):
            lines.append(f"  - leg {i}: " + ", ".join(f"{k} {json.dumps(v, ensure_ascii=False)}" for k, v in f.items()))
    lines += ["(none)"] if not mismatched else []
    lines += ["", "## Not in every leg", ""]
    lines += [f"- {where(e)}: {e['reason']}" for e in missing] or ["(none)"]
    lines += ["", "## Below the capture", ""]
    lines += [f"- {where(e)} ({e['font_size']}): captured false in leg(s) {', '.join(map(str, e['legs']))}" for e in below] or ["(none)"]
    lines += ["", "## Refused", ""]
    lines += [f"- {e['leg']}" + (f" / {e['shot']}" if e["shot"] else "") + f": {e['reason']}" for e in refused] or ["(none)"]
    lines += ["", "## Platforms", ""]
    for i, leg in enumerate(legs, 1):
        lines.append(f"- leg {i}: platform {leg['platform']}; browser {leg['browser']}; launcher {leg['launcher']}; python {leg['python']}; "
                     f"ua {json.dumps(leg['ua'])}; font smoothing {json.dumps(leg['font_smoothing'])}; meta {', '.join(leg['metas'])}"
                     + (f"; {len(leg['failed'])} shot(s) failed in this leg" if leg["failed"] else ""))
    lines += ["(none accepted)"] if not legs else []
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="directory for compare.md, compare.json and the row PNGs (created)")
    ap.add_argument("legs", nargs="+", metavar="LEG_DIR", help="one shoot.py --rows --meta output directory per OS x browser")
    ap.add_argument("--zoom", type=int, default=4, help="integer nearest-neighbour zoom of every crop (default 4)")
    ap.add_argument("--rows", nargs="+", metavar="KEY", help="compare only these row keys")
    ap.add_argument("--min-legs", type=int, default=2, help="legs that must be accepted for exit 0 (default 2)")
    args = ap.parse_args(argv)
    if args.zoom < 1:
        ap.error("--zoom must be at least 1")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    refused, legs = [], []
    for d in args.legs:
        leg = load_leg(d, refused)
        if leg:
            legs.append(leg)
    rows, mismatched, missing, below = compare(out, legs, args.zoom, set(args.rows or ())) if legs else ([], [], [], [])
    ok = len(legs) >= args.min_legs
    (out / "compare.md").write_text(markdown(legs, rows, mismatched, missing, below, refused, args.zoom, args.min_legs, ok), encoding="utf-8")
    report = {"zoom": args.zoom, "min_legs": args.min_legs, "ok": ok,
              "legs": [{"dir": str(leg["dir"]), "label": leg["label"], "platform": leg["platform"], "browser": leg["browser"],
                        "launcher": leg["launcher"], "python": leg["python"], "ua": leg["ua"], "font_smoothing": leg["font_smoothing"],
                        "metas": leg["metas"], "shots": [s["png"].name for s in leg["shots"].values()], "failed": leg["failed"]} for leg in legs],
              "rows": rows, "mismatched": mismatched, "not_in_every_leg": missing, "below_capture": below, "refused": refused}
    (out / "compare.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out / "compare.md")
    if not ok:
        print(f"compare-shots.py: {len(legs)} leg(s) accepted, fewer than --min-legs {args.min_legs}; see {out / 'compare.md'} (Refused)",
              file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
