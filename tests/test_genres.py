"""The genre recipes are legal, compatible concepts, and the genre table names exactly them.

WHAT IT'S FOR: `templates/concepts.genres.js` holds one recipe per genre the generator
can reach, and `references/genres.md` is the table that says what each reaches. Three things can
drift silently: a recipe that params() or the exporter would refuse (a project copying it would
find out at its first build), a table row naming a recipe that does not exist (or a recipe the table
never mentions), and a genres page that does not carry the recipes it claims to show. Each test
executes the real code (gen.js through node, build-page.js, the table parsed from the markdown).

What these tests prove, and do not: a recipe loads, every coordinate of every glyph is finite, and its
Regular and its 1.5 x Bold take the same branch in every glyph, so the pair can be a variable font. They
do NOT prove a recipe looks like its genre; that is the render review recorded in genres.md (a dated
verdict per recipe: reaches, partly or no), which the table test only requires to exist.

Mutations (watched red on 2026-11-16; the outcome of each is in references/testing.md section 8):
- test 1, the weakest mutation that must break EVERY recipe (plan finding F009): in gen.js `glyph()`
  take the sample counts from the FITTED path, `samplePath(st.d, counts[si])` ->
  `samplePath(st.d, sampleCounts(st.d))`. The flat and round fits move endpoints by `hwFlat`, which
  follows W, so the Bold's counts differ from the Regular's on every recipe. Run it by copying
  scripts/gen.js to a scratch file, applying the edit there and pointing FONT_DESIGN_GENRES_GEN at
  the copy (the variable exists only so a mutation never edits the shared generator; unset, the test
  reads the real scripts/gen.js).
- test 1, second and serif-only: `xs 0.86` on a serif recipe flips the italic `w`'s serif-kind branch
  (gen.js: the kind test is inside mode "serif"), so it goes red there and CANNOT go red on the
  grotesque; that is why it is not the main mutation.
- test 1, the finite-coordinate check (2026-11-16: `grot` and `geometric` set `cut` ends and no `cut`, so
  Math.cos(undefined) made 18 glyphs NaN and Chrome dropped whole words): delete the `P.cut` default in
  params() in the scratch copy. Red on `grot` and `geometric`, naming the glyphs.
- the duplicated-field tests (2026-11-16, review finding T5): edit one number in a table row's knobs cell, or
  the same number in the recipe; edit `content.concepts.<id>.desc`; edit a recipe's `from` or `desc`.
- the documented build command (T6): put `content.minimal.json` back into the comment in concepts.genres.js.
- the relational knobs cells (V1): change a key of geometric, fatface or slab that its cell does not name.
- the smoke step 8b script (T7): empty one recipe's paths in a synthetic dumped DOM, or put NaN in one.
- the review record (T8): change one number in a recipe, or one verdict in the record.
- test 2: rename one recipe id in concepts.genres.js, or change a table row's id, or change a
  recipe's `desc` verdict so it disagrees with the table.
- test 3: build the page from templates/concepts.example.js instead of concepts.genres.js.
- test 5 (content file drift): add, remove or rename a key in content.genres.json's `concepts`, or edit one
  `risk`, or edit the matching "reaches it today?" cell in genres.md.
"""
import json
import math
import os
import pathlib
import re
import shlex
import sys

import pytest
from conftest import REPO, node, run

GENRES_JS = REPO / "templates" / "concepts.genres.js"
GENRES_MD = REPO / "references" / "genres.md"
GEN = pathlib.Path(os.environ.get("FONT_DESIGN_GENRES_GEN", REPO / "scripts" / "gen.js"))

# Recorded exceptions, written out so they cannot widen unnoticed. Empty since 0.7.0: until then Bract's foil
# (`scotch`, xs 0.9) took a different serif branch on its italic w at mult 1 and mult 1.5, because the serif
# kind read the drawn tangent, which the Bold's xs widening moved (generator.md section 12). Every decision now
# reads the geometry at mult 1, so no recipe is refused; a recipe that appears here again is a regression.
KNOWN_ITALIC_REFUSALS = {}

