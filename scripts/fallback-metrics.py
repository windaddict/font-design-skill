#!/usr/bin/env python3
"""Prints the CSS for a metric-matched fallback face: the values that make the first paint, set in a system
font while the web font loads, take the same room as the font will.

WHAT IT'S FOR: with `font-display: swap` the page is first laid out in the fallback (Georgia, Times, Arial)
and re-laid out when the face arrives; a wider font, or one with a taller line, moves every headline. CSS
Fonts 5 lets a `local()` @font-face rescale and re-space a system font to match (`size-adjust`,
`ascent-override`, `descent-override`, `line-gap-override`), so the swap moves little. Those four numbers come
from two fonts, so a person cannot type them; this reads the built font and each fallback font file and prints
the @font-face for each.

    fallback-metrics.py --font font.json [--group roman] [--file out/Family-VF.woff2] [--location wght=400,opsz=72]
                        [--fallback "Georgia=/path/Georgia.ttf" ...] [--text FILE]

The formula, so it can be checked by hand. Over the characters of the titles (font.json `titles`, or one title
per line of --text), for each character both fonts map:
    avg(font)  = the mean advance width in em (hmtx advance / unitsPerEm), the font at --location
                 (default: each axis at its default)
    size-adjust        = avg(web font) / avg(fallback)
    ascent-override    = hhea.ascent  / unitsPerEm / size-adjust     (descent: -hhea.descent; line gap: hhea.lineGap)
The overrides are divided by size-adjust because they are shares of the font size AFTER it is scaled; the
site-wiring guard (t) checks that override x size-adjust equals the web font's own hhea metric.

Default fallback files: Georgia, Times New Roman and Arial from the macOS Supplemental fonts, the Windows
font folder as WSL mounts it, and the Linux msttcorefonts folder, whichever exist. `--fallback NAME=PATH`
(repeatable) replaces that search with exactly the files named. With one fallback the face is called
"<Family> Fallback"; with several, "<Family> Fallback <name>". A default family with no file is skipped.

Exact guarantee: the arithmetic above on the advances and hhea metrics the two files hold. Not included:
kerning (the web font's pair kerns and the fallback's), ligatures, and any difference between the fallback
file on this machine and the one a visitor's machine has (a visitor's Georgia may be another version). The
number is one `size-adjust` for one location: a face with an optical-size axis has narrower display cuts than
text cuts, so run this at the location the headlines use (`--location opsz=72`) and treat the result as a
better starting point than none, to be confirmed by a screenshot of the swap. Nothing here is a CSS parser's
verdict: whether a browser honours the descriptors is the browser's.

Copyright 2026 John Knox. MIT licence.
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import specimen  # noqa: E402  (its default_font_file() is build.py's output naming, kept in one place)

DEFAULT_FALLBACKS = {
    "Georgia": ["/System/Library/Fonts/Supplemental/Georgia.ttf", "/Library/Fonts/Georgia.ttf", "/mnt/c/Windows/Fonts/georgia.ttf",
                "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf"],
    "Times New Roman": ["/System/Library/Fonts/Supplemental/Times New Roman.ttf", "/Library/Fonts/Times New Roman.ttf", "/mnt/c/Windows/Fonts/times.ttf",
                        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf"],
    "Arial": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "/mnt/c/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"],
}


def parse_location(text):
    """'wght=400,opsz=72' -> {'wght': 400.0, 'opsz': 72.0}; raises ValueError on anything else."""
    out = {}
    for part in filter(None, (text or "").split(",")):
        tag, sep, value = part.partition("=")
        if not sep or len(tag.strip()) != 4:
            raise ValueError(f"--location wants TAG=VALUE pairs such as wght=400,opsz=72, not {part!r}")
        out[tag.strip()] = float(value)
    return out


def load_font(path, location):
    """A TTFont for `path`; a variable font is instanced at `location` (axes not named stay at their default)."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError as exc:
        sys.exit(f"fallback-metrics.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
                 "Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/fallback-metrics.py ...")
    font = TTFont(str(path))
    if "fvar" in font:
        unknown = sorted(set(location) - {a.axisTag for a in font["fvar"].axes})
        if unknown:
            raise ValueError(f"{path}: no axis {unknown}; its axes are {[a.axisTag for a in font['fvar'].axes]}")
        font = instancer.instantiateVariableFont(font, {a.axisTag: location.get(a.axisTag, a.defaultValue) for a in font["fvar"].axes}, inplace=True)
    elif location:
        raise ValueError(f"{path} is not a variable font, so --location {location} cannot apply")
    return font


