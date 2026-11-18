"""scripts/shoot_playwright.py, the Firefox launcher, and shoot.py's `--browser firefox` path, exercised for real.

WHAT IT'S FOR: the Firefox leg of the platform shots is only evidence if shoot.py's server proofs (the tokenised page
served 200, the shot's cookie on every later request, the sentinel's beacon, the element probe) run on it exactly as on
Chrome, and if a machine without Playwright says SKIPPED, NOT PASSED instead of passing or failing. Each test here runs
the shipped module: the launcher against shoot.py's own serve() on pages and fonts built in tmp (test_shoot.py's
make_font and page, imported, not copied), and shoot.py itself as a subprocess for the exit code. Tests whose names
contain "firefox" need Playwright and its Firefox; without either they skip LOUDLY, and on a Mac where Firefox still
exits at launch with "Could not find profile folder" (the macOS profile failure in shoot_playwright.py's header) they
skip with that message: the leg is then judged on the GitHub runner. The tests without "firefox" in their names run
everywhere, the repo's own venv included, which has no Playwright on purpose. Every guard was watched failing under the
mutation named in its docstring.
"""
import subprocess
import sys
import time

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "scripts"))
import shoot  # noqa: E402
import shoot_playwright  # noqa: E402
from test_shoot import make_font, page  # noqa: E402

SHOOT = REPO / "scripts" / "shoot.py"
MAC_SKIP = ("SKIPPED, NOT PASSED: Playwright's Firefox exits at launch on this Mac with \"Could not find profile folder\" "
            "(the macOS profile failure in scripts/shoot_playwright.py's header); judge the Firefox leg on the GitHub runner "
            "(.github/workflows/platform-shots.yml)")
# Runs a script file as __main__ after making `playwright` unimportable (the repo venv has none; this makes the scratch
# venv that does have it take the same path).
BLOCKED = """
import runpy, sys
for name in ("playwright", "playwright.sync_api"):
    sys.modules[name] = None
sys.argv = [{script!r}] + {args!r}
runpy.run_path({script!r}, run_name="__main__")
"""


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """A served directory with fonts/Probe.woff2 and fonts/Probe-Italic.woff2 (test_shoot.py's fonts)."""
    d = tmp_path_factory.mktemp("pwsite")
    (d / "fonts").mkdir()
    make_font(d / "fonts" / "Probe.woff2", italic=False)
    make_font(d / "fonts" / "Probe-Italic.woff2", italic=True)
    return d


@pytest.fixture(scope="module")
def firefox(site):
    """Skips loudly unless Playwright and its Firefox are installed and Firefox launches here: one real capture of an
    empty page through the shipped launcher. Any other launch fault is NOT a skip; the tests then fail on it."""
    try:
        shoot_playwright.require()
    except shoot_playwright.PlaywrightMissing:
        pytest.skip("SKIPPED, NOT PASSED: playwright is not installed in this interpreter (the repo venv has none on purpose): "
                    "pip install -r requirements-platform.txt && python -m playwright install firefox to run it here; "
                    "the skill's platform-shots workflow runs it on every OS")
    (site / "blank.html").write_text("<!doctype html><title>blank</title><p>blank</p>", encoding="utf-8")
    server, port = shoot.serve(site, seconds=120)
    try:
        cap = shoot_playwright.capture("firefox", f"http://127.0.0.1:{port}/blank.html", site / "blank.png", 600, 400, 1, 60)
    finally:
        server.shutdown()
    if cap.error and shoot_playwright.MAC_PROFILE_ERROR in cap.error:
        pytest.skip(MAC_SKIP)
    if cap.error and "Executable doesn't exist" in cap.error:
        pytest.skip(f"SKIPPED, NOT PASSED: Playwright is installed without its Firefox: {sys.executable} -m playwright install firefox")
    return cap


# ---------------------------------------------------------------- without Playwright: SKIPPED, NOT PASSED, never a pass or a failed shot