COMPARE = r"""
const m = require(process.argv[1]); const list = m.loadConcepts(process.argv[2]);
const sig = g => JSON.stringify([g.polys.map(p => p.length), g.runs, g.sig]);
const out = [];
for (const c of list) {
  const r = { id: c.id, apex: "apex" in c, roman: [], italic: [], nonfinite: [], compared: 0 };
  const finite = g => g.polys.every(p => p.every(q => Number.isFinite(q[0]) && Number.isFinite(q[1])));
  try { for (const italic of [false, true]) {
    const a = m.params(c, 1, italic), b = m.params(c, 1.5, italic);
    const keys = Object.keys(m.G).concat(italic ? Object.keys(m.GI) : []);
    for (const k of new Set(keys)) {
      const g1 = m.glyph(k, a), g2 = m.glyph(k, b);
      if (!g1 || !g2) continue;
      r.compared++;
      if (!finite(g1) || !finite(g2)) r.nonfinite.push((italic ? "i:" : "") + k);
      if (sig(g1) !== sig(g2)) r[italic ? "italic" : "roman"].push(k);
    }
  } } catch (e) { r.crash = String(e.message).slice(0, 80); }
  out.push(r);
}
console.log(JSON.stringify(out));
"""


def recipes():
    """The recipes as plain dicts, read through the generator's own loader."""
    r = run([node(), "-e", "const m=require(process.argv[1]);console.log(JSON.stringify(m.loadConcepts(process.argv[2])))",
             str(REPO / "scripts" / "gen.js"), str(GENRES_JS)])
    assert r.returncode == 0, r.stderr
    return {c["id"]: c for c in json.loads(r.stdout)}


def recipe_ids():
    r = run([node(), "-e", "const m=require(process.argv[1]);console.log(JSON.stringify(m.loadConcepts(process.argv[2]).map(c=>c.id)))",
             str(REPO / "scripts" / "gen.js"), str(GENRES_JS)])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_missing_generator_override_fails_loudly():
    """FONT_DESIGN_GENRES_GEN, when set for a mutation run, must name a file; an unset variable is the real
    scripts/gen.js."""
    assert GEN.exists(), f"{GEN} does not exist"


def test_every_genre_recipe_passes_params_and_exports_two_compatible_masters():
    """Each recipe loads through params() at mult 1 and 1.5 (roman and italic), and every glyph has the
    same polygon counts, point counts, edge runs and branch record in both masters: the comparison
    export.js makes, restated here. Mutation: see the module docstring (the fitted-path sample count,
    red on every recipe)."""
    r = run([node(), "-e", COMPARE, str(GEN), str(GENRES_JS)])
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    assert len(rows) >= 9, "the genres file has lost recipes"
    failures = []  # every recipe is checked and every failure named, so a mutation that breaks all of them shows all of them
    for row in rows:
        if row.get("crash"):
            failures.append(f'{row["id"]}: the generator threw ({row["crash"]})')
            continue
        if row["nonfinite"]:
            failures.append(f'{row["id"]}: {len(row["nonfinite"])} glyphs have non-finite coordinates: {row["nonfinite"][:10]}')
        if row["compared"] <= 150:
            failures.append(f'{row["id"]}: only {row["compared"]} glyphs compared; the check is hollow')
        if row["apex"]:
            failures.append(f'{row["id"]} sets apex, which is designed and not built (params() refuses it)')
        if row["roman"]:
            failures.append(f'{row["id"]}: the Regular and the 1.5 Bold differ in structure or branch for {len(row["roman"])} glyphs: {row["roman"][:6]}')
        want = KNOWN_ITALIC_REFUSALS.get(row["id"], [])
        if row["italic"] != want:
            failures.append(f'{row["id"]}: italic structure differences are {row["italic"][:6]}, expected {want}')
    assert not failures, "\n".join(failures)

def parse_tables():
    """Rows of every markdown table in genres.md as lists of cells (header and separator rows dropped)."""
    rows = []
    for line in GENRES_MD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|$", line):
            continue
        rows.append([c.strip() for c in line.strip().strip("|").split(" | ")])
    return rows