def advances(font, text):
    """{character: advance in em} for every distinct non-space-collapsing character of `text` the font maps
    (a no-break space is read as the space, as the face's cmap does)."""
    cmap, hmtx, em = font.getBestCmap(), font["hmtx"].metrics, font["head"].unitsPerEm
    out = {}
    for ch in set(text.replace(" ", " ")):
        if ord(ch) in cmap and not ch.isspace() or ch == " " and ord(" ") in cmap:
            out[ch] = hmtx[cmap[ord(ch)]][0] / em
    return out


def mean_advance(font_adv, other_adv, text):
    """(mean advance of `font_adv`, mean advance of `other_adv`, characters counted): the mean over every occurrence
    in `text` of a character BOTH fonts map, so a character one lacks does not tilt the ratio."""
    chars = [c for c in text.replace(" ", " ") if c in font_adv and c in other_adv]
    if not chars:
        raise ValueError("no character of the text is mapped by both fonts")
    return sum(font_adv[c] for c in chars) / len(chars), sum(other_adv[c] for c in chars) / len(chars), len(chars)


def face_css(family, local_name, primary, fallback, text, location_label):
    """The @font-face block (as a string) for one fallback, and the numbers behind it."""
    pa, fa = advances(primary, text), advances(fallback, text)
    avg_p, avg_f, n = mean_advance(pa, fa, text)
    size = avg_p / avg_f
    em = primary["head"].unitsPerEm
    hh = primary["hhea"]
    over = {"ascent": hh.ascent / em / size, "descent": -hh.descent / em / size, "line-gap": hh.lineGap / em / size}
    css = (f'/* {local_name}: mean advance {avg_p:.4f} em in the web font against {avg_f:.4f} em in the fallback over {n} characters of the titles, '
           f'web font at {location_label}; kerning not included */\n'
           f'@font-face {{\n  font-family: "{family}";\n  src: local("{local_name}");\n  size-adjust: {100 * size:.2f}%;\n'
           f'  ascent-override: {100 * over["ascent"]:.2f}%;\n  descent-override: {100 * over["descent"]:.2f}%;\n  line-gap-override: {100 * over["line-gap"]:.2f}%;\n}}')
    return css, {"size_adjust": size, **{k + "_override": v for k, v in over.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font", required=True, help="the project's font.json")
    ap.add_argument("--group", help="the group whose font to read (default: the first)")
    ap.add_argument("--file", help="the built font file (default: where build.py writes the group's woff2)")
    ap.add_argument("--location", default="", help="where to measure the web font, e.g. wght=400,opsz=72 (default: every axis at its default)")
    ap.add_argument("--fallback", action="append", default=[], metavar="NAME=PATH",
                    help="a fallback font file; repeatable; replaces the default search for Georgia, Times New Roman and Arial")
    ap.add_argument("--text", help="a file with one title per line, instead of font.json's titles")
    args = ap.parse_args(argv)
    try:
        cfg = json.loads(pathlib.Path(args.font).read_text(encoding="utf-8"))
        group = args.group or next(iter(cfg["groups"]))
        if group not in cfg["groups"]:
            raise ValueError(f"no group {group!r} in {args.font}")
        path = pathlib.Path(args.file) if args.file else specimen.default_font_file(cfg, args.font, group)
        if not path.is_file():
            raise ValueError(f"no built font at {path}; build first, or pass --file")
        titles = pathlib.Path(args.text).read_text(encoding="utf-8").splitlines() if args.text else cfg.get("titles", [])
        text = "\n".join(t for t in titles if t.strip())
        if not text:
            raise ValueError("no titles: set `titles` in font.json or pass --text FILE")
        location = parse_location(args.location)
        primary = load_font(path, location)
        fallbacks = {}
        if not args.fallback:
            for name, candidates in DEFAULT_FALLBACKS.items():
                found = next((c for c in candidates if pathlib.Path(c).is_file()), None)
                if found:
                    fallbacks[name] = found
        for spec in args.fallback:
            name, sep, file = spec.partition("=")
            if not sep or not name.strip() or not pathlib.Path(file).is_file():
                raise ValueError(f"--fallback wants NAME=PATH naming a file that exists, not {spec!r}")
            fallbacks[name.strip()] = file
        if not fallbacks:
            raise ValueError("no fallback font file found (Georgia, Times New Roman or Arial); pass --fallback NAME=PATH")
        label = ",".join(f"{k}={v:g}" for k, v in location.items()) or "its default location"
        for name, file in fallbacks.items():
            family = f"{cfg['family']} Fallback" + (f" {name}" if len(fallbacks) > 1 else "")
            css, _numbers = face_css(family, name, primary, load_font(file, {}), text, label)
            print(css + "\n")
        suffix = " <name>" if len(fallbacks) > 1 else ""
        print(f'/* in the stylesheet: font-family: "{cfg["family"]}", "{cfg["family"]} Fallback{suffix}", <the fallback it names>, serif; */')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"fallback-metrics.py: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
