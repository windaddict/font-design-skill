"""The site-wiring template, filled, runs green against the fixture site in the CSS forms a real site writes,
and still catches a character the font lacks.

WHAT IT'S FOR: dry-run finding W12. The first template read one quote style around the family name,
one selector per rule and clamp() sizes only, and refused a stylesheet written any other way; it also
required a replaced face to name. This builds the neutral face into a copy of tests/fixtures/site-sample
(as test_copy_into_site does), wires the Sampler font into the fixture's stylesheet in two styles, fills
scripts/tests/test_site_wiring.py.tmpl for that site and runs the filled suite there with pytest.
Style A: single quotes, one selector per rule, a clamp() size, an old face named. Style B: double
quotes, a selector list (`h3, .plate-title`), a plain rem size inside an @media block, font-synthesis
in a separate shared rule, no old face (the slot left empty). Style C (second dry run, finding 9): the
static_config slot empty and font_synthesis declined, both skipped with their reasons, in a site that is
not a git work tree, which skips the tracked-fonts guard; and the static_config slot pointed at the
stylesheet, which the guard refuses by name instead of passing on the url() it finds there. Then the
display rules are extended to the fixture's h2, whose text carries Å and Ž, which Sampler lacks: the
coverage test must go red naming both. Each guard of the template was watched failing under the weakest
mutation of the template that breaks it (named in the assertions below) when this test was written.
Re-review (code-b F008, F009): guard (s) requires every selector the stylesheet sets in the face to be listed
as display or text-cut, and (a2) requires the italic src to be an italic font; both are run red below.
"""
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, run
from test_copy_into_site import make_site

TMPL = REPO / "scripts" / "tests" / "test_site_wiring.py.tmpl"
PRELOAD = '<link rel="preload" href="/fonts/Sampler-VF.woff2" as="font" type="font/woff2" crossorigin>'
STYLESHEET = '<link rel="stylesheet" href="css/site.css">'

FACES_A = """
@font-face { font-family: 'Sampler'; font-weight: 400 700; font-style: normal; font-display: swap; src: url('/fonts/Sampler-VF.woff2') format('woff2'); }
@font-face { font-family: 'Sampler'; font-weight: 400 700; font-style: italic; font-display: swap; src: url('/fonts/Sampler-Italic-VF.woff2') format('woff2'); }
h1 { font-family: 'Sampler', serif; font-size: clamp(2rem, 4.5vw, 4.5rem); font-optical-sizing: auto; }
.plate-title { font-family: 'Sampler', serif; font-weight: 500; }
h3 { font-family: 'Sampler', serif; font-weight: 500; }
.frontispiece h1 { font-family: 'Sampler', serif; }
"""
FACES_B = """
@font-face { font-family: "Sampler"; font-weight: 400 700; font-display: swap; src: url("/fonts/Sampler-VF.woff2") format("woff2"); }
@font-face { font-family: "Sampler"; font-weight: 400 700; font-style: italic; font-display: swap; src: url("/fonts/Sampler-Italic-VF.woff2") format("woff2"); }
h1 { font-family: "Sampler", serif; font-size: 3rem; }
@media (min-width: 1px) {
  h1 { font-size: 4.5rem; }
}
h3, .plate-title { font-family: "Sampler", serif; font-weight: 500; }
h1, h3, .plate-title { font-synthesis: none; }
"""
H2_DISPLAY = "\nh2 { font-family: 'Sampler', serif; }\n"
FACES_B_TEXT_CUT = "[]"  # style B sets the family on h1, h3 and .plate-title only, all of them display selectors


def fill(values):
    tmpl = TMPL.read_text(encoding="utf-8")
    filled = re.sub(r"{{\s*([a-z_]+)\s*}}", lambda m: values[m.group(1)], tmpl)
    assert "{{" not in filled, "a slot was left unfilled"
    return filled


