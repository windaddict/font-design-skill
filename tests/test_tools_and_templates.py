"""The review and concept tools run on the fixtures, and the shipped templates are inert and fillable.

WHAT IT'S FOR: these are the tools a run of the skill reaches for after the font exists (and before,
for the concept pages), and each has a quiet failure mode the plan names: a concept page that builds
markup from content (finding F009), a charset miner that drops the no-break space with str.split(),
a screenshot tool that quietly lays out a 360 px request at 500 px, a site-test template that no
longer compiles once its slots are filled. Every test here executes the real script on the fixtures
under tests/fixtures/ or examples/neutral/, without a browser, so it runs in CI.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, node, run

NEUTRAL = REPO / "examples" / "neutral"
CONCEPTS = REPO / "scripts" / "concepts"
SAMPLE = REPO / "tests" / "fixtures" / "site-sample"


def build_page(template, content, out):
    return run([node(), str(CONCEPTS / "build-page.js"), "--template", template, "--concepts", str(NEUTRAL / "concepts.js"), "--content", str(content), str(out)])


def json_block(html):
    m = re.search(r'<script type="application/json" id="fd-content">(.*?)</script>', html, re.S)
    assert m, "the content block is missing"
    return m.group(1)


@pytest.mark.parametrize("template", ["round1", "round2", "round3"])
def test_each_round_builds_from_the_neutral_content_and_embeds_it_inertly(template, tmp_path):
    out = tmp_path / f"{template}.html"
    r = build_page(template, NEUTRAL / "content.json", out)
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    block = json_block(html)
    assert "<" not in block and ">" not in block and "&" not in block, "the embedded JSON must escape every markup character"
    parsed = json.loads(block)
    assert isinstance(parsed, dict) and parsed.get("titles"), "the embedded content must parse back"
    assert html.count("/*GEN*/") == 0 and html.count("/*CONTENT*/") == 0, "a placeholder survived"
    assert "innerHTML" not in html


def test_the_minimal_content_builds_round_one_and_says_what_rounds_two_and_three_need(tmp_path):
    """Dry-run finding W10: a project needs a content skeleton with only the required fields.
    scripts/concepts/content.minimal.json must build round 1 as is, and rounds 2 and 3 must refuse it
    naming the key they need (so its own note stays true)."""
    minimal = CONCEPTS / "content.minimal.json"
    r = build_page("round1", minimal, tmp_path / "r1.html")
    assert r.returncode == 0, r.stderr
    for template, key in (("round2", "choosing"), ("round3", "verdict")):
        r = build_page(template, minimal, tmp_path / f"{template}.html")
        assert r.returncode != 0 and key in (r.stderr + r.stdout), f"{template} should refuse the minimal content naming {key}"


def test_the_mock_slot_sizes_come_from_content_and_an_unknown_slot_is_refused(tmp_path):
    """Second dry run, finding 7: the round-2/3 mocks hard-coded hop-safari's sizes. content.slot_sizes
    overrides size, min, fit and lh per named slot; the builder refuses a slot name it does not know
    (a typo would otherwise keep the default in silence) and a field that is not one of the four. The
    sizes taking effect in the rendered page is test_the_mock_slot_sizes_take_effect_in_chrome below."""
    content = json.loads((CONCEPTS / "content.example.json").read_text(encoding="utf-8"))
    assert "slot_sizes" in content and "article_title" in content["slot_sizes"], "the example content documents slot_sizes"
    content["slot_sizes"] = {"article_title": {"size": 60, "min": 30}}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    assert build_page("round2", path, tmp_path / "r2.html").returncode == 0
    content["slot_sizes"] = {"article_titel": {"size": 60}}
    path.write_text(json.dumps(content), encoding="utf-8")
    r = build_page("round2", path, tmp_path / "r2b.html")
    assert r.returncode != 0 and "slot_sizes.article_titel names no mock slot" in r.stderr, r.stderr
    content["slot_sizes"] = {"article_title": {"size": 60, "weight": 700}}
    path.write_text(json.dumps(content), encoding="utf-8")
    r = build_page("round2", path, tmp_path / "r2c.html")
    assert r.returncode != 0 and "slot_sizes.article_title.weight is not one of size, min, fit, lh" in r.stderr, r.stderr


def test_the_builder_refuses_a_missing_placeholder_and_a_bad_image_path(tmp_path):
    bad_tmpl = tmp_path / "t.html"
    bad_tmpl.write_text((CONCEPTS / "round1-template.html").read_text(encoding="utf-8").replace("/*RENDER*/", ""), encoding="utf-8")
    r = build_page(str(bad_tmpl), NEUTRAL / "content.json", tmp_path / "x.html")
    assert r.returncode != 0 and "RENDER" in (r.stderr + r.stdout)
    # round 1 does not read the mock pages, so the bad path is reached by rounds 2 and 3
    r = build_page("round2", REPO / "tests" / "fixtures" / "content-adversarial.json", tmp_path / "adv.html")
    assert r.returncode != 0, "the adversarial fixture's img/../x.jpg path must be refused"
    assert "img/../x.jpg" in (r.stderr + r.stdout)
    assert not (tmp_path / "adv.html").exists()


@pytest.mark.parametrize("template", ["round1", "round2", "round3"])
def test_hostile_text_renders_inertly(template, tmp_path):
    """F009: quotes, </script>, <img onerror>, an inline script and U+2028 in every text field. The
    page must build, its JSON block must contain none of them raw, and no onerror attribute may exist."""
    adv = json.loads((REPO / "tests" / "fixtures" / "content-adversarial.json").read_text(encoding="utf-8"))
    fixed = json.loads(json.dumps(adv).replace('"img/../x.jpg"', "null"))
    content = tmp_path / "adv.json"
    content.write_text(json.dumps(fixed), encoding="utf-8")
    out = tmp_path / f"{template}.html"
    r = build_page(template, content, out)
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    block = json_block(html)
    assert "</script" not in block and "<img" not in block and "\u2028" not in block
    assert not re.search(r"<img[^>]*onerror", html), "an onerror attribute reached the markup"
    assert "data-fd-pwned" not in html.split('id="fd-content"')[0].split("<script>")[0]


def test_mine_charset_counts_the_traps_and_names_the_first_page():
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE), "--selectors", "h1,h2,h3,.plate-title,.wordmark", "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["nbsp_count"] == 5, "str.split() eats U+00A0; the first version of the miner counted 0"
    assert data["straight_apostrophe_count"] == 2
    assert "Ž" in data["accented_letters"] and data["longest_title"]["where"] == "essay.html"
    # U+00A0 stays in required_characters beside the plain space (second dry run, finding 11): nbsp_to_space maps it
    # to the space glyph, and test_every_required_character_is_mapped must see it in the cmap
    assert "'" in data["required_characters"] and "#" in data["required_characters"]
    assert "\u00a0" in data["required_characters"] and " " in data["required_characters"], repr(data["required_characters"])
    assert data["charset"]["required"] == data["required_characters"]
    assert data["charset"]["nbsp_to_space"] is True
    assert data["text_transform"] == "not read: no --css" and data["case_mapped"] == []
    text = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE), "--selectors", "h1,h2,h3,.plate-title,.wordmark"]).stdout
    assert "no-break spaces: 5" in text and "U+00A0" in text
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE), "--selectors", "h1,.no-such-class"])
    assert r.returncode != 0 and "no-such-class" in (r.stderr + r.stdout)


def test_mine_charset_reads_descendant_and_compound_selectors_like_mine_sizes():
    """Dry-run finding W8: the two miners read different selector grammars, so a selector that worked
    for mine-sizes was refused by mine-charset with a message naming the wrong cause. Both now read
    tags, .classes, tag.class compounds and descendant chains; a chain whose ancestor is absent
    matches nothing (exit 1 naming it), and an unsupported combinator is refused naming the reason."""
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE),
             "--selectors", ".frontispiece h1,article.latest .plate-title,h3.plate-title,h2", "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["nbsp_count"] >= 2 and "#" in data["required_characters"], data
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE), "--selectors", ".nope h1"])
    assert r.returncode != 0 and ".nope h1" in (r.stderr + r.stdout), "a chain with an absent ancestor must match nothing"
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(SAMPLE), "--selectors", "h1 > b"])
    assert r.returncode != 0 and "'>'" in (r.stderr + r.stdout), r.stderr


WIRED_CSS = """
@font-face { font-family: 'Sampler'; src: url('/fonts/sampler/Sampler-VF.woff2') format('woff2'); font-weight: 400 700; }
h1, h2, h3, .plate-title, .frontis-title { font-family: 'Sampler', Georgia, serif; }
.wordmark { font-family: "Sampler", Georgia, serif; }
@media (max-width: 700px) { .chapters .num { font-family: Sampler, serif; } }
"""


def wired_site(tmp_path):
    """The fixture site with Sampler wired into its stylesheet in three quote styles, one rule inside @media."""
    site = tmp_path / "site"
    shutil.copytree(SAMPLE, site)
    css = site / "css" / "site.css"
    css.write_text(css.read_text(encoding="utf-8") + WIRED_CSS, encoding="utf-8")
    return site, css


def test_mine_sizes_family_finds_every_selector_set_in_the_display_face(tmp_path):
    """Second dry run, finding 16: a hand-typed selector list missed .frontis-title, .wordmark and the
    15.2 px .num, which moved the floor from 44.6 to 49.3 units. --family NAME mines every selector whose
    rule sets that family first, across quote styles and inside @media, and prints the list. Mutations
    watched red: selectors_for_family() returning [] (exit 2 naming the family); the @media descent
    dropped (.num missing, floor 44.6)."""
    site, css = wired_site(tmp_path)
    r = run([sys.executable, str(REPO / "scripts" / "mine-sizes.py"), str(css), "--family", "Sampler", "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["selectors_from_family"] == ["h1", "h2", "h3", ".plate-title", ".frontis-title", ".wordmark", ".chapters .num"], data["selectors_from_family"]
    assert data["smallest_px"] == 15.2 and data["floor_units"] == 49.3, (data["smallest_px"], data["floor_units"])
    r = run([sys.executable, str(REPO / "scripts" / "mine-sizes.py"), str(css), "--family", "Sampler", "--selectors", ".lede"])
    assert r.returncode == 0, r.stderr
    assert "selectors whose rule sets font-family: Sampler first: h1,h2,h3,.plate-title,.frontis-title,.wordmark,.chapters .num" in r.stdout, r.stdout
    r = run([sys.executable, str(REPO / "scripts" / "mine-sizes.py"), str(SAMPLE / "css" / "site.css"), "--family", "Georgia"])
    assert r.returncode != 0 and "`font:` shorthand" in r.stderr, "Georgia is set only through the body's `font:` shorthand, which the tool must say it cannot read"


def test_mine_charset_family_and_text_transform_through_the_stylesheet(tmp_path):
    """Second dry run, findings 10 and 16: mine-charset.py read source text only, so .wordmark's
    `text-transform: uppercase` was invisible, and its selectors were typed by hand. With --css the
    selectors come from --family and every mined selector's text-transform adds the characters the
    browser draws, each named with the selector and the source character (J K P Z: no capital of these
    appears in the fixture's display text, so they can only come from the transform). Mutations watched
    red: case_mapped() adding nothing (J K P Z absent); --family ignored (the .num characters I, II, III,
    IV absent and the wordmark letters absent)."""
    site, css = wired_site(tmp_path)
    (site / "extra.html").write_text('<!doctype html><html><head><link rel="stylesheet" href="css/site.css"></head>'
                                     '<body><a class="wordmark" href="/">jkpz</a><p>Body text: xyz</p></body></html>', encoding="utf-8")
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(site), "--css", str(css), "--family", "Sampler", "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["text_transform"].startswith(".wordmark: uppercase"), data["text_transform"]
    assert {a["char"] for a in data["case_mapped"]} == {"J", "K", "P", "Z"}, data["case_mapped"]
    by_char = {a["char"]: a for a in data["case_mapped"]}
    assert by_char["J"]["selector"] == ".wordmark" and by_char["J"]["from"] == "j" and by_char["J"]["transform"] == "uppercase", by_char["J"]
    assert all(c in data["required_characters"] for c in "JKPZjkpzIV"), repr(data["required_characters"])
    assert "x" not in data["required_characters"], "body text was counted"
    text = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(site), "--css", str(css), "--family", "Sampler"]).stdout
    assert "text-transform: .wordmark: uppercase" in text and "drawn by .wordmark (uppercase) from 'j'" in text, text
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(site), "--family", "Sampler"])
    assert r.returncode != 0 and "--family needs --css" in r.stderr, r.stderr


def test_mine_charset_sees_a_text_transform_on_a_descendant_and_on_a_class_inside_the_display_text(tmp_path):
    """Re-review code-b F006: text_transforms() associated a transform with a mined selector only when the
    rule's selector matched that selector's text, so `.display span { text-transform: uppercase }` under a
    mined `.display` added nothing, and neither did a `.caps` class on an element inside an h1. Both now add
    the capitals, each named with the rule responsible; a transform rule the tool cannot read is named in the
    text_transform field rather than dropped. Mutation watched red: DisplayText not inheriting the parent's
    active transform rules (the span's text is then collected under no rule and C, D are absent)."""
    pages = tmp_path / "pages"
    pages.mkdir()
    css = tmp_path / "site.css"
    css.write_text(".display { font-family: 'Sampler', serif; font-size: 2rem; }\n.display span { text-transform: uppercase; }\n"
                   "h1 { font-family: 'Sampler', serif; }\n.caps { text-transform: uppercase; }\n.display > b { text-transform: lowercase; }\n", encoding="utf-8")
    (pages / "p.html").write_text('<!doctype html><html><head><link rel="stylesheet" href="../site.css"></head><body>'
                                  '<h1 class="display">ab <span>cd <i>ef</i></span></h1><h1>gh <em class="caps">ij</em></h1>'
                                  '<p class="caps">zz</p></body></html>', encoding="utf-8")
    r = run([sys.executable, str(REPO / "scripts" / "mine-charset.py"), "--html", str(pages), "--css", str(css), "--family", "Sampler", "--json"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert {a["char"] for a in data["case_mapped"]} == {"C", "D", "E", "F", "I", "J"}, data["case_mapped"]
    by_char = {a["char"]: a for a in data["case_mapped"]}
    assert by_char["C"]["selector"] == ".display span" and by_char["F"]["selector"] == ".display span" and by_char["I"]["selector"] == ".caps", by_char
    assert "Z" not in data["required_characters"] and "z" not in data["required_characters"], "the .caps paragraph is not display text"
    assert data["text_transform"].startswith(".display span: uppercase; .caps: uppercase; not read: .display > b"), data["text_transform"]


def test_the_mock_rounds_refuse_content_without_slot_sizes_and_name_the_slots_left_at_the_default(tmp_path):
    """Re-review code-b F007: slot_sizes was optional, so rounds 2 and 3 built at the template's fixed sizes
    with nothing said when the block was missing. It is required for both rounds, and every named slot the
    block leaves out is listed on stderr as keeping the default. Mutation watched red: the spec entry back to
    "slotsizes?" (the block-less content builds); the stderr line removed."""
    content = json.loads((NEUTRAL / "content.json").read_text(encoding="utf-8"))
    assert "slot_sizes" in content and len(content["slot_sizes"]) == 17, "the neutral example documents every slot"
    content.pop("slot_sizes")
    path = tmp_path / "c.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    for template in ("round2", "round3"):
        r = build_page(template, path, tmp_path / f"{template}.html")
        assert r.returncode != 0 and "content.slot_sizes is missing" in r.stderr, (template, r.stderr)
    assert build_page("round1", path, tmp_path / "round1.html").returncode == 0, "round 1 has no mock slots and needs no block"
    content["slot_sizes"] = {"article_title": {"size": 48}}
    path.write_text(json.dumps(content), encoding="utf-8")
    r = build_page("round2", path, tmp_path / "r2.html")
    assert r.returncode == 0, r.stderr
    assert "16 mock slot(s) not in content.slot_sizes keep the template's default size: " in r.stderr and "contents_title" in r.stderr, r.stderr
    assert "article_title" not in r.stderr.split("default size:")[1], r.stderr


def test_mine_sizes_reports_the_smallest_size_and_the_floor_formula():
    r = run([sys.executable, str(REPO / "scripts" / "mine-sizes.py"), str(SAMPLE / "css" / "site.css"),
             "--selectors", "h1,.plate-title,.num", "--root", "100", "150"])
    assert r.returncode == 0, r.stderr
    assert "smallest display size: 15.2px" in r.stdout, r.stdout
    assert "hairline floor: 49.3 units" in r.stdout and "1000 x 0.75 / 15.2" in r.stdout, r.stdout
    assert "32 to 48px" in r.stdout
    r = run([sys.executable, str(REPO / "scripts" / "mine-sizes.py"), str(SAMPLE / "css" / "site.css"), "--selectors", "h1,.desc"])
    assert r.returncode != 0 and ".desc" in (r.stderr + r.stdout)


def test_shoot_refuses_a_width_under_500_before_looking_for_chrome(tmp_path):
    """Trap 7: Chrome headless lays out at 500 px minimum and crops narrower requests, which reads as
    overflow. The refusal must not depend on Chrome being installed, so CI without a browser sees it."""
    env = {"PATH": "/nonexistent", "CHROME": str(tmp_path / "no-chrome")}
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(tmp_path / "o"), "--serve", str(tmp_path), "--widths", "360"],
                       capture_output=True, text=True, env=env, cwd=REPO)
    assert r.returncode != 0
    assert "500" in r.stderr and "narrow.html" in r.stderr, r.stderr


def test_shoot_names_chrome_when_it_cannot_find_one(tmp_path):
    env = {"PATH": str(tmp_path), "CHROME": str(tmp_path / "no-chrome")}
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(tmp_path / "o"), "--serve", str(tmp_path), "--widths", "500"],
                       capture_output=True, text=True, env=env, cwd=REPO)
    assert r.returncode != 0 and "CHROME" in r.stderr, r.stderr