def test_capture_without_playwright_raises_the_skip_text_not_a_run_failure(monkeypatch, tmp_path):
    """capture() with `playwright` unimportable raises PlaywrightMissing carrying SKIP_TEXT, and that exception is neither
    a RuntimeError nor a ValueError, the two shoot.py's per-shot handler turns into a FAILED shot (exit 1). Runs in every
    venv. Mutations watched red on 2026-11-17: require() raising RuntimeError(SKIP_TEXT) instead (the isinstance check);
    the `then ... playwright install firefox` half dropped from SKIP_TEXT."""
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)
    with pytest.raises(Exception) as info:
        shoot_playwright.capture("firefox", "http://127.0.0.1:9/x.html", tmp_path / "x.png", 1280, 2400, 1, 30)
    exc = info.value
    assert isinstance(exc, shoot_playwright.PlaywrightMissing), repr(exc)
    assert not isinstance(exc, (RuntimeError, ValueError)), "a skip must not be catchable as a failed shot"
    assert str(exc) == shoot_playwright.SKIP_TEXT, str(exc)
    assert str(exc).startswith("SKIPPED, NOT PASSED") and "requirements-platform.txt" in str(exc) and "playwright install firefox" in str(exc)


def test_browser_firefox_without_playwright_exits_3_and_names_the_install(site, tmp_path):
    """The real shoot.py, run as __main__ with `playwright` unimportable, on a page that would pass in Chrome: exit 3,
    SKIPPED, NOT PASSED with requirements-platform.txt and `playwright install firefox`, no shot reported FAILED and no
    PNG written. This is the seam between shoot.py (work item A1) and the launcher (E1). Mutations watched red on
    2026-11-17: see the report of work item E1 (it depends on shoot.py's --browser dispatch)."""
    path = page(site, "skip", "<h1>Harbour Review</h1>")
    out = tmp_path / "shots"
    args = [str(out), "--serve", str(site), "--pages", path.lstrip("/"), "--widths", "1280", "--scales", "1", "--bands", "none",
            "--family", "Probe", "--font-url", "/fonts/Probe.woff2", "--browser", "firefox"]
    r = subprocess.run([sys.executable, "-c", BLOCKED.format(script=str(SHOOT), args=args)], capture_output=True, text=True, timeout=120)
    text = r.stdout + r.stderr
    assert r.returncode == shoot_playwright.EXIT_SKIPPED == 3, text
    assert "SKIPPED, NOT PASSED" in text and "requirements-platform.txt" in text and "playwright install firefox" in text, text
    assert "FAILED:" not in text, text
    assert not list(out.glob("*.png")), list(out.glob("*"))


def test_capture_refuses_webkit_and_unknown_browsers_before_importing_anything(monkeypatch, tmp_path):
    """WebKit is designed, not built (plan 2.5): capture("webkit") raises ValueError with the reason, and does so before
    it looks for Playwright, so the refusal reads the same on every machine. Mutation watched red on 2026-11-17: the
    webkit branch removed (the call reaches require() and raises PlaywrightMissing instead)."""
    monkeypatch.setitem(sys.modules, "playwright", None)
    with pytest.raises(ValueError, match="designed, not built: Playwright's WebKit is not Safari"):
        shoot_playwright.capture("webkit", "http://127.0.0.1:9/x.html", tmp_path / "x.png", 1280, 2400, 1, 30)
    with pytest.raises(ValueError, match="firefox and chrome only"):
        shoot_playwright.capture("safari", "http://127.0.0.1:9/x.html", tmp_path / "x.png", 1280, 2400, 1, 30)
    with pytest.raises(ValueError, match="needs the Chrome binary"):
        shoot_playwright.capture("chrome", "http://127.0.0.1:9/x.html", tmp_path / "x.png", 1280, 2400, 1, 30)


def test_launch_env_points_firefox_away_from_the_real_firefox_folder_on_macos_only(monkeypatch, tmp_path):
    """The macOS profile failure's workaround (header): on darwin Firefox is launched with CFFIXED_USER_HOME naming a
    folder of its own (FD_FIREFOX_HOME when set), with the rest of the environment kept; elsewhere the environment is
    inherited untouched (None). A test, not only a header line, because on this Mac the Firefox tests SKIP rather than
    fail when the workaround is gone, so they cannot catch its loss. Mutation watched red on 2026-11-17: launch_env()
    returning None on every platform."""
    home = tmp_path / "ffhome"
    monkeypatch.setenv("FD_FIREFOX_HOME", str(home))
    monkeypatch.setenv("FD_MARKER", "kept")
    monkeypatch.setattr(sys, "platform", "darwin")
    env = shoot_playwright.launch_env()
    assert env is not None and env["CFFIXED_USER_HOME"] == str(home) and env["FD_MARKER"] == "kept", env
    assert home.is_dir()
    monkeypatch.setattr(sys, "platform", "linux")
    assert shoot_playwright.launch_env() is None


# ---------------------------------------------------------------- with Playwright: the launcher