def test_the_genre_table_and_the_recipes_name_the_same_concepts():
    """Section 2's rows (four cells) carry recipe ids in backticks in the first cell; those ids are exactly
    the ids in concepts.genres.js, once each; every row's last cell opens with a verdict (reaches, partly
    or no) and the review date, so an undated or unknown verdict fails; a recipe's own `desc` opens with the
    same verdict and date as its row. Section 3's rows (three
    cells) are all `no` and name no recipe. Mutation: rename a recipe id (in the js or the table), or
    change a `desc` verdict, drop a date, or write `candidate`."""
    ids = recipe_ids()
    rows = parse_tables()
    recipe_rows = [r for r in rows if len(r) == 4 and r[0] != "Genre"]
    no_rows = [r for r in rows if len(r) == 3 and r[0] not in ("Genre or feature",)]
    assert recipe_rows and no_rows
    named, verdicts = [], {}
    for r in recipe_rows:
        found = re.findall(r"`([a-z][a-z0-9-]*)`", r[0])
        assert found, f"a recipe row names no concept id: {r[0]}"
        named += found
        m = re.match(r"^\*\*(reaches|partly|no)\*\* \((\d{4}-\d{2}-\d{2})\): \S", r[3])
        assert m, f"{found}: the cell must open with **reaches**, **partly** or **no**, then the review date in brackets, a colon and a sentence: {r[3][:70]}"
        for i in found:
            verdicts[i] = (m.group(1).capitalize(), m.group(2))
    assert sorted(named) == sorted(ids), f"table ids {sorted(named)} differ from the recipes {sorted(ids)}"
    assert len(named) == len(set(named)), "an id appears in two rows"
    for r in no_rows:
        assert r[2].startswith("**no**"), f"a row without a recipe must be a **no** row: {r[0]}"
        assert not set(re.findall(r"`([^`]+)`", r[0])) & set(ids), f"a no row names a recipe: {r[0]}"
    # the recipe's own desc must open with the same verdict as the table (two places state it)
    js = ("const m=require(process.argv[1]);console.log(JSON.stringify("
          "m.loadConcepts(process.argv[2]).map(c=>[c.id,c.desc||'',c.name||'',c.from||''])))")
    r = run([node(), "-e", js, str(REPO / "scripts" / "gen.js"), str(GENRES_JS)])
    for cid, desc, name, frm in json.loads(r.stdout):
        verdict, date = verdicts[cid]
        assert desc.startswith(f"{verdict} ({date}): "), f"{cid}: desc opens {desc[:30]!r}, the table says {verdict} ({date})"
        assert name and frm, f"{cid} needs name and from"


def test_the_genres_page_builds_and_names_every_recipe(tmp_path):
    """build-page.js round 1 over concepts.genres.js succeeds, and the CONCEPTS block it embeds in the page
    has exactly the recipe ids (read back by evaluating that block, not by searching the file). The content
    is content.minimal.json with its `concepts` block emptied, because that block names `text` and `display` and
    the builder refuses it beside other ids (genres.md section 6). Mutation: build from
    templates/concepts.example.js (the ids differ)."""
    content = json.loads((REPO / "scripts" / "concepts" / "content.minimal.json").read_text())
    ids = recipe_ids()
    content["concepts"] = {}  # required, but may be empty: an empty block cannot make the builder refuse another concepts file, so the id comparison below is the guard
    cpath = tmp_path / "content.json"
    cpath.write_text(json.dumps(content))
    page = tmp_path / "genres.html"
    r = run([node(), str(REPO / "scripts" / "concepts" / "build-page.js"), "--template", "round1", "--concepts", str(GENRES_JS),
             "--content", str(cpath), str(page)])
    assert r.returncode == 0, r.stderr
    html = page.read_text(encoding="utf-8")
    start = html.index("/* ---- concepts.js ---- */\n") + len("/* ---- concepts.js ---- */\n")
    end = html.index("/* ---- render.js ---- */", start)
    r = run([node(), "-e", "const C=new Function(process.argv[1]+';return CONCEPTS')();console.log(JSON.stringify(C.map(c=>c.id)))", html[start:end]])
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == ids
    for i in ids:  # the page has a face to switch to, so ?face=<id> has a target
        assert f'"{i}"' in html


def test_the_example_file_would_not_pass_as_the_genres_file(tmp_path):
    """The guard behind test 3's mutation, run for real: the same page built from templates/concepts.example.js
    does not carry the recipe ids, so test 3 can tell the two files apart (a test that cannot fail is
    decorative)."""
    ids = recipe_ids()
    example = run([node(), "-e", "const m=require(process.argv[1]);console.log(JSON.stringify(m.loadConcepts(process.argv[2]).map(c=>c.id)))",
                   str(REPO / "scripts" / "gen.js"), str(REPO / "templates" / "concepts.example.js")])
    assert json.loads(example.stdout) != ids