def test_specimen_renders_from_the_neutral_config_without_a_browser(tmp_path):
    """The page carries every review size and title, and the proof rows: the four spacing kinds with their exact
    leading control strings (written here from the alphabet) and the legibility row at the smallest review size and
    its weight. Weakest mutations watched red: the spacing loop made empty (every row gone); the legibility row set
    at the largest size; its weight forced to 400; the capitals group switched off."""
    out = tmp_path / "specimen.html"
    r = run([sys.executable, str(REPO / "scripts" / "specimen.py"), "--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"),
             "--group", "roman", "--font-url", "/fonts/Sampler-VF.woff2", str(out)])
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    cfg = json.loads((NEUTRAL / "font.json").read_text())
    for size in cfg["review"]["sizes"]:
        assert f"font-size:{size}px" in html.replace(" ", ""), f"{size}px row missing"
    import html as html_mod
    for title in cfg["titles"]:
        t = html_mod.escape(title, quote=True)
        assert t in html or t.replace("\u00a0", "&nbsp;") in html or title in html, f"title {title!r} missing"
    assert "font-optical-sizing: auto" in html and "font-synthesis: none" in html
    assert "/fonts/Sampler-VF.woff2" in html
    # the proof rows: four spacing kinds and the legibility row, observed in the written page
    rows = proof_rows(html)
    assert sorted(k for k in rows if k.startswith("spacing")) == ["spacing:figures", "spacing:lower", "spacing:punct", "spacing:upper"], sorted(rows)
    assert rows["spacing:lower"][2].startswith("nnann ooaoo nnbnn ooboo"), rows["spacing:lower"][2][:40]
    assert rows["spacing:upper"][2].startswith("HHAHH OOAOO HHBHH OOBOO"), rows["spacing:upper"][2][:40]
    assert rows["spacing:figures"][2].startswith("00000 11011 00100 11111"), rows["spacing:figures"][2][:40]
    assert rows["spacing:punct"][2].startswith("r. f. y. r, f, y,"), rows["spacing:punct"][2][:40]
    size, weight, text = rows["legibility"]
    smallest = min(cfg["review"]["sizes"])
    assert text == "Il1 O0 B8 rn m cl d" and size == smallest, rows["legibility"]
    assert weight == (500 if smallest < cfg["review"]["medium_below_px"] else 400), rows["legibility"]


