#!/usr/bin/env python3
"""Screenshots pages in headless Chrome, with proof that each shot shows the page and the font it claims to.

WHAT IT'S FOR: the instrument the design-review loop reads. A reviewer judges a typeface on PNGs,
so a PNG that quietly shows a 404 page, or the fallback serif because the woff2 failed to load, is
worse than no evidence: it looks like evidence. This tool serves a directory from a self-terminating
http.server, shoots each page at the requested widths and device scales, and refuses to count a shot
unless it can prove what was rendered (the list below). It needs no process management: the server
lives on a daemon thread and a threading.Timer shuts it down, so an interrupted run leaves nothing
listening and nothing to kill.

    shoot.py OUT_DIR --serve DIR [--pages index.html ...] [--widths 500 1280 ...] [--scales 1 2]
             [--jobs N] [--root N] [--family NAME] [--font-url /fonts/X.woff2] [--probe SELECTOR]
             [--dump-dom] [--no-sentinel] [--height 2400] [--bands head:0:900,body:900:1800] [--query k=v ...]

What a counted shot proves (every item is checked; any failure is reported and the exit code is 1):
  1. Chrome exited 0 and the PNG exists. Any PNG of the same name is deleted before the run, so a
     file left by an earlier run can never pass as this run's result.
  2. The page URL carried a unique token (?shot=<id>) and the server answered THAT request 200.
     With --jobs above 1 several Chromes run at once; the token is what ties a response to a shot.
  3. A sentinel script, injected into every .html response, ran in the page after document.fonts.ready
     and sent a beacon GET to /__fd/beacon carrying the same token. The server records it per token,
     and only when the request also carries that shot's cookie (item 5; the derived <token>.inner of
     narrow.html's inner page counts for its outer page and the other way round), so a beacon from
     another process or another shot's Chrome is noted as a departure and ignored. TRUST ASSUMPTION,
     stated exactly: the page under test is the operator's own site. The sentinel runs in the page's
     own document, so the page's own script could read the token from the injected script or the
     URL and send a beacon of its choosing with the right cookie; nothing here defends against a page
     that lies about itself, and a shot of a page the operator does not control is not evidence
     (independent re-review, code-b F001).
  4. With --family: the beacon says font=loaded, which the sentinel sets only when
     document.fonts.check('16px "FAMILY"') is true AND a hidden span measures a different width in
     '"FAMILY", serif' than in 'serif'. The width comparison is the load-bearing half: check() also
     returns true for a face whose file failed to load (status "error") and for a family no
     @font-face declares, which is exactly how a fallback-serif screenshot passes a naive check.
  5. With --font-url: that path was served 200 to THIS shot's Chrome. Every .html response that
     carries a shot token sets a cookie (fd_shot=<id>, Path=/) in that Chrome's jar; each shot runs
     its own Chrome on a fresh --user-data-dir, so the jar holds exactly one shot's token, and every
     later request from that Chrome (fonts, stylesheets, images, the beacon) carries it. The server
     records (shot, path, query, status) per response, and the font check accepts only responses
     whose cookie is this shot's token (or a derived <token>.<suffix>, which narrow.html gives its
     inner page). A font 200 is therefore attributable to exactly one shot; another shot's 200 for
     the same path no longer covers a page that never requested it (independent review, C4).
     Limit: a font fetched before the page response arrived (nothing does this) or by a client
     that drops cookies would carry no token and would not count.
  6. With --family, the element probe: every VISIBLE element with text of its own whose computed
     font-family names the family first (or, with --probe SELECTOR, every visible element matching
     the selector) is checked: its first computed family is the family; document.fonts holds a
     loaded FontFace of that family whose style matches the element's (an italic or oblique element
     needs an italic/oblique face, an upright one an upright face) AND whose declared weight range
     covers the element's computed font-weight (a 400-only face does not serve a 700 element: Chrome
     would draw a synthesised bold, which document.fonts.check() alone does not see because it answers
     true when no face matches the request; re-review, code-b F004), and document.fonts.check() of
     the element's computed style/weight/size shorthand is true; an element marked
     data-fd-probe="italic" (the specimen's italic rows) has computed font-style italic; and every
     distinct non-space character of the element's own text measures a different advance in
     '"FAMILY", serif' than in 'serif' (canvas measureText at 100px). At least one such element must
     exist. VISIBLE means: Element.checkVisibility() with the opacity and visibility properties
     counted (so display:none, visibility:hidden, content-visibility and an opacity of 0 on the
     element or an ancestor all mean hidden; a browser without checkVisibility, older than Chrome
     105, sees only the element's own display and visibility), a box with width and height, and a box that touches the
     document (an element positioned beyond the left or top edge is not visible); what is NOT seen:
     an element inside the document but outside the captured viewport (a far right or far down
     position widens or lengthens the document, and it counts), a clip-path or an overflow:hidden
     ancestor that crops the text, and text the same colour as its background (re-review, code-b
     F003).
     Verdicts are written per element as data-fd-probe-result (face / fallback / not-italic /
     no-face / no-italic-face / no-weight-face / missing-chars), with data-fd-missing-chars on the
     element, and on <html> as data-fd-probe-count, data-fd-probe-bad, data-fd-probe-italic (loaded /
     missing / none: whether every italic element is served by a loaded italic face) and
     data-fd-missing-chars. The shot fails when the count is 0, any element is bad, or any character
     is missing.
     Exactly what 6 proves: the visible text in the family is drawn by a loaded face of the right
     style and weight range and every character it shows has a glyph whose advance differs from the
     fallback's. A character the face lacks falls back to serif in BOTH measurements, so it is always
     reported; the false alarm is a glyph whose advance equals the fallback glyph's to the sub-pixel
     at 100px. It does not read the pixels: a face that loads and draws badly still passes.
  7. The page's own self-test, when it has one (the concept pages): the sentinel reads data-fd-font,
     data-fd-rendered, data-fd-round and data-fd-error from <html> after the page's scripts ran and
     sends them in the beacon (the page's data-fd-font is preserved as data-fd-page-font before the
     sentinel writes its own; without --family the sentinel leaves a page's own data-fd-font in
     place). The shot fails on any data-fd-error, on data-fd-rendered="0", on a
     page that sets data-fd-round without data-fd-rendered, and on a page-reported font "missing".
     With --dump-dom these are read from the dumped DOM (the same Chrome invocation as the PNG),
     otherwise from the beacon. Not a proof the page drew the right thing: a count of glyphs.
The sentinel also writes data-fd-shot, data-fd-font (loaded / missing / none), data-fd-width-face
and data-fd-width-fallback onto <html>, so --dump-dom (which saves the DOM Chrome laid out as
<name>.dom.html beside the PNG, from the same Chrome invocation as the screenshot) carries the
same verdict in a form a test can read. --no-sentinel turns 3, 4, 6 and 7 off, for a page that
must be served byte-identical: the shot is then a picture, explicitly not evidence ("verified" is
reported, but only items 1, 2 and 5 were checked).

Serving: `--serve DIR` is served at /, and this scripts folder at /__fd/ (narrow.html, opsz.html).
Every request path is percent-decoded, joined to its root, resolved through symlinks, and must land
strictly inside that root (DIR resolved, or this folder resolved); anything else, including
/__fd//etc/passwd, %2e%2e segments, a NUL byte and a symlink inside the tree that points out of it,
is answered 404 and noted at the end of the run (independent review, C1). Under /__fd/ only files
are served, never a directory listing. Consequence: a font symlinked into DIR from elsewhere is
refused; copy the file in.

Exact guarantee: a PNG here is what Chrome's headless renderer drew with this machine's text stack
(CoreText on macOS, FreeType on Linux). It says nothing about Safari, Firefox, Windows or Android,
and nothing about hinting on a display this machine does not have. Chrome headless lays out at no
less than 500 CSS px wide, so narrower widths are refused: for a phone reading use
scripts/narrow.html, an iframe wrapper that reports the inner page's overflow at any width, after
checking that the inner page was served 200, that none of its faces failed and (with ?family=)
that a face of the family loaded; narrow_verdict() below reads its dumped DOM.

`?root=N` on an .html path injects `html{font-size:N%}`, to see rem-sized type at a reader's
enlarged default. `--query k=v` appends a query parameter to every page URL (a concept page reads
?face=<id> and ?text=...). Files are named <page>[-root<N>][-<k>-<v>]-<width>@<scale>x.png, with
band crops <...>-<band>.png cut with Pillow.

Chrome is found through $CHROME, then the macOS application path, then the Windows install paths
(Program Files, Program Files (x86) and the user's LocalAppData, read from the environment; they name
nothing on another OS), then google-chrome, google-chrome-stable, chromium and chromium-browser on PATH.
The skill supports macOS and Linux, and Windows only through WSL; inside WSL install Chrome or Chromium in the Linux
distribution: the Windows variables are normally unset there and /mnt/c paths are not candidates, so the Windows paths
are not searched from WSL (they exist for a native Python that sets those variables, which is not a supported setup). Copyright 2026 John Knox. MIT licence.
Generalised from the Bract review tool (hopsafari.com, 2026-11-15).
"""
import argparse
import functools
import html as html_mod
import http.server
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
MIN_WIDTH = 500  # Chrome headless's minimum layout width; see narrow.html for narrower readings
DEFAULT_HEIGHT = 2400
DEFAULT_BANDS = "head:0:900,body:900:1800"
CHROME_MAC_APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_WINDOWS_ENV = ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData")  # environment variables whose value holds Google/Chrome/Application under it
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
BEACON_PATH = "/__fd/beacon"
TOOL_PREFIX = "/__fd/"  # narrow.html and opsz.html are served from this folder under this prefix
BEACON_WAIT = 3.0  # seconds to wait for a beacon after Chrome exits (it is a loopback GET)
SHOT_COOKIE = "fd_shot"  # set by every .html response carrying ?shot=; ties this Chrome's later requests to the shot
SHOT_TOKEN_OK = re.compile(r"^[A-Za-z0-9._-]{1,80}$")  # what may go into the Set-Cookie header
# Returned by translate_path for a request that escapes its root. It lies under os.devnull, which is
# not a directory, so no such path can exist; SimpleHTTPRequestHandler.send_head answers 404 for a
# path ending in "/" that is not a directory, and never opens it.
REFUSED = os.path.join(os.devnull, "refused") + "/"

