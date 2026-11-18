"""shoot.py's server and sentinel, and specimen.py's probe marker and charset check, exercised for real.

WHAT IT'S FOR: shoot.py is the instrument every screenshot in the review loop is read through, so a
hole in it makes every PNG look like evidence. An independent review of this repository found five
(C1 a request path that escapes the served tree; C4 a font 200 from another concurrent shot counting
for this one; C5 a loaded face that no visible element uses; C11 a 360 px check that passed on
"overflow" or "error"; W2 a page self-test shoot.py never read; W16 a character the face lacks drawn
by the fallback with the shot still passing). Each test here runs the real server (serve()) and,
where the property needs a browser, the real Chrome through shoot.py itself, on pages and fonts built
in tmp (the fonts with fontTools' FontBuilder, so nothing licensed is needed). Tests whose names
contain "chrome" skip LOUDLY when no Chrome is found; the CI chrome job runs them by that name.
Every guard was watched failing under the weakest mutation that breaks its property (the mutation is
named in each docstring) before it was kept.
"""
import http.client
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import shoot  # noqa: E402

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


# Chrome's command line on Windows lays a page out narrower than its --window-size (492 px for a 500 px shot on the
# runner), which shoot.py's width check rightly fails; there the rows tests drive the same Chrome through Playwright,
# which the platform workflow installs on every leg. Elsewhere they keep testing the command line.
ROWS_LAUNCHER = "playwright" if os.name == "nt" else "cli"


def chrome_or_skip():
    try:
        return shoot.find_chrome()
    except FileNotFoundError as exc:
        pytest.skip(f"SKIPPED, NOT PASSED: {exc}. The CI chrome job runs this test; set $CHROME to run it here.")


# ---------------------------------------------------------------- find_chrome(): the order it looks in
def fake_exe(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return str(path)


@pytest.fixture
def no_chrome(monkeypatch, tmp_path):
    """An environment with no Chrome anywhere: $CHROME unset, the three Windows variables unset, the macOS
    app path moved to a file that does not exist, PATH an empty directory. Each test then puts back exactly the
    places it wants found, so the order find_chrome() looks in is what decides the result."""
    monkeypatch.delenv("CHROME", raising=False)
    for var in shoot.CHROME_WINDOWS_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(shoot, "CHROME_MAC_APP", str(tmp_path / "mac" / "Chrome"))
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    return tmp_path


def windows_chrome(root, var, monkeypatch):
    """A fake chrome.exe under <root>/<var>/Google/Chrome/Application, with the variable pointing at it."""
    monkeypatch.setenv(var, str(root / var))
    return fake_exe(root / var / "Google" / "Chrome" / "Application" / "chrome.exe")


def test_find_chrome_prefers_the_chrome_variable_over_every_install_path(no_chrome, monkeypatch):
    """Documented order, first place: $CHROME, even when the macOS app, a Windows install and a PATH name all exist."""
    fake_exe(pathlib.Path(shoot.CHROME_MAC_APP))
    windows_chrome(no_chrome, "ProgramFiles", monkeypatch)
    fake_exe(no_chrome / "emptybin" / "google-chrome")
    chosen = fake_exe(no_chrome / "mine" / "chrome")
    monkeypatch.setenv("CHROME", chosen)
    assert shoot.find_chrome() == chosen


def test_find_chrome_names_the_variable_when_it_points_at_nothing(no_chrome, monkeypatch):
    """A $CHROME that names no file is an error naming $CHROME, never a silent fall through to another browser."""
    fake_exe(pathlib.Path(shoot.CHROME_MAC_APP))
    monkeypatch.setenv("CHROME", str(no_chrome / "nowhere"))
    with pytest.raises(FileNotFoundError, match=r"\$CHROME is set to"):
        shoot.find_chrome()


def test_find_chrome_order_is_mac_then_each_windows_location_then_path(no_chrome, monkeypatch):
    """With no $CHROME the order is: the macOS app, Program Files, Program Files (x86), LocalAppData, then PATH
    names. Each candidate is removed in turn and the next must be returned; the last removal must raise. Executes
    find_chrome() on real files and a real PATH (the Windows locations are made under tmp, from the environment
    variables find_chrome reads, so this runs on any OS)."""
    mac = fake_exe(pathlib.Path(shoot.CHROME_MAC_APP))
    pf = windows_chrome(no_chrome, "ProgramFiles", monkeypatch)
    pf86 = windows_chrome(no_chrome, "ProgramFiles(x86)", monkeypatch)
    local = windows_chrome(no_chrome, "LocalAppData", monkeypatch)
    on_path = fake_exe(no_chrome / "emptybin" / "google-chrome")
    for expected in (mac, pf, pf86, local, on_path):
        assert shoot.find_chrome() == expected
        pathlib.Path(expected).unlink()
    with pytest.raises(FileNotFoundError) as exc:
        shoot.find_chrome()
    msg = str(exc.value)
    assert "$CHROME" in msg and pf in msg and pf86 in msg and local in msg and "google-chrome" in msg, msg


def test_find_chrome_refuses_a_chrome_variable_that_is_a_file_but_not_executable(no_chrome, monkeypatch):
    """A file that exists but cannot be executed passed `is_file()` and failed later at launch. With $CHROME it is an error
    that says so, not a fall through. Weakest mutation watched red: `runnable()` reduced to the `is_file()` test."""
    plain = no_chrome / "chrome"
    plain.write_text("not a program\n")
    plain.chmod(0o644)
    monkeypatch.setenv("CHROME", str(plain))
    with pytest.raises(FileNotFoundError, match="not executable"):
        shoot.find_chrome()


def test_find_chrome_skips_a_candidate_that_is_not_executable(no_chrome, monkeypatch):
    """The macOS app path names a file without the execute bit: discovery moves on to the next candidate (a Windows
    location here) instead of returning it. Weakest mutation watched red: the candidate loop using `is_file()` again."""
    mac = pathlib.Path(shoot.CHROME_MAC_APP)
    mac.parent.mkdir(parents=True)
    mac.write_text("x")
    mac.chmod(0o644)
    pf = windows_chrome(no_chrome, "ProgramFiles", monkeypatch)
    assert shoot.find_chrome() == pf


def test_shoot_reports_a_chrome_that_cannot_be_started_as_a_runtime_error(tmp_path):
    """Passing a non-executable file as the browser made subprocess raise PermissionError out of shoot() as a bare
    traceback. It is a RuntimeError naming the binary and $CHROME now. Weakest mutation watched red: the
    `except OSError` removed from the launch."""
    plain = tmp_path / "chrome"
    plain.write_text("x")
    plain.chmod(0o644)
    with pytest.raises(RuntimeError, match="Chrome could not be started.*set \\$CHROME"):
        shoot.shoot("http://127.0.0.1:1/x.html", tmp_path / "x.png", 500, 1, chrome=str(plain))


def test_find_chrome_ignores_a_windows_variable_that_is_unset(no_chrome, monkeypatch):
    """The Windows candidates come from the environment; on another OS nothing sets them and they must name nothing
    (a candidate built from an empty or missing variable would be a relative path under the working directory)."""
    assert shoot.chrome_candidates() == [shoot.CHROME_MAC_APP]
    monkeypatch.setenv("LocalAppData", str(no_chrome / "L"))
    assert shoot.chrome_candidates() == [shoot.CHROME_MAC_APP, str(no_chrome / "L" / "Google" / "Chrome" / "Application" / "chrome.exe")]


def make_font(path, italic, chars=LETTERS, family="Probe"):
    """A real woff2: box glyphs on 1000-unit advances for `chars` (so any text measures far wider than the
    fallback serif), the italic one flagged in OS/2 fsSelection, post.italicAngle and head.macStyle."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    glyphs = {".notdef": 500, "space": 400}
    cmap = {0x20: "space"}
    for ch in chars:
        name = f"u{ord(ch):04X}"
        glyphs[name] = 1000
        cmap[ord(ch)] = name
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(list(glyphs))
    fb.setupCharacterMap(cmap)
    outlines = {}
    for name, adv in glyphs.items():
        pen = TTGlyphPen(None)
        if name != "space":
            pen.moveTo((50, 0))
            pen.lineTo((50, 700))
            pen.lineTo((adv - 100, 700))
            pen.lineTo((adv - 100, 0))
            pen.closePath()
        outlines[name] = pen.glyph()
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({n: (a, 50) for n, a in glyphs.items()})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    style = "Italic" if italic else "Regular"
    fb.setupNameTable({"familyName": family, "styleName": style, "fullName": f"{family} {style}", "psName": f"{family}-{style}"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200, fsSelection=(0x01 if italic else 0x40))
    fb.setupPost(italicAngle=-10 if italic else 0)
    fb.font["head"].macStyle = 2 if italic else 0
    fb.font.flavor = "woff2"
    fb.save(str(path))
    return path


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """A served directory with fonts/Probe.woff2 and fonts/Probe-Italic.woff2."""
    d = tmp_path_factory.mktemp("site")
    (d / "fonts").mkdir()
    make_font(d / "fonts" / "Probe.woff2", italic=False)
    make_font(d / "fonts" / "Probe-Italic.woff2", italic=True)
    return d


def page(site, name, body, faces=("normal",), extra_css="", html_attrs=""):
    """Writes <name>.html into `site`: @font-face rules for the named styles, h1 in Probe, p in Georgia."""
    css = ""
    if "normal" in faces:
        css += '@font-face { font-family: Probe; src: url(/fonts/Probe.woff2) format("woff2"); font-style: normal; }\n'
    if "italic" in faces:
        css += '@font-face { font-family: Probe; src: url(/fonts/Probe-Italic.woff2) format("woff2"); font-style: italic; }\n'
    # font-weight 400: the user agent's h1 default is bold, and the Probe faces declare no weight (so 400 only), which
    # the weight check (re-review code-b F004) would report as no-weight-face on every h1
    css += ("h1 { font-family: Probe, serif; font-size: 48px; font-weight: 400; font-synthesis: none; } "
            ".i { font-style: italic } p { font-family: Georgia, serif }\n" + extra_css)
    (site / f"{name}.html").write_text(f"<!doctype html><html{html_attrs}><head><meta charset='utf-8'><style>{css}</style></head>"
                                       f"<body>{body}</body></html>", encoding="utf-8")
    return f"/{name}.html"


def get(port, path):
    """A raw GET (http.client does not normalise the path, so /../x and %2e%2e reach the server as written)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r.status, body


def served(tmp_path, **kw):
    server, port = shoot.serve(tmp_path, seconds=60, **kw)
    return server, port


def one_shot(server, port, path, out, **kw):
    """One real Chrome shot at 500@1x through shoot.shoot(), verified against `server`."""
    return shoot.shoot(f"http://127.0.0.1:{port}{path}", out, 500, 1, server=server, chrome=chrome_or_skip(), **kw)


# ---------------------------------------------------------------- C1: the served tree cannot be escaped

ESCAPES = ["/__fd//etc/passwd", "/__fd/%2e%2e/%2e%2e/LICENSE", "/__fd/..%2fLICENSE", "/__fd/../LICENSE", "/__fd/../../LICENSE",
           "/__fd/", "/__fd/concepts/", "/__fd/%00narrow.html"]


def test_tool_prefix_refuses_every_path_that_escapes_the_scripts_folder(tmp_path):
    """C1. Mutation watched red: `contained()` returning the resolved path without the is_relative_to test
    (then /__fd//etc/passwd and the %2e%2e variants are served)."""
    server, port = served(tmp_path)
    try:
        bad = {}
        for p in ESCAPES:
            status, body = get(port, p)
            if status != 404:
                bad[p] = (status, body[:60])
        assert not bad, f"these requests were not refused with 404: {bad}"
        status, body = get(port, "/__fd/narrow.html")
        assert status == 200 and b"Narrow-width reading" in body, "the legitimate tool page must still be served"
        assert any("refused" in d for d in server.departures), "a refused path must be noted, not swallowed"
    finally:
        server.shutdown()


def test_served_directory_refuses_escapes_and_a_symlink_that_points_out_of_it(tmp_path):
    """C1, the main tree. A symlink inside DIR to a file outside it is refused (resolve() follows it), and
    the encoded `..` forms never reach a file outside DIR. Mutation watched red: translate_path returning
    `local` without the containment test (the symlink is then served 200 with the secret)."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("SECRET-OUTSIDE", encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<!doctype html><title>ok</title>", encoding="utf-8")
    (site / "leak").symlink_to(outside / "secret.txt")
    (site / "leakdir").symlink_to(outside)
    server, port = served(site)
    try:
        for p in ["/leak", "/leakdir/secret.txt", "/../outside/secret.txt", "/%2e%2e/outside/secret.txt", "/..%2foutside%2fsecret.txt", "/%00"]:
            status, body = get(port, p)
            assert status == 404 and b"SECRET-OUTSIDE" not in body, (p, status, body[:60])
        status, body = get(port, "/index.html")
        assert status == 200 and b"<title>ok</title>" in body
        status, body = get(port, "/")
        assert status == 200, "the served root itself (index.html) must still answer"
    finally:
        server.shutdown()


def test_contained_resolves_symlinks_and_refuses_the_root_itself(tmp_path):
    """The resolver shoot.py's handler uses for /__fd/, tested directly because HERE is fixed to the scripts
    folder: a symlink inside the root that points outside it is refused; the root itself is refused."""
    root = tmp_path / "root"
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "f.txt").write_text("x", encoding="utf-8")
    (tmp_path / "elsewhere.txt").write_text("y", encoding="utf-8")
    (root / "link.txt").symlink_to(tmp_path / "elsewhere.txt")
    assert shoot.contained(root, "sub/f.txt") == (root / "sub" / "f.txt").resolve()
    assert shoot.contained(root, "link.txt") is None
    assert shoot.contained(root, "/etc/passwd") is None
    assert shoot.contained(root, "../elsewhere.txt") is None
    assert shoot.contained(root, "") is None
    assert shoot.contained(root, "sub/\x00f.txt") is None


# ---------------------------------------------------------------- C4: a font 200 belongs to exactly one shot

def test_chrome_font_200_is_attributed_to_the_shot_that_requested_it_c4(site, tmp_path):
    """Two concurrent shots (--jobs 2): page a loads /fonts/Probe.woff2, page b names a font file that
    404s and never requests Probe.woff2. With --font-url /fonts/Probe.woff2 and no --family, b must FAIL
    (nothing served that path to b's Chrome) and a must pass, every time. Mutation watched red: the
    font check matching responses by path alone (`mine` built without the cookie comparison), which is
    the pre-review code: a's 200 then covers b."""
    chrome = chrome_or_skip()
    page(site, "a", "<h1>Harbour Review</h1>")
    page(site, "b", "<h1>Harbour Review</h1>", faces=(), extra_css='@font-face { font-family: Probe; src: url(/fonts/other.woff2) format("woff2"); }')
    out = tmp_path / "shots"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(out), "--serve", str(site), "--pages", "a.html", "b.html",
                        "--widths", "500", "--scales", "1", "--jobs", "2", "--bands", "none", "--font-url", "/fonts/Probe.woff2"],
                       capture_output=True, text=True, timeout=240, env={**os.environ, "CHROME": chrome})
    assert r.returncode == 1, r.stderr
    failed = [ln for ln in r.stderr.splitlines() if ln.startswith("FAILED:")]
    assert len(failed) == 1 and "/fonts/Probe.woff2 was not served 200 to the shot of /b.html" in failed[0], r.stderr
    assert "no request carried its token" in failed[0], failed[0]
    results = [json.loads(ln) for ln in r.stderr.splitlines() if ln.startswith("{")]
    assert [pathlib.Path(x["png"]).name for x in results] == ["a-500@1x.png"] and results[0]["font_status"] == [200], r.stderr
    assert (out / "a-500@1x.png").is_file()