def proof_rows(html):
    """{"spacing:<kind>", "legibility" or "junctions": (px, weight, text)} read from a written specimen page."""
    import html as html_mod
    pat = r'<p class="f" data-fd-(?:spacing="(\w+)"|(legibility|junctions)="true")[^>]*style="font-size:([\d.]+)px; font-weight:(\d+)[^"]*">(.*?)</p>'
    return {("spacing:" + kind if kind else leg): (float(px), int(w), html_mod.unescape(inner))
            for kind, leg, px, w, inner in re.findall(pat, html, re.S)}


def test_the_specimen_carries_the_junction_row(tmp_path):
    """The junction row sets the glyphs whose strokes meet end to end (measured with node over gen.js on a serif concept, plan-0.2
    section 0: `1 4 5 v w A M N V W`; `y` and `k` are not joints) and two runs of them, in the Bold, at the smallest review size,
    marked data-fd-junctions, and it comes BEFORE the readable rows like every proof row. The expected text, size and weight are
    written here from the config, not read from specimen.py. With a font file that lacks `5` and `W`, the tokens that need them are
    dropped and the others stay. Weakest mutations watched red 2026-11-16: the row's tokens built from an empty list (no row);
    the row set at weight 400; the row set at the largest size."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    cfg = json.loads((NEUTRAL / "font.json").read_text())
    wght_max = next(a["max"] for a in cfg["groups"]["roman"]["axes"] if a["tag"] == "wght")
    base = [sys.executable, str(REPO / "scripts" / "specimen.py"), "--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"),
            "--group", "roman", "--font-url", "/fonts/Sampler-VF.woff2"]
    out = tmp_path / "specimen.html"
    r = run([*base, str(out)])
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    size, weight, text = proof_rows(html)["junctions"]
    assert text == "1 4 5 v w A M N V W AVAWMNW vwvwv", text
    assert size == min(cfg["review"]["sizes"]) and weight == wght_max, (size, weight)
    assert "y" not in text and "k" not in text, "y and k have no end-to-end joint and do not belong in the row"
    assert 0 < html.index('data-fd-junctions="true"') < html.index("Readable on"), "the junction row is a proof row and must precede the readable rows"
    assert "[data-fd-junctions]" in html, "the page's proof-bottom script must count the junction row, or a shot can cut it off unnoticed"
    src = NEUTRAL / "out" / "Sampler-VF.woff2"
    if not src.is_file():
        pytest.fail("the neutral example is not built; the dropped-token half of this test needs examples/neutral/out/Sampler-VF.woff2 (build it)")
    font = TTFont(src)
    opts = subset.Options()
    opts.layout_features, opts.notdef_outline = ["*"], True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=[cp for cp in font.getBestCmap() if chr(cp) not in "5W"])
    sub.subset(font)
    font.flavor = "woff2"
    part = tmp_path / "Part.woff2"
    font.save(part)
    r = run([*base, "--font-file", str(part), "--allow-missing", str(tmp_path / "part.html")])
    assert r.returncode == 0, r.stderr
    assert proof_rows((tmp_path / "part.html").read_text(encoding="utf-8"))["junctions"][2] == "1 4 v w A M N V vwvwv"


def test_the_proof_rows_hold_only_characters_the_font_file_maps(tmp_path):
    """A subset of the built Sampler without q, Z, 8 and ! is given as --font-file: no control string may set
    those characters (they would fall back to the system face), the legibility row drops its `B8` word, and the
    full font still has them. Mutation watched red: the cmap filter in specimen.build() switched off
    (`if font_file is not None and ... is_file()` made `if False`)."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    src = NEUTRAL / "out" / "Sampler-VF.woff2"
    if not src.is_file():
        pytest.skip("SKIPPED, NOT PASSED: examples/neutral/out/Sampler-VF.woff2 is not built (build the neutral example first)")
    font = TTFont(src)
    keep = [cp for cp in font.getBestCmap() if chr(cp) not in "qZ8!"]
    opts = subset.Options()
    opts.layout_features, opts.notdef_outline = ["*"], True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=keep)
    sub.subset(font)
    part = tmp_path / "Part.woff2"
    font.flavor = "woff2"
    font.save(part)
    base = [sys.executable, str(REPO / "scripts" / "specimen.py"), "--font", str(NEUTRAL / "font.json"), "--group", "roman", "--font-url", "/fonts/Sampler-VF.woff2"]
    r = run([*base, "--font-file", str(src), str(tmp_path / "whole.html")])
    assert r.returncode == 0, r.stderr
    whole = proof_rows((tmp_path / "whole.html").read_text(encoding="utf-8"))
    assert "nnqnn" in whole["spacing:lower"][2] and "HHZHH" in whole["spacing:upper"][2]
    assert "00800" in whole["spacing:figures"][2] and "r! " in whole["spacing:punct"][2]
    r = run([*base, "--font-file", str(part), "--allow-missing", str(tmp_path / "part.html")])
    assert r.returncode == 0, r.stderr
    rows = proof_rows((tmp_path / "part.html").read_text(encoding="utf-8"))
    assert "q" not in rows["spacing:lower"][2].replace("nn", "").replace("oo", "") and "Z" not in rows["spacing:upper"][2]
    assert "8" not in rows["spacing:figures"][2].replace("00", "").replace("11", "") and "!" not in rows["spacing:punct"][2]
    assert rows["legibility"][2] == "Il1 O0 rn m cl d", rows["legibility"]