# The sentinel. %(shot)s, %(family)s and %(probe)s are substituted as JSON literals with "</" written
# "<\/" (js_literal), so a --family or --probe value holding "</script>" cannot end the script element
# (re-review, code-b F002). It waits for
# document.fonts.ready (after asking for the family explicitly, so a declared but unused face is
# loaded too), measures a probe span in the family and in the fallback, probes every visible element
# set in the family (item 6 of the header), reads the page's own self-test attributes (item 7),
# writes the verdicts on <html> and sends them to the server as a GET recorded against the shot token.
SENTINEL = """<script data-fd-sentinel>
(function () {
  var shot = %(shot)s, fam = %(family)s, sel = %(probe)s;
  function q(s) { return "\\"" + String(s).replace(/"/g, "") + "\\""; }
  function first(ff) { return String(ff || "").split(",")[0].trim().replace(/^["']|["']$/g, "").toLowerCase(); }
  function ownText(el) { var t = ""; for (var n = el.firstChild; n; n = n.nextSibling) if (n.nodeType === 3) t += n.nodeValue; return t; }
  function visible(el) {
    var r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    if (!(r.width > 0 && r.height > 0) || cs.visibility === "hidden" || cs.display === "none") return false;
    // checkVisibility (Chrome 105+; headless new has it) sees display:none and content-visibility on any ancestor
    // and, with these options, visibility:hidden and opacity:0 on the element or an ancestor; it is the one
    // opacity test, on purpose: a second test of the element's own opacity could be deleted unnoticed behind it
    try { if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return false; } catch (e) {}
    // off the document: beyond the left or top edge, or beyond the laid-out width and height (left:-9999px, the usual hiding)
    var h = document.documentElement, dw = Math.max(h.scrollWidth, h.clientWidth), dh = Math.max(h.scrollHeight, h.clientHeight);
    var x = r.left + window.scrollX, y = r.top + window.scrollY;
    return x + r.width > 0 && y + r.height > 0 && x < dw && y < dh;
  }
  function weightCovers(f, w) {
    // a FontFace.weight is "400", "400 700", "normal" or "bold"; the element's computed weight is a number string
    var parts = String(f.weight || "normal").replace("normal", "400").replace("bold", "700").trim().split(/\\s+/).map(parseFloat);
    if (parts.some(isNaN)) return true;  // an unreadable descriptor is not held against the face
    var lo = parts[0], hi = parts.length > 1 ? parts[1] : parts[0], cw = parseFloat(w);
    return isNaN(cw) || (cw >= Math.min(lo, hi) && cw <= Math.max(lo, hi));
  }
  function faces(italic, weight) {
    var out = [];
    try {
      document.fonts.forEach(function (f) {
        if (f.status === "loaded" && first(f.family) === fam.toLowerCase() && (/italic|oblique/.test(f.style) === italic)
            && (weight === undefined || weightCovers(f, weight))) out.push(f);
      });
    } catch (e) {}
    return out;
  }
  var canvas = null;
  function missingChars(text, cs) {
    // every distinct non-space character whose advance is identical in the face and in the fallback:
    // a character the face lacks is drawn by the fallback in both measurements, so it always lands here
    canvas = canvas || document.createElement("canvas");
    var ctx = canvas.getContext("2d"), out = [], seen = {}, chars = Array.from(text), pre = cs.fontStyle + " " + cs.fontWeight + " 100px ";
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (seen[ch] || /\\s/.test(ch)) continue;
      seen[ch] = 1;
      ctx.font = pre + "serif"; var wb = ctx.measureText(ch).width;
      ctx.font = pre + q(fam) + ", serif"; var wf = ctx.measureText(ch).width;
      if (wf === wb) out.push(ch);
    }
    return out;
  }
  function go() {
    var h = document.documentElement, state = "none", wf = 0, wb = 0;
    var pagefont = h.getAttribute("data-fd-font");  // the page's own self-test, before this script writes the attribute
    if (pagefont !== null) h.setAttribute("data-fd-page-font", pagefont);
    if (fam) {
      var probe = document.createElement("span");
      probe.style.cssText = "position:absolute;left:-9999px;top:0;visibility:hidden;white-space:nowrap;font-size:48px;font-weight:400;font-style:normal";
      probe.textContent = "Handgloves Hamburgefonstiv 0123456789";
      (document.body || h).appendChild(probe);
      probe.style.fontFamily = "serif"; wb = probe.getBoundingClientRect().width;
      probe.style.fontFamily = q(fam) + ", serif"; wf = probe.getBoundingClientRect().width;
      var checked = false;
      try { checked = document.fonts.check("16px " + q(fam)); } catch (e) { checked = false; }
      state = (checked && wf !== wb) ? "loaded" : "missing";
      probe.parentNode.removeChild(probe);
    }
    var count = 0, bad = 0, italics = 0, italicsOk = 0, firstBad = "", missing = {}, perr = "";
    if (fam) {
      var els = [];
      try { els = sel ? document.querySelectorAll(sel) : document.getElementsByTagName("*"); } catch (e) { perr = "bad selector: " + sel; }
      for (var i = 0; i < els.length; i++) {
        var el = els[i], tag = el.tagName.toLowerCase();
        if (tag === "script" || tag === "style" || tag === "html" || tag === "head" || tag === "title") continue;
        var cs, text = ownText(el);
        try { cs = getComputedStyle(el); } catch (e) { continue; }
        if (!/\\S/.test(text) || !visible(el)) continue;
        if (!sel && first(cs.fontFamily) !== fam.toLowerCase()) continue;
        count++;
        var italic = /italic|oblique/.test(cs.fontStyle), verdict = "face", ok = false;
        try { ok = document.fonts.check(cs.fontStyle + " " + cs.fontWeight + " " + cs.fontSize + " " + q(fam)); } catch (e) { ok = false; }
        if (first(cs.fontFamily) !== fam.toLowerCase()) verdict = "fallback";
        else if (el.getAttribute("data-fd-probe") === "italic" && !italic) verdict = "not-italic";
        else if (!faces(italic).length || !ok) verdict = italic ? "no-italic-face" : "no-face";
        else if (!faces(italic, cs.fontWeight).length) verdict = "no-weight-face";
        else {
          var miss = [];
          try { miss = missingChars(text, cs); } catch (e) { perr = "measureText failed: " + e; }
          if (miss.length) {
            verdict = "missing-chars"; el.setAttribute("data-fd-missing-chars", miss.join(""));
            for (var k = 0; k < miss.length; k++) missing[miss[k]] = 1;
          }
        }
        el.setAttribute("data-fd-probe-result", verdict);
        if (italic) { italics++; if (verdict === "face") italicsOk++; }
        if (verdict !== "face") { bad++; if (!firstBad) firstBad = tag + (el.className ? "." + String(el.className).split(/\\s+/)[0] : "") + ":" + verdict; }
      }
    }
    var italicState = italics === 0 ? "none" : (italicsOk === italics ? "loaded" : "missing");
    var missingList = Object.keys(missing).sort().join("");
    h.setAttribute("data-fd-shot", shot);
    if (fam || pagefont === null) h.setAttribute("data-fd-font", state);  // without a family, a page's own verdict is left in place
    h.setAttribute("data-fd-width-face", String(wf)); h.setAttribute("data-fd-width-fallback", String(wb));
    h.setAttribute("data-fd-probe-count", String(count)); h.setAttribute("data-fd-probe-bad", String(bad));
    h.setAttribute("data-fd-probe-italic", italicState); h.setAttribute("data-fd-missing-chars", missingList);
    if (perr) h.setAttribute("data-fd-probe-error", perr);
    var url = "/__fd/beacon?shot=" + encodeURIComponent(shot) + "&font=" + state + "&wf=" + wf + "&wb=" + wb +
      "&probe=" + count + "&bad=" + bad + "&italic=" + italicState + "&pfail=" + encodeURIComponent(firstBad.slice(0, 120)) +
      "&missing=" + encodeURIComponent(missingList.slice(0, 60));
    function add(k, v) { if (v !== null) url += "&" + k + "=" + encodeURIComponent(String(v).slice(0, 200)); }
    add("pagefont", pagefont); add("rendered", h.getAttribute("data-fd-rendered")); add("round", h.getAttribute("data-fd-round"));
    add("error", h.getAttribute("data-fd-error")); if (perr) add("perr", perr);
    var img = new Image();
    img.src = url;
  }
  function start() {
    var ready = Promise.resolve();
    if (document.fonts) {
      if (fam && document.fonts.load) {
        try { ready = document.fonts.load("16px " + q(fam)); } catch (e) { ready = Promise.resolve(); }
      }
      ready = ready.then(function () { return document.fonts.ready; }, function () { return document.fonts.ready; });
    }
    ready.then(go, go);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
</script>
"""


