"""The Playwright launcher for shoot.py: takes one screenshot, in Playwright's Firefox or in an installed Chrome driven by
Playwright, of a page shoot.py's server is serving.

WHAT IT'S FOR: shoot.py proves a shot from the server's side (the tokenised page answered 200, the shot's cookie on every
later request, the sentinel's beacon, the element and italic probes, the missing-character probe), so the same proofs hold
for any browser pointed at the same URL. Chrome is launched through its command line; this module is the second launcher,
so a platform run can also show what Firefox's own text path draws (on Windows it drew grayscale where Chrome drew
subpixel; operator's measurement, 2026-11-17). shoot.py imports it only for `--browser firefox` and for
`--browser chrome --launcher playwright`, so shoot.py keeps a standard-library import block and a machine without
Playwright loses nothing but those legs.

Why Chrome too: Chrome's command line on a Windows runner lays the page out in a window 16 px narrower than its
--window-size (innerWidth 1264 for 1280, platform-shots run 44227825840) and then captures at 1280, so the row boxes the
sentinel measured belonged to a different layout from the PNG (text that wrapped in 1264 px moved every row under it).
Playwright sets the page's viewport itself, so the page is measured and captured at one width. `chrome` launches the
Chrome binary shoot.py found (`executable`), not Playwright's own Chromium build: the leg is meant to show Google Chrome.

    capture(browser, url, out_png, width, height, scale, timeout, dump_dom=False, executable=None) -> Capture(ua, dom_text, error)

`browser` is "firefox" or "chrome" (which needs `executable`). "webkit" is refused (designed, not built: docs/plan-platform-shots.md section 2.5). Playwright is
imported inside capture() (through require()); when it is not installed, PlaywrightMissing is raised carrying SKIP_TEXT,
and shoot.py turns that into exit 3, SKIPPED, NOT PASSED, never 0. A Playwright that is installed without its Firefox, and
every other fault (a launch that fails, a navigation timeout, a screenshot error), is returned as `error`, and shoot.py
fails the shot with it: the operator asked for the leg and it did not run.

Settle rule (Firefox has no twin of Chrome's --virtual-time-budget): page.goto(wait_until="networkidle"); then wait until
<html> carries data-fd-shot, which the sentinel writes last, after document.fonts.ready and the probes, in the same task
that sends its beacon (a page served with --no-sentinel has no sentinel script and is not waited for); screenshot the
viewport of `width` x `height` CSS px at `scale` (full_page=False, the same frame as Chrome's --window-size shot); with
dump_dom read page.content(); close. Everything shares one deadline of `timeout` seconds. If the sentinel has not
written data-fd-shot while SCREENSHOT_RESERVE seconds (at most a quarter of the timeout) are still left, a NOTE is
printed and the screenshot is still taken: shoot.py's beacon check then fails the shot, so the note is the reason and
the failure is the verdict.
The sentinel wait is for a page whose own script keeps the main thread busy after `load`, which reaches networkidle
before the sentinel has run: without the wait, one such capture returned before its beacon was sent (an ad-hoc run,
2026-11-17), but the test of it cannot make that happen every time (tests/test_shoot_playwright.py records the
survivor), so shoot.py's beacon check, not this wait, is what stands behind a shot. A third step, waiting until no
request had been in flight for half a second, was tried and removed: no page was found on which it changed the outcome,
even with the server taking 1.5 s to answer the beacon (the request is on the wire when the attribute appears, and the
server records it whether or not the browser is still open).

Exact guarantee: a returned Capture with error None means the browser Playwright launched loaded the URL, the page settled by the rule
above, and Playwright wrote out_png and raised nothing (item 1 of shoot.py's list, for Firefox). It says nothing about the
font: that is shoot.py's server proofs, which run on the same records as for Chrome. The browser is Playwright's own
Firefox build at the version playwright==1.64.1 bundles (requirements-platform.txt), not Mozilla's release and not a
reader's Firefox; `ua` records which.

macOS: "Could not find profile folder". Playwright 1.64.1's Firefox (Firefox 157) exits at launch with that line on the
author's Mac (macOS 27.2.1). Measured 2026-11-17: it is not the -profile directory Playwright passes (the Firefox binary
run by hand with an existing empty directory as -profile, or with XRE_PROFILE_PATH, fails the same way), not the agent's
command sandbox (it fails outside it too), and not $HOME (a fake HOME changes nothing). On that Mac a real Firefox is
installed and ~/Library/Application Support/Firefox, where it keeps its profiles, answers "Operation not permitted" even to
`ls` from a terminal: macOS's protection of another app's data. With CFFIXED_USER_HOME (CoreFoundation's override of the
home directory) naming an empty folder, the same launch succeeds and Firefox creates Library/Application Support/Firefox
inside it. The cause is therefore inferred to be Firefox's profile service failing to open the protected folder before it
looks at -profile; that is from these measurements, not traced in Firefox's source. So on macOS
the launch passes CFFIXED_USER_HOME=firefox_home(), one fixed folder under the system temporary directory, reused by every
run: macOS also refuses to delete the "Application Support" folder Firefox makes inside it (measured: shutil.rmtree fails
with "Permission denied"), so a temporary folder per launch would leave one undeletable folder behind per shot. A runner
with no Firefox data of its own needs none of this; it is applied on macOS only, and FD_FIREFOX_HOME overrides the folder.
If the launch still fails with the line, the error says so (MAC_PROFILE_ERROR) and the test that launches Firefox skips
with it; the leg is then judged on the GitHub runner.

Copyright 2026 John Knox. MIT licence.
"""
import collections
import os
import pathlib
import sys
import tempfile
import time

