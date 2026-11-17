#!/usr/bin/env python3
"""Mines the characters a site's display face must carry, from its built HTML or a list of titles.

WHAT IT'S FOR: the character set of a display face is decided by the titles that already exist, not
by a guess, and real titles carry traps a guess misses: a no-break space before the last word
(U+00A0, which must map to the space glyph or the title shows a box), a straight ASCII apostrophe
typed where a curly one is meant, a `#` in "Notes #4", a `+` and a `*` in headings, accented letters,
and one title long enough to wrap three times at phone width. This tool walks the elements that the
display selectors match, with their descendants, exactly as a browser would set them, and reports
what it found with the first page that uses each unusual character. Its output is pasted into
font.json (`charset`) and requirements.json (`required_characters`).

    mine-charset.py --html DIR --selectors 'h1,h2,h3,.plate-title' [--css FILE] [--json]
    mine-charset.py --html DIR --css FILE --family 'Bodoni Moda' [--selectors ...] [--json]
    mine-charset.py --titles FILE [--json]                 # one title per line

Selectors are tag names and `.class` names only (a plain HTMLParser, no CSS engine): an element is
display text when its tag or one of its classes is listed, and so is everything inside it. Exact
guarantee: elements made display-face by any OTHER route (an inline style, a selector this cannot
read, text inserted by script) are not seen, so a selector list that is too wide can only make the
set stricter, and one that is too narrow misses characters: compare the count with what you expect.
Exits non-zero when a selector matches nothing in any page, or a page cannot be read.

--css FILE reads the stylesheet for two things (second dry run, findings 10 and 16). With --family NAME
it finds every selector whose rule sets `font-family: NAME` first, the same way mine-sizes.py --family
does, and mines those (plus any --selectors). And for every rule in the stylesheet that declares
`text-transform` (whatever its selector: the mined selector itself, a descendant such as `.display
span`, or a rule like `.caps` that an element inside the display text carries; re-review, code-b F006),
the elements inside the display text that the rule matches, with their descendants (text-transform is
inherited), have the characters the browser DRAWS added: `uppercase` adds the upper-case form of every
letter in that text, `lowercase` the lower-case form, `capitalize` the upper-case form of every letter
(over-inclusive: it cannot tell word starts from the rest without a layout). The source characters stay
in the set too (a transform can be undone at another width), so a transform can only make the set
stricter. Without --css a `text-transform` is invisible, and the output says so in its
`text_transform` field ("not read: no --css"); a transform rule whose selector this tool cannot read
(`>`, `+`, `~`, `:`, `[`, `#`, `*`) is named there as "not read: <selector>", never dropped in silence.
Copyright 2026 John Knox. MIT licence. From the Bract test-suite's DisplayText parser (2026-11-15).
"""
import argparse
import json
import pathlib
import re
import sys
import unicodedata
from html.parser import HTMLParser

VOID = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "area", "col", "embed", "track"}
PLAIN = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,:;!?-()")