def wire(tmp_path, faces, old_family, old_files, extra_css="", static_config="serve.conf", font_synthesis="declined", git=True,
         text_cut='[".frontispiece h1"]', fallback_family="", balance_selectors="[]"):
    """A site with the Sampler face built, the fonts served from fonts/, the fixture pages carrying the
    preload, a static config naming woff2, the stylesheet extended with `faces`, and the filled template at
    tests/test_site_wiring.py. The fonts are git-tracked (staged) so guard (e) can run, unless git=False."""
    site, face = make_site(tmp_path)
    fonts = site / "fonts"
    fonts.mkdir()
    for name in ("Sampler-VF.woff2", "Sampler-Italic-VF.woff2"):
        shutil.copyfile(face / "out" / name, fonts / name)
    for name in ("index.html", "essay.html"):
        page = site / name
        text = page.read_text(encoding="utf-8")
        assert STYLESHEET in text
        page.write_text(text.replace(STYLESHEET, PRELOAD + "\n" + STYLESHEET), encoding="utf-8")
    (site / "templates").mkdir()
    (site / "templates" / "page.html").write_text(f"<!doctype html><head>{PRELOAD}\n{STYLESHEET}</head>", encoding="utf-8")
    (site / "serve.conf").write_text("static: *.html *.css *.woff2\n", encoding="utf-8")
    css = site / "css" / "site.css"
    css.write_text(css.read_text(encoding="utf-8") + faces + extra_css, encoding="utf-8")
    for cmd in ((["git", "init", "-q"], ["git", "add", "fonts"]) if git else ()):
        r = run(cmd, cwd=site)
        assert r.returncode == 0, r.stderr
    (site / "tests").mkdir()
    (site / "tests" / "test_site_wiring.py").write_text(fill({
        "family": "Sampler", "static_root": ".", "css_path": "css/site.css", "templates_glob": "templates/*.html",
        "built_pages_glob": "*.html", "font_url": "/fonts/Sampler-VF.woff2", "italic_font_url": "/fonts/Sampler-Italic-VF.woff2",
        "preload_tag": PRELOAD, "stylesheet_tag": STYLESHEET, "static_config": static_config,
        "old_family_pattern": old_family, "old_files_glob": old_files,
        "display_selectors": '["h1", "h3", ".plate-title"]', "text_cut_selectors": text_cut, "medium_selectors": '[".plate-title", "h3"]',
        "opsz_max_px": "72", "font_synthesis": font_synthesis, "fallback_family": fallback_family, "balance_selectors": balance_selectors,
    }), encoding="utf-8")
    return site