def test_playwright_without_its_firefox_is_a_failed_run_not_a_skip(site, tmp_path, monkeypatch):
    """A Playwright installed without its Firefox (PLAYWRIGHT_BROWSERS_PATH naming an empty folder) is returned as an
    error naming the missing executable, not raised as PlaywrightMissing: the operator asked for the leg and it did
    not run (plan 2.4), so shoot.py must fail it (exit 1), not skip it (exit 3). Needs Playwright, not its Firefox.
    Mutation watched red on 2026-11-17: capture() turning a launch error into PlaywrightMissing."""
    try:
        shoot_playwright.require()
    except shoot_playwright.PlaywrightMissing:
        pytest.skip("SKIPPED, NOT PASSED: playwright is not installed in this interpreter; this test needs the package only")
    empty = tmp_path / "no-browsers"
    empty.mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(empty))
    server, port = shoot.serve(site, seconds=60)
    try:
        cap = shoot_playwright.capture("firefox", f"http://127.0.0.1:{port}/blank.html", tmp_path / "x.png", 600, 400, 1, 60)
    finally:
        server.shutdown()
    assert cap.error and "Executable doesn't exist" in cap.error, cap
    assert not (tmp_path / "x.png").exists()


def test_firefox_capture_waits_for_a_sentinel_that_runs_after_networkidle(firefox, site, tmp_path):
    """The settle rule on an adversarial page: its own script keeps the main thread busy for 1.5 s after `load`, so the
    network is idle (and goto's networkidle has fired) before the sentinel runs. The moment capture() returns, with no
    wait of any kind in between, the server already holds the shot's beacon with font=loaded; the font response
    carried the shot's cookie (Firefox's jar took it from the page response); the PNG is the VIEWPORT at the scale
    (1280 x 600 CSS px at 1.25 = 1600 x 750 device px, on a page 3000 px tall); and ua names Firefox. Mutation watched
    red on 2026-11-17: full_page=True (the PNG is the whole document, 3901 px tall). SURVIVOR, recorded rather than
    hidden: removing the data-fd-shot wait leaves this test green. An ad-hoc run of the same busy page at 800 x 600 @1x
    did return before the beacon without the wait (2026-11-17), but in this test the screenshot, which needs the page's
    main thread, is queued behind the busy script and the sentinel, so the order is a race and no deterministic page
    was found. The wait stays (plan 2.4); what proves the beacon for a shot is shoot.py's beacon check, which fails the
    shot if it is missing. A third settle step (half a second with no request in flight) also survived its removal,
    even with the server taking 1.5 s per beacon, and was taken out of the launcher (header)."""
    from PIL import Image
    busy = ("<script>addEventListener('load', function () { setTimeout(function () { var t = Date.now(); "
            "while (Date.now() - t < 1500); }, 0); });</script>")
    path = page(site, "settle", "<h1>Harbour Review</h1><div style='height:3000px'></div>" + busy)
    server, port = shoot.serve(site, seconds=120, family="Probe")
    try:
        cap = shoot_playwright.capture("firefox", f"http://127.0.0.1:{port}{path}?shot=settle1", tmp_path / "s.png", 1280, 600, 1.25, 120)
        beacon = dict(server.beacons.get("settle1") or {})
        fonts = [(s, code) for s, p, q, code in server.responses if p == "/fonts/Probe.woff2"]
    finally:
        server.shutdown()
    assert cap.error is None, cap.error
    assert beacon.get("font") == "loaded" and int(beacon.get("probe") or 0) >= 1, (beacon, server.departures)
    assert fonts and all(s == "settle1" and code == 200 for s, code in fonts), fonts
    assert "Firefox/" in cap.ua, cap.ua
    assert Image.open(tmp_path / "s.png").size == (1600, 750)


def test_firefox_capture_does_not_wait_for_a_sentinel_a_page_does_not_have(firefox, site, tmp_path):
    """A page served with --no-sentinel has no sentinel script, so data-fd-shot never appears; the launcher must not
    sit out its whole sentinel wait for it (plan 2.4's "or the timeout" would cost every such shot its timeout less the
    reserve). With a 60 s timeout the capture returns in well under the 45 s the wait would take. Mutation watched red
    on 2026-11-17: SETTLED_JS reduced to the data-fd-shot test alone (the capture takes 45 s and prints the NOTE)."""
    path = page(site, "plain", "<h1>Harbour Review</h1>")
    server, port = shoot.serve(site, seconds=120, sentinel=False)
    try:
        t0 = time.monotonic()
        cap = shoot_playwright.capture("firefox", f"http://127.0.0.1:{port}{path}?shot=plain1", tmp_path / "p.png", 800, 400, 1, 60)
        took = time.monotonic() - t0
    finally:
        server.shutdown()
    assert cap.error is None and (tmp_path / "p.png").is_file(), cap
    assert took < 20, f"the capture of a page without a sentinel took {took:.1f}s"