def test_chrome_html_response_sets_the_shot_cookie_and_later_requests_are_recorded_with_it(site, tmp_path):
    """The mechanism under C4, observed on the server: after a shot, every font response recorded for that
    Chrome carries the shot's token as its cookie; the page response itself (before the cookie exists)
    carries none."""
    page(site, "c", "<h1>Harbour Review</h1>")
    server, port = served(site)
    try:
        res = one_shot(server, port, "/c.html", tmp_path / "c.png", shot_id="shotc1234")
        fonts = [(s, p, code) for s, p, q, code in server.responses if p == "/fonts/Probe.woff2"]
        assert fonts and all(s == "shotc1234" and code == 200 for s, p, code in fonts), server.responses
        pages = [(s, code) for s, p, q, code in server.responses if p == "/c.html"]
        assert pages == [("", 200)], pages
        assert res["font_status"] is None  # no --font-url asked for the check
    finally:
        server.shutdown()


# ---------------------------------------------------------------- re-review code-b F001, F002: the beacon's cookie, the script terminator

def test_a_beacon_without_the_shots_cookie_is_ignored_and_noted(tmp_path):
    """Re-review code-b F001: the beacon endpoint recorded whatever ?shot= it was sent, so a GET from any
    process could plant a verdict for a shot. It now requires the request to carry that shot's fd_shot cookie
    (or one sharing its base token, which narrow.html's inner page gives), ignores the rest and notes it as a
    departure. The remaining trust assumption (the page's own script can send a cookied beacon) is stated in
    the header. Mutation watched red: the cookie comparison removed (the forged beacon is recorded)."""
    server, port = served(tmp_path)
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/__fd/beacon?shot=forged123&font=loaded&probe=3&bad=0")
        assert conn.getresponse().status == 204
        conn.close()
        assert "forged123" not in server.beacons, "a beacon without the shot's cookie was recorded"
        assert any("beacon for shot 'forged123' ignored" in d for d in server.departures), server.departures
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/__fd/beacon?shot=other999&font=loaded", headers={"Cookie": "fd_shot=forged123"})
        assert conn.getresponse().status == 204
        conn.close()
        assert "other999" not in server.beacons, "a beacon carrying another shot's cookie was recorded"
        # Another shot's inner-page cookie must not pass either: a check that accepted any `.inner` cookie
        # survived the cases above (host mutation, 2026-11-16).
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/__fd/beacon?shot=other999&font=loaded", headers={"Cookie": "fd_shot=forged123.inner"})
        assert conn.getresponse().status == 204
        conn.close()
        assert "other999" not in server.beacons, "a beacon carrying another shot's inner-page cookie was recorded"
        for cookie, shot in (("real456", "real456"), ("real456.inner", "real456"), ("real456", "real456.inner")):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", f"/__fd/beacon?shot={shot}&font=loaded", headers={"Cookie": f"fd_shot={cookie}"})
            conn.getresponse()
            conn.close()
            assert server.beacons.get(shot, {}).get("font") == "loaded", (cookie, shot, server.beacons)
    finally:
        server.shutdown()


def test_the_sentinel_cannot_be_ended_by_a_family_or_probe_value():
    """Re-review code-b F002: the three values were embedded with json.dumps, which leaves "</script>" as it
    is, so a --family or --probe value holding it ended the script element and the rest of the value ran as
    markup. js_literal writes "</" with a backslash before the slash. Mutation watched red: the replace removed
    (two closing tags)."""
    hostile = 'x</script><script>document.documentElement.setAttribute("data-fd-pwned","1")</script>'
    script = shoot.sentinel_for("shot1", hostile, hostile)
    assert script.count("</script>") == 1, "a value ended the sentinel's script element"
    assert shoot.js_literal(hostile) == json.dumps(hostile).replace("</", "<\\/")
    assert shoot.js_literal(None) == "null" and shoot.js_literal("plain") == '"plain"'


# ---------------------------------------------------------------- C5 + W16(b): visible elements, italic faces, missing characters

def test_chrome_probe_fails_an_italic_element_served_without_an_italic_face_c5(site, tmp_path):
    """A page whose only @font-face is upright, with an italic h1 in the family: font-synthesis none means
    Chrome draws it upright, the hidden family probe passes, and only the element probe can see it.
    Mutation watched red: faces() ignoring the style (`(/italic|oblique/.test(f.style) === italic)`
    dropped), so the upright face satisfies the italic element."""
    path = page(site, "noital", "<h1>Harbour Review</h1><h1 class='i'>Italic row</h1>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"1 of 2 probed element\(s\).*h1\.i:no-italic-face"):
            one_shot(server, port, path, tmp_path / "noital.png", require_family="Probe", dump_dom=True)
        dom = (tmp_path / "noital.dom.html").read_text(encoding="utf-8")
        attrs = shoot.html_attrs(dom)
        assert attrs["data-fd-probe-italic"] == "missing" and attrs["data-fd-probe-count"] == "2" and attrs["data-fd-probe-bad"] == "1", attrs
        assert 'class="i" data-fd-probe-result="no-italic-face"' in dom
    finally:
        server.shutdown()


def test_chrome_probe_passes_when_the_italic_face_is_loaded_and_marks_every_element(site, tmp_path):
    """The positive case for C5: both faces declared, an upright h1 and an italic one marked
    data-fd-probe="italic" (the specimen's marker). The shot passes, both elements carry result "face",
    and <html> says probe-italic=loaded."""
    path = page(site, "both", "<h1>Harbour Review</h1><h1 class='i' data-fd-probe='italic'>Italic row</h1><p>body in Georgia</p>", faces=("normal", "italic"))
    server, port = served(site, family="Probe")
    try:
        res = one_shot(server, port, path, tmp_path / "both.png", require_family="Probe", dump_dom=True)
        assert res["probe"] == {"probe": "2", "bad": "0", "italic": "loaded", "pfail": "", "missing": ""}, res
        dom = (tmp_path / "both.dom.html").read_text(encoding="utf-8")
        assert dom.count('data-fd-probe-result="face"') == 2 and shoot.html_attrs(dom)["data-fd-probe-italic"] == "loaded"
    finally:
        server.shutdown()


def test_chrome_probe_fails_a_marked_italic_element_whose_style_is_not_italic(site, tmp_path):
    """An element marked data-fd-probe="italic" whose computed font-style is normal (the specimen's .fi rule
    dropped) fails as not-italic even though both faces loaded."""
    path = page(site, "unmarked", "<h1 data-fd-probe='italic'>Should be italic</h1>", faces=("normal", "italic"))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"h1:not-italic"):
            one_shot(server, port, path, tmp_path / "unmarked.png", require_family="Probe")
    finally:
        server.shutdown()