def test_the_site_wiring_template_compiles_once_its_slots_are_filled(tmp_path):
    tmpl = (REPO / "scripts" / "tests" / "test_site_wiring.py.tmpl").read_text(encoding="utf-8")
    slots = set(re.findall(r"{{\s*([a-z_]+)\s*}}", tmpl))
    assert slots, "the template has no slots"
    values = {s: f"SLOT_{s}" for s in slots}
    values.update({"opsz_max_px": "80", "display_selectors": '["h1", ".title"]', "medium_selectors": '[".small"]',
                   "preload_tag": '<link rel="preload" href="/f.woff2" as="font" type="font/woff2" crossorigin />',
                   "stylesheet_tag": '<link rel="stylesheet" href="/css/site.css" />', "old_family_pattern": "OldFace|Older"})
    filled = re.sub(r"{{\s*([a-z_]+)\s*}}", lambda m: values[m.group(1)], tmpl)
    assert "{{" not in filled
    compile(filled, "test_site_wiring.py", "exec")
    assert "font-synthesis" in filled and "does not use it" in filled, "the recommendation must say Bract did not use it"


def chrome_or_skip():
    """The Chrome-marked tests need a browser. A skip is a check nobody performed, so the reason is
    printed, and the CI job that installs Chrome runs these tests by the "chrome" keyword."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("shoot", REPO / "scripts" / "shoot.py")
    shoot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shoot)
    try:
        return shoot.find_chrome()
    except FileNotFoundError as exc:
        pytest.skip(f"no Chrome: {exc} (set CHROME; the CI chrome job runs this test)")


@pytest.mark.parametrize("template", ["round1", "round2", "round3"])
def test_hostile_text_is_inert_in_chrome(template, tmp_path):
    """Review finding C10 (of this repo's independent review): the source-only check above cannot
    show that hostile content renders inertly. This opens each adversarial page in headless Chrome
    through shoot.py and reads the DOM Chrome built: the page ran and drew glyphs, the hostile strings
    are present as TEXT (the serialised DOM carries them entity-escaped), no element carries an
    onerror handler, no script beyond the template's own two exists, nothing set data-fd-pwned (the
    fixture's inline script would), and no runtime error was recorded.
    --dom-only, not --dump-dom: the hostile page's DOM is 96-124 MB of SVG path data (6,106-7,790
    glyphs at ~1,200 path points each, because the fixture prefixes ~190 hostile characters to all
    185 strings), and asked to screenshot it under --virtual-time-budget Chrome 156/157 on the macOS
    CI runners stalled before the screenshot in about half of all attempts ("Chrome took over 300s",
    10 of 14 macOS jobs on PR #2, 2026-11-17). Without --screenshot it never stalled in 12 probes.
    Nothing here reads the PNG."""
    chrome = chrome_or_skip()
    adv = json.loads((REPO / "tests" / "fixtures" / "content-adversarial.json").read_text(encoding="utf-8"))
    fixed = json.loads(json.dumps(adv).replace('"img/../x.jpg"', "null"))
    pages = tmp_path / "pages"
    pages.mkdir()
    content = tmp_path / "adv.json"
    content.write_text(json.dumps(fixed), encoding="utf-8")
    r = build_page(template, content, pages / f"{template}.html")
    assert r.returncode == 0, r.stderr
    shots = tmp_path / "shots"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(shots), "--serve", str(pages), "--pages", f"{template}.html",
                        "--widths", "1280", "--scales", "1", "--dom-only", "--no-sentinel", "--bands", "none"],
                       capture_output=True, text=True, cwd=REPO, env={**os.environ, "CHROME": chrome})
    assert r.returncode == 0, r.stderr[-1500:]
    doms = list(shots.glob("*.dom.html"))
    assert len(doms) == 1, doms
    assert not list(shots.glob("*.png")), "--dom-only must not take a screenshot"
    dom = doms[0].read_text(encoding="utf-8")
    assert int(re.search(r'data-fd-rendered="(\d+)"', dom).group(1)) > 0, "the page did not draw"
    # the hostile TEXT itself contains the attribute name, so the check is on the <html> element
    assert not re.search(r"<html[^>]*data-fd-pwned", dom), "the fixture's inline script ran"
    assert not re.search(r"<html[^>]*data-fd-error", dom), "a runtime error was recorded in the page"
    # attribute VALUES legitimately carry the hostile text (aria-label, data-t); only a real attribute
    # named on* or a third script element would mean the content was parsed as markup
    from html.parser import HTMLParser

    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.handlers, self.scripts, self.imgs = [], 0, 0

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                self.scripts += 1
            if tag == "img":
                self.imgs += 1
            for name, _ in attrs:
                if name.lower().startswith("on"):
                    self.handlers.append((tag, name))

    el = Elements()
    el.feed(dom)
    assert not el.handlers, f"event-handler attributes reached the DOM: {el.handlers}"
    assert el.scripts == 2, f"{el.scripts} script elements; the template has exactly two"
    assert el.imgs == 0, "the hostile <img> became an element"
    assert "&lt;/script&gt;" in dom and "onerror=alert(1)" in dom, "the hostile text is not present as text"
    assert "<img src=x onerror" not in dom


@pytest.mark.parametrize("template", ["round2", "round3"])
def test_the_mock_slot_sizes_take_effect_in_chrome(template, tmp_path):
    """The override is read by the template's sized(): the article title slot must carry data-size="61"
    and data-min="31" in the DOM Chrome built, and a slot left out keeps its default (the contents title
    at 64). Mutation watched red: sized() returning the default unchanged."""
    chrome = chrome_or_skip()
    content = json.loads((CONCEPTS / "content.example.json").read_text(encoding="utf-8"))
    content["slot_sizes"] = {"article_title": {"size": 61, "min": 31}}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    pages = tmp_path / "pages"
    pages.mkdir()
    assert build_page(template, path, pages / f"{template}.html").returncode == 0
    shots = tmp_path / "shots"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(shots), "--serve", str(pages), "--pages", f"{template}.html",
                        "--widths", "1280", "--scales", "1", "--dump-dom", "--no-sentinel", "--bands", "none"],
                       capture_output=True, text=True, cwd=REPO, env={**os.environ, "CHROME": chrome})
    assert r.returncode == 0, r.stderr[-1500:]
    dom = next(shots.glob("*.dom.html")).read_text(encoding="utf-8")
    title = content["pages"]["article"]["title"]
    m = re.search(r'<div class="r" data-t="' + re.escape(title) + r'" data-size="([^"]*)"(?: data-w="[^"]*")? data-min="([^"]*)"', dom)
    assert m and (m.group(1), m.group(2)) == ("61", "31"), (m.group(0) if m else "article title slot not found", dom[:0])
    contents = content["pages"]["contents"]["title"]
    m = re.search(r'<div class="r" data-t="' + re.escape(contents) + r'" data-size="([^"]*)"', dom)
    assert m and m.group(1) == "64", "a slot left out of slot_sizes must keep its default"


def test_the_review_checklist_and_the_reviewer_brief_ask_for_the_proof_rows():
    """The specimen's spacing and legibility rows are read only if the checklist the reviewer gets names them.
    A text check on two documents, kept because the document is what the reviewer reads, and aimed at the two
    CHECKLIST ITEMS (not at any mention: the legibility string also appears in the list of specimen rows, so a
    whole-file search survived deleting it from the item): the item that starts "Spacing, then kerning" must name
    the control-string patterns and the rule that spacing is reported before any kern, and the item that starts
    "Legibility" must hold the row verbatim and say "smallest"; the item "Junctions" must name the glyphs and say
    "smallest"; and the brief's "What changed since round" bullet must name `diff.md`. Mutations watched red: the row's
    last word dropped from the item; "before any kern" reworded; (2026-11-16) `diff.md` removed from the brief's slot; the
    junction glyph list shortened in the brief."""
    for path in (REPO / "references" / "review-loop.md", REPO / "templates" / "reviewer-brief-design-round.md"):
        text = path.read_text(encoding="utf-8")
        items = {m.group(1): re.sub(r"\s+", " ", m.group(0)) for m in re.finditer(r"^\d+\. \*\*(Spacing|Legibility)[^\n]*(?:\n(?!\d+\. |\n|## )[^\n]*)*", text, re.M)}
        assert set(items) == {"Spacing", "Legibility"}, f"{path.name}: checklist items found {sorted(items)}"
        for need in ("nn", "oo", "HH", "OO", "00", "11", "before any kern"):
            assert need in items["Spacing"], f"{path.name}: the spacing item does not mention {need!r}: {items['Spacing']}"
        assert "Il1 O0 B8 rn m cl d" in items["Legibility"] and "smallest" in items["Legibility"], f"{path.name}: {items['Legibility']}"
        junction = re.search(r"^\d+\. \*\*Junctions[^\n]*(?:\n(?!\d+\. |\n|## )[^\n]*)*", text, re.M)
        assert junction and "1 4 5 v w A M N V W" in junction.group(0) and "smallest" in junction.group(0), f"{path.name}: no junction checklist item naming the glyphs"
    brief = (REPO / "templates" / "reviewer-brief-design-round.md").read_text(encoding="utf-8")
    changed = re.search(r"^- What changed since round[^\n]*(?:\n(?!- |\n|#)[^\n]*)*", brief, re.M)
    assert changed and "diff.md" in changed.group(0), "the brief's 'what changed' slot must name diff.md, the per-round visual diff the reviewer is told to read"


def test_specimen_refuses_a_font_url_that_could_end_the_style_block(tmp_path):
    """Review finding C2: a font URL goes into the page's <style> block unescaped, so
    `</style><script>` in one would end the block and run script. css_url allow-lists URL characters
    for both the main font URL and a comparison face's url."""
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["concepts"] = str(NEUTRAL / "concepts.js")
    cfg["review"]["comparison_faces"] = [{"name": "Evil", "family": "Evil", "url": "</style><script>alert(1)</script>"}]
    font = tmp_path / "font.json"
    font.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "s.html"
    base = [sys.executable, str(REPO / "scripts" / "specimen.py"), "--font", str(font), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman"]
    r = run(base + ["--font-url", "/fonts/Sampler-VF.woff2", str(out)])
    assert r.returncode != 0 and "font URL" in (r.stderr + r.stdout), (r.returncode, r.stderr[-400:])
    assert not out.exists()
    # The --font-url cases run against the unmodified config. Against the hostile comparison face above,
    # every run is refused on that face whatever --font-url holds, so these cases could not fail: allowing
    # `<>` in the https branch alone left them green (host mutation, 2026-11-16). The clean run first
    # proves that this config builds, so a refusal below can only come from the URL being tested.
    clean = [sys.executable, str(REPO / "scripts" / "specimen.py"), "--font", str(NEUTRAL / "font.json"),
             "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman"]
    r = run(clean + ["--font-url", "https://cdn.example/x.woff2", str(out)])
    assert r.returncode == 0 and out.exists(), (r.returncode, r.stderr[-400:])
    out.unlink()
    for url in ("/fonts/x.woff2</style><script>", "https://cdn.example/x.woff2</style><script>"):
        r = run(clean + ["--font-url", url, str(out)])
        assert r.returncode != 0 and "font URL" in (r.stderr + r.stdout), url
        assert not out.exists(), url


# ---- build.py refuses a font.json whose names.fs_type is missing or not an OS/2 fsType --------------------------------
def fs_type_config(tmp_path, **names):
    """A copy of the neutral font.json (its concepts.js beside it) with names.fs_type replaced; `fs_type=...` sets
    it, passing the sentinel MISSING deletes the key. Everything else is the neutral file, so the config is valid
    in every other respect and only the fs_type check can refuse it."""
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    value = names["fs_type"]
    if value == "MISSING":
        del cfg["names"]["fs_type"]
    else:
        cfg["names"]["fs_type"] = value
    shutil.copyfile(NEUTRAL / "concepts.js", tmp_path / "concepts.js")
    path = tmp_path / "font.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


@pytest.mark.parametrize("value,message", [
    ("MISSING", "names.fs_type is required and has no default"),
    (True, "names.fs_type is required and has no default"),
    ("4", "names.fs_type is required and has no default"),
    (6, "names.fs_type 6 is not a valid OS/2 fsType"),
    (16, "names.fs_type 16 is not a valid OS/2 fsType"),
    (10, "names.fs_type 10 is not a valid OS/2 fsType"),
    (12, "names.fs_type 12 is not a valid OS/2 fsType"),
    (0x200, "sets bit 9 (bitmap-only embedding)"),
    (0x204, "sets bit 9 (bitmap-only embedding)"),
])
def test_build_refuses_a_missing_or_invalid_fs_type_before_writing_anything(tmp_path, value, message):
    """Executed refusals, each with its own message and no file written: no key (it must not be a KeyError or a
    default of 4), a boolean (True is an int in Python), a string, 6 (bits 1 and 2: two exclusive embedding levels)
    and 16 (bit 4 does not exist). The rest of the config is the neutral one, so only this check can refuse it.
    Weakest mutations watched red: the mask 0x010E widened to 0xFFFF (16 passes); the exclusive-level test `<= 1`
    widened to `<= 3` (6 passes); bit 3 dropped from FS_TYPE_LEVELS, 0x000E to 0x0006 (10 and 12, Editable combined
    with another level, pass: this one survived with only 6 in the list, the coordinator's mutation of 2026-11-16);
    the `not isinstance(fs_type, bool)` term removed (True gets the other message); the bit-9 check removed (0x200
    is then refused as "not a valid", the wrong message, and 0x204 likewise)."""
    font = fs_type_config(tmp_path, fs_type=value)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(font), "--no-requirements", "--out-dir", str(out)],
                       capture_output=True, text=True)
    assert r.returncode != 0, r.stderr
    assert message in r.stderr and "Traceback" not in r.stderr, r.stderr[-600:]
    assert not out.exists() or not any(out.iterdir()), "a refused config wrote files"


