/* render.js: draws generator text into a page element as one inline SVG path.
 *
 * WHAT IT'S FOR: the browser half of the concept pipeline. gen.js makes outlines; this lays a line
 * of text with layWord()/wrap() and writes it into an element as an SVG, so a concept page can show
 * a parameter set on real titles at real sizes before any font file exists. The concept-page builder
 * (scripts/concepts/build-page.js) splices gen.js (its module.exports stripped), the project's
 * concepts.js and this file into one <script>, so glyph, kern, layWord and wrap are in scope here.
 *
 * Contract: render(el, text, P, sizePx, { kern, liga, lh }) wraps `text` to el.clientWidth at
 * `sizePx` CSS pixels (so call it only after the element is in the page and laid out; an earlier
 * version measured before attachment and clipped every title), draws every glyph as a nonzero-fill
 * path, and sets el's content. It returns the number of glyphs drawn, which the page's self-test
 * sums into a DOM attribute for the screenshot tool to check.
 *
 * Copyright 2026 John Knox. MIT licence. From the Bract concept pages (hopsafari.com, 2026-11-15).
 */
function render(el, text, P, size, opt) {
  opt = opt || {};
  var avail = Math.max(120, el.clientWidth || 300), max = avail / size * 1000;
  var words = String(text).split(/\s+/).filter(Boolean);
  var res = wrap(words, P, { kern: opt.kern !== false, liga: opt.liga !== false }, max), lh = opt.lh || 1120, base0 = 800, d = [], maxW = 0, count = 0;
  res.lines.forEach(function (ln, li) {
    var x = 0, by = base0 + li * lh;
    ln.words.forEach(function (lw, wi) {
      if (wi) x += res.space;
      lw.items.forEach(function (it) {
        count++;
        it.g.polys.forEach(function (p) {
          d.push("M" + p.map(function (q) { return (q[0] + x + it.x).toFixed(1) + " " + (by - q[1]).toFixed(1); }).join("L") + "Z");
        });
      });
      x += lw.w;
    });
    if (x > maxW) maxW = x;
  });
  var H = base0 + (res.lines.length - 1) * lh + 280, padL = 60;
  var vbW = maxW + padL * 2;
  // built with DOM calls, not an HTML string, so the text can never be parsed as markup
  var ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg"), path = document.createElementNS(ns, "path");
  svg.setAttribute("role", "img"); svg.setAttribute("aria-label", String(text));
  svg.setAttribute("viewBox", (-padL) + " 0 " + vbW.toFixed(0) + " " + H);
  svg.setAttribute("width", (vbW * size / 1000).toFixed(1)); svg.setAttribute("height", (H * size / 1000).toFixed(1));
  svg.style.marginLeft = (-padL * size / 1000).toFixed(1) + "px";
  path.setAttribute("fill", "currentColor"); path.setAttribute("d", d.join(""));
  svg.appendChild(path);
  while (el.firstChild) el.removeChild(el.firstChild);
  el.appendChild(svg);
  return count;
}
if (typeof module !== "undefined") module.exports = { render: render };
