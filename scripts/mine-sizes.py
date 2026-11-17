#!/usr/bin/env python3
"""Reads a stylesheet's font-size rules for the display selectors and reports the sizes a face must survive.

WHAT IT'S FOR: the smallest size a display face is set at decides its hairline floor (one CSS px at
S px is 1000/S font units, so a 0.75 px hairline needs 750/S units), and the largest decides where
an opsz axis should end. Guessing either from the design is how a face ships with hairlines that
vanish at the plate-title size. This tool parses `font-size:` declarations for the given selectors
(clamp(a, b, c), Nrem, Npx; Nem is reported as a note because it depends on the parent), evaluates
them at each root font size, and prints min/max CSS px per selector, the overall smallest size, and
the hairline floor in units with the formula it used.

    mine-sizes.py CSS --selectors 'h1,.plate-title' [--root 100 150] [--floor-px 0.75]
    mine-sizes.py CSS --family 'Bodoni Moda' [--selectors ...]     # every selector whose rule sets that family first

How --family finds the selectors (second dry run, finding 16: a hand-typed list missed .frontis-title,
.wordmark and a 15.2 px .num, which moved the floor from 44.6 to 49.3 units): every rule, @media
blocks included, whose `font-family` declaration names FAMILY first (quotes optional, case ignored) is
read, and each selector of its selector list is mined; `--selectors` adds to that list. The found list
is printed, so the same list can be given to mine-charset.py. Exact guarantee: a selector inherits
nothing here, so when the headings inherit the display face from `body` (a site whose body and display
face are one family), --family returns `body` and the display selectors must be named by hand from the
templates; and a family set through the `font` shorthand or a custom property is not seen.

How clamp() is read: clamp(MIN, PREFERRED, MAX) sets a range from MIN to MAX; the viewport-dependent
PREFERRED term is not evaluated (there is no viewport), so the range reported is the clamp's own
bounds, which is what the face must cover. `--root N` is a percentage of 16px: 100 is the default
root, 150 a reader's enlarged default (rem and clamp bounds in rem scale with it; px do not).
Exact guarantee: a CSS parser this is not. It matches `selector-list { ... font-size: ...; }` blocks
textually, including inside @media; it ignores specificity and cascade order, so a selector with two
rules reports the union of both; and it does not resolve `font:` shorthand, custom properties or
calc() other than clamp(). Exits non-zero when a selector has no font-size rule in the sheet.
Copyright 2026 John Knox. MIT licence.
"""
import argparse
import json
import pathlib
import re
import sys

NUM = r"[-+]?\d*\.?\d+"
LEN = re.compile(rf"^({NUM})(rem|px|em|vw|vh|%)$")
CLAMP = re.compile(r"^clamp\(\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)$", re.S)


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def blocks(css):
    """Yields (selector_text, declarations_text) for every rule, descending into @media and other
    nested at-rules. Nested blocks are matched by brace depth, not by a grammar."""
    i, n = 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j < 0:
            return
        head = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        if head.startswith("@"):
            if head.split("(")[0].strip().lower() in ("@media", "@supports", "@layer", "@container"):
                yield from blocks(body)
        else:
            yield head, body
        i = k


def length_px(term, root_px):
    m = LEN.match(term.strip())
    if not m:
        return None, f"cannot read {term.strip()!r}"
    v, unit = float(m.group(1)), m.group(2)
    if unit == "rem":
        return v * root_px, None
    if unit == "px":
        return v, None
    if unit == "em":
        return None, f"{term.strip()} depends on the parent font size; read it by hand"
    return None, f"{term.strip()} depends on the viewport"


def size_range(value, root_px):
    """(min_px, max_px, notes) for one font-size value at a root size."""
    value = value.strip()
    m = CLAMP.match(value)
    if m:
        lo, lo_note = length_px(m.group(1), root_px)
        hi, hi_note = length_px(m.group(3), root_px)
        notes = [x for x in (lo_note, hi_note) if x]
        if lo is None or hi is None:
            return None, None, notes + [f"clamp bounds unreadable in {value!r}"]
        return min(lo, hi), max(lo, hi), notes + [f"clamp preferred term {m.group(2).strip()!r} not evaluated (no viewport)"]
    px, note = length_px(value, root_px)
    if px is None:
        return None, None, [note]
    return px, px, []


def selector_matches(sel_list, wanted):
    """True when any selector in the comma list is exactly `wanted` or ends with it as its subject
    (so `.chapters .num` matches `.num`, and `h3, .plate-title` matches both)."""
    for sel in sel_list.split(","):
        sel = sel.strip()
        if not sel:
            continue
        subject = re.split(r"[\s>+~]+", sel)[-1]
        if subject == wanted or sel == wanted:
            return True
    return False


def first_family(value):
    """The first family of a font-family value, without its quotes."""
    return value.split(",")[0].strip().strip("'\"")