def test_chrome_probe_fails_when_the_face_loads_but_nothing_visible_uses_it(site, tmp_path):
    """C5's core: the face is declared and loads (the hidden probe says loaded) but every visible element is
    in Georgia. Mutation watched red: the `count < 1` check removed."""
    path = page(site, "unused", "<p>Everything here is Georgia</p>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"no visible element with text is set in 'Probe'"):
            one_shot(server, port, path, tmp_path / "unused.png", require_family="Probe")
    finally:
        server.shutdown()


@pytest.mark.parametrize("hide, name", [
    ("opacity:0", "opacity"),
    ("position:absolute;left:-9999px;top:0", "offleft"),
    ("position:absolute;top:-9999px;left:0", "offtop"),
])
def test_chrome_probe_does_not_count_an_element_nobody_can_see(site, tmp_path, hide, name):
    """Re-review code-b F003: visible() checked the box size, visibility and display only, so an h1 at
    opacity 0 or positioned off the document counted as the visible element set in the family and the shot
    passed with nothing of the face on screen. The limit, stated in shoot.py's header: an element inside the
    document but beyond the captured viewport (left:5000px widens the document) still counts, as does text
    cropped by an overflow:hidden ancestor. Mutation watched red: the checkVisibility call removed (the opacity
    case and the ancestor case below pass; it is the one opacity test, so there is no second guard to hide
    behind); the document-bounds test removed (the two off-document cases pass)."""
    path = page(site, "hidden" + name, f"<h1 style='{hide}'>Harbour Review</h1><p>Georgia body</p>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"no visible element with text is set in 'Probe'"):
            one_shot(server, port, path, tmp_path / f"hidden{name}.png", require_family="Probe")
    finally:
        server.shutdown()


def test_chrome_probe_counts_an_element_hidden_by_an_ancestors_opacity_as_hidden(site, tmp_path):
    """The ancestor case of F003: the h1's own opacity is 1, its parent's is 0; checkVisibility sees it."""
    path = page(site, "ancestor", "<div style='opacity:0'><h1>Harbour Review</h1></div><p>Georgia body</p>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"no visible element with text is set in 'Probe'"):
            one_shot(server, port, path, tmp_path / "ancestor.png", require_family="Probe")
    finally:
        server.shutdown()


def test_chrome_probe_fails_an_element_whose_weight_no_face_covers(site, tmp_path):
    """Re-review code-b F004: the only @font-face is weight 400 (the default) and the h1 asks for 700;
    document.fonts.check() answers true (no face matches the request, which the API counts as "all loaded")
    and a loaded upright face exists, so the first probe passed while Chrome drew a synthesised bold. The
    face's declared weight range must cover the element's computed weight: verdict no-weight-face.
    Mutation watched red: faces() ignoring the weight argument (the shot passes)."""
    path = page(site, "wght", "<h1 style='font-weight:700'>Harbour Review</h1>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"1 of 1 probed element\(s\).*h1:no-weight-face"):
            one_shot(server, port, path, tmp_path / "wght.png", require_family="Probe", dump_dom=True)
        assert 'data-fd-probe-result="no-weight-face"' in (tmp_path / "wght.dom.html").read_text(encoding="utf-8")
        ranged = page(site, "wghtok", "<h1 style='font-weight:700'>Harbour Review</h1>", faces=(),
                      extra_css='@font-face { font-family: Probe; src: url(/fonts/Probe.woff2) format("woff2"); font-weight: 400 700; }')
        res = one_shot(server, port, ranged, tmp_path / "wghtok.png", require_family="Probe")
        assert res["probe"]["bad"] == "0" and res["probe"]["probe"] == "1", res
    finally:
        server.shutdown()


def test_chrome_probe_selector_fails_an_element_set_in_another_family(site, tmp_path):
    """--probe SELECTOR names the elements that must be in the face; one that computes to Georgia is "fallback"."""
    path = page(site, "sel", "<h1>In Probe</h1><p class='must'>In Georgia</p>", faces=("normal",))
    server, port = served(site, family="Probe", probe="h1, .must")
    try:
        with pytest.raises(RuntimeError, match=r"1 of 2 probed element\(s\).*p\.must:fallback"):
            one_shot(server, port, path, tmp_path / "sel.png", require_family="Probe")
    finally:
        server.shutdown()


def test_chrome_probe_reports_characters_the_face_lacks_w16(site, tmp_path):
    """W16(b): the Probe font has only ASCII letters and digits, so Å and Ž in an h1 are drawn by the fallback
    while the family itself is loaded. Mutation watched red: missingChars() comparing `wf !== wb` (i.e.
    reporting characters whose advance DIFFERS), which inverts the property."""
    path = page(site, "chars", "<h1>Harbour Å and Ž</h1>", faces=("normal",))
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match=r"h1:missing-chars.*characters the face lacks, drawn in the fallback: 'ÅŽ'"):
            one_shot(server, port, path, tmp_path / "chars.png", require_family="Probe", dump_dom=True)
        dom = (tmp_path / "chars.dom.html").read_text(encoding="utf-8")
        assert shoot.html_attrs(dom)["data-fd-missing-chars"] == "ÅŽ" and 'data-fd-missing-chars="ÅŽ" data-fd-probe-result="missing-chars"' in dom
    finally:
        server.shutdown()


# ---------------------------------------------------------------- W2: the page's own self-test is enforced

@pytest.mark.parametrize("attrs, expect", [
    (' data-fd-round="round1"', "no data-fd-rendered"),
    (' data-fd-round="round1" data-fd-rendered="0"', "rendered 0 glyphs"),
    (' data-fd-rendered="12" data-fd-error="TypeError: boom"', "script error"),
    (' data-fd-rendered="12" data-fd-font="missing"', "comparison font missing"),
])
@pytest.mark.parametrize("dump_dom", [False, True], ids=["beacon", "dom"])
def test_chrome_page_self_test_attributes_fail_the_shot_w2(site, tmp_path, attrs, expect, dump_dom):
    """A page that sets the concept pages' self-test attributes on <html> fails the shot, read from the
    beacon or (with --dump-dom) from the dumped DOM. No --family: these are page claims, not font ones.
    Mutation watched red: self_test_failures() returning [] (each case then passes)."""
    name = "selftest" + re.sub(r"[^a-z0-9]", "", attrs + ("dom" if dump_dom else ""))
    path = page(site, name, "<p>plain page</p>", faces=(), html_attrs=attrs)
    server, port = served(site)
    try:
        with pytest.raises(RuntimeError, match=expect) as exc:
            one_shot(server, port, path, tmp_path / f"{name}.png", dump_dom=dump_dom)
        assert ("from the dumped DOM" if dump_dom else "from the beacon") in str(exc.value)
    finally:
        server.shutdown()


def test_chrome_a_clean_page_with_a_passing_self_test_is_not_failed(site, tmp_path):
    path = page(site, "selfok", "<p>plain page</p>", faces=(), html_attrs=' data-fd-round="round1" data-fd-rendered="12" data-fd-font="loaded"')
    server, port = served(site)
    try:
        res = one_shot(server, port, path, tmp_path / "selfok.png", dump_dom=True)
        attrs = shoot.html_attrs((tmp_path / "selfok.dom.html").read_text(encoding="utf-8"))
        assert attrs["data-fd-font"] == "loaded" and attrs["data-fd-page-font"] == "loaded", "without --family the page's own verdict stays"
        assert res["font"] == "none"
    finally:
        server.shutdown()


# ---------------------------------------------------------------- C11: the narrow reading counts only after the fonts settled

def test_narrow_verdict_reads_the_two_attributes_from_the_html_tag_only():
    """Mutation watched red: narrow_verdict() reading data-fd-narrow-stage from anywhere in the document
    (the body copy below carries a decoy)."""
    dom = ('<!DOCTYPE html><html lang="en" data-fd-overflow="true" data-fd-narrow-stage="load"><head></head>'
           '<body><p data-fd-overflow="false" data-fd-narrow-stage="fonts">decoy</p></body></html>')
    assert shoot.narrow_verdict(dom) == ("true", "load")
    assert shoot.narrow_verdict("<html><body></body></html>") == (None, None)
    assert shoot.narrow_verdict("no html tag at all") == (None, None)
    assert shoot.html_attrs('<html data-x="a &amp; b">')["data-x"] == "a & b"


def test_chrome_narrow_verdict_is_the_settled_fonts_reading_c11(site, tmp_path):
    """Two pages with a web-font title: one holds a 600 px wide block, one fits. Shot through narrow.html at
    360 (as smoke.sh step 10 does) the verdicts are ("true", "fonts") and ("false", "fonts"): the stage is
    the reading taken after the inner document's fonts settled, never the earlier "load" one.
    Mutation watched red: narrow.html's tick() never reaching measure("fonts") (`if (settled())` made
    false), which leaves the stage at "load"."""
    chrome = chrome_or_skip()
    page(site, "wide", "<h1>Harbour Review</h1><div style='width:600px;height:20px;background:#ccc'></div>")
    page(site, "fit", "<h1 style='font-size:20px'>Harbour</h1>")
    verdicts = {}
    for name in ("wide", "fit"):
        out = tmp_path / f"narrow-{name}"
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(out), "--serve", str(site), "--pages", "__fd/narrow.html",
                            "--widths", "500", "--scales", "1", "--bands", "none", "--dump-dom", "--no-sentinel",
                            "--query", f"url=/{name}.html", "--query", "width=360"],
                           capture_output=True, text=True, timeout=240, env={**os.environ, "CHROME": chrome})
        assert r.returncode == 0, r.stderr
        doms = list(out.glob("*.dom.html"))
        assert len(doms) == 1, doms
        verdicts[name] = shoot.narrow_verdict(doms[0].read_text(encoding="utf-8"))
    assert verdicts == {"wide": ("true", "fonts"), "fit": ("false", "fonts")}, verdicts


def narrow_run(site, tmp_path, name, url, chrome, family=None):
    out = tmp_path / f"narrow-{name}"
    query = ["--query", f"url={url}", "--query", "width=360"] + (["--query", f"family={family}"] if family else [])
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(out), "--serve", str(site), "--pages", "__fd/narrow.html",
                        "--widths", "500", "--scales", "1", "--bands", "none", "--dump-dom", "--no-sentinel", *query],
                       capture_output=True, text=True, timeout=240, env={**os.environ, "CHROME": chrome})
    assert r.returncode == 0, r.stderr
    doms = list(out.glob("*.dom.html"))
    assert len(doms) == 1, doms
    dom = doms[0].read_text(encoding="utf-8")
    return shoot.narrow_verdict(dom), shoot.html_attrs(dom)