class DisplayText(HTMLParser):
    """Collects the text set by the display selectors, with descendants, and, per text-transform rule
    (`transforms`: [(selector text, chain, values)]), the characters of every element inside the display
    text that the rule matches, with that element's descendants, since text-transform is inherited.
    `convert_charrefs` is on, so &nbsp; and &amp; arrive as the characters a browser would show."""

    def __init__(self, selectors, transforms=()):
        super().__init__(convert_charrefs=True)
        self.selectors = selectors  # [(text, chain)]
        self.transforms = list(transforms)
        self.stack = []  # (tag, classes, inside_display, selector texts active on this element, transform rules active)
        self.chars = {}  # char -> None (ordered set)
        self.by_selector = {text: {} for text, _ in selectors}  # selector text -> ordered set of its characters
        self.by_transform = {}  # (rule selector text, values tuple) -> ordered set of the characters it transforms
        self.texts = []  # the text of each matched top-level element, for the longest-title report
        self.matched = {text: 0 for text, _ in selectors}
        self._cur = None

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        cls = set((dict(attrs).get("class") or "").split())
        ancestry = [(t, c) for t, c, _, _, _ in self.stack] + [(tag, cls)]
        mine = False
        active = list(self.stack[-1][3]) if self.stack else []  # a descendant carries its ancestors' selectors
        for text, chain in self.selectors:
            if chain_matches(chain, ancestry):
                self.matched[text] += 1
                mine = True
                if text not in active:
                    active.append(text)
        inside = mine or (bool(self.stack) and self.stack[-1][2])
        tf = list(self.stack[-1][4]) if self.stack else []  # inherited from the parent, as text-transform is
        for text, chain, values in self.transforms:
            key = (text, tuple(values))
            if key not in tf and chain_matches(chain, ancestry):
                tf.append(key)
        if mine and not (self.stack and self.stack[-1][2]):
            self._cur = []
        self.stack.append((tag, cls, inside, active, tf))

    def handle_endtag(self, tag):
        if tag not in (t for t, _, _, _, _ in self.stack):
            return
        while self.stack:
            t, _, inside, _, _ = self.stack.pop()
            if t == tag:
                break
        if self._cur is not None and not (self.stack and self.stack[-1][2]):
            self.texts.append("".join(self._cur))
            self._cur = None

    def handle_data(self, data):
        if self.stack and self.stack[-1][2]:
            if self._cur is not None:
                self._cur.append(data)
            for c in data:
                if not c.isspace() or c in (" ", " "):
                    self.chars.setdefault(c, None)
                    for text in self.stack[-1][3]:
                        self.by_selector[text].setdefault(c, None)
                    for key in self.stack[-1][4]:
                        self.by_transform.setdefault(key, {}).setdefault(c, None)