def chrome_candidates():
    """The fixed install paths to try, in order: the macOS app, then each Windows install location whose
    environment variable is set. Read at call time, so a caller (or a test) can change the environment."""
    out = [CHROME_MAC_APP]
    for var in CHROME_WINDOWS_ENV:
        base = os.environ.get(var)
        if base:
            out.append(str(pathlib.Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"))
    return out


def runnable(path):
    """True for a file the current user may execute. A file that exists but is not executable (a downloaded app whose bit
    was lost, a stray text file named chrome) used to pass `is_file()` and then fail at launch with a traceback."""
    p = pathlib.Path(path)
    return p.is_file() and os.access(p, os.X_OK)


def find_chrome():
    """The Chrome binary: $CHROME, then the fixed install paths (macOS app, Windows locations), then the
    usual Linux names on PATH. Raises FileNotFoundError naming $CHROME when none is found, so the caller can
    say so plainly."""
    env = os.environ.get("CHROME")
    if env:
        if runnable(env):
            return env
        if pathlib.Path(env).is_file():
            raise FileNotFoundError(f"$CHROME is set to {env!r}, which is a file but is not executable (chmod +x it)")
        raise FileNotFoundError(f"$CHROME is set to {env!r} but no file is there")
    candidates = chrome_candidates()
    for cand in candidates:
        if runnable(cand):
            return cand
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    raise FileNotFoundError("no Chrome found: set $CHROME to the browser binary (looked at "
                            + ", ".join(candidates + CHROME_NAMES) + ")")


def contained(root, rel):
    """The file `rel` (a percent-decoded request path, relative or not) resolved under `root`, or None
    when the resolved path is not strictly inside root's resolved path. Resolution follows symlinks,
    so a link inside the tree that points outside is refused; `..` segments and a leading `/` are
    refused by the same containment test; a NUL byte or a symlink loop raises inside resolve() and
    is refused too. The root itself (a directory listing) is not inside the root."""
    try:
        base = pathlib.Path(root).resolve()
        cand = (base / rel).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if cand == base or not cand.is_relative_to(base):
        return None
    return cand


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves `directory` at /, this scripts folder at /__fd/ (narrow.html, opsz.html), and records
    (shot, path, query, status) of every response on the server, where shot is the fd_shot cookie
    the request carried ("" when none). Into every .html body it injects the sentinel (unless the
    server has sentinel=False) and, for ?root=N, html{font-size:N%}; an .html response carrying
    ?shot=<token> also sets the fd_shot cookie to that token. A request path that escapes its root
    (see the module header) is answered 404 and noted in server.departures. The beacon endpoint
    records its query per shot token and answers 204."""

    def translate_path(self, path):
        clean = urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0])
        if clean.startswith(TOOL_PREFIX) and clean != BEACON_PATH:
            target = contained(HERE, clean[len(TOOL_PREFIX):])
            if target is None or target.is_dir():
                return REFUSED
            return str(target)
        local = super().translate_path(path)  # unquotes, normalises, drops '..' segments, keeps a trailing slash
        try:
            resolved = pathlib.Path(local).resolve()
            root = pathlib.Path(self.directory).resolve()
        except (OSError, RuntimeError, ValueError):
            return REFUSED
        if resolved != root and not resolved.is_relative_to(root):
            return REFUSED
        return local

    def shot_token(self):
        """The fd_shot cookie this request carried, or ""."""
        headers = getattr(self, "headers", None)
        raw = headers.get("Cookie", "") if headers else ""
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == SHOT_COOKIE:
                return v.strip()
        return ""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)  # an empty data-fd-error is still an error
        if parsed.path == BEACON_PATH:
            shot = (query.get("shot") or [""])[0]
            record = {k: (v[0] if v else "") for k, v in query.items()}
            cookie = self.shot_token()
            if not shot:
                self.server.departures.append(f"beacon without a shot token: {self.path[:200]!r}")
            elif not same_shot(cookie, shot):
                # the beacon must come from the Chrome that was served this shot's page (its cookie, item 5 of the
                # header); one from elsewhere is ignored, not recorded (re-review, code-b F001)
                self.server.departures.append(f"beacon for shot {shot[:80]!r} ignored: the request carried the cookie "
                                              f"{cookie[:80]!r}, not that shot's token")
            else:
                self.server.beacons[shot] = record
            self.send_response(204)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        local = self.translate_path(self.path)
        if local == REFUSED:
            self.server.departures.append(f"refused a request path outside the served tree: {self.path[:200]!r}")
            self.send_error(404, "Not Found")
            return
        target = pathlib.Path(local)
        if target.suffix == ".html" and target.is_file():
            html = target.read_text(encoding="utf-8")
            inject = ""
            if "root" in query:
                inject += f"<style data-fd-root>html{{font-size:{int(query['root'][0])}%}}</style>"
            shot = (query.get("shot") or [""])[0]
            if self.server.sentinel:
                inject += sentinel_for(shot, self.server.family, self.server.probe)
            body = inject_head(html, inject).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if shot and SHOT_TOKEN_OK.match(shot):
                self.send_header("Set-Cookie", f"{SHOT_COOKIE}={shot}; Path=/; SameSite=Lax")
            elif shot:
                self.server.departures.append(f"shot token is not [A-Za-z0-9._-]: {shot[:80]!r}; this shot's font requests cannot be attributed")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_request(self, code="-", size="-"):
        parsed = urllib.parse.urlparse(self.path)
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = -1
        self.server.responses.append((self.shot_token(), parsed.path, parsed.query, status))

    def log_message(self, *a):
        pass


def js_literal(value):
    """`value` as a JavaScript string literal (or null) safe inside a <script> element: JSON, with every
    "</" written as "<\\/" so the HTML parser cannot read a "</script>" inside it as the end of the
    script (re-review, code-b F002). JSON's own escaping already covers quotes, backslashes, control
    characters and U+2028/2029 (ensure_ascii)."""
    return json.dumps(value).replace("</", "<\\/")


def sentinel_for(shot, family, probe):
    """The sentinel script for one shot, with the three values embedded as JavaScript literals."""
    return SENTINEL % {"shot": js_literal(shot), "family": js_literal(family), "probe": js_literal(probe)}


def same_shot(cookie, shot):
    """Whether a request's fd_shot cookie belongs to `shot`: the same token, or one derived from the same
    base token (narrow.html gives its inner page <token>.inner, and whichever of the two responses lands
    last sets the cookie the outer page's beacon then carries)."""
    return bool(cookie) and cookie.split(".", 1)[0] == shot.split(".", 1)[0]


def inject_head(html, snippet):
    """Puts `snippet` right after <head ...> when the document has one, else at the very start (a
    template that opens with <title> has no <head>; the parser moves leading <style>/<script> into
    the head it creates). Nothing is injected for an empty snippet."""
    if not snippet:
        return html
    m = re.search(r"<head\b[^>]*>", html, re.IGNORECASE)
    if m:
        return html[:m.end()] + snippet + html[m.end():]
    return snippet + html


def serve(directory, seconds=600, family=None, sentinel=True, probe=None):
    """Starts the server for `directory` on a free loopback port; returns (server, port). It shuts
    itself down after `seconds` or on server.shutdown(). `family` is what the sentinel checks;
    `probe` is a CSS selector naming the elements item 6 checks (default: every visible element
    whose computed font-family names the family first)."""
    directory = pathlib.Path(directory).resolve()
    if not directory.is_dir():
        raise NotADirectoryError(f"--serve {directory} is not a directory")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = functools.partial(Handler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.responses = []  # (shot cookie, path, query, status) of every response, in order; list.append is atomic in CPython
    server.beacons = {}  # shot token -> the beacon's query fields
    server.departures = []  # anything unexpected the handler saw, printed at the end rather than swallowed
    server.family = family
    server.sentinel = sentinel
    server.probe = probe
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timer = threading.Timer(seconds, server.shutdown)
    timer.daemon = True
    timer.start()
    return server, port


def with_query(url, params):
    """`url` with the (key, value) pairs or dict `params` added to its query string (values urlencoded)."""
    items = params.items() if isinstance(params, dict) else params
    parts = urllib.parse.urlsplit(url)
    q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True) + [(k, str(v)) for k, v in items]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(q), parts.fragment))


def html_attrs(dom_html):
    """The attributes of the <html ...> start tag of a dumped DOM as a dict (values HTML-unescaped),
    or {} when there is no <html> tag. Chrome's --dump-dom serialises every attribute double-quoted."""
    m = re.search(r"<html\b[^>]*>", dom_html, re.IGNORECASE)
    if not m:
        return {}
    return {k: html_mod.unescape(v) for k, v in re.findall(r'([A-Za-z0-9_:.-]+)="([^"]*)"', m.group(0))}


def narrow_verdict(dom_html):
    """(overflow, stage) read from a dumped narrow.html DOM: the values of data-fd-overflow ("true",
    "false" or "error") and data-fd-narrow-stage ("load" or "fonts") on <html>, each None when absent.
    A page fits only when the pair is ("false", "fonts"): "fonts" is the reading taken at the first
    timer poll after the inner document's fonts settled and its HTTP status arrived, "load" the
    earlier one taken before web fonts applied, which can miss a title that overflows only in the
    custom face. narrow.html writes "error" instead of a reading when the inner page was not served
    200, a face in it failed to load, or (with ?family=) no loaded face of the family is there
    (re-review, code-b F005), with the reason in its #verdict text and the facts in
    data-fd-narrow-inner-http, data-fd-narrow-fonts-failed and data-fd-narrow-family. Anything other
    than ("false", "fonts") is a failed check, not a pass with a caveat."""
    attrs = html_attrs(dom_html)
    return attrs.get("data-fd-overflow"), attrs.get("data-fd-narrow-stage")


def self_test_failures(beacon=None, dom_html=None):
    """Item 7: what the page's own self-test attributes say, read from the dumped DOM when `dom_html`
    is given (the same Chrome invocation as the PNG), else from the beacon's copy of them. Returns a
    list of failure sentences, empty when nothing is wrong."""
    if dom_html is not None:
        a = html_attrs(dom_html)
        # the page's own data-fd-font is preserved as data-fd-page-font when the sentinel overwrites it, and a
        # page whose probe ran after the sentinel wrote data-fd-font itself: "missing" in either fails
        fonts = [a.get("data-fd-page-font"), a.get("data-fd-font")]
        fields = {"error": a.get("data-fd-error"), "rendered": a.get("data-fd-rendered"), "round": a.get("data-fd-round"),
                  "pagefont": "missing" if "missing" in fonts else fonts[0]}
        src = "the dumped DOM"
    else:
        b = beacon or {}
        fields = {k: b.get(k) for k in ("error", "rendered", "round", "pagefont")}
        src = "the beacon"
    out = []
    if fields["error"] is not None:
        out.append(f"the page reported a script error (data-fd-error={fields['error'][:200]!r}, from {src})")
    if fields["round"] is not None and fields["rendered"] is None:
        out.append(f"the page sets data-fd-round={fields['round']!r} but no data-fd-rendered: its self-test did not finish (from {src})")
    if fields["rendered"] is not None and fields["rendered"].strip() in ("", "0"):
        out.append(f"the page rendered 0 glyphs (data-fd-rendered={fields['rendered']!r}, from {src})")
    if fields["pagefont"] == "missing":
        out.append(f"the page's own probe reports its comparison font missing (data-fd-font=missing, from {src})")
    return out


def shoot(url, out_png, width, scale, height=DEFAULT_HEIGHT, profile_root=None, timeout=300, server=None,
          shot_id=None, require_family=None, font_url=None, dump_dom=False, chrome=None):
    """One headless Chrome capture, verified. Returns a dict (png, dom, shot, font, width_face,
    width_fallback, font_status, probe). Raises RuntimeError naming the first failed proof; see the
    module header for the list. `server` is the one from serve(); without it only the Chrome exit
    and the PNG are checked, and the function says so in the result ("verified": False)."""
    if width < MIN_WIDTH:
        raise ValueError(f"width {width} is below Chrome headless's {MIN_WIDTH}px minimum layout width; "
                         f"for a narrower reading shoot scripts/narrow.html with ?url=<page>&width={width}")
    chrome = chrome or find_chrome()
    shot_id = shot_id or uuid.uuid4().hex[:12]
    if not SHOT_TOKEN_OK.match(shot_id):
        raise ValueError(f"shot id {shot_id!r} must be 1-80 characters of [A-Za-z0-9._-]: it travels in a cookie")
    target = pathlib.Path(out_png)
    target.unlink(missing_ok=True)  # never accept a file left by an earlier run
    dom_path = target.with_suffix(".dom.html") if dump_dom else None
    if dom_path is not None:
        dom_path.unlink(missing_ok=True)
    url = with_query(url, {"shot": shot_id})
    first = len(server.responses) if server is not None else 0
    with tempfile.TemporaryDirectory(dir=profile_root) as profile:
        cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
               f"--user-data-dir={profile}", f"--window-size={width},{height}",
               f"--force-device-scale-factor={scale}", "--virtual-time-budget=5000",
               f"--screenshot={target}"]
        if dump_dom:
            cmd.append("--dump-dom")
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Chrome took over {timeout}s for {url} at {width}@{scale}x") from None
        except OSError as exc:  # not executable, wrong architecture, deleted since discovery
            raise RuntimeError(f"Chrome could not be started ({type(exc).__name__}: {exc}): {chrome}; set $CHROME to a working browser binary") from None
    if r.returncode != 0 or not target.is_file():
        raise RuntimeError(f"Chrome exited {r.returncode} and wrote {'a' if target.is_file() else 'no'} screenshot "
                           f"for {url} at {width}@{scale}x: {r.stderr[-400:]}")
    dom_text = None
    if dump_dom:
        if not r.stdout.strip():
            raise RuntimeError(f"--dump-dom produced no DOM for {url}; the screenshot is kept but the run is not verified")
        dom_text = r.stdout
        dom_path.write_text(dom_text, encoding="utf-8")
    result = {"png": str(target), "dom": str(dom_path) if dom_path else None, "shot": shot_id,
              "font": None, "width_face": None, "width_fallback": None, "font_status": None, "probe": None,
              "verified": server is not None}
    if server is None:
        return result
    page = urllib.parse.urlparse(url).path
    served = server.responses[first:]
    page_codes = [code for s, p, q, code in served if p == page and f"shot={shot_id}" in q.split("&")]
    if 200 not in page_codes:
        raise RuntimeError(f"{page}?shot={shot_id} was not served 200 during the shot "
                           f"({'no request' if not page_codes else page_codes}); the screenshot is not evidence")
    if font_url:
        font_path = urllib.parse.urlparse(font_url).path
        mine = [code for s, p, q, code in served if p == font_path and (s == shot_id or s.startswith(shot_id + "."))]
        result["font_status"] = mine
        if 200 not in mine:
            others = [code for s, p, q, code in served if p == font_path and s != shot_id and not s.startswith(shot_id + ".")]
            raise RuntimeError(f"{font_path} was not served 200 to the shot of {page} (shot {shot_id}: "
                               f"{'no request carried its token' if not mine else mine}"
                               f"{'; ' + str(len(others)) + ' response(s) for that path belonged to other shots' if others else ''}); "
                               f"the screenshot is not evidence of the font")
    if server.sentinel:
        deadline = time.monotonic() + BEACON_WAIT
        while shot_id not in server.beacons and time.monotonic() < deadline:
            time.sleep(0.05)
        beacon = server.beacons.get(shot_id)
        if beacon is None:
            raise RuntimeError(f"no sentinel beacon arrived for {page}?shot={shot_id}: the injected script did not run "
                               f"(a page that is not HTML, a script error before document.fonts.ready, or Chrome exited first)")
        result["font"] = beacon.get("font")
        result["width_face"] = beacon.get("wf")
        result["width_fallback"] = beacon.get("wb")
        result["probe"] = {k: beacon.get(k) for k in ("probe", "bad", "italic", "pfail", "missing")}
        failures = self_test_failures(beacon, dom_text)
        if failures:
            raise RuntimeError(f"{page}?shot={shot_id}: " + "; ".join(failures) + "; the screenshot is not evidence")
        if require_family:
            if beacon.get("font") != "loaded" or beacon.get("wf") == beacon.get("wb"):
                raise RuntimeError(f"{page}?shot={shot_id} rendered without {require_family!r}: sentinel font={beacon.get('font')}, "
                                   f"probe width {beacon.get('wf')} in the face vs {beacon.get('wb')} in the fallback; "
                                   f"the screenshot shows a fallback face and is not evidence")
            if beacon.get("perr"):
                raise RuntimeError(f"{page}?shot={shot_id}: the element probe did not run: {beacon['perr'][:200]}")
            count, bad = int(beacon.get("probe") or 0), int(beacon.get("bad") or 0)
            if count < 1:
                raise RuntimeError(f"{page}?shot={shot_id}: no visible element with text is set in {require_family!r} "
                                   f"(the face loaded but nothing on the page shows it); name the elements with --probe SELECTOR "
                                   f"if the family is set another way")
            if bad:
                detail = beacon.get("pfail", "")
                missing = beacon.get("missing", "")
                raise RuntimeError(f"{page}?shot={shot_id}: {bad} of {count} probed element(s) are not drawn by {require_family!r} "
                                   f"(first: {detail})" + (f"; characters the face lacks, drawn in the fallback: {missing!r}" if missing else "")
                                   + "; the screenshot is not evidence")
            if beacon.get("italic") == "missing":
                raise RuntimeError(f"{page}?shot={shot_id}: an italic element is not served by an italic FontFace of {require_family!r}")
    return result