def test_chrome_narrow_reading_errors_on_a_missing_inner_page_a_failed_face_and_a_missing_family(site, tmp_path):
    """Re-review code-b F005 (docs F015): document.fonts.status is "loaded" for a 404 page and for a page
    whose face failed to load, and both lay out narrow, so the wrapper reported ("false", "fonts") for a
    page that was not there and for one without its font. narrow.html now asks the server for the inner
    URL's status (HEAD), counts failed faces and, with ?family=, requires a loaded face of the family, and
    writes data-fd-overflow="error" with the facts in three attributes when any of those fails; a page that
    is there, with its face loaded, still reads ("false", "fonts"). Mutations watched red: the HEAD status
    not held to 200 (the 404 case reads false/fonts); the failed-face count not held to 0 (the failed-font
    case reads false/fonts); the family verdict not held to loaded (the wrong-family case reads false/fonts)."""
    chrome = chrome_or_skip()
    page(site, "fine", "<h1 style='font-size:20px'>Harbour</h1>")
    page(site, "nofont", "<h1 style='font-size:20px'>Harbour</h1>", faces=(),
         extra_css='@font-face { font-family: Probe; src: url(/fonts/missing.woff2) format("woff2"); }')
    verdict, attrs = narrow_run(site, tmp_path, "fine", "/fine.html", chrome, family="Probe")
    assert verdict == ("false", "fonts"), (verdict, attrs)
    assert attrs["data-fd-narrow-inner-http"] == "200" and attrs["data-fd-narrow-fonts-failed"] == "0" and attrs["data-fd-narrow-family"] == "loaded", attrs
    verdict, attrs = narrow_run(site, tmp_path, "404", "/no-such-page.html", chrome)
    assert verdict == ("error", "fonts") and attrs["data-fd-narrow-inner-http"] == "404", (verdict, attrs)
    verdict, attrs = narrow_run(site, tmp_path, "nofont", "/nofont.html", chrome)
    assert verdict == ("error", "fonts") and attrs["data-fd-narrow-fonts-failed"] == "1", (verdict, attrs)
    verdict, attrs = narrow_run(site, tmp_path, "family", "/fine.html", chrome, family="Elsewhere")
    assert verdict == ("error", "fonts") and attrs["data-fd-narrow-family"] == "missing", (verdict, attrs)
    verdict, attrs = narrow_run(site, tmp_path, "noask", "/fine.html", chrome)
    assert verdict == ("false", "fonts") and attrs["data-fd-narrow-family"] == "not asked", (verdict, attrs)


# ---------------------------------------------------------------- specimen.py: the italic marker, the cloth labels, the charset check

NEUTRAL = REPO / "examples" / "neutral"


def run_specimen(args, cwd=None):
    return subprocess.run([sys.executable, str(REPO / "scripts" / "specimen.py"), *args], capture_output=True, text=True, cwd=cwd)


def test_specimen_marks_its_italic_rows_and_colours_labels_per_surface(tmp_path):
    """C5 and W16(a). With --italic-url the two italic rows carry data-fd-probe="italic" (and none without
    it); each label inside a surface section carries that surface's foreground colour, so the cloth
    labels are light on the dark cloth."""
    out = tmp_path / "s.html"
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman",
                      "--font-url", "/fonts/Sampler-VF.woff2", "--italic-url", "/fonts/Sampler-Italic-VF.woff2", "--allow-missing", str(out)])
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert html.count('<p class="f fi" data-fd-probe="italic"') == 2, "two italic rows must carry the probe marker"
    assert 'style="color:#f1ebdd">Readable on cloth' in html and 'style="color:#22201c">Readable on paper' in html
    assert 'style="color:#f1ebdd">Descenders and wrapping on cloth' in html
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--group", "roman", "--font-url", "/fonts/Sampler-VF.woff2", "--allow-missing", str(out)])
    assert r.returncode == 0 and 'data-fd-probe="italic"' not in out.read_text(encoding="utf-8").split("<body>")[1]


def test_specimen_refuses_a_character_the_font_file_lacks_w16(site, tmp_path):
    """W16(b), first layer. The Probe font (letters and digits only) is given as --font-file; the neutral
    titles with an Å added contain characters it lacks, so specimen.py exits non-zero naming them and
    writes nothing; --allow-missing writes the page with the note in its footer. Mutation watched red:
    check_charset() returning [] without raising."""
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["titles"] = ["Harbour Review", "Angstrom Å"]
    font_json = tmp_path / "font.json"
    font_json.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "s.html"
    base = ["--font", str(font_json), "--group", "roman", "--font-url", "/fonts/Probe.woff2", "--font-file", str(site / "fonts" / "Probe.woff2")]
    r = run_specimen([*base, str(out)])
    assert r.returncode != 0 and "'Å' U+00C5" in r.stderr and "--allow-missing" in r.stderr, r.stderr
    assert not out.exists(), "a refused specimen must not be written"
    r = run_specimen([*base, "--allow-missing", str(out)])
    assert r.returncode == 0, r.stderr
    assert "UNCHECKED CHARSET" in out.read_text(encoding="utf-8") and "U+00C5" in out.read_text(encoding="utf-8")


def spec_rows(html):
    """{marker: (font-size px, font-weight, text)} for the specimen's proof rows, read from the written page."""
    import html as html_mod
    out = {}
    row = r'<p class="f" data-fd-(spacing="\w+"|legibility="true")[^>]*style="font-size:([\d.]+)px; font-weight:(\d+)[^"]*">(.*?)</p>'
    for attr, size, weight, inner in re.findall(row, html, re.S):
        out[attr] = (float(size), int(weight), html_mod.unescape(inner))
    return out


def test_specimen_carries_the_spacing_controls_and_the_legibility_row(tmp_path):
    """The proof rows of the design-review checklist: every lowercase letter between nn and oo, every capital between
    HH and OO, every figure between 00 and 11, each punctuation mark after r f y, and `Il1 O0 B8 rn m cl d` at the
    SMALLEST review size (15.2 px, weight 500 because it is under medium_below_px). The expected strings are
    written out here from the alphabet, not read from specimen.py. Needs the built Sampler for the charset check.
    Mutations watched red: the lowercase control written `nn{c}oo`; the legibility row set at the largest size;
    the figures row dropped."""
    out = tmp_path / "s.html"
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman",
                      "--font-url", "/fonts/Sampler-VF.woff2", str(out)])
    assert r.returncode == 0, r.stderr
    rows = spec_rows(out.read_text(encoding="utf-8"))
    lower, upper = "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert rows['spacing="lower"'][2] == " ".join(f"nn{c}nn oo{c}oo" for c in lower), rows['spacing="lower"'][2]
    assert rows['spacing="upper"'][2] == " ".join(f"HH{c}HH OO{c}OO" for c in upper), rows['spacing="upper"'][2]
    assert rows['spacing="figures"'][2] == " ".join(f"00{c}00 11{c}11" for c in "0123456789"), rows['spacing="figures"'][2]
    punct = rows['spacing="punct"'][2]
    for mark in (".", ",", "’", ":", ";", "!", "?", "-", "–", "—", "…"):
        assert f"r{mark} f{mark} y{mark}" in punct, f"{mark!r} is not set after r f y in {punct!r}"
    size, weight, text = rows['legibility="true"']
    assert text == "Il1 O0 B8 rn m cl d" and size == 15.2 and weight == 500, rows['legibility="true"']


def test_specimen_sets_only_characters_the_font_maps_in_its_proof_rows(tmp_path):
    """A font lacking q, Z, 8 and every mark but the full stop: those never appear in a control string, the
    legibility row drops the B8 token (its 8 is unmapped) and keeps the others, and a font with no `n` has no
    lowercase row at all. Titles are letters only so the charset check on the other rows passes. Mutation
    watched red: the allowed set built from the project's required characters alone, without the font's cmap."""
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    cfg["titles"] = ["Harbour Review", "Notes Afloat"]
    font_json = tmp_path / "font.json"
    font_json.write_text(json.dumps(cfg), encoding="utf-8")
    chars = "".join(c for c in LETTERS if c not in "qZ8") + "."
    make_font(tmp_path / "Probe.woff2", False, chars=chars)
    base = ["--font", str(font_json), "--group", "roman", "--font-url", "/fonts/Probe.woff2", "--font-file", str(tmp_path / "Probe.woff2")]
    out = tmp_path / "s.html"
    r = run_specimen([*base, "--allow-missing", str(out)])
    assert r.returncode == 0, r.stderr
    rows = spec_rows(out.read_text(encoding="utf-8"))
    assert "nnqnn" not in rows['spacing="lower"'][2] and "nnpnn oopoo" in rows['spacing="lower"'][2], rows['spacing="lower"'][2]
    assert "HHZHH" not in rows['spacing="upper"'][2] and "HHYHH OOYOO" in rows['spacing="upper"'][2], rows['spacing="upper"'][2]
    assert "00800" not in rows['spacing="figures"'][2] and "00900 11911" in rows['spacing="figures"'][2], rows['spacing="figures"'][2]
    assert rows['spacing="punct"'][2] == "r. f. y.", rows['spacing="punct"'][2]
    assert rows['legibility="true"'][2] == "Il1 O0 rn m cl d", rows['legibility="true"'][2]
    # no `n` in the font: the lowercase control has no letters to stand between, so the row is not written
    make_font(tmp_path / "NoN.woff2", False, chars="".join(c for c in LETTERS if c not in "n"))
    r = run_specimen(["--font", str(font_json), "--group", "roman", "--font-url", "/fonts/NoN.woff2", "--font-file", str(tmp_path / "NoN.woff2"),
                      "--allow-missing", str(out)])
    assert r.returncode == 0, r.stderr
    assert 'spacing="lower"' not in spec_rows(out.read_text(encoding="utf-8"))


def test_specimen_writes_the_proof_rows_before_every_other_section(tmp_path):
    """The proof rows used to be the LAST section, past the 2400 CSS px a default review shot captures (the last ink was at
    5,368 px at 1280 wide and past 9,000 at 500). They are first now: the first proof row precedes the first
    "Readable on" label. No browser. Weakest mutation watched red: the page's pieces sorted so the proof rows move to the
    end (`sections = "".join(sorted(out, key=...))`)."""
    out = tmp_path / "s.html"
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman",
                      "--font-url", "/fonts/Sampler-VF.woff2", str(out)])
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert 0 < html.index('data-fd-legibility="true"') < html.index("Readable on"), "the proof rows must precede the readable-size rows"
    assert html.index('data-fd-spacing="lower"') < html.index("Readable on")


