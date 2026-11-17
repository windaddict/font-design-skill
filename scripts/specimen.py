#!/usr/bin/env python3
"""Renders the review specimen for a built face from the project's font.json.

WHAT IT'S FOR: the design-review loop judges a face on real titles at the sizes and weights the site
really uses, on the site's own surfaces, beside the faces it must differ from. Writing that page by
hand once per project is how a specimen drifts from the site (a size added to the CSS never reaches
the specimen). This tool reads the `review` block (sizes, medium_below_px, surfaces, comparison
faces, body face) and `titles` from font.json, plus the group's axes, and writes a self-contained
HTML page from specimen.html.tmpl. Every string from the config is HTML-escaped on the way in.

    specimen.py --font font.json [--requirements requirements.json] [--group roman]
                --font-url /fonts/Family-VF.woff2 [--italic-url /fonts/Family-Italic-VF.woff2]
                [--font-file out/Family-VF.woff2] [--italic-file ...] [--allow-missing] OUT.html

Sections, in page order: FIRST the proof rows, the spacing control strings (every lowercase between nn and oo, every
capital between HH and OO, every figure between 00 and 11, each punctuation mark after r, f and y; rows marked
data-fd-spacing="lower|upper|figures|punct") and a legibility row `Il1 O0 B8 rn m cl d` at the smallest review size
(marked data-fd-legibility), each built only from characters the font maps. They come first because a review shot
is shoot.DEFAULT_HEIGHT (2400) CSS px tall and the rest of the page is much longer (at 500 px wide it passes 9,000):
<html> carries data-fd-proof-bottom, the page-px bottom of the last proof row, which a dumped DOM compares with the
captured height. Then readable (every review size on every surface; weight 500 under medium_below_px, else 400;
then Bold rows), the largest sizes on each surface (wordmark in capitals and a long title wrapped), the opsz
crossing when the group has an opsz axis (sizes around the axis start and the axis end), intermediate instances
(the midpoint weight, the midpoint opsz, the heaviest corner), the comparison grid, a title over body copy in the
body face, a kerning row, an NBSP wrap row in a 320px column and a quotes/symbols row. The page sets font-optical-sizing: auto and font-synthesis: none, so a
weight or style the file lacks shows as the nearest real instance, never a faux bold or slant. The
italic rows carry data-fd-probe="italic": shoot.py's element probe then fails the shot unless each of
them is drawn by a loaded italic FontFace of the family (a specimen whose italic file failed to load
would otherwise show upright roman in those rows and pass). Section labels inside a surface section
take that surface's foreground colour, so they read on a dark cloth as well as on paper.

Characters the font lacks: a character outside the font's cmap is drawn by the fallback face, and a
shot still proves the family loaded, so the specimen would quietly show a serif Å among the face's
letters (seen on a dry run). Before writing, this tool reads the built woff2 (--font-file, or by
default <font.json dir>/<out_dir>/<Family>-VF.woff2 as build.py names it, and the italic file the
same way for the italic rows), collects every non-space character the page shows in the family
(the rows classed `f`, after HTML-unescaping; whitespace and the no-break space are exempt because
Chrome draws a missing U+00A0 with the space glyph), and refuses to write a specimen whose text
contains a character the cmap lacks, naming each one, unless --allow-missing is given. Exact
guarantee: when the font file is found, every character the page sets in the family has a cmap
entry; it does not check the comparison faces or the body face, and when the file is not found
(the font not built yet) it says so on stderr and in the page footer and writes the page unchecked,
leaving the second layer, shoot.py's per-character probe, to catch a fallback glyph in the shot.

Comparison faces: `family` alone names an installed family; `url` adds an @font-face whose src is
that path exactly as written (serve it beside the page; shoot.py serves the --serve directory, so a
root-relative path there resolves); `css_url` adds a <link rel="stylesheet"> (https only). A
comparison face that fails to load falls back to serif and is not detected here: compare the
screenshot with the face you expected. `--requirements` supplies the titles when present (the
reviewed list), otherwise font.json's. Exact guarantee: the page is what the config says; whether
the font file at --font-url loads is proved by shoot.py --family, not here.
Copyright 2026 John Knox. MIT licence.
"""
import argparse
import html
import json
import pathlib
import re
import string
import sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE / "specimen.html.tmpl"
BODY_COPY = ("The tide came in under the pier while the kettle boiled, and by the time the cups were out the "
             "boats had turned to face the other way. Nobody mentioned it; it happens twice a day.")