def test_firefox_shot_is_verified_by_the_same_server_proofs(firefox, site, tmp_path):
    """shoot.shoot(..., browser="firefox") on the Probe page passes with the same records Chrome's shots are judged on
    (ua names Firefox, font loaded, at least one probed element, the font path served 200 to this shot), and on a page
    set in Georgia, with no --font-url so that only the sentinel can catch it, raises the same "rendered without"
    failure Chrome's shot raises. The macOS profile failure skips
    with MAC_SKIP (fixture `firefox`). Mutations watched red on 2026-11-17: Firefox launched with every cookie
    blocked (firefox_user_prefs network.cookie.cookieBehavior 2: the beacon carries no shot cookie, the server ignores
    it, and the Probe page fails, so the proofs run and are not bypassed for Firefox; stripping the Cookie header in a
    Playwright route did NOT turn it red, because Firefox adds cookies below the route, so that is not a way to test it);
    and, on a throwaway copy of the repo so work item A1's file was not touched, shoot.py's `if server.sentinel:` beacon
    block skipped when browser is firefox (the Georgia page then passes and pytest.raises fails)."""
    good = page(site, "ffgood", "<h1>Harbour Review</h1>")
    bad = page(site, "ffbad", "<p>Harbour Review</p>", faces=())
    server, port = shoot.serve(site, seconds=180, family="Probe")
    try:
        res = shoot.shoot(f"http://127.0.0.1:{port}{good}", tmp_path / "good.png", 1280, 1, height=800, server=server,
                          browser="firefox", require_family="Probe", font_url=["/fonts/Probe.woff2"])
        with pytest.raises(RuntimeError) as info:
            shoot.shoot(f"http://127.0.0.1:{port}{bad}", tmp_path / "bad.png", 1280, 1, height=800, server=server,
                        browser="firefox", require_family="Probe")  # no --font-url: the failure must be the sentinel's
    finally:
        server.shutdown()
    assert "Firefox/" in (res.get("ua") or ""), res
    assert res["font"] == "loaded" and int(res["probe"]["probe"]) >= 1, res
    assert (tmp_path / "good.png").is_file()
    msg = str(info.value)
    assert "rendered without 'Probe'" in msg and "sentinel font=missing" in msg and "not evidence" in msg, msg


@pytest.fixture(scope="module")
def playwright_chrome():
    """The Chrome binary shoot.py finds, when Playwright is installed; skips LOUDLY otherwise. Chrome through Playwright
    needs no `playwright install`: it launches that binary."""
    try:
        shoot_playwright.require()
    except shoot_playwright.PlaywrightMissing:
        pytest.skip("SKIPPED, NOT PASSED: playwright is not installed in this interpreter (the repo venv has none on purpose): "
                    "pip install -r requirements-platform.txt to run it here; the skill's platform-shots workflow runs it on every OS")
    try:
        return shoot.find_chrome()
    except FileNotFoundError as exc:
        pytest.skip(f"SKIPPED, NOT PASSED: {exc}")