def pytest_in(site, *extra):
    """The filled suite run in the site, exactly as a site would run it (no marker to register, no -m)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_site_wiring.py", "-q", "-p", "no:cacheprovider", "-rfs",
                        "-W", "error::pytest.PytestUnknownMarkWarning", *extra], cwd=site, capture_output=True, text=True)
    return r, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]


def test_style_a_single_quotes_one_selector_per_rule_clamp_and_an_old_face(tmp_path):
    """Every guard passes, (c) and (d) run (an old face is named: 'Playfair', which the fixture never
    mentions, and a glob nothing matches). Style A sets no font-synthesis, as Bract did, so the slot says
    declined and guard (r) is the one skip, with its reason. Mutations watched red on this case:
    first_family() not stripping single quotes (no display rule found); the declined skip removed from (r)
    (it then fails on h1)."""
    site = wire(tmp_path, FACES_A, "Playfair|Didot", "fonts/playfair-*.woff2")
    r, summary = pytest_in(site)
    assert r.returncode == 0, f"the filled template failed on style A:\n{r.stdout[-3000:]}\n{r.stderr[-500:]}"
    assert "passed" in summary and "3 skipped" in summary, summary
    assert "font_synthesis is declined" in r.stdout and "fallback_family is empty" in r.stdout and "balance_selectors is empty" in r.stdout, r.stdout[-1500:]


def test_style_b_double_quotes_selector_list_media_rem_size_shared_synthesis_no_old_face(tmp_path):
    """Every guard passes, with (c) and (d) SKIPPED by the empty slots, not failed. Mutations watched red:
    rules_for() matching the whole selector list text instead of each selector (no rule for .plate-title);
    first_family() stripping single quotes only; size_max_px() reading clamp() only; css_blocks() not
    descending into @media (the 4.5rem h1 rule is then swallowed and the opsz check reads 48 px);
    OLD_FAMILY_PATTERN empty compiled as a match-all regex instead of a skip."""
    site = wire(tmp_path, FACES_B, "", "", font_synthesis="adopted", text_cut=FACES_B_TEXT_CUT)
    r, summary = pytest_in(site)
    assert r.returncode == 0, f"the filled template failed on style B:\n{r.stdout[-3000:]}\n{r.stderr[-500:]}"
    assert "passed" in summary and "4 skipped" in summary, summary
    assert "old_family_pattern is empty" in r.stdout and "old_files_glob is empty" in r.stdout, r.stdout[-1500:]


def test_style_c_empty_static_config_declined_synthesis_and_no_git_each_skip_with_a_reason(tmp_path):
    """Second dry run, finding 9: static_config had no empty-slot skip, (e) shelled out to git with no
    fallback, and the font-synthesis guard failed as shipped. Now each skips with its reason printed and
    nothing fails. Mutations watched red: the empty-slot check removed from (f) (REPO / "" is a directory:
    IsADirectoryError, an error, not a skip); the work-tree check removed from (e) (git ls-files fails
    outside a repository); the declined skip removed from (r)."""
    site = wire(tmp_path, FACES_A, "", "", static_config="", font_synthesis="declined", git=False)
    r, summary = pytest_in(site)
    assert r.returncode == 0, f"the filled template failed on style C:\n{r.stdout[-3000:]}\n{r.stderr[-500:]}"
    assert "passed" in summary and "7 skipped" in summary and "error" not in summary, summary
    for reason in ("static_config is empty", "not a git work tree", "font_synthesis is declined", "old_family_pattern is empty", "old_files_glob is empty"):
        assert reason in r.stdout, (reason, r.stdout[-2000:])


def test_the_static_config_guard_refuses_the_stylesheet_instead_of_passing_on_its_url(tmp_path):
    """Second dry run, finding 9: pointed at the stylesheet, (f) passed because the @font-face url() says
    woff2, which proves nothing about the host. The guard must fail naming the stylesheet, and nothing
    else may fail. Mutation watched red: the stylesheet comparison removed (the guard then passes)."""
    site = wire(tmp_path, FACES_A, "", "", static_config="css/site.css")
    r, summary = pytest_in(site)
    assert r.returncode != 0, "the static-config guard passed with the stylesheet as the config"
    failed = [ln for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
    assert len(failed) == 1 and "test_the_static_config_serves_the_font_extension" in failed[0], (failed, summary)
    assert "names the stylesheet site.css" in r.stdout, r.stdout[-1500:]


def test_the_coverage_guard_still_names_the_characters_the_font_lacks(tmp_path):
    """The fixture's h2 titles carry Å ("Ångström") and Ž ("Žal"), which Sampler's cmap lacks. With a rule
    setting h2 in Sampler appended to the stylesheet, guard (g) must fail naming both characters and the
    page, and nothing else may fail: h2 is not in the display_selectors slot (the fixture's own h2 rule
    carries a letter-spacing, which (p) would report), so (g) finds it only by reading the stylesheet,
    which is the point. Mutation watched red: the parser's handle_data() collecting nothing (missing
    becomes {} and the guard passes)."""
    site = wire(tmp_path, FACES_A, "Playfair", "fonts/playfair-*.woff2", extra_css=H2_DISPLAY, text_cut='[".frontispiece h1", "h2"]')
    r, summary = pytest_in(site)
    assert r.returncode != 0, "the coverage guard passed although h2 shows Å and Ž in Sampler"
    failed = [ln for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
    assert len(failed) == 1 and "test_the_font_covers_every_character_the_display_face_sets" in failed[0], (failed, summary)
    assert "'Å': 'essay.html'" in r.stdout and "'Ž': 'essay.html'" in r.stdout, r.stdout[-1500:]


def test_a_selector_set_in_the_face_but_listed_in_neither_cut_fails_the_listing_guard(tmp_path):
    """Re-review code-b F008: an h2 rule set in Sampler, with h2 in neither display_selectors nor
    text_cut_selectors, must fail guard (s) naming h2 (the coverage guard fails too, on the Å and Ž the h2s
    carry; nothing else may). Mutation watched red: `unlisted` built from DISPLAY_SELECTORS instead of
    family_selectors() (the guard then reads the slot it is meant to check and passes)."""
    site = wire(tmp_path, FACES_A, "", "", extra_css=H2_DISPLAY)
    r, summary = pytest_in(site)
    assert r.returncode != 0, "guard (s) passed although h2 is set in Sampler and listed nowhere"
    failed = sorted(ln.split("::")[-1].split(" ")[0] for ln in r.stdout.splitlines() if ln.startswith("FAILED"))
    assert failed == ["test_every_selector_set_in_the_face_is_listed_as_display_or_text_cut",
                      "test_the_font_covers_every_character_the_display_face_sets"], (failed, summary)
    assert "in neither display_selectors nor text_cut_selectors: ['h2']" in r.stdout, r.stdout[-2000:]


def test_the_italic_src_must_be_an_italic_font(tmp_path):
    """Re-review code-b F009: with the italic @font-face's src pointing at the ROMAN woff2 (a file that exists,
    so (a) and (b) pass), guard (a2) must fail naming the file and its upright tables, and nothing else may.
    Mutation watched red: the `== italic` comparisons replaced by `or True` (the guard then checks presence)."""
    faces = FACES_A.replace("src: url('/fonts/Sampler-Italic-VF.woff2')", "src: url('/fonts/Sampler-VF.woff2')")
    assert faces != FACES_A
    site = wire(tmp_path, faces, "", "")
    filled = site / "tests" / "test_site_wiring.py"
    text = filled.read_text(encoding="utf-8").replace('ITALIC_FONT_URL = "/fonts/Sampler-Italic-VF.woff2"', 'ITALIC_FONT_URL = "/fonts/Sampler-VF.woff2"')
    filled.write_text(text, encoding="utf-8")
    r, summary = pytest_in(site)
    assert r.returncode != 0, "guard (a2) passed with the roman file declared as the italic face"
    failed = [ln for ln in r.stdout.splitlines() if ln.startswith("FAILED")]
    assert len(failed) == 1 and "test_each_declared_face_file_carries_the_style_it_is_declared_for" in failed[0], (failed, summary)
    assert "/fonts/Sampler-VF.woff2 is declared as the italic face but its tables say" in r.stdout, r.stdout[-1500:]


# ---- the optional guards (t) and (u): a metric-matched fallback face and text-wrap: balance -------------------------------------------------
def sampler_hhea():
    """(ascent, descent, line gap, units per em) of the built Sampler roman, read here with fontTools."""
    from fontTools.ttLib import TTFont
    f = TTFont(REPO / "examples" / "neutral" / "out" / "Sampler-VF.woff2")
    return f["hhea"].ascent, -f["hhea"].descent, f["hhea"].lineGap, f["head"].unitsPerEm


def fallback_css(size=96.0, scale=(1, 1, 1), name="Sampler Fallback", local="Georgia"):
    """A @font-face for the fallback whose overrides are the font's own metrics divided by size-adjust (the formula
    scripts/fallback-metrics.py implements), each optionally scaled to make it wrong."""
    asc, desc, gap, em = sampler_hhea()
    ov = [100 * v / em / (size / 100) * k for v, k in zip((asc, desc, gap), scale)]
    return (f"@font-face {{ font-family: '{name}'; src: local('{local}'); size-adjust: {size}%; ascent-override: {ov[0]:.4f}%; "
            f"descent-override: {ov[1]:.4f}%; line-gap-override: {ov[2]:.4f}%; }}\n")


FACES_D = FACES_A.replace("font-family: 'Sampler', serif", "font-family: 'Sampler', 'Sampler Fallback', serif") + "h1, h3, .plate-title { text-wrap: balance; }\n"
BALANCED = '["h1", "h3", ".plate-title"]'


def wire_d(tmp_path, faces=FACES_D, fallback=None, **kw):
    return wire(tmp_path, faces, "", "", extra_css=fallback_css() if fallback is None else fallback, fallback_family="Sampler Fallback", balance_selectors=BALANCED, **kw)


def failed_names(r):
    return sorted(ln.split("::")[-1].split(" ")[0] for ln in r.stdout.splitlines() if ln.startswith("FAILED"))


def test_style_d_the_fallback_face_and_text_wrap_balance_pass_when_declared_correctly(tmp_path):
    """Both optional guards run (their slots are filled) and pass: a local() fallback whose three overrides times
    its size-adjust equal the font's hhea metrics, listed right after Sampler in every display stack, and
    text-wrap: balance on the three display selectors. Nothing is skipped by these two."""
    site = wire_d(tmp_path)
    r, summary = pytest_in(site)
    assert r.returncode == 0, f"the filled template failed on style D:\n{r.stdout[-3000:]}\n{r.stderr[-500:]}"
    assert "fallback_family is empty" not in r.stdout and "balance_selectors is empty" not in r.stdout, r.stdout[-1500:]
    ran = subprocess.run([sys.executable, "-m", "pytest", "tests/test_site_wiring.py", "-q", "-p", "no:cacheprovider", "-k", "fallback_face or balance"],
                         cwd=site, capture_output=True, text=True).stdout
    assert "2 passed, 17 deselected" in ran, ran


@pytest.mark.parametrize("scale,what", [((1.05, 1, 1), "ascent-override"), ((1, 0.9, 1), "descent-override"), ((1, 1, 2), "line-gap-override")])
def test_an_override_that_disagrees_with_the_fonts_metrics_fails_the_fallback_guard(tmp_path, scale, what):
    """The font's metrics changed (or the overrides were typed by hand): one override off by a few percent of
    itself. The guard must fail on exactly that property and nothing else may fail. Adversarial input: each case
    changes ONE override only. Mutations watched red: the per-property comparison skipped for line-gap; the
    tolerance widened to 50 points; the `x size-adjust` factor dropped (the overrides then read as shares of the
    unscaled em)."""
    gap = sampler_hhea()[2]
    if what == "line-gap-override" and gap == 0:
        scale = (1, 1, 1)
        extra = fallback_css().replace("line-gap-override: 0.0000%", "line-gap-override: 3.0000%")
    else:
        extra = fallback_css(scale=scale)
    site = wire_d(tmp_path, fallback=extra)
    r, _summary = pytest_in(site)
    assert failed_names(r) == ["test_the_fallback_face_is_metric_matched_to_the_font"], (failed_names(r), r.stdout[-1500:])
    assert f"{what} " in r.stdout and "recompute the values with scripts/fallback-metrics.py" in r.stdout, r.stdout[-1500:]


def test_the_fallback_guard_refuses_a_face_with_a_url_or_a_missing_property_or_a_stack_without_it(tmp_path):
    """Three separate defects, each alone: a url() src (a downloaded fallback is not a local one), no
    size-adjust, and a display stack that does not list the fallback right after the family. Each must fail
    this one guard (the last puts the fallback AFTER serif, where it never applies). Mutations watched red: the `local(` / url() assertion removed;
    the properties loop shortened
    to three; the stack comparison made `in` instead of the first two entries (caught by the `stack order` case only)."""
    cases = {
        "url": (FACES_D, fallback_css().replace("local('Georgia')", "url('/fonts/Sampler-VF.woff2')"), "must be a local() face"),
        "no size-adjust": (FACES_D, fallback_css().replace("size-adjust: 96.0%; ", ""), "lacks size-adjust"),
        "stack": (FACES_A + "h1, h3, .plate-title { text-wrap: balance; }\n", fallback_css(), "the stack must start Sampler, Sampler Fallback"),
        "stack order": (FACES_D.replace("'Sampler', 'Sampler Fallback', serif", "'Sampler', serif, 'Sampler Fallback'"), fallback_css(),
                        "the stack must start Sampler, Sampler Fallback"),
    }
    for name, (faces, extra, text) in cases.items():
        site = wire_d(tmp_path / name.replace(" ", "-"), faces=faces, fallback=extra)
        r, _summary = pytest_in(site)
        assert failed_names(r) == ["test_the_fallback_face_is_metric_matched_to_the_font"], (name, failed_names(r), r.stdout[-1200:])
        assert text in r.stdout, (name, r.stdout[-1200:])


def test_text_wrap_balance_must_be_on_every_listed_selector_in_every_rule(tmp_path):
    """One listed selector without it fails, and so does one that sets text-wrap: wrap in a media rule after
    setting balance (every declared value must be balance, as for font-weight in guard (o)). Mutations watched
    red: the guard reading only the first value; the `all(...)` replaced by `any(...)`."""
    without = FACES_D.replace("h1, h3, .plate-title { text-wrap: balance; }", "h1, h3 { text-wrap: balance; }")
    r, _s = pytest_in(wire_d(tmp_path / "a", faces=without))
    assert failed_names(r) == ["test_display_headings_balance_their_lines"] and ".plate-title must set text-wrap: balance" in r.stdout, r.stdout[-1200:]
    flipped = FACES_D + "@media (max-width: 400px) { h1 { text-wrap: wrap; } }\n"
    r, _s = pytest_in(wire_d(tmp_path / "b", faces=flipped))
    assert failed_names(r) == ["test_display_headings_balance_their_lines"] and "h1 must set text-wrap: balance" in r.stdout and "'wrap'" in r.stdout, r.stdout[-1200:]


@pytest.mark.parametrize("ref,bare_path", [("/fonts/missing.woff2?v=1#x", "/fonts/missing.woff2"), ("/fonts/gone.woff2#v", "/fonts/gone.woff2"),
                                           ("/fonts/late.woff2?v=2", "/fonts/late.woff2")])
def test_a_font_url_with_a_cache_busting_query_or_fragment_is_still_checked(tmp_path, ref, bare_path):
    """`url('/fonts/x.woff2?v=3')` named no font to the extension test (`\\.woff2$` does not match it) and was never checked
    for a file. Query and fragment are stripped before matching and before looking for the file. The real roman face
    written with `?v=3` still passes guards (a) and (b); an extra face whose file does not exist, written with a query
    and fragment, a fragment only, or a query only, fails guard (b) alone and the message names the bare path. Weakest
    mutations watched red: `bare()` the identity function; `bare()` splitting on `?` only (the fragment-only row);
    on `#` only (the query-only row)."""
    faces = FACES_A.replace("url('/fonts/Sampler-VF.woff2')", "url('/fonts/Sampler-VF.woff2?v=3')")
    assert faces != FACES_A
    extra = f"@font-face {{ font-family: 'Ghost'; src: url('{ref}') format('woff2'); }}\n"
    site = wire(tmp_path, faces, "", "", extra_css=extra)
    r, _summary = pytest_in(site)
    assert failed_names(r) == ["test_every_font_url_in_the_stylesheet_has_a_file"], (failed_names(r), r.stdout[-1500:])
    assert f"{bare_path} is referenced by site.css and does not exist" in r.stdout, r.stdout[-1500:]


def test_the_balance_guard_does_not_compute_the_cascade_and_says_so(tmp_path):
    """Pins the stated limit: `.hero { text-wrap: wrap }` overriding `h1` on `<h1 class="hero">` passes guard (u), because only
    declarations on the listed selectors are read. If this ever fails, the guard learned the cascade and the docs
    (variable-font-build.md section 15, testing.md, the template's slot text) must change with it."""
    site = wire_d(tmp_path, faces=FACES_D + ".hero { text-wrap: wrap; }\n")
    r, _summary = pytest_in(site)
    assert r.returncode == 0, r.stdout[-1500:]
    text = TMPL.read_text(encoding="utf-8")
    assert text.count("the cascade is not computed") >= 2 and "<h1 class=\"hero\">" in text
