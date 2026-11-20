#!/usr/bin/env node
"use strict";
/* build-page.js: assembles one self-contained concept page from a template, the generator, the
 * project's concepts and a content JSON.
 *
 * WHAT IT'S FOR: a concept page lets the operator and a reviewer judge parameter sets on real titles
 * at real sizes before any font file exists. The page must be one file (it is opened locally or
 * published as an artifact, where only files beside it load), so this splices four sources into a
 * template: gen.js at the comment marker named GEN (its module.exports block removed), render.js
 * at RENDER (same), the concepts file at CONCEPTS (same; it leaves the global CONCEPTS), and the
 * content JSON at CONTENT, which sits inside <script type="application/json" id="fd-content">.
 * The template reads that block with JSON.parse and builds every element with
 * createElement/textContent/setAttribute, so content can never become markup: the JSON text has
 * `<`, `>`, `&`, U+2028 and U+2029 written as \u escapes, which JSON.parse restores and the HTML
 * parser never sees as a tag (a title containing "</script>" cannot end the block).
 *
 *     node build-page.js --template round1|round2|round3|PATH --concepts C.js --content C.json
 *                        [--skeletons tools/<face>/skeletons.js] [--gen ../gen.js] [--render ../render.js] OUT.html
 *
 * --skeletons names the face's skeleton override (the file font.json's `skeletons` key names; references/generator.md,
 * "Per-face skeletons"), so the page draws the face's own letters. The file is first applied to a fresh gen.js in a child
 * node, so a malformed override is refused here with gen.js's message and no page is written; then it is spliced right
 * after gen.js, wrapped in a function so the only top-level name it adds is SKELETONS, followed by the call to
 * applySkeletons and one line that sets data-fd-skeletons on <html> to the keys the call overrode or added, which the
 * browser can only do once the call has returned (the page's evidence, read by shoot.py --dump-dom). Without the flag
 * nothing is spliced and the page is the one 0.5.0 built.
 *
 * It refuses (exit 1, naming the marker) when a marker appears other than exactly once, parses the
 * assembled main script with new Function so a syntax error fails here and not in the browser, and
 * validates the content: the keys each round needs are present and the right type, every `image`
 * is null or matches ^img/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp)$ (a file beside the page), every
 * colour is #hex or rgb()/rgba(), every face id named exists, the comparison face names an installed
 * family (neither URL), a relative woff2 path (font_url) or an https stylesheet (css_url), not both, and the grid lists have counts that fill their rows (round 1
 * tiles: a multiple of 6, which fills 2 columns at 500px and 6 at 1280 and 1600; round 2/3
 * selection and plates: a multiple of 4; chapters 2 or 4; guides even). Keys that start with "_"
 * are documentation and are dropped before validation.
 *
 * Exact guarantee: validation covers the keys the templates read. A key the templates ignore is not
 * checked, and a template edited to read a new key must add it to SPEC below. Parsing with
 * new Function proves the script is syntactically valid JavaScript; it does not run it, so a
 * runtime error still needs the smoke run in Chrome (shoot.py --dump-dom, data-fd-rendered > 0).
 * Copyright 2026 John Knox. MIT licence. From the Bract concept-page builders (2026-11-15).
 */
var fs = require("fs");
var path = require("path");