def test_the_genres_content_file_follows_the_recipes_and_the_table():
    """scripts/concepts/content.genres.json is what the genres page is built from, and the round-1 template
    shows a recipe's limit only from `concepts.<id>.risk` there. So its `concepts` keys must be exactly the
    recipe ids, and each `risk` must equal that recipe's "reaches it today?" cell in genres.md (markup
    removed), or the page shows a limit the table no longer states. It must also build for round 1.
    Mutations: add, remove or rename a `concepts` key; edit one `risk`; edit the table cell."""
    content = json.loads((REPO / "scripts" / "concepts" / "content.genres.json").read_text())
    ids = recipe_ids()
    assert sorted(content["concepts"]) == sorted(ids), f"content ids {sorted(content['concepts'])} differ from the recipes {sorted(ids)}"
    cells = {}
    for r in parse_tables():
        if len(r) == 4 and r[0] != "Genre":
            for i in re.findall(r"`([a-z][a-z0-9-]*)`", r[0]):
                cells[i] = r[3].replace("**", "").replace("`", "")
    for i in ids:
        assert content["concepts"][i]["risk"] == cells[i], f"{i}: risk differs from the genres.md cell:\n{content['concepts'][i]['risk']}\n{cells[i]}"


RENDER = pathlib.Path(os.environ.get("FONT_DESIGN_GENRES_RENDER", REPO / "scripts" / "render.js"))
RENDER_FIXTURE = r"""
const fs = require("fs"); const m = require(process.argv[1]);
const list = m.loadConcepts(process.argv[2]);
const attrs = {};
const mk = () => ({ setAttribute(k, v) { this[k] = v; }, appendChild() {}, style: {}, firstChild: null, removeChild() {} });
const doc = { documentElement: { setAttribute(k, v) { attrs[k] = v; } }, createElementNS: () => mk() };
const body = fs.readFileSync(process.argv[3], "utf8") + "; return render;";
const render = new Function("wrap", "layWord", "glyph", "kern", "document", body)(m.wrap, m.layWord, m.glyph, m.kern, doc);
const out = {};
for (const [id, patch] of JSON.parse(process.argv[4])) {
  for (const k of Object.keys(attrs)) delete attrs[k];
  const c = Object.assign({}, list.find(c => c.id === id), patch);
  const n = render({ clientWidth: 900, firstChild: null, removeChild() {}, appendChild() {} }, "Scotch eggs, a Gyoza", m.params(c, 1), 40);
  out[id + JSON.stringify(patch)] = { n, error: attrs["data-fd-error"] || null };
}
console.log(JSON.stringify(out));
"""


def test_render_sets_the_error_attribute_when_a_drawn_path_is_not_finite():
    """Chrome stops an SVG path at its first NaN, so a concept page whose glyphs are non-finite loses whole
    words while data-fd-rendered still counts them and no script error fires. render.js therefore sets
    data-fd-error on <html> (which shoot.py fails on). Run with the REAL render.js and gen.js in node
    against a stub document: the recipes draw clean, and `grot` with `cut: NaN` (adversarial: a value that
    params() lets through and that makes every cut end non-finite) sets the error. Mutation: delete the
    NaN|Infinity test in render.js (a scratch copy via FONT_DESIGN_GENRES_RENDER), red on the second
    assertion; delete the P.cut default and the first assertion goes red too."""
    script = RENDER_FIXTURE.replace('JSON.parse(process.argv[4])', '[["grot", {}], ["geometric", {}], ["grot", { cut: NaN }]]')
    r = run([node(), "-e", script, str(GEN), str(GENRES_JS), str(RENDER)])
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for key in ("grot{}", "geometric{}"):
        assert out[key]["n"] > 0 and out[key]["error"] is None, f"{key}: {out[key]}"
    bad = [v for k, v in out.items() if "cut" in k][0]
    assert bad["n"] > 0 and bad["error"] and "NaN" in bad["error"], f"a non-finite path set no error: {bad}"