def parse_bands(spec):
    """'head:0:900,body:900:1800' -> {'head': (0, 900), 'body': (900, 1800)}; 'none' -> {}."""
    if not spec or spec.lower() == "none":
        return {}
    bands = {}
    for part in spec.split(","):
        name, top, bottom = part.split(":")
        top, bottom = int(top), int(bottom)
        if bottom <= top:
            raise ValueError(f"band {name}: bottom {bottom} is not below top {top}")
        bands[name] = (top, bottom)
    return bands


def crop_bands(png, scale, bands):
    """Writes <png>-<band>.png crops of the CSS-px bands (scaled by the device scale)."""
    out = []
    if not bands:
        return out
    try:
        from PIL import Image
    except ImportError as exc:
        sys.exit(f"shoot.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
                 "Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/shoot.py ...")
    with Image.open(png) as im:
        for name, (top, bottom) in bands.items():
            box = (0, top * scale, im.width, min(im.height, bottom * scale))
            if box[1] >= box[3]:
                continue
            target = str(png)[:-4] + f"-{name}.png"
            im.crop(box).save(target)
            out.append(target)
    return out


def slug_for(page, root, query):
    s = page.replace(TOOL_PREFIX.strip("/") + "/", "").replace("/", "-").removesuffix(".html")
    if root:
        s += f"-root{root}"
    for k, v in query:
        s += "-" + re.sub(r"[^A-Za-z0-9]+", "-", f"{k}-{v}").strip("-")
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="directory for the PNGs (created)")
    ap.add_argument("--serve", required=True, metavar="DIR", help="directory served at /")
    ap.add_argument("--pages", nargs="+", default=["index.html"], help="paths under DIR (or __fd/narrow.html, __fd/opsz.html)")
    ap.add_argument("--widths", nargs="+", type=int, default=[500, 1280, 1600])
    ap.add_argument("--scales", nargs="+", type=int, default=[1, 2])
    ap.add_argument("--jobs", type=int, default=3, help="concurrent Chrome processes")
    ap.add_argument("--root", type=int, help="inject html{font-size:N%%} into each .html page (a reader's enlarged default)")
    ap.add_argument("--family", help="the font family every shot must prove it rendered with")
    ap.add_argument("--font-url", help="a path that must be served 200 to each shot, e.g. /fonts/Family-VF.woff2")
    ap.add_argument("--probe", metavar="SELECTOR", help="with --family: the elements that must be drawn in it "
                    "(default: every visible element whose computed font-family names it first)")
    ap.add_argument("--dump-dom", action="store_true", help="also save the DOM Chrome laid out as <name>.dom.html")
    ap.add_argument("--no-sentinel", action="store_true", help="serve .html byte-identical; no beacon, no font proof: a picture, not evidence")
    ap.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="CSS px captured")
    ap.add_argument("--bands", default=DEFAULT_BANDS, help="crops as name:top:bottom,... in CSS px, or 'none'")
    ap.add_argument("--query", action="append", default=[], metavar="K=V", help="query parameter added to every page URL (repeatable)")
    ap.add_argument("--seconds", type=int, default=600, help="the server shuts itself down after this long")
    args = ap.parse_args(argv)
    bad = [w for w in args.widths if w < MIN_WIDTH]
    if bad:
        sys.exit(f"refused: width(s) {bad} are below Chrome headless's {MIN_WIDTH}px minimum layout width, so the "
                 f"screenshot would be cropped, not narrow. For a phone reading shoot scripts/narrow.html: "
                 f"--pages __fd/narrow.html --query url=/<page>.html --query width={bad[0]} --dump-dom, and read "
                 f"data-fd-overflow in the dumped DOM.")
    if args.no_sentinel and args.family:
        sys.exit("refused: --family needs the sentinel; drop --no-sentinel")
    if args.probe and not args.family:
        sys.exit("refused: --probe needs --family to say which face the elements must be drawn in")
    query = []
    for kv in args.query:
        if "=" not in kv:
            sys.exit(f"--query wants K=V, got {kv!r}")
        k, v = kv.split("=", 1)
        query.append((k, v))
    try:
        chrome = find_chrome()
    except FileNotFoundError as exc:
        sys.exit(str(exc))
    try:
        bands = parse_bands(args.bands)
    except ValueError as exc:
        sys.exit(f"--bands: {exc}")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        server, port = serve(args.serve, args.seconds, family=args.family, sentinel=not args.no_sentinel, probe=args.probe)
    except NotADirectoryError as exc:
        sys.exit(str(exc))
    jobs = []
    for page in args.pages:
        page = page.lstrip("/")
        slug = slug_for(page, args.root, query)
        for width in args.widths:
            for scale in args.scales:
                url = f"http://127.0.0.1:{port}/{page}"
                params = dict(query)
                if args.root:
                    params["root"] = args.root
                if params:
                    url = with_query(url, params)
                jobs.append((url, out / f"{slug}-{width}@{scale}x.png", width, scale))
    names = [str(j[1]) for j in jobs]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        sys.exit(f"refused: two shots would write the same file ({dupes[0]}); a page listed twice, or two pages with one slug")
    written, failed, results = [], [], []

    def one(job):
        url, png, width, scale = job
        try:
            res = shoot(url, png, width, scale, height=args.height, profile_root=out, server=server,
                        require_family=args.family, font_url=args.font_url, dump_dom=args.dump_dom, chrome=chrome)
            return res, scale
        except (RuntimeError, ValueError) as exc:  # one failed page must not end the run; it is reported at the end
            failed.append(str(exc))
            return None, scale
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            for res, scale in pool.map(one, jobs):
                if res:
                    results.append(res)
                    written.append(res["png"])
                    if res["dom"]:
                        written.append(res["dom"])
                    written += crop_bands(res["png"], scale, bands)
    finally:
        server.shutdown()
    for w in written:
        print(w)
    for res in results:
        print(json.dumps({k: v for k, v in res.items() if k != "verified"}), file=sys.stderr)
    for d in server.departures:
        print(f"NOTE: {d}", file=sys.stderr)
    for f in failed:
        print(f"FAILED: {f}", file=sys.stderr)
    print(f"{len(written)} files in {out}, {len(results)} shots verified, {len(failed)} shots failed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