@pytest.mark.parametrize("value", [0, 2, 4, 8, 0x100, 0x104])
def test_build_accepts_every_valid_fs_type_in_the_config_check(tmp_path, value):
    """The control for the refusals above: the same copied config passes load_config() with each valid value (an
    in-process call, not a build), so a refusal is the value's doing. Weakest mutation watched red: the mask
    narrowed to 0x000E (0x100 and 0x104 then refused)."""
    sys.path.insert(0, str(REPO / "scripts"))
    import build
    cfg = build.load_config(fs_type_config(tmp_path, fs_type=value))
    assert cfg["names"]["fs_type"] == value


def test_the_vertical_metrics_line_claims_only_what_the_tables_make_true(tmp_path):
    """The build's `vertical metrics written` line said `line-height: normal is X em on every platform`. hhea and typo agree
    now, so a platform that reads either gets X; a platform that reads the win metrics is not covered, and the line says so.
    Built for real (the italic group, into a temp folder). Weakest mutation watched red: the wording put back to
    "on every platform"."""
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(NEUTRAL / "font.json"), "--group", "italic",
                        "--requirements", str(NEUTRAL / "requirements.json"), "--out-dir", str(tmp_path / "o")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    line = next(ln for ln in r.stderr.splitlines() if "vertical metrics written" in ln)
    assert "wherever the platform reads hhea or typo" in line and "win metrics is not covered" in line and "on every platform" not in line, line