def test_export_refuses_non_finite_coordinates(tmp_path):
    """export.js used to write a non-finite coordinate as JSON null and exit 0; build.py then died with a
    TypeError far from the cause. Now it exits 1 naming the master and glyph. Adversarial: a copy of `grot`
    with `cut: NaN` (params() accepts it). Mutation: delete the 1b check in export.js; the exit code is 0."""
    font = json.loads((REPO / "examples" / "neutral" / "font.json").read_text())
    (tmp_path / "concepts.js").write_text(GENRES_JS.read_text().replace('id: "grot",', 'id: "grot", cut: NaN,'))
    font["concepts"] = "concepts.js"
    font["groups"] = {"roman": {"italic": False, "axes": [{"tag": "wght", "name": "Weight", "min": 400, "default": 400, "max": 700}],
                                "masters": {"R": {"concept": "grot", "mult": 1, "location": {"wght": 400}},
                                            "B": {"concept": "grot", "mult": 1.5, "location": {"wght": 700}}},
                                "instances": [{"name": "Regular", "location": {"wght": 400}}], "hairline_floors": {"R": 50, "B": 50}}}
    (tmp_path / "font.json").write_text(json.dumps(font))
    r = run([node(), str(REPO / "scripts" / "export.js"), "--font", str(tmp_path / "font.json"), str(tmp_path / "out.json")])
    assert r.returncode == 1, (r.returncode, r.stderr[-300:])
    assert "non-finite" in r.stderr and "R:" in r.stderr


# --- one source for every duplicated field (review finding T5) -------------------------------------------------------

def table_rows():
    return [r for r in parse_tables() if len(r) == 4 and r[0] != "Genre"]


def test_the_knobs_cells_state_the_recipes_actual_parameters():
    """The table's "knobs" column and the recipe file both state parameter values. Every backticked `key value`
    pair in a row's knobs cell (for example `thin 0.28, pow 2.2`, or `nib 90 * DEG`) must equal that recipe's
    actual value, and a bare `no <key>` must mean the recipe leaves the key unset. The expected values are
    read from the markdown, the actual ones from the file through the generator's loader. Mutation: edit a
    number in the cell, or the same number in the recipe. Rows that name several recipes (the optical-size pair)
    state no pairs and are skipped."""
    rec = recipes()
    known = {"W", "nib", "thin", "thinGrow", "pow", "xs", "swell", "track", "serifLen", "serifH", "serifBracket", "serifGrow", "flareAmt",
             "tear", "dot", "overshoot", "hzThin", "roundGain", "diagThin", "xh", "joints", "crotch", "cut", "beak"}
    checked = 0
    for r in table_rows():
        ids = re.findall(r"`([a-z][a-z0-9-]*)`", r[0])
        if len(ids) != 1:
            continue
        c = rec[ids[0]]
        for frag in re.findall(r"`([^`]+)`", r[2]):
            for pair in frag.split(", "):
                words = pair.split(" ", 1)
                if words[0] not in known or len(words) < 2:
                    continue
                key, val = words[0], words[1]
                if val in ("true", "false"):
                    want = val == "true"
                elif re.fullmatch(r"-?\d+(\.\d+)?", val):
                    want = float(val)
                elif re.fullmatch(r"(\d+) \* DEG", val):
                    want = float(val.split()[0]) * math.pi / 180
                else:
                    raise AssertionError(f"{ids[0]}: cannot read `{pair}` in the knobs cell")
                got = c.get(key)
                ok = got == want if isinstance(want, bool) else (isinstance(got, (int, float)) and not isinstance(got, bool) and abs(got - want) < 1e-9)
                assert ok, f"{ids[0]}: the table says `{pair}`, the recipe has {key} = {got!r}"
                checked += 1
        for key in re.findall(r"no `([A-Za-z]+)`", r[2]):
            assert key not in c, f"{ids[0]}: the table says no `{key}`, the recipe sets it ({c[key]!r})"
            checked += 1
    assert checked >= 40, f"only {checked} table values were compared; the cells changed shape and the check is hollow"


def test_a_relational_knobs_cell_names_every_difference_from_its_base():
    """A knobs cell that says "the grotesque knobs with W 92, ..." claims the recipe equals the base recipe except for
    what follows. Every key the recipe sets differently from the base (id, name, from and desc aside) must be
    named in that cell, as a backticked pair or as "no `key`"; the pairs' values are checked by the test above.
    Found by review: `geometric` had `track: 4` against `grot`'s 2 and the cell did not say so. Mutation: change a
    key of `geometric` (or `fatface`, `slab`) that the cell does not name."""
    rec = recipes()
    bases = {"didone": "didone", "clarendon": "clarendon", "grotesque": "grot"}
    seen = 0
    for r in table_rows():
        m = re.search(r"the (didone|clarendon|grotesque) knobs", r[2], re.I)
        ids = re.findall(r"`([a-z][a-z0-9-]*)`", r[0])
        if not m or len(ids) != 1:
            continue
        base, c = rec[bases[m.group(1).lower()]], rec[ids[0]]
        named = {pair.split(" ", 1)[0] for frag in re.findall(r"`([^`]+)`", r[2]) for pair in frag.split(", ")} | set(re.findall(r"no `([A-Za-z]+)`", r[2]))
        for k in (set(base) | set(c)) - {"id", "name", "from", "desc"}:
            if base.get(k) != c.get(k):
                assert k in named, f"{ids[0]} differs from {base['id']} in `{k}` ({base.get(k)!r} against {c.get(k)!r}) and the knobs cell does not name it"
        seen += 1
    assert seen == 3, f"expected three relational rows (fatface, slab, geometric), found {seen}"