@pytest.mark.parametrize("width", [500, 1280])
def test_chrome_the_specimens_proof_rows_lie_inside_the_default_shot_height(tmp_path, width):
    """The specimen is laid out in real Chrome at `width` and shot at the DEFAULT height; the dumped DOM carries
    data-fd-proof-bottom, the page-px bottom of the last proof row (written by the specimen's own script after the fonts
    settle), which must be positive, count six rows (four spacing kinds, the legibility row and the junction row) and be at most
    shoot.DEFAULT_HEIGHT, so the review PNG contains them. A page whose rows end below the capture fails. Weakest mutation
    watched red: the control strings set at 90px instead of 24 (the section then runs past 2400 at 500 wide); the page's own
    script hard-coding the bottom as 100 while the rows sit past 2400 (the page's figure then disagrees with the test's own)."""
    chrome_or_skip()
    if not (NEUTRAL / "out" / "Sampler-VF.woff2").is_file():
        pytest.skip("SKIPPED, NOT PASSED: examples/neutral/out is not built")
    site = tmp_path / "site"
    (site / "fonts").mkdir(parents=True)
    for name in ("Sampler-VF.woff2", "Sampler-Italic-VF.woff2"):
        shutil.copyfile(NEUTRAL / "out" / name, site / "fonts" / name)
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman",
                      "--font-url", "/fonts/Sampler-VF.woff2", "--italic-url", "/fonts/Sampler-Italic-VF.woff2", str(site / "specimen.html")])
    assert r.returncode == 0, r.stderr
    # an independent measurement: the test appends its OWN script to the written page (the page's script wrote data-fd-proof-bottom,
    # which cannot be the only evidence of where the rows are)
    page = (site / "specimen.html").read_text(encoding="utf-8")
    probe = ("<script>(function(){function m(){var e=document.querySelectorAll('[data-fd-spacing],[data-fd-legibility],[data-fd-junctions]'),b=0;"
             "for(var i=0;i<e.length;i++){var r=e[i].getBoundingClientRect();b=Math.max(b,r.top+r.height+window.pageYOffset);}"
             "document.documentElement.setAttribute('data-test-bottom',String(Math.round(b)));}"
             "m();window.addEventListener('load',m);if(document.fonts&&document.fonts.ready){document.fonts.ready.then(m);}})();</script></body>")
    assert page.count("</body>") == 1
    (site / "specimen.html").write_text(page.replace("</body>", probe), encoding="utf-8")
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "shoot.py"), str(tmp_path / "shots"), "--serve", str(site), "--pages", "specimen.html",
                        "--widths", str(width), "--scales", "1", "--dump-dom", "--family", "Sampler", "--font-url", "/fonts/Sampler-VF.woff2"],
                       capture_output=True, text=True, timeout=300, env={**os.environ, "CHROME": chrome_or_skip()})
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    dom = next((tmp_path / "shots").glob("*.dom.html")).read_text(encoding="utf-8")
    attrs = shoot.html_attrs(dom)
    assert attrs.get("data-fd-proof-count") == "6", attrs.get("data-fd-proof-count")
    bottom = int(attrs["data-fd-proof-bottom"])
    measured = int(attrs["data-test-bottom"])
    assert 0 < measured <= shoot.DEFAULT_HEIGHT, \
        f"the proof rows end at {measured} CSS px (the test's own measurement) at {width} wide; a default shot captures {shoot.DEFAULT_HEIGHT}"
    assert abs(bottom - measured) <= 2, f"the page says its proof rows end at {bottom} px, the test measures {measured}"


def test_specimen_says_so_when_no_font_file_is_there_to_check(tmp_path):
    """The exact guarantee: the charset is checked only when the file is found; otherwise the tool says so on
    stderr and in the page footer rather than claiming a check it did not make."""
    out = tmp_path / "s.html"
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--group", "roman", "--font-url", "/fonts/Sampler-VF.woff2",
                      "--font-file", str(tmp_path / "not-built.woff2"), str(out)])
    assert r.returncode == 0, r.stderr
    assert "NOTE: charset of the roman rows not checked: no font file at" in r.stderr
    assert "not checked: no font file at" in out.read_text(encoding="utf-8")


def test_specimen_shown_chars_reads_the_family_rows_only():
    sections = ('<p class="f" style="x">A&amp;B <span>12</span></p>\n<p class="f fi" data-fd-probe="italic" style="x">Ita</p>\n'
                '<p class="cmp" style="x">zzz</p>\n<p class="body">qqq</p>')
    import specimen
    roman, italic = specimen.shown_chars(sections)
    assert roman == set("A&B12") and italic == set("Ita")


# ---------------------------------------------------------------- run_chrome(): a Chrome that hangs or dies in teardown
def fake_chrome(tmp_path):
    """A stand-in browser: writes the file named by --screenshot=, prints a complete DOM, then does what
    $FAKE_CHROME_THEN says (hang: sleep; exit2: exit 2, the code Chrome's macOS shutdown watchdog uses;
    partial-hang / partial-exit2: the same without the closing </html>)."""
    sh = tmp_path / "fake-chrome"
    sh.write_text('#!/bin/sh\nfor a in "$@"; do case "$a" in --screenshot=*) printf PNG > "${a#--screenshot=}";; esac; done\n'
                  'printf \'<!DOCTYPE html>\\n<html><head></head><body data-fake="1"></body>\'\n'
                  'case "$FAKE_CHROME_THEN" in partial-*) ;; *) printf \'</html>\\n\';; esac\n'
                  'case "$FAKE_CHROME_THEN" in *watchdog1) echo "Teardown watchdog expired; recording dump and terminating." >&2; exit 1;;\n'
                  '                            *watchdog) echo "Teardown watchdog expired; recording dump and terminating." >&2; exit 2;; esac\n'
                  'case "$FAKE_CHROME_THEN" in *hang) sleep 1000;; *exit2) exit 2;; *exit1) exit 1;; esac\n')
    sh.chmod(0o755)
    return str(sh)


@pytest.mark.parametrize("then, said", [("hang", "Chrome had not exited 1s after writing the screenshot and the DOM"),
                                        ("watchdog", "Chrome exited 2 (its teardown watchdog) 1s after")])
def test_shoot_keeps_a_complete_shot_when_chrome_hangs_or_dies_in_its_teardown(tmp_path, monkeypatch, capsys, then, said):
    """One of the two CI failures of 2026-11-17 (PR #2): Chrome 157 on macOS wrote the screenshot and the
    whole ~100 MB DOM of a hostile concept page, then stalled in its own teardown until its 10-second
    shutdown watchdog logged "Teardown watchdog expired" and _exit-ed with 2, and the helpers it left
    behind held stdout open; shoot.py waited the full timeout and reported the shot as not taken with
    both outputs on disk. Now a complete shot (PNG present, stdout ending in </html>) is kept after
    EXIT_GRACE seconds when Chrome hangs (killed, with its process group) or when it exits 2 with that
    watchdog line on stderr, and the departure is printed. Red on the code before the fix: 'hang'
    raised "Chrome took over 3s", 'watchdog' raised "Chrome exited 2"."""
    monkeypatch.setattr(shoot, "EXIT_GRACE", 1.0, raising=False)
    monkeypatch.setenv("FAKE_CHROME_THEN", then)
    t0 = time.monotonic()
    res = shoot.shoot("http://127.0.0.1:1/x.html", tmp_path / "x.png", 500, 1, chrome=fake_chrome(tmp_path), dump_dom=True, timeout=3)
    assert time.monotonic() - t0 < 3, "the complete shot was not kept before the timeout"
    assert (tmp_path / "x.png").read_bytes() == b"PNG"
    assert 'data-fake="1"' in pathlib.Path(res["dom"]).read_text() and res["verified"] is False
    err = capsys.readouterr().err
    assert said in err and "both outputs are complete and are used" in err, err


@pytest.mark.parametrize("then, error", [("partial-hang", "Chrome took over 2s"), ("partial-watchdog", "Chrome exited 2 and wrote a screenshot"),
                                         ("exit2", "Chrome exited 2 and wrote a screenshot"), ("exit1", "Chrome exited 1 and wrote a screenshot"),
                                         ("watchdog1", "Chrome exited 1 and wrote a screenshot")])
def test_shoot_still_fails_a_chrome_that_hangs_or_dies_before_the_dom_is_complete_or_for_another_reason(tmp_path, monkeypatch, then, error):
    """The grace above is for a COMPLETE shot and the WATCHDOG exit only: with the DOM cut short (no closing
    </html>) a hang is still the timeout and the watchdog exit is still a failed shot, and a complete DOM
    followed by an exit 2 without the watchdog line, or by any other exit code with or without it, is still a failed shot
    (a renderer that died leaves a complete DOM of an error page). The first version accepted every
    non-zero exit after a complete DOM, and test_the_mock_slot_sizes_take_effect_in_chrome[round3]
    then passed shoot.py and failed on a DOM without the slot (fix branch CI, job 134106502866).
    Weakest mutations watched red: complete() returning True on any stdout; the exit-code and
    watchdog-line conditions dropped."""
    monkeypatch.setattr(shoot, "EXIT_GRACE", 1.0, raising=False)
    monkeypatch.setenv("FAKE_CHROME_THEN", then)
    with pytest.raises(RuntimeError, match=error):
        shoot.shoot("http://127.0.0.1:1/x.html", tmp_path / "x.png", 500, 1, chrome=fake_chrome(tmp_path), dump_dom=True, timeout=2)


def test_shoot_dom_only_asks_chrome_for_no_screenshot_and_keeps_the_dom(tmp_path, monkeypatch):
    """The other CI failure of 2026-11-17 (PR #2), the frequent one: asked for a screenshot of a hostile
    concept page (96-124 MB of SVG path data) under --virtual-time-budget, Chrome on the macOS runners
    stalled before taking it in about half of all attempts, every process idle until the timeout, and
    never did without --screenshot (12 of 12 clean) or without the budget (12 of 12). dom_only=True
    drops --screenshot from the command, keeps --dump-dom, requires no PNG, and returns png None. The
    fake records its arguments. Red before the fix: shoot() had no dom_only parameter."""
    sh = tmp_path / "fake-chrome"
    sh.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$(dirname "$0")/args.txt"\n'
                  'printf \'<!DOCTYPE html>\\n<html><head></head><body data-fake="1"></body></html>\\n\'\n')
    sh.chmod(0o755)
    res = shoot.shoot("http://127.0.0.1:1/x.html", tmp_path / "x.png", 500, 1, chrome=str(sh), dom_only=True, timeout=5)
    args = (tmp_path / "args.txt").read_text().splitlines()
    assert not any(a.startswith("--screenshot") for a in args) and "--dump-dom" in args, args
    assert res["png"] is None and 'data-fake="1"' in pathlib.Path(res["dom"]).read_text()
    assert not (tmp_path / "x.png").exists()


# ---------------------------------------------------------------- 0.3: fractional scales, the Windows teardown, --meta, --rows, several --font-url
# Fake browsers here are Python (a script run by sys.executable, or `python -c`), not #!/bin/sh, so the same tests run on
# the Windows leg of the skill's platform workflow (plan-platform-shots F010). Each mutation below was applied to the
# shipped code, the test was run and seen red on the named assertion, and the code was restored, on 2026-11-17.