KERN_PAIRS = "AT AV AW AY LT LV LY Ta Te To Tr Ty Va Vo Wa We Ya Yo r. r, f' 11 17 74"
KERN_SHORT = "AT LT Ta Ty Va Wa Yo r. 74"
# Spacing control strings (Tracy's method: judge a letter between runs of the letters whose spacing is settled)
# and the punctuation set the proof sets after r, f and y. See spacing_rows().
PUNCT_AFTER = ".,'’:;!?-–—…)\""
LEGIBILITY = "Il1 O0 B8 rn m cl d"  # the pairs a reader confuses at the smallest size; see legibility_row()
GLYPH_ROW = "Bracket's Stand / Keepers’ Walk / \"Update\" / “Update” / ‘quay’ / #4 / C++ / *Update* / Salt & Stone … 2019–2026 — fin"


def e(s):
    return html.escape(str(s), quote=True)


def css_text(s, what):
    """A value that goes inside the <style> block, where HTML escaping does not apply (a style element
    is raw text): `<` is refused because `</style>` would end the block."""
    s = str(s)
    if "<" in s:
        raise ValueError(f"{what} may not contain '<': {s!r}")
    return s


def css_string(s):
    return '"' + css_text(s, "a CSS string").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


# A font URL goes into the page's <style> block, where nothing is HTML-escaped, so it is allow-listed
# rather than escaped: a root-relative or relative path, or an https URL, made only of URL characters.
# `<`, `>`, quotes, parentheses, whitespace and backslashes are refused outright: `</style><script>` in
# a font URL would otherwise end the style block (independent review of this repo, finding C2).
FONT_URL_OK = re.compile(r"^(?:https://[A-Za-z0-9._~%/:?=&+#-]+|/?[A-Za-z0-9._~%-]+(?:/[A-Za-z0-9._~%-]+)*)$")


def css_url(s):
    s = str(s)
    if not FONT_URL_OK.fullmatch(s) or "//" in s.split("://", 1)[-1]:
        raise ValueError(f"a font URL must be a relative path or an https URL of URL characters only (no < > quotes, parentheses or whitespace): {s!r}")
    return f"url('{s}')"


def row(cls, size, text, weight=400, lh=None, extra="", attrs=""):
    style = f"font-size:{size:g}px; font-weight:{weight}" + (f"; line-height:{lh}" if lh else "") + (f"; {extra}" if extra else "")
    return f'  <p class="{cls}"{" " + attrs if attrs else ""} style="{style}">{text}</p>\n'


def lbl(text, surface=None):
    """A section label; inside a surface section it takes that surface's foreground colour, because the
    stylesheet's label colour is the first surface's ink and reads dark-on-dark on a cloth surface."""
    style = f' style="color:{e(surface["foreground"])}"' if surface else ""
    return f'  <div class="lbl"{style}>{e(text)}</div>\n'


def shown_chars(sections_html):
    """(roman, italic): the sets of non-space characters the page shows in the family, read back from
    the rows classed `f` (italic ones also classed `fi`) with tags stripped and entities unescaped.
    Read from the markup rather than the inputs so a row added later is covered without bookkeeping."""
    roman, italic = set(), set()
    for cls, inner in re.findall(r'<p class="(f[^"]*)"[^>]*>(.*?)</p>', sections_html, re.S):
        text = html.unescape(re.sub(r"<[^>]+>", "", inner))
        (italic if "fi" in cls.split() else roman).update(c for c in text if not c.isspace())
    return roman, italic