def test_the_content_file_and_the_recipes_state_the_same_words():
    """content.genres.json repeats each recipe's one-line definition (`desc` = the recipe's `from`), and the
    recipe's own `desc` is the table's verdict cell with markup removed and its first letter capitalised, which is
    also the content `risk`. Mutation: edit content.concepts.didone.desc to describe another face, or a recipe's
    `from` or `desc`."""
    content = json.loads((REPO / "scripts" / "concepts" / "content.genres.json").read_text())["concepts"]
    for i, c in recipes().items():
        assert content[i]["desc"] == c["from"], f"{i}: content desc {content[i]['desc']!r} differs from the recipe's from {c['from']!r}"
        risk = content[i]["risk"]
        assert c["desc"] == risk[0].upper() + risk[1:], f"{i}: the recipe's desc differs from the content risk (the table cell):\n{c['desc']}\n{risk}"


def test_the_documented_build_command_in_the_recipe_file_runs(tmp_path):
    """The comment in concepts.genres.js tells a reader how to build the page. Run that command (the output path
    replaced by a temporary one), so a comment that names a content file the builder refuses fails here. Found
    by review: it once named content.minimal.json, whose `concepts` block names `text` and `display`.
    Mutation: put content.minimal.json back into the comment."""
    text = GENRES_JS.read_text()
    block = text[text.index("// Build the page:"):]
    lines = []
    for line in block.splitlines()[1:]:
        if not line.startswith("//   "):
            break
        lines.append(line[5:].rstrip())
    cmd = shlex.split(" ".join(ln.rstrip("\\") for ln in lines))
    assert cmd[0] == "node" and "build-page.js" in cmd[1], cmd
    cmd[-1] = str(tmp_path / "genres.html")
    r = run(cmd)
    assert r.returncode == 0, f"{' '.join(cmd)}\n{r.stderr}"
    assert "content.genres.json" in " ".join(cmd)


def smoke_8b_script():
    text = (REPO / "scripts" / "smoke.sh").read_text()
    start = text.index('"$HERE/concepts/content.genres.json" <<\'EOF\'\n') + len('"$HERE/concepts/content.genres.json" <<\'EOF\'\n')
    return text[start:text.index("\nEOF\n", start)]


def fake_genres_dom(ids, empty=None, nan=None):
    sections = ""
    for i in ids:
        n = 3 if i == empty else 19
        body = "L1 1" * 200
        paths = "".join(f'<svg><path fill="currentColor" d="M0 0L{"NaN" if i == nan and k == 0 else "1"} 1{body}Z"></path></svg>' for k in range(n))
        sections += f'<section class="part concept" id="concept-{i}">{paths}</section>'
    tail = '<section class="part concept" id="concept-comparison"></section>'
    return f'<html data-fd-round="round1" data-fd-rendered="3330" data-fd-font="loaded"><body>{sections}{tail}</body></html>'


@pytest.mark.parametrize("fault", [None, "empty", "nan"])
def test_smoke_step_8b_asserts_that_every_recipe_drew(tmp_path, fault):
    """Smoke step 8b used to assert only data-fd-rendered > 0 (a sum over the whole page, so one dead recipe
    passed). It now reads each recipe's <section id="concept-<id>"> in the dumped DOM. This runs the real
    script text from scripts/smoke.sh against synthetic dumped DOMs: all ten drawn passes; one recipe with
    too few paths, or with NaN in a path, fails naming the recipe. Mutation: loosen the per-recipe check
    (delete the `bad` assertion) and both faulty cases go green, so this goes red."""
    ids = sorted(json.loads((REPO / "scripts" / "concepts" / "content.genres.json").read_text())["concepts"])
    shots = tmp_path / "shots"
    shots.mkdir()
    for w in (500, 1280):
        (shots / f"genres-{w}@1x.dom.html").write_text(fake_genres_dom(ids, empty="slab" if fault == "empty" else None, nan="grot" if fault == "nan" else None))
    r = run([sys.executable, "-c", smoke_8b_script(), str(REPO / "scripts"), str(shots), str(REPO / "scripts" / "concepts" / "content.genres.json")])
    if fault is None:
        assert r.returncode == 0, r.stderr
    else:
        assert r.returncode != 0 and ("slab" if fault == "empty" else "grot") in r.stderr, r.stderr[-300:]