EXIT_SKIPPED = 3
SKIP_TEXT = ("SKIPPED, NOT PASSED: --browser firefox and --launcher playwright need playwright: .venv/bin/pip install -r "
             "requirements-platform.txt, then (for Firefox) .venv/bin/python3 -m playwright install firefox")
WEBKIT_REFUSAL = ("--browser webkit is designed, not built: Playwright's WebKit is not Safari (not Safari's version, its "
                  "font loading or its font-synthesis), on Linux and Windows it draws through a text stack no reader has, and "
                  "Safari itself is on the macOS runner, where safaridriver is the better future leg (plan section 2.5)")
MAC_PROFILE_ERROR = "Could not find profile folder"
SCREENSHOT_RESERVE = 30.0  # seconds of the deadline kept back from the sentinel wait (at most a quarter of it)
SETTLED_JS = ("() => !document.querySelector('script[data-fd-sentinel]') "
              "|| document.documentElement.hasAttribute('data-fd-shot')")

Capture = collections.namedtuple("Capture", "ua dom_text error")


class PlaywrightMissing(ImportError):
    """Playwright is not importable in this interpreter. Its first argument is SKIP_TEXT; shoot.py prints it and exits
    EXIT_SKIPPED. A subclass of ImportError, not of RuntimeError or ValueError, so the per-shot handler in shoot.py's
    main() (which turns those two into a failed shot) cannot catch it and report a skip as a failure."""


def require():
    """playwright.sync_api's sync_playwright and TimeoutError, or PlaywrightMissing with SKIP_TEXT. A module that is
    installed but raises ImportError on its own import (a missing dependency of it) is reported the same way, with the
    original error appended, because either way this interpreter cannot run the leg until the install is repaired."""
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        detail = "" if getattr(exc, "name", None) in ("playwright", "playwright.sync_api") else f" ({exc})"
        raise PlaywrightMissing(SKIP_TEXT + detail) from None
    return sync_playwright, PlaywrightTimeout