def load_mine_sizes():
    """scripts/mine-sizes.py as a module (its name has a hyphen), for the one stylesheet reader both tools share."""
    import importlib.util
    path = pathlib.Path(__file__).resolve().with_name("mine-sizes.py")
    if not path.is_file():
        sys.exit(f"--css needs {path.name} beside this script (the stylesheet reader lives there); copy the whole scripts/ folder")
    spec = importlib.util.spec_from_file_location("mine_sizes", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def transform_rules(css_text):
    """([(selector text, chain, [values])] for every rule anywhere in the stylesheet that declares text-transform
    uppercase, lowercase or capitalize, one entry per selector of its list, @media blocks included; [selector
    texts this tool cannot read]). The rules are matched against the elements inside the display text by
    DisplayText, so a transform on a descendant of a mined element, or on a class an element inside it
    carries, is seen (re-review, code-b F006; the first version read only rules whose selector was a mined
    selector)."""
    ms = load_mine_sizes()
    decl = re.compile(r"(?:^|;)\s*text-transform\s*:\s*([^;!]+)", re.I)
    rules, unread = [], []
    for head, body in ms.blocks(ms.strip_comments(css_text)):
        if head.startswith("@"):
            continue
        values = sorted({m.group(1).strip().lower() for m in decl.finditer(body)} & {"uppercase", "lowercase", "capitalize"})
        if not values:
            continue
        for part in head.split(","):
            part = part.strip()
            if not part:
                continue
            chain = readable_chain(part)
            if chain is None:
                unread.append(part)
            else:
                rules.append((part, chain, values))
    return rules, unread


def case_mapped(by_transform, first_use):
    """The characters a text-transform makes the browser draw, from the characters each transform rule
    collected, added to first_use with the page their source character came from; returns the additions
    with the rule's selector and transform responsible."""
    added = []
    for (text, values), chars in by_transform.items():
        for c in chars:
            forms = set()
            if "uppercase" in values or "capitalize" in values:
                forms.update(c.upper())
            if "lowercase" in values:
                forms.update(c.lower())
            for f in sorted(forms - {c}):
                if f not in first_use:
                    first_use[f] = first_use.get(c, "?")
                    added.append({"char": f, "codepoint": describe(f), "from": c, "selector": text, "transform": "/".join(values)})
    return added


def parse_compound(part):
    """`h3`, `.plate-title` or `h3.plate-title.featured` -> (tag or None, {classes})."""
    m = re.fullmatch(r"([a-zA-Z][a-zA-Z0-9]*)?((?:\.[\w-]+)*)", part)
    if not m or not part:
        return None
    return (m.group(1).lower() if m.group(1) else None, set(c for c in m.group(2).split(".") if c))


def readable_chain(part):
    """One selector as a chain of compounds, or None when it uses anything beyond tags, .classes, tag.class
    compounds and descendant space (`>`, `+`, `~`, `:`, `[`, `#`, `*`)."""
    if re.search(r"[>+~\[\]:#*]", part):
        return None
    chain = [parse_compound(c) for c in part.split()]
    return None if not chain or any(c is None for c in chain) else chain


def parse_selectors(spec):
    """The same grammar mine-sizes.py reads: a comma list of selectors, each a descendant chain of
    compounds (`h1`, `.plate-title`, `h3.plate-title`, `.prose h1`, `article.latest .plate-title`).
    Combinators other than descendant space (`>`, `+`, `~`), pseudo-classes and attribute selectors
    are refused with the reason, because this tool matches markup without a CSS engine."""
    selectors = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if re.search(r"[>+~\[\]:#*]", part):
            sys.exit(f"selector {part!r}: this tool reads tags, .classes, tag.class compounds and descendant chains only; "
                     f"'>', '+', '~', ':', '[', '#' and '*' are not understood")
        chain = readable_chain(part)
        if chain is None:
            sys.exit(f"selector {part!r} is not a tag, .class, tag.class or a space-separated chain of them")
        selectors.append((part, chain))
    if not selectors:
        sys.exit("--selectors is empty")
    return selectors


def compound_matches(compound, tag, classes):
    t, cs = compound
    return (t is None or t == tag) and cs <= classes


def chain_matches(chain, ancestry):
    """`ancestry` is the open elements as (tag, classes), outermost first, the element itself last."""
    if not compound_matches(chain[-1], *ancestry[-1]):
        return False
    i = len(ancestry) - 2
    for compound in reversed(chain[:-1]):
        while i >= 0 and not compound_matches(compound, *ancestry[i]):
            i -= 1
        if i < 0:
            return False
        i -= 1
    return True


def describe(c):
    try:
        name = unicodedata.name(c)
    except ValueError:
        name = "no name"
    return f"U+{ord(c):04X} {name}"


def mine_html(root, selectors, transforms=()):
    pages = sorted(p for p in pathlib.Path(root).rglob("*.html") if p.is_file())
    if not pages:
        sys.exit(f"no .html files under {root}")
    first_use, titles, matched, by_selector, by_transform = {}, [], {}, {text: {} for text, _ in selectors}, {}
    for page in pages:
        p = DisplayText(selectors, transforms)
        try:
            p.feed(page.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            sys.exit(f"cannot read {page}: {exc}")
        rel = page.relative_to(root).as_posix()
        for c in p.chars:
            first_use.setdefault(c, rel)
        for text, chars in p.by_selector.items():
            for c in chars:
                by_selector[text].setdefault(c, None)
        for key, chars in p.by_transform.items():
            for c in chars:
                by_transform.setdefault(key, {}).setdefault(c, None)
        # collapse ASCII whitespace only: str.split() would also eat the no-break spaces being counted
        titles += [(re.sub(r"[ \t\r\n\f]+", " ", t).strip(), rel) for t in p.texts if t.strip()]
        for s, n in p.matched.items():
            matched[s] = matched.get(s, 0) + n
    unmatched = [s for s, n in matched.items() if n == 0]
    return first_use, titles, unmatched, len(pages), by_selector, by_transform


def mine_titles(file):
    try:
        lines = pathlib.Path(file).read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError) as exc:
        sys.exit(f"cannot read {file}: {exc}")
    first_use, titles = {}, []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        titles.append((line.rstrip("\r"), f"line {i}"))
        for c in line.rstrip("\r"):
            if not c.isspace() or c in (" ", " "):
                first_use.setdefault(c, f"line {i}")
    if not titles:
        sys.exit(f"{file} holds no titles")
    return first_use, titles


def report(first_use, titles, source_count, as_json, transform_note="not read: no --css", added=()):
    chars = sorted(first_use)
    nbsp = sum(t.count(" ") for t, _ in titles)
    straight = sum(t.count("'") for t, _ in titles)
    marks = {m: sum(t.count(m) for t, _ in titles) for m in "#+*"}
    accented = [c for c in chars if c.isalpha() and ord(c) > 127]
    unusual = [c for c in chars if c not in PLAIN]
    longest = max(titles, key=lambda t: len(t[0])) if titles else ("", "")
    # NBSP (U+00A0) stays in required_characters when the titles carry it: nbsp_to_space maps it to the space
    # glyph, and test_every_required_character_is_mapped must see it (second dry run, finding 11). A plain
    # space is required alongside, because the glyph NBSP maps to is the space glyph.
    required = "".join(chars)
    if " " in first_use and " " not in required:
        required = " " + required
    out = {
        "sources": source_count,
        "distinct_characters": len(chars),
        "nbsp_count": nbsp,
        "straight_apostrophe_count": straight,
        "marks": marks,
        "accented_letters": accented,
        "longest_title": {"text": longest[0], "length": len(longest[0]), "where": longest[1]},
        "unusual_characters": [{"char": c, "codepoint": describe(c), "first": first_use[c]} for c in unusual],
        "text_transform": transform_note,
        "case_mapped": list(added),
        "charset": {"required": required, "nbsp_to_space": nbsp > 0, "ascii_apostrophe_curly": straight > 0},
        "required_characters": required,
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    print(f"{len(chars)} distinct characters in the display text of {source_count} source(s)")
    print(f"no-break spaces: {nbsp}   straight apostrophes ('): {straight}   #: {marks['#']}  +: {marks['+']}  *: {marks['*']}")
    print(f"accented letters: {' '.join(accented) if accented else 'none'}")
    print(f"longest title ({len(longest[0])} chars, {longest[1]}): {longest[0]}")
    print("unusual characters (first use):")
    for u in out["unusual_characters"]:
        print(f"  {u['char']!r:6} {u['codepoint']:40} {u['first']}")
    print(f"text-transform: {transform_note}")
    for a in out["case_mapped"]:
        print(f"  {a['char']!r:6} {a['codepoint']:40} drawn by {a['selector']} ({a['transform']}) from {a['from']!r}")
    print("\ncharset block for font.json:")
    print(json.dumps({"charset": out["charset"]}, ensure_ascii=False, indent=2))
    print("required_characters for requirements.json:")
    print(json.dumps(required, ensure_ascii=False))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--html", metavar="DIR", help="built site: every .html under DIR is read")
    src.add_argument("--titles", metavar="FILE", help="one title per line")
    ap.add_argument("--selectors", default=None, help="comma list of selectors the display face sets, as mine-sizes.py reads them: "
                    "tag, .class, tag.class, descendant chains (default h1,h2,h3 unless --family)")
    ap.add_argument("--css", metavar="FILE", help="the stylesheet: enables --family and the text-transform reading")
    ap.add_argument("--family", metavar="NAME", help="with --css: mine every selector whose rule sets font-family: NAME first")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.html:
        css_text = None
        if args.css:
            try:
                css_text = pathlib.Path(args.css).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                sys.exit(f"cannot read {args.css}: {exc}")
        elif args.family:
            sys.exit("--family needs --css FILE: the selectors are found in the stylesheet")
        from_family = []
        if args.family:
            from_family = load_mine_sizes().selectors_for_family(css_text, args.family)
            if not from_family:
                sys.exit(f"no rule in {args.css} sets font-family: {args.family} first (the name is spelled differently, or the family "
                         f"is set through the `font:` shorthand or a custom property, which this tool does not read)")
        spec = ",".join(from_family + [args.selectors or ("" if from_family else "h1,h2,h3")])
        selectors = parse_selectors(spec)
        rules, unread = transform_rules(css_text) if css_text is not None else ([], [])
        first_use, titles, unmatched, n, by_selector, by_transform = mine_html(args.html, selectors, rules)
        if unmatched:
            sys.exit(f"selector(s) matched nothing in any of {n} pages: {', '.join(unmatched)} (a typo, or the class is not in the built HTML)")
        note, added = "not read: no --css", []
        if css_text is not None:
            # the rules that matched an element inside the display text, in stylesheet order (one that matched
            # nothing there is not listed), then any rule this tool could not read, so it is not taken as absent
            applied = []
            for t, _, v in rules:
                if (t, tuple(v)) in by_transform and (t, v) not in applied:
                    applied.append((t, v))
            note = ("; ".join(f"{t}: {'/'.join(v)}" for t, v in applied) or ("none declared" if not rules else "none applies to the display text")) \
                + "".join(f"; not read: {u}" for u in unread) + f" (read from {args.css})"
            added = case_mapped(by_transform, first_use)
        report(first_use, titles, n, args.json, note, added)
    else:
        first_use, titles = mine_titles(args.titles)
        report(first_use, titles, len(titles), args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