def py_exe(path, code):
    """A runnable fake browser at `path` (POSIX: a sh wrapper; Windows: path.cmd) that runs `code` with this
    interpreter and passes its arguments on. Returns the path to give as $CHROME or chrome=."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    script = path.with_name(path.name + ".py")
    script.write_text(code, encoding="utf-8")
    if os.name == "nt":
        path = path.with_name(path.name + ".cmd")
        path.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        path.chmod(0o755)
    return str(path)


# Fetches the page (so the server records it served 200 under the shot's token), writes b"PNG" to --screenshot=,
# logs its arguments, and exits 1 instead for a URL naming die.html.
FETCHING_FAKE = r'''
import pathlib, sys, urllib.request
args = sys.argv[1:]
url = args[-1]
with open(pathlib.Path(__file__).with_name("args.log"), "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=10).read()
if "/die.html" in url:
    sys.exit(1)
for a in args:
    if a.startswith("--screenshot="):
        pathlib.Path(a.split("=", 1)[1]).write_bytes(b"PNG")
'''


def plain_site(tmp_path, names):
    site = tmp_path / "site"
    site.mkdir()
    for n in names:
        (site / f"{n}.html").write_text("<!doctype html><title>x</title><p>x</p>", encoding="utf-8")
    return site


def test_scales_accept_a_fraction_and_name_the_file_by_it(tmp_path, monkeypatch):
    """--scales 1 1.25 2 writes x-1280@1x.png, x-1280@1.25x.png and x-1280@2x.png (the @1x and @2x names unchanged from
    0.2) and passes 1.25 to the browser as written. Mutations watched red on 2026-11-17: `type=int` restored (argparse
    refuses 1.25: SystemExit 2); the name format `@{scale}x` restored (@1.0x and @2.0x written)."""
    site = plain_site(tmp_path, ["x"])
    fake = py_exe(tmp_path / "bin" / "chrome", FETCHING_FAKE)
    monkeypatch.setenv("CHROME", fake)
    out = tmp_path / "shots"
    rc = shoot.main([str(out), "--serve", str(site), "--pages", "x.html", "--widths", "1280", "--scales", "1", "1.25", "2",
                     "--no-sentinel", "--bands", "none", "--jobs", "1"])
    assert rc == 0
    assert sorted(p.name for p in out.glob("*.png")) == ["x-1280@1.25x.png", "x-1280@1x.png", "x-1280@2x.png"]
    assert "--force-device-scale-factor=1.25" in (tmp_path / "bin" / "args.log").read_text(encoding="utf-8")


def test_crop_bands_rounds_a_fractional_box(tmp_path):
    """At scale 1.25 a CSS band is a fractional device box. head:0:901 is 1126.25 device px (900 would be 1125 exactly and
    could not tell anything apart, plan review F009) and must crop to 1126; body:0:903 is 1128.75 and must crop to 1129,
    which a truncating box (`int(bottom * scale)`) gets wrong. Mutation watched red on 2026-11-17: `int(round(...))`
    replaced by `int(...)` (body is 1128 px). SURVIVED, and kept as a finding: the plan's mutation, `int(round())` removed
    so the float box reaches Pillow, stays green, because Pillow 13's Image._crop itself does `map(int, map(round, box))`;
    the rounding in crop_bands() only makes the box independent of that."""
    from PIL import Image
    png = tmp_path / "x-1280@1.25x.png"
    Image.new("RGB", (1280, 2400), "white").save(png)
    written = shoot.crop_bands(png, 1.25, shoot.parse_bands("head:0:901,body:0:903"))
    sizes = {pathlib.Path(w).name: Image.open(w).size for w in written}
    assert sizes == {"x-1280@1.25x-head.png": (1280, 1126), "x-1280@1.25x-body.png": (1280, 1129)}, sizes


def pid_alive(pid):
    """Whether process `pid` still runs (POSIX: signal 0; Windows: OpenProcess and its exit code)."""
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gone_within(pid, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not pid_alive(pid):
            return True
        time.sleep(0.05)
    return not pid_alive(pid)


def end(pid):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, 9)
    except OSError:
        pass


# A browser whose helper (a grandchild) inherits stdout and stderr and sleeps: the browser prints the helper's pid and a
# complete DOM, then hangs. The helper's open pipe is what kept run_chrome() waiting (shoot.py's item 1, 2026-11-17).
HELPER_HOLDS_STDOUT = (
    "import subprocess, sys, time\n"
    "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
    "sys.stdout.buffer.write(b'%d\\n<html></html>\\n' % g.pid); sys.stdout.buffer.flush()\n"
    "time.sleep(30)\n")


def test_kill_group_ends_a_grandchild_that_holds_stdout(monkeypatch):
    """Plan review F003/F010: the real failure is a helper that inherited the stdout pipe. run_chrome(), once the DOM is
    complete and EXIT_GRACE (1 s here) has passed, kills the group: it returns within 4 s, the helper is dead and the
    browser is reaped. Mutation watched red on 2026-11-17: kill_group()'s POSIX branch replaced by `p.kill()` alone (the
    helper survives holding the pipe; run_chrome returns only after the 10 s bounded join, and the helper is alive). On
    Windows the matching mutation is taskkill run after p.kill() (the tree is gone and the helper survives); that one is
    for the Windows leg of the platform workflow to show, not run here."""
    monkeypatch.setattr(shoot, "EXIT_GRACE", 1.0)
    t0 = time.monotonic()
    r = shoot.run_chrome([sys.executable, "-c", HELPER_HOLDS_STDOUT], 30, complete=lambda tail: tail.endswith(shoot.DOM_END))
    took = time.monotonic() - t0
    helper = int(r.stdout.split()[0])
    try:
        assert took < 4, f"run_chrome took {took:.1f}s: the helper held stdout after the kill"
        assert r.killed and r.complete and r.returncode is not None, (r.killed, r.complete, r.returncode)
        assert gone_within(helper, 3), f"the helper {helper} survived kill_group()"
    finally:
        end(helper)


def test_run_chrome_returns_after_a_kill_even_when_a_helper_holds_stdout(monkeypatch):
    """Part b of the Windows teardown: when a kill misses a helper (kill_group() here kills the browser only, as p.kill()
    alone does on Windows), run_chrome() still returns within EXIT_GRACE + 10 + 1 s, with killed true and the stdout read
    so far. Mutation watched red on 2026-11-17: the bounded join replaced by `t.join()` (run_chrome waits until the
    helper's 30 s sleep ends). The 0.2 code was red too: it joined each of the two held pipes for 10 s, 21 s in all."""
    monkeypatch.setattr(shoot, "EXIT_GRACE", 1.0)

    def browser_only(p):
        p.kill()
        p.wait(timeout=10)
    monkeypatch.setattr(shoot, "kill_group", browser_only)
    t0 = time.monotonic()
    r = shoot.run_chrome([sys.executable, "-c", HELPER_HOLDS_STDOUT], 60, complete=lambda tail: tail.endswith(shoot.DOM_END))
    took = time.monotonic() - t0
    end(int(r.stdout.split()[0]))
    assert took < shoot.EXIT_GRACE + 10 + 1, f"run_chrome took {took:.1f}s"
    assert r.killed and "<html></html>" in r.stdout, (r.killed, r.stdout)


# Writes a file into its --user-data-dir and the screenshot, then makes the profile impossible to remove: on Windows a
# detached helper holds the file open; on POSIX the profile's PARENT is made read-only. (Making the profile itself
# read-only does not work: TemporaryDirectory's cleanup chmods a path that refuses removal and tries again.)
PROFILE_HELD = r'''
import os, pathlib, sys, time
args = sys.argv[1:]
prof = next(a.split("=", 1)[1] for a in args if a.startswith("--user-data-dir="))
held = os.path.join(prof, "Cookies")
pathlib.Path(held).write_text("x")
for a in args:
    if a.startswith("--screenshot="):
        pathlib.Path(a.split("=", 1)[1]).write_bytes(b"PNG")
if os.name == "nt":
    time.sleep(2)  # the test holds Cookies open from its own process (see the test); give its watcher time to open it
else:
    os.chmod(os.path.dirname(prof), 0o555)
'''


def test_shoot_notes_a_profile_directory_a_helper_left_behind(tmp_path, capsys):
    """Part c of the Windows teardown: a profile directory that cannot be removed after the browser exited is a teardown
    leak, not a page fault. shoot() returns the shot and prints a NOTE naming the directory. Mutations watched red on
    2026-11-17: `ignore_cleanup_errors=True` removed (PermissionError out of shoot()); the note line removed."""
    if os.name != "nt" and os.geteuid() == 0:
        pytest.skip("SKIPPED, NOT PASSED: root ignores the read-only directory this test relies on")
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    fake = py_exe(tmp_path / "bin" / "chrome", PROFILE_HELD)
    # On Windows the holder is this test's own thread, not a child of the fake Chrome: kill_group()'s taskkill /T kills
    # the fake's whole tree, so a helper child died before the cleanup and nothing was left (run 44226847590).
    done, handles = threading.Event(), []

    def hold():
        while not done.is_set() and not handles:
            for f in profiles.glob("*/Cookies"):
                try:
                    handles.append(open(f))
                except OSError:
                    pass
            time.sleep(0.02)
        done.wait(30)
        for h in handles:
            h.close()
    holder = threading.Thread(target=hold, daemon=True) if os.name == "nt" else None
    if holder:
        holder.start()
    try:
        res = shoot.shoot("http://127.0.0.1:1/x.html", tmp_path / "x.png", 500, 1, chrome=fake, profile_root=profiles, timeout=20)
        left = [p for p in profiles.iterdir()]
        err = capsys.readouterr().err
        assert res["png"] and (tmp_path / "x.png").read_bytes() == b"PNG"
        assert len(left) == 1, left
        assert f"NOTE: profile {left[0]} left behind" in err, err
    finally:
        done.set()
        if holder:
            holder.join(5)
        profiles.chmod(0o755)


def test_a_shot_whose_browser_dies_does_not_stop_the_run_and_the_run_exits_1(tmp_path, monkeypatch):
    """One of two shots fails (its browser exits 1): the other PNG is written, main() returns 1, and --meta lists one
    shot and one failure. Mutations watched red on 2026-11-17: `except (RuntimeError, ValueError)` in one() narrowed to
    ValueError (the RuntimeError ends the run); `return 1 if failed else 0` made `return 0`."""
    site = plain_site(tmp_path, ["live", "die"])
    monkeypatch.setenv("CHROME", py_exe(tmp_path / "bin" / "chrome", FETCHING_FAKE))
    out, meta = tmp_path / "shots", tmp_path / "meta.json"
    rc = shoot.main([str(out), "--serve", str(site), "--pages", "live.html", "die.html", "--widths", "500", "--scales", "1",
                     "--no-sentinel", "--bands", "none", "--jobs", "2", "--meta", str(meta)])
    assert rc == 1
    assert (out / "live-500@1x.png").is_file() and not (out / "die-500@1x.png").exists()
    m = json.loads(meta.read_text(encoding="utf-8"))
    assert [pathlib.Path(s["png"]).name for s in m["shots"]] == ["live-500@1x.png"], m["shots"]
    assert len(m["failed"]) == 1 and "Chrome exited 1" in m["failed"][0] and "die.html" in m["failed"][0], m["failed"]


def test_chrome_meta_file_records_the_platform_the_verified_shots_the_failures_and_the_exit_code(site, tmp_path, monkeypatch):
    """--meta, on two real shots: one page in Probe (verified), one in Georgia (failed: nothing visible is in Probe).
    The file names the platform, the browser, one verified shot with a ua from the page and its height, and the
    failure; it changes no verdict (main() still returns 1). Named "chrome" (the plan's name was
    test_meta_file_records_...) so the CI chrome job, which selects -k chrome, runs it. Mutations watched red on
    2026-11-17: `failed` written as []; `add("ua", ...)` dropped from the sentinel (ua null); main's exit made 0."""
    monkeypatch.setenv("CHROME", chrome_or_skip())
    page(site, "metaok", "<h1>Harbour Review</h1>")
    page(site, "metageorgia", "<p>Everything here is Georgia</p>")
    out, meta = tmp_path / "shots", tmp_path / "leg" / "meta.json"
    rc = shoot.main([str(out), "--serve", str(site), "--pages", "metaok.html", "metageorgia.html", "--widths", "500", "--scales", "1",
                     "--bands", "none", "--family", "Probe", "--font-url", "/fonts/Probe.woff2", "--meta", str(meta)])
    assert rc == 1
    m = json.loads(meta.read_text(encoding="utf-8"))
    import platform
    assert m["platform"] == platform.platform() and m["browser"] == "chrome" and m["launcher"] == os.environ["CHROME"], m
    if platform.system() != "Windows":
        assert m["font_smoothing"] is None
    assert len(m["shots"]) == 1, m["shots"]
    s = m["shots"][0]
    assert s["verified"] is True and "Chrome/" in (s["ua"] or "") and s["height"] == shoot.DEFAULT_HEIGHT, s
    assert len(m["failed"]) == 1 and "/metageorgia.html" in m["failed"][0], m["failed"]


ROWS_BODY = ("<h1 style='margin:0'>Probe row</h1>"
             "<h1 data-fd-row='r-a' style='position:absolute;left:40px;top:100px;width:300px;height:60px;margin:0'>Harbour</h1>"
             "<h1 data-fd-row='r-b' style='position:absolute;left:60px;top:700px;width:400px;height:80px;margin:0'>Review</h1>"
             "<h1 data-fd-row='r-c' style='position:absolute;left:20px;top:3000px;width:200px;height:50px;margin:0'>Below</h1>")
ROWS_BOXES = {"r-a": (40, 100, 300, 60), "r-b": (60, 700, 400, 80), "r-c": (20, 3000, 200, 50)}


def test_chrome_rows_json_carries_every_marked_row_in_viewport_coordinates_with_the_scroll_and_scale(site, tmp_path):
    """--rows (plan review F005): three data-fd-row elements at known CSS boxes, one at top 3000 below the 2400 capture,
    plus one unmarked element in the family (key probe-1). At scale 1 and 2 each box is within 1 px of its CSS value (CSS
    px, never device px), scroll_y is 0, height is 2400, the row below the capture is captured: false, and the file
    is <png stem>.rows.json. The plan asserted viewport_h == 2400; measured on 2026-11-17, Chrome 157's headless page
    reports innerHeight 2313 for --window-size=500,2400 while its PNG is 2400 px tall and draws the page down to 2400
    (a red box at top 2300 fills PNG rows 2300-2399), so `captured` is judged against the shot's height (?fdh=) and
    viewport_h records what the page measured. Mutations watched red on 2026-11-17: the sentinel multiplying the rect by devicePixelRatio
    (the scale-2 shot fails); captured computed against the document height (r-c reads true); scroll_y left out (None)."""
    path = page(site, "rowsbox", ROWS_BODY)
    server, port = served(site, family="Probe")
    try:
        for scale in (1, 2):
            png = tmp_path / f"rowsbox-500@{scale}x.png"
            res = shoot.shoot(f"http://127.0.0.1:{port}{path}", png, 500, scale, server=server, chrome=chrome_or_skip(),
                              require_family="Probe", rows=True, launcher=ROWS_LAUNCHER)
            assert res["rows"] == str(tmp_path / f"rowsbox-500@{scale}x.rows.json"), res["rows"]
            doc = json.loads(pathlib.Path(res["rows"]).read_text(encoding="utf-8"))
            assert doc["scroll_x"] == 0 and doc["scroll_y"] == 0 and doc["height"] == shoot.DEFAULT_HEIGHT, doc
            assert 0 < doc["viewport_h"] <= doc["height"], doc  # 2313 in Chrome 157 headless on macOS: see the docstring
            assert doc["scale"] == scale and doc["shot"] == res["shot"] and "Chrome/" in doc["ua"], doc
            got = {r["key"]: r for r in doc["rows"]}
            assert set(got) == {"probe-1", *ROWS_BOXES}, sorted(got)
            for key, (x, y, w, h) in ROWS_BOXES.items():
                r = got[key]
                assert all(abs(a - b) <= 1 for a, b in ((r["x"], x), (r["y"], y), (r["w"], w), (r["h"], h))), (scale, key, r)
            assert got["r-a"]["captured"] and got["r-b"]["captured"] and not got["r-c"]["captured"], got
            assert got["r-a"]["text"] == "Harbour" and got["r-a"]["font_style"] == "normal" and got["r-a"]["font_size"] == "48px", got["r-a"]
    finally:
        server.shutdown()


def test_chrome_a_page_that_scrolled_records_the_offset(site, tmp_path):
    """A page whose own script scrolls by 500 px before the fonts are ready: rows.json records scroll_y 500 and the row's
    y is its CSS top minus 500 (viewport coordinates; compare-shots.py refuses such a shot, plan review F005). Mutation
    watched red on 2026-11-17: the sentinel adding window.scrollY into y (document coordinates: y reads 800)."""
    body = ("<div style='height:6000px'></div>"
            "<h1 data-fd-row='r-s' style='position:absolute;left:40px;top:800px;width:300px;height:60px;margin:0'>Harbour</h1>"
            "<script>window.scrollTo(0, 500)</script>")
    path = page(site, "rowsscroll", body)
    server, port = served(site, family="Probe")
    try:
        res = shoot.shoot(f"http://127.0.0.1:{port}{path}", tmp_path / "s.png", 500, 1, server=server, chrome=chrome_or_skip(),
                          require_family="Probe", rows=True, launcher=ROWS_LAUNCHER)
        doc = json.loads(pathlib.Path(res["rows"]).read_text(encoding="utf-8"))
        assert doc["scroll_y"] == 500, doc
        assert abs(doc["rows"][0]["y"] - 300) <= 1, doc["rows"]
    finally:
        server.shutdown()


def test_chrome_rows_json_is_not_written_for_a_shot_that_failed_its_proof(site, tmp_path):
    """The rows file is written only after every proof passed: a page in Georgia with marked rows, shot with
    require_family Probe, raises and leaves no rows file (the sentinel did send its rows). Mutation watched red on
    2026-11-17: the rows block moved before the beacon's proofs (the file is written, then the shot fails)."""
    path = page(site, "rowsgeorgia", "<p data-fd-row='g-1'>Georgia one</p><p data-fd-row='g-2'>Georgia two</p>")
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match="no visible element with text is set in 'Probe'"):
            shoot.shoot(f"http://127.0.0.1:{port}{path}", tmp_path / "g.png", 500, 1, server=server, chrome=chrome_or_skip(),
                        require_family="Probe", rows=True, launcher=ROWS_LAUNCHER)
        assert not (tmp_path / "g.rows.json").exists()
        assert any(server.rows.values()), "the sentinel must have sent the rows, or this test shows nothing"
    finally:
        server.shutdown()