def cmap_of(path):
    """The code points the woff2/ttf at `path` maps, via fontTools."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:
        sys.exit(f"specimen.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
                 "Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/specimen.py ...")
    with TTFont(str(path)) as f:
        return set(f.getBestCmap())


def default_font_file(cfg, font_path, group_name):
    """Where build.py writes the group's font: <font.json dir>/<out_dir>/<Family>-VF.woff2, -Italic-VF for
    an italic group, or the group's `file` key relative to out_dir. Mirrors build.py's naming; it is
    a default the operator can override with --font-file."""
    group = cfg["groups"][group_name]
    out_dir = pathlib.Path(font_path).parent / cfg.get("out_dir", "out")
    if group.get("file"):
        return out_dir / group["file"]
    token = str(cfg["family"]).replace(" ", "")
    return out_dir / (f"{token}-Italic-VF.woff2" if group.get("italic") else f"{token}-VF.woff2")


def check_charset(chars, font_file, what):
    """The characters in `chars` the font at `font_file` cannot map, sorted, or None when the file is not
    there (reported by the caller). Raises ValueError naming each missing character and its code point."""
    if font_file is None or not pathlib.Path(font_file).is_file():
        return None
    missing = sorted(c for c in chars if ord(c) not in cmap_of(font_file))
    if missing:
        raise ValueError(f"{what}: the specimen shows {len(missing)} character(s) the font at {font_file} lacks, which Chrome would draw "
                         f"in the fallback face: {' '.join(f'{c!r} U+{ord(c):04X}' for c in missing)}; fix the charset or pass --allow-missing")
    return []


def spacing_rows(allowed):
    """[(label, class marker, text)] for the spacing proof: every lowercase letter x as `nnxnn ooxoo`, every
    capital as `HHXHH OOXOO`, every figure as `00d00 11d11`, and each punctuation mark after r, f and y
    (`r. f. y.`). The rhythm of the letters between runs of n and o (round and straight) and of H and O is what a
    title shows, and a reviewer reading titles does not see it. `allowed` is the set of characters the font maps;
    a control string needs its own letters (n and o, H and O, 0 and 1, r f y), so a group whose controls are
    unmapped is left out, and any other character that is unmapped is left out of its group."""
    def has(*chars):
        return all(c in allowed for c in chars)
    rows = []
    lower = [c for c in string.ascii_lowercase if c in allowed]
    if lower and has("n", "o"):
        rows.append(("each lowercase letter between nn and oo: nnxnn ooxoo", "lower", " ".join(f"nn{c}nn oo{c}oo" for c in lower)))
    upper = [c for c in string.ascii_uppercase if c in allowed]
    if upper and has("H", "O"):
        rows.append(("each capital between HH and OO: HHXHH OOXOO", "upper", " ".join(f"HH{c}HH OO{c}OO" for c in upper)))
    figures = [c for c in string.digits if c in allowed]
    if figures and has("0", "1"):
        rows.append(("each figure between 00 and 11: 00d00 11d11", "figures", " ".join(f"00{c}00 11{c}11" for c in figures)))
    punct = [c for c in PUNCT_AFTER if c in allowed]
    if punct and has("r", "f", "y"):
        rows.append(("each punctuation mark after r, f and y", "punct", " ".join(f"r{c} f{c} y{c}" for c in punct)))
    return rows


def legibility_tokens(allowed):
    """The words of the legibility row whose every character the font maps (the row is `Il1 O0 B8 rn m cl d`)."""
    return [w for w in LEGIBILITY.split() if all(c in allowed for c in w)]


def surface_style(s):
    return f'style="background:{e(s["background"])}; color:{e(s["foreground"])}"'


def build(cfg, titles, group_name, font_url, italic_url, source, font_file=None, italic_file=None, allow_missing=False):
    """The specimen HTML. `font_file`/`italic_file` are the built fonts whose cmaps the shown text is
    checked against (None: no check, noted in the footer); `allow_missing` turns a missing character
    into a footer note instead of a ValueError."""
    rev = cfg["review"]
    family = cfg["family"]
    group = cfg["groups"][group_name]
    axes = {a["tag"]: a for a in group["axes"]}
    if "wght" not in axes:
        raise ValueError(f"group {group_name} has no wght axis; the specimen needs one")
    wmin, wmax = axes["wght"]["min"], axes["wght"]["max"]
    opsz = axes.get("opsz")
    sizes = sorted(float(s) for s in rev["sizes"])
    medium_below = rev.get("medium_below_px", 0)
    surfaces = rev["surfaces"]
    comps = rev.get("comparison_faces", [])
    body_face = rev.get("body_face", "Georgia, serif")
    if not titles:
        raise ValueError("no titles: set `titles` in font.json or pass --requirements with a titles list")
    longest = max(titles, key=len)
    shortest = min(titles, key=len)
    wordmark = cfg.get("review", {}).get("wordmark") or shortest
    t = lambda i: e(titles[i % len(titles)])  # noqa: E731

    faces = [f"  @font-face {{ font-family: {css_string(family)}; font-weight: {wmin} {wmax}; font-style: normal; src: {css_url(font_url)} format('woff2'); }}"]
    if italic_url:
        faces.append(f"  @font-face {{ font-family: {css_string(family)}; font-weight: {wmin} {wmax}; font-style: italic; "
                     f"src: {css_url(italic_url)} format('woff2'); }}")
    links = []
    for c in comps:
        if c.get("url"):
            ws = c.get("weights") or [400, 700]
            faces.append(f"  @font-face {{ font-family: {css_string(c['family'])}; font-weight: {min(ws)} {max(ws)}; "
                         f"src: {css_url(c['url'])} format('woff2'); }}")
        if c.get("css_url"):
            if not str(c["css_url"]).startswith("https://"):
                raise ValueError(f"comparison face {c['name']}: css_url must be https")
            links.append(f'<link rel="stylesheet" href="{e(c["css_url"])}">')
    if links:
        faces.insert(0, "</style>" + "".join(links) + "<style>")

    out = []
    # 0. the proof rows FIRST. The review shots are 2400 CSS px tall (shoot.DEFAULT_HEIGHT) and the specimen is far longer at 500 px
    # wide, so rows at the end were never in a default shot (measured in Chrome: last ink at 5,368 px at 1280 wide, past 9,000 at 500).
    # The rows hold the characters the font maps (or, with no font file yet, the project's required characters; the charset check
    # below then covers what the cmap lacks)
    allowed = set(cfg["charset"]["required"]) - {" ", "\u00a0"}
    if font_file is not None and pathlib.Path(font_file).is_file():
        allowed = {c for c in set(string.ascii_letters + string.digits + PUNCT_AFTER) | allowed if ord(c) in cmap_of(font_file)}
    small = sizes[0]
    small_w = 500 if small < medium_below else 400
    out.append("<section>\n")
    for label, kind, text in spacing_rows(allowed):
        out.append(lbl(f"Spacing, {label}, at 24px Regular"))
        out.append(row("f", 24, e(text), 400, lh=1.4, attrs=f'data-fd-spacing="{kind}"'))
    legible = legibility_tokens(allowed)
    if legible:
        out.append(lbl(f"Legibility at the smallest size ({small:g}px, weight {small_w}): which letters and figures read apart"))
        out.append(row("f", small, e(" ".join(legible)), small_w, lh=1.4, attrs='data-fd-legibility="true"'))
    out.append("</section>\n")
    # 1. readable
    for s in surfaces:
        out.append(f'<section {surface_style(s)}>\n')
        out.append(lbl(f"Readable on {s['name']}: every size the site sets, Medium 500 under {medium_below:g}px, else Regular", s))
        for i, px in enumerate(sizes):
            w = 500 if px < medium_below else 400
            out.append(row("f", px, f"{t(i)} <span style=\"opacity:.6\">{px:g}px {w}</span>", w, lh=1.2 if px < 24 else 1.1))
        out.append(lbl(f"Bold {wmax} on {s['name']} at every size", s))
        for i, px in enumerate(sizes):
            out.append(row("f", px, t(i + 1), wmax, lh=1.2 if px < 24 else 1.1))
        out.append("</section>\n")
    # 2. largest sizes
    big = sizes[-3:] if len(sizes) >= 3 else sizes
    for s in surfaces:
        out.append(f'<section {surface_style(s)}>\n')
        out.append(lbl(f"The wordmark in capitals, Bold, and the largest sizes on {s['name']}: {', '.join(f'{b:g}' for b in big)}px Regular", s))
        out.append(row("f cap", min(24, big[0]), e(wordmark), wmax))
        for b in big:
            out.append(row("f", b, e(wordmark).replace(" ", "&nbsp;"), 400, lh=".95"))
        out.append(lbl(f"Descenders and wrapping on {s['name']} at {big[-1]:g}px, line-height .95, 14em measure", s))
        out.append(row("f wrapmax", big[-1], e(longest), 400, lh=".95"))
        out.append("</section>\n")
    # 3. opsz crossing
    if opsz:
        lo, hi = opsz["min"], opsz["max"]
        start = [lo - 1, lo, lo + 4, lo + 8]
        top = [hi - 8, hi, hi + 8]
        out.append("<section>\n")
        out.append(lbl(f"Across the opsz axis start ({lo}): {', '.join(f'{x:g}' for x in start)}px Regular, font-optical-sizing auto"))
        for x in start:
            out.append(row("f", x, t(0), 400, lh=1.06))
        out.append(lbl(f"At the axis end ({hi}): {', '.join(f'{x:g}' for x in top)}px Regular; past the end the axis is clamped"))
        for x in top:
            out.append(row("f", x, e(shortest), 400, lh=1))
        out.append("</section>\n")
    # 4. intermediate instances
    wmid = round((wmin + wmax) / 2)
    mid_px = sizes[len(sizes) // 2]
    out.append("<section>\n")
    if opsz:
        omid = round((opsz["min"] + opsz["max"]) / 2)
        out.append(lbl(f"Intermediate instances: wght {wmid} at {mid_px:g}px; opsz {omid} at {omid}px (auto); "
                       f"the heaviest corner, wght {wmax} at {opsz['max']}px"))
        out.append(row("f", mid_px, t(2), wmid))
        out.append(row("f", omid, e(shortest), 400, lh=1))
        out.append(row("f", opsz["max"], e(shortest), wmax, lh=1))
    else:
        out.append(lbl(f"Intermediate instances: wght {wmid} at {mid_px:g}px; the heaviest weight {wmax} at {sizes[-1]:g}px"))
        out.append(row("f", mid_px, t(2), wmid))
        out.append(row("f", sizes[-1], e(shortest), wmax, lh=1))
    if italic_url:
        out.append(lbl(f"Italic at {mid_px:g}px Regular and Bold (a second file, font-style: italic)"))
        out.append(row("f fi", mid_px, t(3), 400, attrs='data-fd-probe="italic"'))
        out.append(row("f fi", mid_px, t(4), wmax, attrs='data-fd-probe="italic"'))
    out.append("</section>\n")
    # 5. comparison
    out.append("<section>\n")
    names = [family] + [c["name"] for c in comps]
    out.append(lbl(f"Beside: {' / '.join(names)} at 28px Bold and 48px Regular"))
    for px, w in ((28, wmax), (48, 400)):
        out.append('  <div class="cols">\n')
        out.append(row("f", px, t(5), w, lh=1.06))
        for c in comps:
            ws = c.get("weights") or [400, 700]
            cw = min(ws, key=lambda x: abs(x - (700 if w > 500 else 400)))
            out.append(row("cmp", px, t(5), cw, lh=1.06, extra=f"font-family:{e(css_string(c['family']))}, serif"))
        out.append("  </div>\n")
    out.append(lbl("A title over body copy in the body face"))
    out.append(row("f", 44, t(0), 400, lh=1.06))
    out.append(f'  <p class="body">{e(BODY_COPY)}</p>\n')
    out.append("</section>\n")
    # 6. kerning, NBSP, glyphs
    out.append("<section>\n")
    out.append(lbl(f"Kerning: the pair row at 40px Regular and {sizes[-1]:g}px"))
    out.append(row("f", 40, e(KERN_PAIRS), 400))
    out.append(row("f", sizes[-1], e(KERN_SHORT), 400, lh=1))
    small = sizes[0]
    out.append(lbl(f"Word space and NBSP wrap at {small:g}px in a 320px column: the no-break spaces never break"))
    nb = e(longest).replace(" ", "&nbsp;", 1) if " " in longest else e(longest)
    small_w = 500 if small < medium_below else 400
    out.append(f'  <div class="narrow">{row("f", small, nb + " with " + e(wordmark).replace(" ", "&nbsp;"), small_w, lh=1.2)}</div>\n')
    out.append(f'  <div class="narrow">{row("f", 40, e(wordmark).replace(" ", "&nbsp;") + " at " + e(wordmark).replace(" ", "&nbsp;"), 400, lh=1.06)}</div>\n')
    out.append(lbl("Quotes, apostrophes and symbols: ' ’ \" “ ” ‘ # + * & … – —"))
    out.append(row("f", 40, e(GLYPH_ROW), 400))
    out.append("</section>\n")

    paper = surfaces[0]
    sections = "".join(out)
    roman_chars, italic_chars = shown_chars(sections)
    notes = []
    for chars, path, what in ((roman_chars, font_file, "roman rows"), (italic_chars if italic_url else set(), italic_file, "italic rows")):
        if not chars:
            continue
        try:
            found = check_charset(chars, path, what)
        except ValueError as exc:
            if not allow_missing:
                raise
            notes.append(f"UNCHECKED CHARSET, --allow-missing given: {exc}")
            continue
        if found is None:
            notes.append(f"charset of the {what} not checked: no font file at {path} (build the font, or pass --font-file)")
            print(f"specimen.py: NOTE: {notes[-1]}", file=sys.stderr)
    tpl = string.Template(TEMPLATE.read_text(encoding="utf-8"))
    return tpl.substitute(
        TITLE=e(f"{family} specimen"), FONT_FACES="\n".join(faces), PAPER_BG=e(paper["background"]), PAPER_FG=e(paper["foreground"]),
        PENCIL=e(paper["foreground"]), BODY_FACE=css_text(body_face, "review.body_face"), FAMILY_STACK=css_string(family) + ", serif",
        CMP_COLS=len(comps) + 1, SECTIONS=sections, SOURCE=e(source),
        NOTES="".join(f'  <p class="lbl">{e(n)}</p>\n' for n in notes))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="the HTML file to write")
    ap.add_argument("--font", required=True, help="the project's font.json")
    ap.add_argument("--requirements", help="requirements.json; its titles are used when present")
    ap.add_argument("--group", help="which group's axes to read (default: the first)")
    ap.add_argument("--font-url", required=True, help="where the page will find the woff2, e.g. /fonts/Family-VF.woff2")
    ap.add_argument("--italic-url", help="the italic group's woff2, if built")
    ap.add_argument("--font-file", help="the built woff2 whose cmap the shown text is checked against (default: where build.py writes the group)")
    ap.add_argument("--italic-file", help="the italic group's built woff2, for the italic rows (default: build.py's name for the italic group)")
    ap.add_argument("--allow-missing", action="store_true", help="write the specimen even when it shows characters the font lacks (noted in the footer)")
    args = ap.parse_args(argv)
    try:
        cfg = json.loads(pathlib.Path(args.font).read_text(encoding="utf-8"))
        titles = cfg.get("titles") or []
        if args.requirements:
            req = json.loads(pathlib.Path(args.requirements).read_text(encoding="utf-8"))
            titles = req.get("titles") or titles
        if "review" not in cfg:
            sys.exit(f"{args.font} has no `review` block; the specimen needs sizes and surfaces")
        group = args.group or next(iter(cfg["groups"]))
        if group not in cfg["groups"]:
            sys.exit(f"no group {group!r} in {args.font} (have {', '.join(cfg['groups'])})")
        font_file = pathlib.Path(args.font_file) if args.font_file else default_font_file(cfg, args.font, group)
        italic_groups = [g for g, spec in cfg["groups"].items() if spec.get("italic")]
        italic_file = pathlib.Path(args.italic_file) if args.italic_file else (default_font_file(cfg, args.font, italic_groups[0]) if italic_groups else None)
        page = build(cfg, titles, group, args.font_url, args.italic_url, pathlib.Path(args.font).name,
                     font_file=font_file, italic_file=italic_file, allow_missing=args.allow_missing)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        sys.exit(f"specimen.py: {type(exc).__name__}: {exc}")
    pathlib.Path(args.out).write_text(page, encoding="utf-8")
    print(f"{args.out}: {len(page)} bytes, group {group}, {len(titles)} titles, {len(cfg['review']['sizes'])} sizes, "
          f"{len(cfg['review']['surfaces'])} surfaces, {len(cfg['review'].get('comparison_faces', []))} comparison faces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