@pytest.mark.parametrize("scale", [1, 1.25])
def test_playwright_chrome_lays_the_page_out_at_the_shots_width_and_passes_every_proof(site, tmp_path, playwright_chrome, scale):
    """shoot.py --launcher playwright: a page marked with one row, shot at 1280 x 900 at scale 1 and 1.25 through
    Playwright driving the Chrome shoot.py found. The shot passes the server proofs (the same records as the command
    line), the browser is Chrome (HeadlessChrome or Chrome in the user agent, not Firefox), the rows were measured on a
    page exactly 1280 px wide and 900 tall (Chrome's command line on a Windows runner measured 1264, platform-shots run
    44227825840), and the PNG is 1280 x 900 times the scale. Mutation watched red on 2026-11-17: shoot() calling
    launch_chrome() for every Chrome shot whatever the launcher (the meta's launcher reads the command-line path and the
    capture is not Playwright's)."""
    path = page(site, "pwchrome", "<h1 data-fd-row='pc-1'>Harbour Review</h1>")
    server, port = shoot.serve(site, 120, family="Probe")
    calls = []
    real = shoot.launch_playwright

    def spy(*a, **k):
        calls.append(a[0])
        return real(*a, **k)
    try:
        shoot.launch_playwright = spy
        png = tmp_path / f"pc-1280@{scale:g}x.png"
        res = shoot.shoot(f"http://127.0.0.1:{port}{path}", png, 1280, scale, height=900, server=server, chrome=playwright_chrome,
                          require_family="Probe", rows=True, launcher="playwright")
    finally:
        shoot.launch_playwright = real
        server.shutdown()
    assert calls == ["chrome"], calls
    assert "Chrome/" in res["ua"] and "Firefox" not in res["ua"], res["ua"]
    import json
    doc = json.loads(open(res["rows"], encoding="utf-8").read())
    assert doc["viewport_w"] == 1280 and doc["viewport_h"] == 900, doc
    from PIL import Image
    assert Image.open(png).size == (round(1280 * scale), round(900 * scale))


def test_capture_launches_chrome_with_its_sandbox_and_without_the_gpu(monkeypatch, tmp_path):
    """Playwright starts Chrome with --no-sandbox unless chromium_sandbox=True is passed, and adds no --disable-gpu, so
    the Playwright leg would draw on another raster path from the command-line launch (Impasse review of bd24d55, F001 and
    F002). A stand-in for Playwright records the launch's arguments and refuses to start, so this runs without Playwright:
    capture() returns that refusal as its error, and the launch carried the sandbox, the flag and the binary. Mutations
    watched red on 2026-11-17: chromium_sandbox=True removed; args=["--disable-gpu"] removed."""
    seen = {}

    class Chromium:
        def launch(self, **kw):
            seen.update(kw)
            raise RuntimeError("stand-in: not launching")

    class PW:
        chromium = Chromium()

        def stop(self):
            pass

    class Start:
        def start(self):
            return PW()
    monkeypatch.setattr(shoot_playwright, "require", lambda: (lambda: Start(), TimeoutError))
    cap = shoot_playwright.capture("chrome", "http://127.0.0.1:9/x.html", tmp_path / "x.png", 1280, 900, 1, 30, executable="/bin/chrome")
    assert cap.error and "stand-in" in cap.error, cap
    assert seen.get("chromium_sandbox") is True, seen
    assert "--disable-gpu" in (seen.get("args") or []), seen
    assert seen.get("executable_path") == "/bin/chrome", seen


def test_playwright_chrome_waits_for_a_late_stylesheet_before_judging_the_font(site, tmp_path, playwright_chrome, monkeypatch):
    """The page's @font-face lives in an external stylesheet the server answers 1.5 s late, as a site's site.css can be.
    The sentinel is injected at the top of <head>, before the <link>; started at DOMContentLoaded it asked for the family
    before any rule declared it, found nothing loading, and beaconed font=missing, and only then did Chrome fetch the font
    (platform-shots run 44236884579: every Chrome-through-Playwright leg failed /index.html that way, on Windows and
    Ubuntu, and so did this Mac). Started at `load`, which waits for stylesheets, the same page verifies. Mutation watched
    red on 2026-11-17: the sentinel started at DOMContentLoaded again (font=missing)."""
    (site / "late.css").write_text('@font-face { font-family: Probe; src: url(/fonts/Probe.woff2) format("woff2"); }\n'
                                   "h1 { font-family: Probe, serif; font-size: 48px; font-weight: 400; font-synthesis: none; }",
                                   encoding="utf-8")
    (site / "latecss.html").write_text("<!doctype html><html><head><meta charset='utf-8'><link rel='stylesheet' href='/late.css'>"
                                       "</head><body><h1>Harbour Review</h1></body></html>", encoding="utf-8")
    real = shoot.Handler.do_GET

    def slow(self):
        if self.path.startswith("/late.css"):
            time.sleep(1.5)
        return real(self)
    monkeypatch.setattr(shoot.Handler, "do_GET", slow)
    server, port = shoot.serve(site, 120, family="Probe")
    try:
        res = shoot.shoot(f"http://127.0.0.1:{port}/latecss.html", tmp_path / "late.png", 1280, 1, height=900, server=server,
                          chrome=playwright_chrome, require_family="Probe", font_url="/fonts/Probe.woff2", launcher="playwright")
    finally:
        server.shutdown()
    assert res["font"] == "loaded", res