def test_chrome_a_verified_shot_whose_rows_never_arrive_is_failed(site, tmp_path, monkeypatch):
    """The rows endpoint drops every body (monkeypatched): a shot that passes every other proof raises "no rows arrived"
    and writes no rows file, so a PNG never ships without its boxes. Mutation watched red on 2026-11-17: the wait made
    optional (`if got is None: return result`)."""
    def drop(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self.send_response(204)
        self.end_headers()
    monkeypatch.setattr(shoot.Handler, "do_POST", drop)
    path = page(site, "rowsdrop", "<h1 data-fd-row='d-1'>Harbour Review</h1>")
    server, port = served(site, family="Probe")
    try:
        with pytest.raises(RuntimeError, match="no rows arrived"):
            shoot.shoot(f"http://127.0.0.1:{port}{path}", tmp_path / "d.png", 500, 1, server=server, chrome=chrome_or_skip(),
                        require_family="Probe", rows=True, launcher=ROWS_LAUNCHER)
        assert not (tmp_path / "d.rows.json").exists()
    finally:
        server.shutdown()


def post_rows(port, shot, cookie, body=b'{"scroll_x": 0, "scroll_y": 0, "rows": []}'):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", f"/__fd/rows?shot={shot}", body=body, headers={"Cookie": f"fd_shot={cookie}", "Content-Type": "text/plain"})
    status = conn.getresponse().status
    conn.close()
    return status


def test_rows_from_another_shots_browser_are_ignored_and_noted(tmp_path):
    """The rows POST is recorded per shot only under that shot's cookie, as the beacon is: a POST for shot A carrying
    B's cookie is ignored and noted; one carrying A's is recorded. Mutation watched red on 2026-11-17: the same_shot()
    test dropped from do_POST (A's rows are planted by B)."""
    server, port = served(tmp_path)
    try:
        assert post_rows(port, "shotA", "shotB") == 204
        assert "shotA" not in server.rows, "rows carrying another shot's cookie were recorded"
        assert any("rows for shot 'shotA' ignored" in d for d in server.departures), server.departures
        assert post_rows(port, "shotA", "shotA") == 204
        assert server.rows["shotA"]["rows"] == []
    finally:
        server.shutdown()


def test_chrome_font_urls_pass_when_each_requested_one_is_served_and_fail_when_none_is_requested_or_one_404s(site, tmp_path):
    """Repeatable --font-url (plan host finding H1): every named path the shot requested must be served 200, and at least
    one must be requested. A page using only the roman passes with the italic also named; a named path never requested
    does not fail it; a page in Georgia fails "none of the named font paths was requested"; a page that requests a named
    path that 404s fails naming it, though another named path was served 200. Mutations watched red on 2026-11-17:
    "every named path served 200" (the italic case fails); "any named path served 200" (the 404 case passes)."""
    roman = page(site, "furoman", "<h1>Harbour Review</h1>", faces=("normal", "italic"))
    georgia = page(site, "fugeorgia", "<p>Everything here is Georgia</p>", faces=())
    gone = page(site, "fugone", "<h1>Harbour Review</h1><h2>Gone row</h2>",
                extra_css='@font-face { font-family: Gone; src: url(/fonts/Missing.woff2) format("woff2"); } h2 { font-family: Gone, serif }')
    server, port = served(site)
    try:
        def go(path, urls, name):
            return shoot.shoot(f"http://127.0.0.1:{port}{path}", tmp_path / f"{name}.png", 500, 1, server=server, chrome=chrome_or_skip(), font_url=urls)
        res = go(roman, ["/fonts/Probe.woff2", "/fonts/Probe-Italic.woff2"], "r1")
        assert res["font_status"] == {"/fonts/Probe.woff2": [200], "/fonts/Probe-Italic.woff2": []}, res["font_status"]
        go(roman, ["/fonts/Nothing.woff2", "/fonts/Probe.woff2"], "r2")
        with pytest.raises(RuntimeError, match="none of the named font paths was requested"):
            go(georgia, ["/fonts/Probe.woff2", "/fonts/Probe-Italic.woff2"], "g")
        with pytest.raises(RuntimeError, match=r"/fonts/Missing\.woff2 was not served 200 to the shot of /fugone\.html"):
            go(gone, ["/fonts/Probe.woff2", "/fonts/Missing.woff2"], "m")
    finally:
        server.shutdown()


# ---------------------------------------------------------------- specimen.py: a data-fd-row key on every family row (0.3)

def test_specimen_gives_every_family_row_a_unique_data_fd_row_key(tmp_path):
    """Every row set in the family carries data-fd-row, the keys are unique, the six proof rows' keys are exactly
    spacing-lower/upper/figures/punct, legibility and junctions, and the readable keys name their surface (paper and cloth
    rows at one size and weight would otherwise collide). Mutations watched red on 2026-11-17: the surface dropped from
    the readable key (specimen.py refuses the duplicate and exits 1); row() writing data-fd-row only when `attrs` is given
    (most rows lack the key)."""
    out = tmp_path / "s.html"
    r = run_specimen(["--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "roman",
                      "--font-url", "/fonts/Sampler-VF.woff2", "--italic-url", "/fonts/Sampler-Italic-VF.woff2", "--allow-missing", str(out)])
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    tags = re.findall(r'<p class="f[^"]*"[^>]*>', html)
    assert len(tags) > 40, len(tags)
    keys = [re.search(r'data-fd-row="([^"]+)"', t) for t in tags]
    assert all(keys), [t for t, k in zip(tags, keys) if not k][:3]
    keys = [k.group(1) for k in keys]
    assert len(keys) == len(set(keys)), sorted(k for k in keys if keys.count(k) > 1)
    proof = {"spacing-lower", "spacing-upper", "spacing-figures", "spacing-punct", "legibility", "junctions"}
    marked = re.findall(r'<p class="f"[^>]*data-fd-(?:spacing|legibility|junctions)="[^"]*"[^>]*data-fd-row="([^"]+)"', html)
    assert set(marked) == proof and len(marked) == 6, marked
    readable = [k for k in keys if k.startswith("readable-")]
    assert readable and all(k.startswith(("readable-paper-", "readable-cloth-")) for k in readable), readable
    assert {"italic-1", "italic-2", "quotes"} <= set(keys)


def test_specimen_refuses_a_duplicate_row_key():
    """build() with a surface list naming paper twice: the readable rows of both surfaces would share keys, and
    compare-shots.py would crop one row as another; build() raises naming the key. Mutation watched red on 2026-11-17:
    the row_keys() call removed from build() (the page is built)."""
    import specimen
    cfg = json.loads((NEUTRAL / "font.json").read_text(encoding="utf-8"))
    paper = cfg["review"]["surfaces"][0]
    cfg["review"]["surfaces"] = [paper, dict(paper)]
    with pytest.raises(ValueError, match=r"data-fd-row key 'readable-paper-"):
        specimen.build(cfg, cfg["titles"], "roman", "/fonts/Sampler-VF.woff2", None, "font.json")


def test_chrome_is_given_an_absolute_screenshot_path_when_the_output_folder_is_relative(tmp_path, monkeypatch):
    """Chrome on Windows does not write a relative --screenshot path (platform-shots run 44216537669: "Failed to write
    file leg\\index-1280@1x.png ... cannot find the path specified"). launch_chrome() is called with the relative target
    main() builds from a relative OUT_DIR, and the command it runs must name the file absolutely. Mutation watched red on
    2026-11-17: `--screenshot={target}` restored."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "leg").mkdir()
    seen = {}

    def fake_run(cmd, timeout, complete=None):
        seen["cmd"] = cmd
        shot = next(a for a in cmd if a.startswith("--screenshot="))[len("--screenshot="):]
        pathlib.Path(shot).write_bytes(b"png")  # written where Chrome would write it, so the run counts as a success
        return SimpleNamespace(returncode=0, stdout="", stderr="", complete=False, killed=False)

    monkeypatch.setattr(shoot, "run_chrome", fake_run)
    shoot.launch_chrome("chrome", "http://127.0.0.1:1/x.html", pathlib.Path("leg") / "x-1280@1x.png", 1280, 1.0, 900,
                        str(tmp_path), 30, False, False, lambda msg: None)
    arg = next(a for a in seen["cmd"] if a.startswith("--screenshot="))[len("--screenshot="):]
    assert pathlib.Path(arg).is_absolute(), f"Chrome was given a relative screenshot path: {arg}"
    assert pathlib.Path(arg) == (tmp_path / "leg" / "x-1280@1x.png").resolve()


@pytest.mark.parametrize("codes, ok", [([200], True), ([200, 200], True), ([200, 404], False), ([404, 200], False), ([304], False)])
def test_check_font_urls_needs_every_response_for_a_named_path_to_be_200(codes, ok):
    """The rule says every response this shot got for a named font path was 200. A path requested twice, once 200 and
    once 404, passed while `200 in` the list was the test (Impasse F004). Mutation watched red on 2026-11-17:
    `if 200 not in mine` restored (the two mixed cases pass)."""
    served = [("s1", "/fonts/A.woff2", "", c) for c in codes]
    if ok:
        assert shoot.check_font_urls(served, ["/fonts/A.woff2"], "/x.html", "s1") == codes
    else:
        with pytest.raises(RuntimeError, match="not served 200"):
            shoot.check_font_urls(served, ["/fonts/A.woff2"], "/x.html", "s1")


def test_chrome_require_captured_fails_a_shot_with_a_row_below_the_capture(site, tmp_path):
    """--require-captured (Impasse F002): the ROWS_BODY page has r-c at top 3000, below the 2400 capture. With
    require_captured the shot raises, naming r-c, and writes no rows file; without it the same page passes (so the
    page itself is fine and the failure is the flag's). Mutation watched red on 2026-11-17: the check removed."""
    path = page(site, "rowsbelow", ROWS_BODY)
    server, port = served(site, family="Probe")
    try:
        url = f"http://127.0.0.1:{port}{path}"
        with pytest.raises(RuntimeError, match=r"end below the 2400 px capture \(r-c\)"):
            shoot.shoot(url, tmp_path / "b.png", 500, 1, server=server, chrome=chrome_or_skip(), require_family="Probe", rows=True, launcher=ROWS_LAUNCHER,
                        require_captured=True)
        assert not (tmp_path / "b.rows.json").exists()
        res = shoot.shoot(url, tmp_path / "ok.png", 500, 1, server=server, chrome=chrome_or_skip(), require_family="Probe", rows=True, launcher=ROWS_LAUNCHER)
        assert res["rows"]
    finally:
        server.shutdown()


def test_rows_whose_entries_are_not_objects_are_ignored_and_noted(tmp_path):
    """A rows POST under the shot's cookie whose `rows` list holds a scalar is not recorded, and the departure says why;
    shoot() then fails the shot "no rows arrived" rather than raising AttributeError on r.get() in --require-captured's
    check, which the per-shot handler does not catch (Impasse re-review F002). Mutation watched red on 2026-11-17: the
    all(isinstance(r, dict)) clause removed (the rows are recorded)."""
    server, port = served(tmp_path)
    try:
        assert post_rows(port, "shotA", "shotA", body=b'{"scroll_x": 0, "scroll_y": 0, "rows": [3]}') == 204
        assert "shotA" not in server.rows, server.rows
        assert any("rows for shot 'shotA' ignored" in d and "row objects" in d for d in server.departures), server.departures
    finally:
        server.shutdown()


def test_chrome_rows_measured_on_a_page_of_another_width_fail_the_shot(site, tmp_path, monkeypatch):
    """The rows endpoint is made to record viewport_w 1264 for a 1280 shot, as Chrome's command line on a Windows runner
    did (platform-shots run 44227825840: every row under a line that wrapped differently was cropped from the wrong place).
    The shot raises naming both widths and writes no rows file; 1282 (Linux Chrome's rounding at 1.25x) passes. Mutation
    watched red on 2026-11-17: the width check removed (the 1264 shot writes its rows)."""
    real = shoot.Handler.do_POST
    narrow = {"w": 1264}

    def post(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length))
        body["viewport_w"] = narrow["w"]
        data = json.dumps(body).encode()
        self.rfile = __import__("io").BytesIO(data)
        self.headers.replace_header("Content-Length", str(len(data)))
        return real(self)
    monkeypatch.setattr(shoot.Handler, "do_POST", post)
    path = page(site, "rowswide", "<h1 data-fd-row='w-1'>Harbour Review</h1>")
    server, port = served(site, family="Probe")
    try:
        url = f"http://127.0.0.1:{port}{path}"
        with pytest.raises(RuntimeError, match="measured on a page 1264 px wide and the shot is 1280 px wide"):
            shoot.shoot(url, tmp_path / "n.png", 1280, 1, height=900, server=server, chrome=chrome_or_skip(), require_family="Probe", rows=True)
        assert not (tmp_path / "n.rows.json").exists()
        narrow["w"] = 1282
        assert shoot.shoot(url, tmp_path / "r.png", 1280, 1, height=900, server=server, chrome=chrome_or_skip(), require_family="Probe",
                           rows=True)["rows"]
    finally:
        server.shutdown()


@pytest.mark.parametrize("argv, why", [(["--browser", "firefox", "--launcher", "cli"], "Firefox is started through Playwright only"),
                                       (["--launcher", "playwright", "--dom-only"], "--dom-only is a mode of Chrome's command line")])
def test_launcher_combinations_that_cannot_run_are_refused(tmp_path, argv, why):
    """Firefox has no command-line launcher here, and --dom-only exists only for Chrome's command line: both are refused
    before any server starts. Mutations watched red on 2026-11-17: each refusal removed."""
    with pytest.raises(SystemExit) as exc:
        shoot.main([str(tmp_path / "o"), "--serve", str(tmp_path), "--pages", "x.html", *argv])
    assert why in str(exc.value.code), exc.value.code



@pytest.mark.parametrize("missing", ["--family", "--font-url"])
def test_rows_without_both_font_proofs_are_refused(tmp_path, missing):
    """compare-shots.py reads every rows file as evidence of the font, and a shot without --family and --font-url is a
    picture, not evidence; so --rows without either is refused before any server starts (Impasse review of bd24d55,
    F003). Mutation watched red on 2026-11-17: the refusal removed (main goes on to serve and shoot)."""
    argv = [str(tmp_path / "o"), "--serve", str(tmp_path), "--pages", "x.html", "--rows",
            "--family", "Probe", "--font-url", "/fonts/Probe.woff2"]
    i = argv.index(missing)
    del argv[i:i + 2]
    with pytest.raises(SystemExit) as exc:
        shoot.main(argv)
    assert "--rows needs --family and --font-url" in str(exc.value.code), exc.value.code