var IMAGE = /^img\/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp)$/;
var COLOUR = /^(#[0-9a-fA-F]{3}([0-9a-fA-F]{3}([0-9a-fA-F]{2})?)?|rgba?\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*(,\s*[\d.]+\s*)?\))$/;
var FONT_URL = /^(?!\/)(?!.*\.\.)[A-Za-z0-9_./-]+\.woff2$/;
var CSS_URL = /^https:\/\/[^\s"'<>]+$/;
var ID = /^[a-z][a-z0-9-]*$/;
var MARKERS = ["/*GEN*/", "/*RENDER*/", "/*CONCEPTS*/", "/*CONTENT*/"];

function fail(msg) { console.error("build-page.js: " + msg); process.exit(1); }

// options: --template roundN|PATH, --concepts PATH, --content PATH, OUT.html; --skeletons PATH, the face's skeleton
// override (above); and --gen PATH / --render PATH to splice another gen.js or render.js (kept for a site still on the
// copy-and-patch convention that 0.6.0's --skeletons replaces)
function args(argv) {
  var o = { out: null };
  for (var i = 0; i < argv.length; i++) {
    var a = argv[i];
    if (a.slice(0, 2) === "--") { o[a.slice(2)] = argv[++i]; }
    else if (!o.out) { o.out = a; }
    else { fail("unexpected argument " + a); }
  }
  ["template", "concepts", "content"].forEach(function (k) { if (!o[k]) fail("--" + k + " is required"); });
  if (!o.out) fail("OUT.html is required");
  return o;
}

/* Removes the CommonJS export block: everything from the last `if (typeof module !== "undefined")`
   to the end of the file, which must mention module.exports and nothing else. */
function stripExports(src, name) {
  var marker = 'if (typeof module !== "undefined")';
  var i = src.lastIndexOf(marker);
  if (i < 0) fail(name + ' has no `if (typeof module !== "undefined")` export block to remove');
  var tail = src.slice(i);
  if (!/module\.exports/.test(tail)) fail(name + ": the export block does not mention module.exports");
  var oneLine = /^if \(typeof module !== "undefined"\) module\.exports = [^\n]*;?\n?$/;
  var block = /^if \(typeof module !== "undefined"\) \{\s*module\.exports = [\s\S]*?;\s*\}\s*$/;
  if (!oneLine.test(tail) && !block.test(tail)) fail(name + ": the export block is not the last thing in the file, or has an unexpected shape: " + tail.slice(0, 80));
  return src.slice(0, i);
}

/* The override's splice: the file applied to a fresh gen.js in a child node first (so every refusal of applySkeletons fires
   here, with its message, before a page exists), then its source with the export block removed, wrapped so its own top-level
   declarations stay inside a function, the call, and the evidence line. Returns { text, report }. */
var APPLY_JS = 'try { const m = require(process.argv[1]); const r = m.applySkeletons(require(process.argv[2]), require("path").basename(process.argv[2]));' +
  ' process.stdout.write(JSON.stringify(r)); } catch (e) { process.stderr.write(e.message); process.exit(1); }';
function skeletonsSplice(file, genPath) {
  if (!fs.existsSync(file)) fail("--skeletons names no file: " + file);
  var name = path.basename(file);
  var raw = fs.readFileSync(file, "utf8"), src = stripExports(raw, file);
  // the page reads the function by the name SKELETONS, node by module.exports, so a file can pass node and leave the page
  // without its override (an anonymous export, or SKELETONS set only where `module` exists: diff review F001 and its re-review).
  // Rather than match the file's text, run the page's own wrapper as a page would, with gen.js's names and no `module`, and
  // require it to return a function
  var asPage;
  try {
    asPage = require("vm").runInNewContext("(function () {\n" + src + "\n;return SKELETONS; })()", Object.assign({}, require(genPath)), { filename: file });
  } catch (e) { asPage = e; }
  if (typeof asPage !== "function") {
    fail("--skeletons " + file + " must declare SKELETONS and export it: var SKELETONS = function (G, GI, S, D, ring) { ... }; " +
         'if (typeof module !== "undefined") module.exports = SKELETONS;');
  }
  var sha = require("crypto").createHash("sha256").update(raw).digest("hex");
  var r = require("child_process").spawnSync(process.execPath, ["-e", APPLY_JS, genPath, file], { encoding: "utf8" });
  if (r.status !== 0) fail("--skeletons " + file + " is refused by " + genPath + ": " + (r.stderr || "").trim());
  var report = JSON.parse(r.stdout);
  var text = "var SKELETONS = (function () { /* ---- skeletons: " + name + " ---- */\n" + src + "\n;return SKELETONS; })();\n" +
    "document.documentElement.setAttribute(\"data-fd-override-sha256\", " + JSON.stringify(sha) + ");\n" +
    "document.documentElement.setAttribute(\"data-fd-skeletons\", (function (r) { return r.overridden.concat(r.added).join(\",\"); })(applySkeletons(SKELETONS, " +
    JSON.stringify(name) + ")));\n";
  return { text: text, report: report };
}

function jsonForScript(obj) {
  return JSON.stringify(obj)
    .replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026")
    .replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
}

function dropDocs(v) {
  if (Array.isArray(v)) return v.map(dropDocs);
  if (v && typeof v === "object") {
    var o = {};
    Object.keys(v).forEach(function (k) { if (k.charAt(0) !== "_") o[k] = dropDocs(v[k]); });
    return o;
  }
  return v;
}

/* ---- content validation: a small descriptor language ----
   "str" string, "str?" optional string, "text?" string or null, "num", "bool", "colour", "image",
   "id" face id, {..} object, ["item"] array of item, ["item", n] array whose length % n == 0. */
var COMMON = {
  site: { name: "str", wordmark: "str", lede: "str", nav: ["str"], kicker: "str" },
  round: { title: "str", intro: ["str"] },
  colours: { paper: "colour", plate: "colour", ink: "colour", pencil: "colour", accent: "colour", "accent-lift": "colour", cloth: "colour",
    "cloth-deep": "colour", "cloth-ink": "colour", stamp: "colour", desk: "colour", rule: "colour", placeholder: "colour" },
  fonts: { body: "css", label: "css" },
  comparison: { name: "str", family: "str", font_url: "fonturl?", css_url: "cssurl?", weights: ["num"], note: "str?" },
  weights: [{ label: "str", mult: "num" }],
  bold_mult: "num", medium_mult: "num", storage_key: "str", titles: ["str"]
};
var ROUND1 = {
  lineup_text: "str", audit_intro: "str?", audit: [{ first: "bool", finding: "str", fix: "str", font_effect: "str" }],
  guidelines: [{ lead: "str", text: "str" }], concepts: "conceptinfo",
  specimen: { heading: "str", chapters: [{ num: "str", name: "str", blurb: "text?" }], essay: { title: "str", date: "str", paragraph: "str" },
    plateline: "str", tiles: [{ title: "str", date: "str", colour: "colour" }, 6], tiles_note: "str?", chars: "str" },
  recommendation: { heading: "str", paragraphs: ["str"] }
};
var MOCK = {
  shortlist: ["id"], notes: "notes", glance_titles: ["str"],
  pages: {
    home: { caption: "str", sizes: "str", fore_read: "str", strip: ["colour"], years: ["year"],
      front: { image: "image", alt: "str", caption: "str", volume: "str", since: "str", buttons: ["str"] },
      latest: { heading: "str", title: "str", image: "image", alt: "str", plateline: "str", desc: "str", go: "str" },
      chapters_heading: "str", more: "str",
      chapters: [{ image: "image", alt: "str", num: "str", name: "str", blurb: "str", count: "str" }, 2],
      selection_heading: "str", selection: [{ no: "num", title: "str", date: "str", image: "image", alt: "str" }, 4],
      guides_heading: "str", guides: [{ title: "str", blurb: "str" }, 2],
      colophon: { heading: "str", text: "str", facts: ["pair"] } },
    article: { caption: "str", sizes: "str", title: "str", date: "str", image: "image", alt: "str", paragraphs: ["str"], heading: "str",
      paragraph_after: "str", read_next: [{ title: "str", sub: "str" }] },
    contents: { caption: "str", sizes: "str", title: "str", blurb: "str", chips: [{ label: "str", count: "str", on: "bool" }],
      plates: [{ no: "num", title: "str", date: "str", image: "image", alt: "str" }, 4] }
  },
  choosing: { heading: "str", paragraphs: ["str"] },
  slot_sizes: "slotsizes"
};
// the named headline slots of the round-2/3 mock pages; content.slot_sizes (required for rounds 2 and 3, re-review
// code-b F007: an optional block let both mocks build at the template's fixed hop-safari sizes with nothing said)
// overrides size, min, fit, lh per slot, and every slot it leaves at the template default is named on stderr
var SLOT_NAMES = ["glance_wordmark_small", "glance_wordmark", "glance_heading", "glance_title", "spine_wordmark", "front_wordmark",
  "section_heading", "latest_title", "chapter_num", "chapter_name", "guide_title", "colophon_heading", "article_title",
  "article_heading", "read_next_title", "contents_title", "plate_title"];
var ROUND3 = {
  faces: [{ id: "newid", name: "str", from: "str", cuts: { text: "conceptid", display: "conceptid", from: "num" } }],
  verdict: { headline: "str", summary: "str", items: [{ face: "id", text: "str" }], ranking: ["id"], next: "str", source: "str" }
};
var SPEC = { round1: [COMMON, ROUND1], round2: [COMMON, MOCK], round3: [COMMON, MOCK, ROUND3] };

function validate(content, round, conceptIds) {
  var errors = [];
  // one content file drives all three rounds, so a round-3 two-cut face is a known id in every round
  var faceIds = conceptIds.slice();
  if (Array.isArray(content.faces)) {
    content.faces.forEach(function (f) { if (f && typeof f.id === "string") faceIds.push(f.id); });
  }
  faceIds.push("comparison");
  function check(v, spec, where) {
    if (typeof spec === "string") {
      var opt = spec.slice(-1) === "?", kind = opt ? spec.slice(0, -1) : spec;
      if (v === undefined || (v === null && (opt || kind === "image" || kind === "text"))) { if (!opt && v === undefined && kind !== "image") errors.push(where + " is missing"); return; }
      switch (kind) {
        case "str": case "text": case "css": if (typeof v !== "string") errors.push(where + " must be a string");
          else if (kind === "css" && /[<;{}]/.test(v)) errors.push(where + " is a CSS family list and may not contain < ; { }"); break;
        case "num": if (typeof v !== "number" || !isFinite(v)) errors.push(where + " must be a number"); break;
        case "bool": if (typeof v !== "boolean") errors.push(where + " must be true or false"); break;
        case "colour": if (typeof v !== "string" || !COLOUR.test(v)) errors.push(where + " must be #hex or rgb()/rgba(): " + JSON.stringify(v)); break;
        case "image": if (typeof v !== "string" || !IMAGE.test(v)) errors.push(where + " must be null or img/<name>.(jpg|jpeg|png|webp), a file beside the page: " + JSON.stringify(v)); break;
        case "fonturl": if (typeof v !== "string" || !FONT_URL.test(v)) errors.push(where + " must be a relative .woff2 path with no '..': " + JSON.stringify(v)); break;
        case "cssurl": if (typeof v !== "string" || !CSS_URL.test(v)) errors.push(where + " must be an https URL: " + JSON.stringify(v)); break;
        case "id": if (typeof v !== "string" || faceIds.indexOf(v) < 0) errors.push(where + " names no known face: " + JSON.stringify(v) + " (have " + faceIds.join(", ") + ")"); break;
        case "conceptid": if (typeof v !== "string" || conceptIds.indexOf(v) < 0) errors.push(where + " names no concept: " + JSON.stringify(v) + " (have " + conceptIds.join(", ") + ")"); break;
        case "newid": if (typeof v !== "string" || !ID.test(v)) errors.push(where + " must be a lowercase id: " + JSON.stringify(v));
          else if (conceptIds.indexOf(v) >= 0 || v === "comparison") errors.push(where + " collides with a concept id or 'comparison': " + v); break;
        case "year": if (!Array.isArray(v) || v.length !== 2 || typeof v[0] !== "number" || typeof v[1] !== "string") errors.push(where + " must be [weight, label]"); break;
        case "pair": if (!Array.isArray(v) || v.length !== 2 || typeof v[0] !== "string" || typeof v[1] !== "string") errors.push(where + " must be [term, value]"); break;
        case "notes": if (!v || typeof v !== "object") { errors.push(where + " must be an object of face id to text"); break; }
          Object.keys(v).forEach(function (k) { if (faceIds.indexOf(k) < 0) errors.push(where + "." + k + " names no known face"); if (typeof v[k] !== "string") errors.push(where + "." + k + " must be a string"); }); break;
        case "slotsizes": if (!v || typeof v !== "object" || Array.isArray(v)) { errors.push(where + " must be an object of slot name to {size, min, fit, lh}"); break; }
          Object.keys(v).forEach(function (k) {
            if (SLOT_NAMES.indexOf(k) < 0) { errors.push(where + "." + k + " names no mock slot (have " + SLOT_NAMES.join(", ") + ")"); return; }
            if (!v[k] || typeof v[k] !== "object" || Array.isArray(v[k])) { errors.push(where + "." + k + " must be an object"); return; }
            Object.keys(v[k]).forEach(function (f) {
              if (["size", "min", "fit", "lh"].indexOf(f) < 0) errors.push(where + "." + k + "." + f + " is not one of size, min, fit, lh");
              else if (typeof v[k][f] !== "number" || !(v[k][f] > 0)) errors.push(where + "." + k + "." + f + " must be a positive number");
            });
            if (v[k].size === undefined) errors.push(where + "." + k + ".size is missing");
          }); break;
        case "conceptinfo": if (!v || typeof v !== "object") { errors.push(where + " must be an object of concept id to {desc, cost, risk, pick}"); break; }
          Object.keys(v).forEach(function (k) { if (conceptIds.indexOf(k) < 0) errors.push(where + "." + k + " names no concept");
            check(v[k], { desc: "str", cost: "str", risk: "str", pick: "bool" }, where + "." + k); }); break;
        default: errors.push("internal: unknown spec " + kind + " at " + where);
      }
      return;
    }
    if (Array.isArray(spec)) {
      if (!Array.isArray(v)) { errors.push(where + " must be a list"); return; }
      if (!v.length) errors.push(where + " is empty");
      if (spec.length > 1 && v.length % spec[1] !== 0) errors.push(where + " has " + v.length + " items; it must be a multiple of " + spec[1] + " so no grid row is left with orphan tiles");
      v.forEach(function (item, i) { check(item, spec[0], where + "[" + i + "]"); });
      return;
    }
    if (!v || typeof v !== "object" || Array.isArray(v)) { errors.push(where + " must be an object"); return; }
    Object.keys(spec).forEach(function (k) { check(v[k], spec[k], where + "." + k); });
  }
  SPEC[round].forEach(function (s) { check(content, s, "content"); });
  if (content.comparison && typeof content.comparison === "object") {
    // neither URL means an installed family (the current face is often a system font, dry-run finding W2); the template sets it as the CSS stack
    if (content.comparison.font_url && content.comparison.css_url) errors.push("content.comparison: give font_url or css_url, not both");
  }
  if (round !== "round1" && Array.isArray(content.shortlist)) {
    content.shortlist.forEach(function (id) { if (conceptIds.indexOf(id) < 0) errors.push("content.shortlist names no concept: " + id); });
  }
  return errors;
}

function main() {
  var o = args(process.argv.slice(2));
  var here = __dirname;
  var round = /^round[123]$/.test(o.template) ? o.template : null;
  var templatePath = round ? path.join(here, round + "-template.html") : path.resolve(o.template);
  if (!round) {
    var m = /^<!--\s*fd-round:\s*(round[123])\s*-->/.exec(fs.readFileSync(templatePath, "utf8"));
    if (!m) fail("a custom template must open with <!-- fd-round: roundN --> so its content can be validated");
    round = m[1];
  }
  var genPath = path.resolve(o.gen || path.join(here, "..", "gen.js"));
  var renderPath = path.resolve(o.render || path.join(here, "..", "render.js"));
  var conceptsPath = path.resolve(o.concepts);
  var contentPath = path.resolve(o.content);
  var template = fs.readFileSync(templatePath, "utf8");
  MARKERS.forEach(function (k) {
    var n = template.split(k).length - 1;
    if (n !== 1) fail("template " + templatePath + " has " + n + " occurrences of " + k + "; exactly one is needed");
  });
  var gen = stripExports(fs.readFileSync(genPath, "utf8"), genPath);
  var render = stripExports(fs.readFileSync(renderPath, "utf8"), renderPath);
  var concepts = stripExports(fs.readFileSync(conceptsPath, "utf8"), conceptsPath);
  var skeletons = o.skeletons ? skeletonsSplice(path.resolve(o.skeletons), genPath) : null;
  var list = require(genPath).loadConcepts(conceptsPath);
  var params = require(genPath).params;
  list.forEach(function (c) { params(c, 1, false); }); // a concept gen.js refuses must fail here, not in the browser
  var conceptIds = list.map(function (c) { return c.id; });
  var content;
  try { content = dropDocs(JSON.parse(fs.readFileSync(contentPath, "utf8"))); }
  catch (e) { fail("content " + contentPath + " is not valid JSON: " + e.message); }
  var errors = validate(content, round, conceptIds);
  if (errors.length) fail("content " + contentPath + " is not valid for " + round + ":\n  " + errors.join("\n  "));
  if (round !== "round1") {
    var defaulted = SLOT_NAMES.filter(function (n) { return !(n in content.slot_sizes); });
    if (defaulted.length) console.error("build-page.js: " + defaulted.length + " mock slot(s) not in content.slot_sizes keep the template's default size: " + defaulted.join(", "));
  }
  // the template's script shares one function scope with the spliced sources, so a top-level name
  // declared in both silently overwrites (gen.js's ROUND table once became the string "round3")
  // (var, function, let, const and class are all read since 0.6.0; a let or const clash is a SyntaxError in the browser)
  function topNames(src) { var out = {}, re = /^(?:var|function|let|const|class)\s+([A-Za-z_$][\w$]*)/gm, m; while ((m = re.exec(src))) out[m[1]] = true; return out; }
  var templateScript = (template.match(/<script>([\s\S]*?)<\/script>/) || ["", ""])[1];
  var ours = topNames(templateScript);
  var theirs = topNames(gen + "\n" + render + "\n" + concepts);
  var clash = Object.keys(ours).filter(function (n) { return theirs[n]; });
  if (clash.length) fail("the template declares top-level names that gen.js, render.js or concepts.js also declare: " + clash.join(", "));
  // the override's splice declares one top-level name, SKELETONS, and sets one attribute, data-fd-skeletons; neither may be
  // anyone else's (its own declarations sit inside the wrapper function, so they cannot clash with gen.js's DEG and the like)
  if (skeletons) {
    if (ours.SKELETONS || theirs.SKELETONS) fail("--skeletons: the template, gen.js, render.js or concepts.js already declare SKELETONS, the one name the override's splice adds");
    if (/data-fd-skeletons/.test(template + gen + render + concepts)) fail("--skeletons: data-fd-skeletons is already used by the template or a source; the splice sets it");
  }
  [gen, render, concepts].concat(skeletons ? [skeletons.text] : []).forEach(function (src, i) {
    if (/<\/script/i.test(src)) fail(["gen", "render", "concepts", "skeletons"][i] + " contains '</script', which would end the page's script block");
  });
  var page = template
    .replace("/*GEN*/", function () { return "/* ---- gen.js ---- */\n" + gen + (skeletons ? "\n" + skeletons.text : ""); })
    .replace("/*RENDER*/", function () { return "/* ---- render.js ---- */\n" + render; })
    .replace("/*CONCEPTS*/", function () { return "/* ---- concepts.js ---- */\n" + concepts; })
    .replace("/*CONTENT*/", function () { return jsonForScript(content); });
  var scripts = page.match(/<script>([\s\S]*?)<\/script>/g) || [];
  if (scripts.length !== 1) fail("the template must hold exactly one plain <script> block (found " + scripts.length + ")");
  var js = scripts[0].slice("<script>".length, -"</script>".length);
  try { new Function(js); } catch (e) { fail("the assembled script does not parse: " + e.message); }
  var block = page.match(/<script type="application\/json" id="fd-content">([\s\S]*?)<\/script>/);
  if (!block) fail("the template lost its fd-content JSON block");
  if (/<|>|&|\u2028|\u2029/.test(block[1])) fail("internal: the JSON block still contains < > & or a line separator");
  fs.mkdirSync(path.dirname(path.resolve(o.out)), { recursive: true });
  fs.writeFileSync(o.out, page);
  console.log(o.out + ": " + round + ", " + conceptIds.length + " concept(s) [" + conceptIds.join(", ") + "], " +
    (skeletons ? "skeletons " + path.basename(o.skeletons) + " (" + skeletons.report.overridden.concat(skeletons.report.added).join(", ") + "), " : "") +
    page.length + " bytes, script parses");
}

main();