def firefox_home():
    """The folder CFFIXED_USER_HOME names on macOS (see the header): $FD_FIREFOX_HOME, else fd-firefox-home-<uid> under the
    system temporary directory. Created when missing; reused, never deleted."""
    path = os.environ.get("FD_FIREFOX_HOME") or os.path.join(tempfile.gettempdir(), f"fd-firefox-home-{getattr(os, 'getuid', lambda: 'user')()}")
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    return path


def launch_env():
    """The environment Firefox is launched with: this process's, plus CFFIXED_USER_HOME on macOS only (see the header).
    None elsewhere, which Playwright reads as "inherit"."""
    if sys.platform != "darwin":
        return None
    return {**os.environ, "CFFIXED_USER_HOME": firefox_home()}


def capture(browser, url, out_png, width, height, scale, timeout, dump_dom=False, executable=None):
    """One Playwright capture of `url` into `out_png`, settled by the header's rule. Returns Capture(ua, dom_text, error):
    `ua` is the page's navigator.userAgent (None if the page never loaded), `dom_text` the serialised DOM when `dump_dom`
    (else None), `error` None or a one-line description of what failed. Raises ValueError for a browser it does not launch
    and PlaywrightMissing when Playwright is not installed; it never raises for a fault in the run itself. `executable`
    is the Chrome binary for browser "chrome" (required there, ignored for Firefox)."""
    if browser == "webkit":
        raise ValueError(WEBKIT_REFUSAL)
    if browser not in ("firefox", "chrome"):
        raise ValueError(f"shoot_playwright launches firefox and chrome only, not {browser!r}")
    if browser == "chrome" and not executable:
        raise ValueError("browser chrome needs the Chrome binary (executable): shoot.py passes the one it found")
    name = "Firefox" if browser == "firefox" else "Chrome (through Playwright)"
    sync_playwright, PlaywrightTimeout = require()
    deadline = time.monotonic() + timeout
    ua = dom_text = None
    pw = br = ctx = None

    def ms_left():
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError(f"{name} took over {timeout}s for {url}")
        return max(1, int(left * 1000))

    try:
        pw = sync_playwright().start()
        if browser == "firefox":
            br = pw.firefox.launch(env=launch_env(), timeout=ms_left())
        else:
            br = pw.chromium.launch(executable_path=str(executable), timeout=ms_left())
        ctx = br.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=ms_left())
        reserve = min(SCREENSHOT_RESERVE, timeout / 4) * 1000  # kept back so a sentinel that never finishes still leaves a screenshot
        try:
            page.wait_for_function(SETTLED_JS, timeout=max(1, ms_left() - reserve))
        except PlaywrightTimeout:
            print(f"NOTE: shoot_playwright: the sentinel had not written data-fd-shot on {url} in its share of {timeout}s; "
                  f"the screenshot is taken and shoot.py's beacon check decides", file=sys.stderr)
        ua = page.evaluate("navigator.userAgent")
        page.screenshot(path=str(out_png), full_page=False, timeout=ms_left())
        if dump_dom:
            dom_text = page.content()
        return Capture(ua, dom_text, None)
    except Exception as exc:  # every fault of the run is the shot's failure, returned for shoot.py to raise (header)
        text = f"{type(exc).__name__}: {exc}".strip()
        if MAC_PROFILE_ERROR in text:
            text = (f"Firefox exited at launch with \"{MAC_PROFILE_ERROR}\" (the macOS profile failure in "
                    f"shoot_playwright.py's header; CFFIXED_USER_HOME was {(launch_env() or {}).get('CFFIXED_USER_HOME')!r}): " + text)
        return Capture(ua, dom_text, text[:2000])
    finally:
        for thing, how in ((ctx, "close"), (br, "close"), (pw, "stop")):
            if thing is not None:
                try:
                    getattr(thing, how)()
                except Exception as exc:  # a teardown fault after the outputs exist is not the page's; say so, do not fail
                    print(f"NOTE: shoot_playwright: {type(thing).__name__}.{how}() raised {type(exc).__name__}: {str(exc)[:200]}",
                          file=sys.stderr)