def selectors_for_family(css_text, family):
    """Every selector (each member of a selector list, whitespace-normalised, in source order, once) whose rule
    declares `font-family` with FAMILY as its first family. Descends into @media and the other nested at-rules
    as blocks() does; @font-face and other declaration-holding at-rules are not rules and are skipped."""
    want = family.strip().strip("'\"").lower()
    decl = re.compile(r"(?:^|;)\s*font-family\s*:\s*([^;!]+)", re.I)
    found = []
    for head, body in blocks(strip_comments(css_text)):
        if head.startswith("@"):
            continue
        values = [m.group(1) for m in decl.finditer(body)]
        if values and first_family(values[-1]).lower() == want:
            for sel in head.split(","):
                sel = re.sub(r"\s+", " ", sel.strip())
                if sel and sel not in found:
                    found.append(sel)
    return found


def mine(css_text, selectors, roots, floor_px):
    css = strip_comments(css_text)
    decl = re.compile(r"(?:^|;)\s*font-size\s*:\s*([^;!]+)", re.I)
    found = {s: [] for s in selectors}
    for head, body in blocks(css):
        for s in selectors:
            if selector_matches(head, s):
                for m in decl.finditer(body):
                    found[s].append((head, m.group(1).strip()))
    missing = [s for s, rules in found.items() if not rules]
    out = {"css": None, "roots": {}, "notes": [], "floor_px": floor_px}
    smallest = None
    for root in roots:
        root_px = 16 * root / 100
        per = {}
        for s, rules in found.items():
            lo, hi = None, None
            for head, value in rules:
                a, b, notes = size_range(value, root_px)
                for note in notes:
                    msg = f"{head} {{ font-size: {value} }}: {note}"
                    if msg not in out["notes"]:
                        out["notes"].append(msg)
                if a is None:
                    continue
                lo = a if lo is None else min(lo, a)
                hi = b if hi is None else max(hi, b)
            per[s] = {"min_px": lo, "max_px": hi, "rules": [f"{h} {{ font-size: {v} }}" for h, v in rules]}
            if lo is not None:
                smallest = lo if smallest is None else min(smallest, lo)
        out["roots"][str(root)] = per
    out["smallest_px"] = smallest
    if smallest:
        out["floor_units"] = round(1000 * floor_px / smallest, 1)
        out["formula"] = f"units = 1000 x floor_px / smallest_px = 1000 x {floor_px} / {smallest:g} = {out['floor_units']}"
    return out, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("css")
    ap.add_argument("--selectors", help="comma list of tags and .classes, e.g. 'h1,h2,.plate-title'")
    ap.add_argument("--family", metavar="NAME", help="mine every selector whose rule sets font-family: NAME first (added to --selectors)")
    ap.add_argument("--root", nargs="+", type=float, default=[100], help="root font sizes as %% of 16px (100 150)")
    ap.add_argument("--floor-px", type=float, default=0.75, help="the thinnest stroke in CSS px the face must keep")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        css_text = pathlib.Path(args.css).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        sys.exit(f"cannot read {args.css}: {exc}")
    from_family = selectors_for_family(css_text, args.family) if args.family else []
    if args.family and not from_family:
        sys.exit(f"no rule in {args.css} sets font-family: {args.family} first (the name is spelled differently, or the family "
                 f"is set through the `font:` shorthand or a custom property, which this tool does not read)")
    selectors = from_family + [s.strip() for s in (args.selectors or "").split(",") if s.strip() and s.strip() not in from_family]
    if not selectors:
        sys.exit("give --selectors, --family or both")
    out, missing = mine(css_text, selectors, args.root, args.floor_px)
    out["css"] = args.css
    out["selectors"] = selectors
    out["selectors_from_family"] = from_family
    if missing:
        sys.exit(f"no font-size rule in {args.css} for: {', '.join(missing)} (the selector is spelled differently, "
                 f"or the size comes from a shorthand `font:` or a custom property this tool does not read)")
    if out["smallest_px"] is None:
        sys.exit("every matched rule was unreadable (em, vw or shorthand); see the notes")
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    if from_family:
        print(f"selectors whose rule sets font-family: {args.family} first: {','.join(from_family)}")
    for root, per in out["roots"].items():
        print(f"root {root}% ({16 * float(root) / 100:g}px):")
        for s, r in per.items():
            rng = "unreadable" if r["min_px"] is None else (f"{r['min_px']:g}px" if r["min_px"] == r["max_px"] else f"{r['min_px']:g} to {r['max_px']:g}px")
            print(f"  {s:18} {rng:22} {'; '.join(r['rules'])}")
    print(f"smallest display size: {out['smallest_px']:g}px")
    print(f"hairline floor: {out['floor_units']} units   ({out['formula']})")
    for note in out["notes"]:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