def test_a_group_file_outside_font_json_dir_is_recorded_relative(tmp_path):
    """A site keeps font.json in tools/face/ and ships the woff2 under static/ (hopsafari.com does). The manifest
    recorded that file as an ABSOLUTE path, so it named one clone's home directory and `--check` failed in any
    other clone. It is now `../../static/F-VF.woff2`. Built for real with out_dir "." (group.file resolves
    against out_dir), then checked from a different working directory, then the whole site copied elsewhere and
    checked again: the manifest must still match. Mutation watched red: the old absolute fallback restored."""
    face = tmp_path / "site" / "tools" / "face"
    face.mkdir(parents=True)
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["out_dir"] = "."
    cfg["groups"]["roman"]["file"] = "../../static/F-VF.woff2"
    cfg["groups"] = {"roman": cfg["groups"]["roman"]}
    shutil.copyfile(NEUTRAL / "concepts.js", face / "concepts.js")
    shutil.copyfile(NEUTRAL / "requirements.json", face / "requirements.json")
    (face / "font.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    build = [sys.executable, str(REPO / "scripts" / "build.py"), "--font", "font.json"]
    r = run(build, cwd=face)
    assert r.returncode == 0, r.stderr[-1500:]
    assert (tmp_path / "site" / "static" / "F-VF.woff2").is_file()
    entry = json.loads((face / "manifest.json").read_text(encoding="utf-8"))["groups"]["roman"]["file"]
    assert entry == "../../static/F-VF.woff2", f"the manifest records {entry!r}"
    r = run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(face / "font.json"), "--check"], cwd=tmp_path)
    assert r.returncode == 0 and "manifest identical" in r.stderr, r.stderr[-1500:]
    moved = tmp_path / "elsewhere" / "site"
    shutil.copytree(tmp_path / "site", moved)
    r = run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(moved / "tools" / "face" / "font.json"), "--check"], cwd=moved)
    assert r.returncode == 0 and "manifest identical" in r.stderr, f"a copied site fails --check:\n{r.stderr[-1500:]}"