# --- the review record (review finding T8) ---------------------------------------------------------------------------

RECORD = REPO / "docs" / "reviews" / "genres-2026-11-25.md"
DIGEST = r"""
const crypto = require("crypto"); const m = require(process.argv[1]); const list = m.loadConcepts(process.argv[2]);
const r2 = v => Math.round(v * 100) / 100, out = {};
for (const c of list) {
  const h = crypto.createHash("sha256");
  for (const mult of [1, 1.25, 1.5]) {
    const P = m.params(c, mult, false);
    for (const k of Object.keys(m.G).sort()) {
      const g = m.glyph(k, P); if (!g) continue;
      h.update(JSON.stringify([mult, k, g.polys.map(p => p.map(q => [r2(q[0]), r2(q[1])]))]));
    }
  }
  out[c.id] = h.digest("hex");
}
console.log(JSON.stringify({ node: process.versions.node.split(".")[0], digests: out }));
"""


def current_digests():
    r = run([node(), "-e", DIGEST, str(GEN), str(GENRES_JS)])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def read_record():
    text = RECORD.read_text()
    block = re.search(r"```json digests\n(.*?)\n```", text, re.S)
    assert block, "the review record has no ```json digests block"
    verdicts = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if line.startswith("| ") and len(cells) >= 3 and re.fullmatch(r"[a-z][a-z0-9-]*", cells[0]) and cells[0] != "recipe":
            verdicts[cells[0]] = (cells[1], cells[2])
    return json.loads(block.group(1)), verdicts


def test_the_review_record_holds_the_verdicts_the_table_states():
    """docs/reviews/genres-2026-11-25.md is what the dated verdicts in genres.md rest on: its verdict table (id,
    verdict, date) must equal the table in genres.md for every recipe. Mutation: change one verdict in the record
    or in genres.md."""
    _, verdicts = read_record()
    for r in table_rows():
        m = re.match(r"^\*\*(reaches|partly|no)\*\* \((\d{4}-\d{2}-\d{2})\)", r[3])
        for i in re.findall(r"`([a-z][a-z0-9-]*)`", r[0]):
            assert verdicts.get(i) == (m.group(1), m.group(2)), f"{i}: record {verdicts.get(i)}, genres.md {(m.group(1), m.group(2))}"
    assert sorted(verdicts) == sorted(recipe_ids())


def test_a_verdict_is_stale_when_the_recipe_outlines_change():
    """The recorded verdicts describe what the generator drew on 2026-11-25: a sha256 over every glyph's outline
    (roman, mult 1, 1.25 and 1.5, coordinates rounded to 0.01) per recipe, recorded in the review record BY NODE MAJOR
    (V8 arithmetic can differ between majors; CI runs 20 and 22). On a recorded major whose digest differs, the
    verdict is stale. On a major with no record the test fails with the instructions to record it, which is not a
    claim that anything is stale. Mutation: change one number in a recipe (for example grot's `xh`), for the stale
    message; delete the running major's entry from the record, for the other."""
    recorded, _ = read_record()
    now = current_digests()
    by_major = recorded["by_node_major"]
    assert now["node"] in by_major, (f"no digests are recorded for node {now['node']} (recorded: {sorted(by_major, key=int)}). This is not a stale verdict: "
                                     "confirm the digests of a recorded major still match, then run current_digests() under this node "
                                     "and add the result under by_node_major in docs/reviews/genres-2026-11-25.md")
    rec = by_major[now["node"]]
    assert sorted(rec) == sorted(now["digests"]), "the record and the recipe file name different recipes"
    for i, d in now["digests"].items():
        assert rec[i] == d, f"the genre verdict for {i} is stale: re-run the render review (genres.md section 6)"
