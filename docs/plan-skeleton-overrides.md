# Plan: per-face skeleton overrides (issue #9), with Bract's n, m, h and r as the first use

WHAT IT'S FOR: the implementation plan for issue #9, written by Claude (Fable 5.1) on 2026-11-19 on
branch `feature/per-face-skeletons` from `origin/main` at `5d0b29f` (0.5.0), before any code, for
independent review (Impasse) and then implementation. It adds one optional input to a face: a project
file that edits the skeleton tables before anything is drawn, named by a `font.json` key and by the
concept-page builder's `--skeletons` flag. The first use is Bract's lowercase `n`, `m`, `h` and `r`,
whose shoulder shows a nick where the head serif meets the arch. A second, conditional user is
Driftwood (movingavg.com): its needs are designed for here and its override is **not** part of this
change (section 2.7).

Status: **plan, revision 2 after the Impasse review of revision 1 (section 12: nine findings, all
accepted); no code.** Every number in sections 0, 1 and 4 was produced by
running node against the unmodified `scripts/gen.js` of this worktree (0.5.0) and against override
files applied to it, in a scratch folder outside the repository
(`measure.js`, since ported to `tests/skeleton_probe.js`'s `shoulder` mode, reads the top edge; `compare.py` diffs two exports; `mod/` is a copy of `gen.js` and
`export.js` with a six-line prototype hook; `ovr/*.js` are the candidate overrides; `exports/` holds
the export JSON of Bract's roman group before and after each candidate). That folder is session-scoped
and not evidence anyone else can re-run; the implementation commits the probe as
`tests/skeleton_probe.js` and the hop-safari half as `tests/bract_shoulder.js` there, and every figure
here is re-stated from their output before the version is bumped (the rule `docs/plan-r-leg.md` took
from review finding F008).

**Markers.** **(read)** = checked against the named file. **(measured)** = run or counted here.
**(inferred)** = not verified; the implementer must check before relying on it.

## 0. The defect, measured

### 0.1 What the generator draws today

The roman `n` is two strokes (read: `scripts/gen.js` lines 72–73): the stem `S("M 90 500 L 90 0", "s", "s")`
and the arch-plus-right-stem `S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s")`.
`h` (line 63) uses the same arch on a 740-tall stem; `m` (lines 69–71) uses two shorter arches that start
at `y` 390; `r` (lines 79–80) uses the same arch start and ends in a free terminal at (405, 455). The
stem's head is the lowercase one-sided wedge serif (`serifPoly`, lines 466–471): at the stem's right
edge it rises to `y + 0.18·h` above the stem's top, with `h = SW × serifH` (48 units for Bract's `text`
cut: 96 × 0.5). The arch's control points at 510 are the round overshoot: the fit moves them to
`500 + overshoot − hw` and the drawn top edge lands at 510 (read: `fitSkeleton`, `ROUND`, lines 808
and 867–868).

Measured with `measure.js` over the drawn polygons (the stem body, the head serif and the arch body are
found by shape; the "top profile" is the maximum `y` of every polygon at each `x`, which is the filled
union's upper edge because the glyph has no holes), on hop-safari's `tools/bract/concepts.js` at the
four masters:

| Master | serif top at the stem's right edge | arch's upper edge where it leaves the stem | arch peak | nick depth (serif top − lowest profile point just right of the stem) | nick width (to where the profile regains the serif height) |
|---|---|---|---|---|---|
| `n` TextRegular (W 96) | **508.6** | **480.1** | **510.3** | **28.3** units (1.1 px at 40 px) | 113 units |
| `n` TextBold (W 144) | 510.0 | 490.2 | 511.0 | 19.6 (0.8 px at 40 px) | 127 |
| `n` DisplayRegular (W 104) | 507.5 | 479.3 | 510.4 | 28.0 (2.2 px at 80 px) | 101 |
| `n` DisplayBold (W 156) | 508.6 | 489.3 | 511.4 | 19.2 (1.5 px at 80 px) | 101 |
| `m` TextRegular | 508.6 | 487.4 | 510.4 | 21.0 | 89 |
| `m` TextBold | 510.0 | 495.1 | 511.4 | 14.7 | 97 |
| `m` DisplayRegular / DisplayBold | 507.5 / 508.6 | 486.9 / 494.8 | 510.6 / 512.2 | 20.4 / 13.7 | 78 / 74 |
| `r` TextRegular | 508.6 | 479.7 | 524.0 (the drop) | 28.7 | 115 |
| `r` TextBold | 510.0 | 489.8 | 531.4 | 20.0 | 156 |
| `r` DisplayRegular / DisplayBold | 507.5 / 508.6 | 479.0 / 489.0 | 523.5 / 531.3 | 28.3 / 19.5 | 102 / 102 |

Command (measured): `node measure.js <worktree>/scripts/gen.js <hop-safari>/tools/bract/concepts.js text:1,text:1.5,display:1,display:1.5 n,m,h,r`.
No join cap pokes above the outline anywhere (the "nub" column of the probe is 0.0 in every row).

**The issue's numbers, checked.** "Serif to y 508 at the stem's right edge": holds (507.5–510.0 over
the four masters). "Arch peaks at 510": holds (510.3–511.4). "Leaves the stem near y 475": **low**;
measured 480 on the two Regulars and 489–490 on the two Bolds (the Bolds' thicker arch leaves higher),
and 487–495 on `m`, whose arch starts at 390. The nick itself is 28 units deep and about 100 wide on
the Regulars, 20 deep on the Bolds, so the defect reads as the issue says: a flat top line with a
notch just right of the stem, one pixel deep at 40 px and two at 80 px.

**`h` has no nick.** Its stem is 740 tall, so its head serif sits at the ascender and the arch leaves
the stem 260 units below it, as in every `h`. The issue lists `h` because it shares the arch stroke
with `n` (read: the two strings are identical), not because it shows the defect. Whether `h` changes is
therefore a consistency question: under a fix that redraws the arch (candidate B, section 4) `h` follows
`n` so the two shoulders match; under a fix that only moves the serif (candidate A) `h` is untouched.

### 0.2 The same skeleton under other pens

The same probe on the other concept files (measured; `n` at mult 1):

| Concept (file) | stem end | serif top at stem edge | arch leaves at | arch peak | nick | note |
|---|---|---|---|---|---|---|
| `foil` / genres `scotch` (thin flat serif) | serif | 502.6 | 485.5 | 510.0 | 16.9 | the serif is lower than the arch: a notch, not a step |
| `burin` | serif | 505.1 | 478.4 | 510.4 | 26.4 | as Bract |
| `blind` (serifH 0.85) | serif | **517.4** | 494.8 | 510.1 | never regains | the serif stands 7 above the arch: candidate A's shape, for free |
| genres `clarendon` | serif | 516.5 | 491.6 | 509.5 | never regains | the same |
| genres `didone`, `slab` (serifBracket 0, serifH 0.13) | serif | 500.0 | 482.4 / 491.6 | 510.0 / 509.5 | 17.3 / 8.2 | the slab is level with the stem top |
| `field` | serif | 507.5 | 458.9 | 509.3 | 48.0 | the shallowest arch departure in the set |
| `driftwood` (W 88, serifH 0.4) | serif | 506.3 | 468.0 | 510.4 | **38.1** (27.6 at mult 1.5) | deeper than Bract |
| neutral `text` / `display` | serif | 510.8 / 509.7 | 491.5 / 493.8 | 509.9 / 509.9 | 19.1 / 15.8 | |
| `bine` (ends.s butt, fit on) | butt | 500.0 | 482.4 | 510.3 | 17.4 | the arch rises 10 above the flat stem top: the issue's "ordinary small corner" |
| `tideline` (butt, **no fit**: `overshoot` unset) | butt | 500.0 | 494.3 | 542.7 | 5.3 | without the fit the arch top sits 43 above the stem cut |
| `dune` (ends.s disk, no fit) | disk | cap top 543.7 | 505.9 | 552.8 | — | the cap stands 38 above where the arch leaves and 9 below the arch's peak |
| genres `grot` (xh 540, joints) | butt | 540.0 | 528.1 | 548.8 | 11.6 | |

So the shoulder of this one skeleton reads three different ways depending on the pen: a serif standing
above the arch (`blind`, `clarendon`: 7 units), a serif level with the arch and a nick beside it
(Bract, `burin`, Driftwood, the neutral example: 19–38 units), or a stem lower than the arch (`foil`,
`didone`, the sans recipes: a 10–17 unit corner). A change to `G.n` that fixes Bract moves every one
of these, and only Bract's and Driftwood's have been design-reviewed on a page; `clarendon`'s and
`blind`'s shapes are what Bract's candidate A would produce. That is the case for a per-face override
rather than a change to the shared table, and the measurements support the issue on this point. The
alternative, a generator rule that places the arch relative to the serif's drawn corner, is a
pen-dependent construction that would change all twelve faces at once and is not planned.

## 1. What the mechanism must do, and what it must not change

1. A `font.json` may name one JavaScript file, `skeletons`, **a bare file name beside `font.json`**
   (review F008: no directory part, so the manifest's basename key and hop-safari's `SOURCE_HOMES`
   resolution both hold), exporting `function (G, GI, S, D, ring)` that edits the two tables in place:
   replaces entries, adds entries. One file serves every group and every master of the face (section 2.1).
2. `export.js` applies it before drawing anything and records the file's sha256 in the export JSON;
   `build.py` hashes it into the manifest beside the five sources it hashes today (read:
   `SCRIPT_SOURCES`, `compose_manifest`, lines 151 and 1290–1292), records its name, and refuses a
   `--masters` export drawn with another override or with none (review F002), so `--check`, the two
   manifest tests and hop-safari's `font-diff.py` see an edit to it as they see an edit to `gen.js`.
3. `build-page.js --skeletons PATH` splices the same file into a concept page, so rounds 1–3 draw the
   face's letters (read: `build-page.js` already takes `--gen` and `--render` for the copy-and-patch
   convention, lines 48–50 and 222–223).
4. Glyphs derived from a base (the accented letters) follow the base (section 2.4). A roman override
   reaches an italic group wherever `GI` has no entry of its own (section 2.5).
5. A `font.json` without the key builds byte for byte as today: the export JSON, the woff2 and the
   manifest. `tests/test_backward_compat.py` against the unchanged `tests/fixtures/baseline.json` is the
   proof. A `font.json` **with** the key naming an empty override builds the same woff2 bytes; its export
   carries two more fields and its manifest three more or changed values (the key, the override's hash,
   and `font.json`'s own hash, which the key changes; review F001). Section 5's test a states both.
6. Every departure from the shared table is printed on every export, and refused loudly when malformed
   (section 2.6).

Not in this change: per-concept skeletons for round 1's structural alternatives (section 2.1 says why
they do not fall out for free), Driftwood's own override file (section 2.7), any change to `GI.w` or to
the italic opening quotes' advance (another PR, section 10), and any change to a shared skeleton.

## 2. Design decisions

### 2.1 Scope: one file per `font.json`, shared by every group and master

**Decided: per face.** The file is named once in `font.json` and applied identically for every group
(`export.js` runs once per group, each run applying the file) and so for every master. Per-master or
per-concept skeletons are rejected for round 1:

- Masters of a group must share a skeleton or `varLib` cannot interpolate them, which is what the
  exporter's compatibility check enforces (read: `export.js` lines 184–194). A per-concept override
  would make the two masters of one group able to disagree, and the exporter would then refuse the
  group with a message about branch records that is about the wrong thing.
- Per-concept skeletons do **not** fall out for free. `glyph()` reads the module-level `G` and `GI`
  (line 954) and caches by `P.key` (lines 952–953); the composites are built at load (lines 236–281);
  `kern()` reads `glyph("n", P)` as its reference (line 1158). Letting a concept carry its own tables
  means threading a table reference through `glyph()`, `kern()`, the cache key and the derivation, and
  teaching the exporter which disagreements are legal. That is a second mechanism, and the one planned
  here is a prerequisite for it (the override function and the derivation rerun are reusable). It is
  recorded as the follow-on in section 11, not built.
- Driftwood's stated need (section 2.7) is exactly per face: one override shared by every master of a
  group and by both groups for `t`.

### 2.2 The file's contract

```js
// tools/<face>/skeletons.js
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 480 C 170 510 225 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s");
  // ...
};
if (typeof module !== "undefined") module.exports = SKELETONS;
```

The same shape as `concepts.js` (read: `loadConcepts`, line 1229, and `stripExports` in `build-page.js`,
lines 64–76): a CommonJS module in node, and a script that leaves one global, `SKELETONS`, when spliced
into a concept page. The function mutates the two live tables; its return value is ignored. It receives
the three constructors `S`, `D` and `ring` so an entry is written in the grammar of `generator.md`
section 2, and nothing else: the mark helpers (`acute`, `tilde`, `raise`, `exitStem`) stay private in
round 1, because exposing them fixes their signatures as an API (section 11 asks whether to expose them).

Every key is present while the function runs, composites included. **A composite the override touches
is the override's; a composite it leaves alone follows its base** (section 2.4): `G["ñ"] = [...]` or
`G["ñ"][0] = ...` both count as touched (the comparison is by content, not by reference) and are kept;
an untouched `G["ñ"]` is rebuilt from the overridden `G.n`. (Revision 1 deleted the composites before
the call and refused in-place edits; review F004 showed the key-set bookkeeping that needed was wrong
for `©`, `™` and `•`, and the content rule needs no bookkeeping at all.)

**Two limits of the contract**, stated here and in `generator.md`: an added key must be mappable (a
single code point, or a `LIGS` name; 2.6 item 4), and an italic-only addition is refused (a new `GI` key
with no `G` counterpart; review F003: `export.js` draws `Object.keys(m.G)`, line 147, so the italic
export would leave it out in silence). And the accented capitals exist only in `G` (`gen.js` lines
269–273: `Á À Â Ä É È Ê Ë Í Ï Ó Ô Ö Ú Ü Ñ Ç` are `G[base].concat(...)`; `GI` has none), so an italic
group draws them from the roman table slanted, today and after an override of `GI.A`: overriding an
italic capital does not reach its accented forms (review F009). An override that wants italic `Á`
assigns `GI["Á"]` itself. The no-key output is unchanged by stating this.

### 2.3 Where it is applied: `gen.js` owns the application, callers only name the file

`gen.js` gains `applySkeletons(fn)` and exports it. It does, in order: deep-snapshot the two tables
(JSON of every entry, so an in-place edit of `G.n[1]` is seen as a change, not only a reassignment);
call `fn(G, GI, S, D, ring)`; run the guardrails (section 2.6); rerun the derivation (section 2.4) for
every derived key whose content the override did not change; reset the glyph cache (`cache = {}`, line
880, so a draw made before the call cannot be served afterwards); mark the module as applied, so a
second call throws ("skeletons already applied in this process"; a test that needs two overrides runs
two processes, as `tests/test_r_leg_join.py` does); and return a report
`{ overridden: ["G n", "G m", ...], added: [...], rederived: ["G ñ", ...] }`.

Callers:

- `export.js`: `loadFontConfig` validates the key (a string, a bare file name ending `.js` with no `/`
  or `\`, the file exists beside `font.json`; else "font.json skeletons must name a .js file beside
  font.json: <value>" or "names no file") and sets `cfg._skeletonsPath`. `main()` calls
  `m.applySkeletons(require(cfg._skeletonsPath))` right after `loadConcepts` and **before**
  `Object.keys(m.G)` (line 147 moves below it), prints one stderr line
  `skeletons <name>: overrides G n, G m, G h, G r; re-derives G ñ` (and `adds ...` when any), and writes
  two fields into the export JSON **only when the key is set**: `skeletons` (the name) and
  `skeletonsSha256` (the file's sha256, read at apply time), so an export without the key is
  byte-identical. `templates/export.schema.json` has `additionalProperties: false` at the top level
  (read: line 8), so both keys are added there as optional strings.
- `build.py`: `compose_manifest` adds `sources[cfg["skeletons"]] = sha256(path)` and
  `manifest["skeletons"] = cfg["skeletons"]` **only when the key is set** (an unconditional
  `"skeletons": null` would move the manifest digest of every project; read: `tests/baseline_digest.py`
  `manifest_digest`, which drops only `sources_sha256` and `tools`). The name may not be one of the five
  existing source names (refused) and may carry no directory part (refused, the same rule as the
  exporter's). The stderr line from `export.js` already reaches the build log (read: `run_export` writes
  `r.stderr`, line 1090). **The `--masters` path is guarded** (review F002): `PARAMS_JS` (lines 944–952)
  re-reads only `params()` and neither applies nor hashes the override, so a stale export drawn before
  an override edit, or with no override, would have been built and recorded under the current file's
  hash. `load_masters` therefore refuses, naming both values, an export whose `skeletons` presence or
  name disagrees with `font.json`'s key, or whose `skeletonsSha256` differs from the file's sha256 now.
- `build-page.js --skeletons PATH`: reads the file, `stripExports` it like `concepts.js`, and splices
  it **wrapped**, after `gen.js` and `render.js` and before `concepts.js` at the `/*GEN*/` marker (the
  same splice, appended: no new template marker, so the three templates are untouched):

  ```js
  var SKELETONS = (function () { /* ---- skeletons.js ---- */ <stripped source> ; return SKELETONS; })();
  applySkeletons(SKELETONS);
  document.documentElement.setAttribute("data-fd-skeletons", <the report's overridden and added keys, joined>);
  ```

  The wrapper is review F006: `topNames` (lines 249–253) reads only `var` and `function` declarations
  and compares the template's names against the sources', never the sources against each other
  (`concepts.js` and `gen.js` both declare `DEG` today, so a pairwise check cannot be added without
  breaking every page). Wrapped, the override declares exactly one top-level name, `SKELETONS`, and
  `build-page.js` checks that name, and `data-fd-skeletons`, against the template's and every other
  source's top-level names (`var`, `function`, `let`, `const`, `class`) and refuses a clash. Before
  splicing, `build-page.js` also `require`s the file and calls `applySkeletons` on a fresh `gen.js`
  module (a `require` of the file through a cache-busting query is not available for CommonJS; the
  implementer loads `gen.js` in a child `node -e`, as `build.py`'s `PARAMS_JS` does), so every refusal of
  2.6 fires at build time with its message, not in a browser console. The `data-fd-skeletons` attribute
  is the page's own evidence that the call completed (it throws otherwise), read by `shoot.py --dump-dom`
  in test g and in the smoke run. Without the flag nothing is appended: the page is the page built
  today. The `--gen` and `--render` flags stay for anyone still on the copy-and-patch convention, which
  the docs stop recommending (section 7).

### 2.4 Derived glyphs: which bases have derivatives, and the rerun

(read: `gen.js` lines 236–281; the coordinator's second-hand claims about `a` and the accented `a`s
were checked here and hold.) Every assignment below runs at module load, from the base's entry at that
moment, so without a rerun an override of a base leaves its derivatives on the old drawing:

| Table | Base | Derived keys | How |
|---|---|---|---|
| `G` | `a` | `á à â ä` (line 248–252, `if (!G[k])`), `ā` (238) | `G.a.concat(mark)` |
| `G` | `e` | `é` (239), `è ê ë` (248–252) | `G.e.concat(mark)` |
| `G` | `o` | `ó ò ô ö` | the same |
| `G` | `u` | `ú ù û ü` | the same |
| `G` | `n` | `ñ` (255) | `G.n.concat(tilde(275))` |
| `G` | `c` | `ç` (256) | `G.c.concat(...)` |
| `G` | `s` | `š` (237) | `G.s.concat(...)` |
| `G` | `A E I O U N` | `Á À Â Ä É È Ê Ë Í Ï Ó Ô Ö Ú Ü Ñ` (270–272) | `G[base].concat(raise(mark, 170))` |
| `G` | `C` | `Ç` (273) | `G.C.concat(...)` |
| `G` | (none) | `í ì î ï` (253) | `DOTLESS_I.concat(mark)`: a literal, not `G.i`; an override of `i` does **not** reach them |
| `GI` | `a` | `ā á à â ä` (275, 277) | `GI.a.concat(...)` |
| `GI` | `e` | `é è ê ë` (276, 278) | `GI.e.concat(...)` |
| `GI` | `u` | `ú ù û ü` (279) | `GI.u.concat(...)` |
| `GI` | `n` | `ñ` (280) | `GI.n.concat(tilde(275))` |
| `GI` | (none) | `í ì î ï` (281) | `exitStem(110, 500, "s")`, a literal |

Not derived, and so not followed: the ligatures `fi fl ff` are authored (lines 167–170, 206–209), so an
override of `f` or `i` does not reach them; **`©`, `™` and `•` (lines 257–260) are authored entries that
happen to sit inside the derivation block** and must not be treated as derived (review F004: a
before/after key-set comparison over lines 236–281 would have listed them, and a rerun would then have
overwritten an override of `©`); `GI_CAPS` is authored and merged into `GI` at load (line 235), which is
where it stays, before any override runs; the accented capitals exist in `G` only (2.2, review F009).

**The rerun.** Each base-built assignment in lines 237–281 becomes a registered derivation:
`derive(G, "ñ", function () { return G.n.concat(tilde(275)); })`, which at load assigns the key if absent
(what `if (!G[k])` already does for `á à â ä`, line 251) **and** records `{table, key, build}` in
`DERIVATIONS`, in file order. `©`, `™` and `•` keep their plain assignments where they are, so the
load-time tables and their key order are exactly today's. `applySkeletons` reruns every registered
derivation whose key's content the override did not change (the deep snapshot of 2.3 decides), by
assigning in place, so the glyph order is unchanged too; a derivation whose key the override touched is
skipped and the key is reported as overridden. `DERIVED` is `DERIVATIONS.map(d => d.key)`: a list the
code builds, not a hand-kept one. The helpers (`acute`, `grave`, `circ`, `diaer`, `tilde`, `raise`,
`exitStem`, `DOTLESS_I`, `BASES`, `CAPS`) stay module-level.

For Bract's first use the rerun reaches exactly one glyph: `G["ñ"]` follows `G.n`. Bract's `charset.required`
does not name `ñ` (read: `tools/bract/font.json`), but every key of `G` is a glyph in the font (131
glyphs, read: the export log), so `ñ`'s outline changes in the woff2 and `font-diff.py` lists `uni00F1`
beside `n m h r` (section 10). Leaving `ñ` on the old arch would be an inconsistency inside one font;
the rerun is the right default.

### 2.5 An italic group that falls back to `G` sees the `G` override

`glyph()` reads `(P.italic && GI[key]) || G[key]` from the live tables at draw time (read: line 954), and
`applySkeletons` edits those tables, so a `G` override reaches the italic for every key `GI` lacks:
`t` (the coordinator's case: `GI` has no `t`; read: lines 178–210, 214–234) and the whole of the roman
set outside `GI`'s 47 keys. An override that **adds** `GI.t` makes the italic stop falling back, which
is the way to give the italic its own form. `GI` entries that exist (`GI.a`, `GI.r`) are untouched by a
`G` override of the same key, as the coordinator expects.

### 2.6 Guardrails, and the one in the issue that is not needed

Refused by `applySkeletons`, each naming the file, the table, the key and the stroke index:

1. The module does not export a function.
2. A key present before the call is absent after it (an override may not delete; a required character
   that vanished would otherwise surface only through `--requirements`, and an unrequired one not at
   all).
3. An entry is not an array of at least one stroke, or a stroke is not one of the three shapes, checked
   by an **explicit validator** (review F005: `sampleCounts` and `samplePath`, lines 298–333, skip a
   token they do not recognise, so a `Q` or a stray number is silently dropped today, not refused; the
   validator is new code, not a reuse): `{d, a, b}` with `d` a string whose tokens (split on whitespace
   and commas) start with `M` and two finite numbers, continue with `L` plus two or `C` plus six finite
   numbers, contain at least one `L` or `C`, and nothing else, and `a`, `b` each in `"" s t u x j i`;
   `{dot: [x, y]}` with two finite numbers; a ring, `{d, closed: true, r: [cx, cy, rx, ry]}` with four
   finite numbers, `rx` and `ry` positive, and `d` equal to what `ring(cx, cy, rx, ry)` produces.
4. A new key that the cmap cannot map: longer than one code point and not in `LIGS` (read: `cmap_for`
   and `gname`, `build.py` lines 185–194 and 417–435: a one-character key maps by its code point, a
   `LIGS` key is a ligature glyph, anything else becomes a glyph with no code point and no feature).
5. A new `GI` key with no `G` counterpart (review F003: the export's glyph list is `Object.keys(m.G)`,
   so an italic-only addition would be drawn by nothing). An override adding a glyph adds it to `G`,
   and to `GI` as well when the italic form differs.
6. A second call in one process.

**Not built: "refuse an override that changes a glyph's stroke count between roman masters".** Under
per-face scope every master of a group draws from the same table, so stroke counts cannot differ
between masters by construction; the exporter's compatibility check (lines 184–194) already refuses the
case where the pen makes them differ, naming the glyph. **Not built as a refusal: "shadows a composite's
base without the composite".** The rerun (2.4) makes the composite follow the base, and the stderr
report names what was re-derived, so the case is handled rather than refused.

### 2.7 Driftwood's stated needs, checked and designed for (not built here)

The movingavg-website session may take this hook. Its claims, each checked against `gen.js` (read):
`G.r`'s arm is `C 345 510 385 495 405 455` (line 80) and would become `C 330 510 360 500 380 480`;
`G.t`'s stem starts `"x"` (line 84) and would become `"s"`; `G.a`'s bowl joins at `440 290` and runs
`90 280 90 140` (line 51) and would become `440 270` and `90 260 90 130`. `GI` has no `t` (2.5), so the
italic draws the overridden `G.t`; `GI.a` and `GI.r` exist and stay. The accented `a`s are derived from
`G.a` and `GI.a` (2.4) and follow through the rerun. Every one of those needs is met by one `skeletons.js`
named once in Driftwood's `font.json`, applied to both groups. Nothing Driftwood-specific is written in
this change; section 5's tests c and d use its `a` and `t` as fixtures because they are the cases the
mechanism must get right.

## 3. The generator, exporter, builder and page-builder changes, listed

| File | Change |
|---|---|
| `scripts/gen.js` | header comment item 8 (the hook); `derive(table, key, build)` and `DERIVATIONS` replacing the base-built assignments of lines 237–281 in place (`©`, `™`, `•` untouched); the stroke validator; `applySkeletons(fn)` with the six refusals, the rerun, the cache reset, the once-only mark and the report; exported beside `G`, `GI`, `S`, `D`, `ring` |
| `scripts/export.js` | `loadFontConfig`: the key's checks (bare `.js` name, exists) and `cfg._skeletonsPath`; `main`: apply before `keys`, the stderr report line, `skeletons` and `skeletonsSha256` in the output when set |
| `scripts/build.py` | `compose_manifest`: the sixth source hash and the `skeletons` name when set; the name refusals; `load_masters`: the presence and hash comparison against `font.json` and the file (F002); the module docstring's list of hashed sources |
| `scripts/concepts/build-page.js` | `--skeletons PATH`; the build-time application in a child node; the wrapped splice, the call and the `data-fd-skeletons` line; the clash check widened to `let`/`const`/`class` and to the new names against every source; header comment and the `args()` list |
| `templates/font.schema.json` | `"skeletons": { "type": "string", "pattern": "^[^/\\\\]+\\.js$", "description": ... }` beside `concepts` |
| `templates/export.schema.json` | optional top-level `skeletons` and `skeletonsSha256` strings |

Estimated size: about 120 lines in `gen.js` (the derivation registration, the validator, the apply
function), 35 in `export.js`, 30 in `build.py`, 45 in `build-page.js` (inferred from the prototype hook,
which was 2 lines, and the lists above).

## 4. Bract's override: the two candidates, measured

The issue names two fixes. Both were drawn as override files against the 0.5.0 generator and measured
with the probe of section 0 and with a full export of Bract's roman group compared field by field with
the shipped generator's export (`compare.py`: glyphs whose `adv`, `polys`, `raw`, `runs`, `keptIdx` or
`minw` differ; kern pairs whose value or presence differs; `titles`, `space`, `minStrokeWidth`).

### 4.1 Candidate A: raise the wedge serif above the arch

The only skeleton change that raises the serif is a taller first stem (the serif's height is the pen's
`serifH`, shared by every serif). `A20`: `G.n[0]`, `G.m[0]`, `G.r[0]` become `S("M 90 520 L 90 0", "s", "s")`;
`h` untouched.

| Master | serif top at stem edge | serif − arch peak | export: glyphs changed | advances changed | kern pairs changed (of 4,100) | of those on pairs **without** `n m r` | pair list |
|---|---|---|---|---|---|---|---|
| TextRegular | 528.6 | +18.3 | `m n r` | **`m n r`** | **1,777** (worst 45) | 1,607 | 4,100 → 4,070 |
| TextBold | 530.0 | +18.9 | `m n r` | `m n r` | 1,497 (worst 47) | 1,344 | 4,070 |
| DisplayRegular | 527.5 | +17.0 | `m n r` | `m n r` | 1,642 (worst 81) | 1,460 | 4,070 |
| DisplayBold | 528.6 | +17.2 | `m n r` | none | 1,324 (worst 28) | 1,172 | 4,070 |

`A15` (stem to 515) gives +12 to +14 and the same pattern. **Why the whole lowercase re-kerns:** `kern()`
measures every lowercase pair against the `n|n` reference gap (read: line 1158–1160), and the taller
serif changes `n`'s left profile in the bins near the x-height, so its sidebearing, its advance and the
reference gap all move, and every pair's kern moves with the reference. Thirty pairs leave the list
(their value fell under the threshold of 12 in every master), which changes the GPOS structure. The
`titles` widths change in every master. Candidate A is therefore not a four-glyph change but a
respacing of the face; `font-diff.py` would list hmtx, HVAR and most GPOS pairs. It stays on the gate's
crop because the issue asked for it, with this cost printed beside it.

### 4.2 Candidate B: start the arch at the serif's corner

The arch's start moves up the stem and its first control points sit **on the 510 line**, so the fit sees
them. (A first attempt with a control at 505, `B2`, bulged to 517.8 at the peak in the Bold, because
`ROUND` moves only control points that sit exactly on 510; read: line 867. Draw new arch controls on the
fit lines, as `generator.md` section 7 says.) `B7`, the closest to "one line" without overshooting:

```js
G.n[1] = S("M 90 480 C 170 510 225 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s");
G.h[1] = the same string;
G.m[1] = S("M 90 484 C 160 510 205 510 260 510 C 360 510 405 450 405 350 L 405 0", "", "s");
G.m[2] = S("M 405 484 C 475 510 520 510 575 510 C 675 510 720 450 720 350 L 720 0", "", "s");
G.r[1] = S("M 90 480 C 170 510 225 510 290 510 C 345 510 385 495 405 455", "", "t");
```

| Master | `n` nick | `m` nick | `r` nick | arch peak | `r` arm minimum width | export: glyphs changed | advances / titles | kern pairs changed | on pairs without `n m h r` |
|---|---|---|---|---|---|---|---|---|---|
| TextRegular | 28.3 → **4.0** | 21.0 → 1.7 | 28.7 → 4.2 | 510.3 | 41.61 → 46.03 | `h m n r` | none / equal | 14, each by 1 unit | 13 |
| TextBold | 19.6 → 0.2 | 14.7 → 0.1 | 20.0 → 1.3 | 511.1 | 50.99 → 57.06 | `h m n r` | none / equal | 7, by 1 | 6 |
| DisplayRegular | 28.0 → 4.6 | 20.4 → 2.3 | 28.3 → 4.8 | 510.5 | 32.78 → 36.02 | `h m n r` | none / equal | 29, by 1 | 14 |
| DisplayBold | 19.2 → 1.5 | 13.7 → −0.3 | 19.5 → 1.8 | 511.5 | 40.16 → 45.94 | `h m n r` | none / equal | 21, by 1 | 20 |

`B5` (start at 465) halves the nick instead (10.4 / 6.2 / 9.8 / 5.9 on `n`) with the same export pattern.
Three things the table settles:

- **The hairline floors hold, with more room.** `r`'s arm is the thinnest interior stroke of three of
  the four shipped masters today (41.61 against a floor of 41 on TextRegular; read: the export log and
  `HAIRLINE_FLOORS` in hop-safari's `tests/test_bract_font.py`). The redrawn arm no longer runs at the
  nib angle in its interior, so its minimum rises by 3–6 units and the face's minimum moves to `U`
  (41.62 / 50.99 / 32.79 / 40.16: every floor still holds).
- **A few kerns outside the four glyphs move by one unit, and the cause is structural.** `n`'s right
  stem is the same stroke as its arch, so the redrawn arch changes that stroke's sample count and the
  right stem's edge points move by hundredths (measured: `R` profile bins 18–38 by 0.01–0.05 units, `L`
  unchanged, advance 637.574 → 637.566, rounding the same). Every lowercase pair is kerned against the
  `n|n` gap, so a change of hundredths in the reference re-rounds the pairs that sat nearest a half
  unit: 7–29 per master, each by exactly 1 unit, `&|o` −76 → −75 among them (`why.js`, measured).
  This is inherent to overriding the reference glyph and is accepted as a listed, bounded consequence
  (section 10 states the count the rollout must see); pinning the reference to a frozen `n` would change
  the generator's kerning for every face and is rejected.
- **Nothing else moves.** No advance, no title width, no word space, no other glyph's outline, record
  or minimum.

### 4.3 The gate: before, A and B on a real page at 1×

The operator chooses on crops, not on numbers. Section 9 step 6 builds three fonts into scratch
(`build.py --out-dir` from three copies of `tools/bract/{font.json, concepts.js, requirements.json}`:
no override, `A20`, `B7`), then:

1. `scripts/diff.py` with `--before` on the shipped font against each candidate at Bract's `review.sizes`
   (read: the tool renders every size and reports changed glyphs), for the specimen-level before/after.
2. `scripts/shoot.py` on a copy of hop-safari's `static-pages` with the candidate woff2 copied over
   `fonts/bract/Bract-VF.woff2`, pages `essays.html` (Regular and Medium at text sizes, many `n m r`) and
   one essay whose H1 sets `n`, `m` and `r` at the display size, widths 1280 and 500, scale 1 and 2,
   `--family Bract --font-url /fonts/bract/Bract-VF.woff2`.
3. Crops at 1× of the same words in all three fonts, side by side, read before 2×; the kern and
   advance cost of A beside its crop (4.1).

The operator names A, B, a B with a different arch start (the probe reports the nick for any file in
seconds), or neither. Neither ends the hop-safari half; the skill half ships regardless, with the
neutral fixture's tests. Recommendation: **B7**. It removes the nick to within 0.2 px at 40 px, moves
no advance and no title, leaves the floors with more margin, and keeps the shoulder's weight; A's
shape exists already in `blind` and `clarendon` and costs a face-wide respacing.

## 5. Tests, each with the mutation that must turn it red

A new `tests/test_skeleton_overrides.py` and a node probe `tests/skeleton_probe.js` (it loads a `gen.js`,
applies an override file, and prints the drawings, records, profiles and the report as JSON, the way
`tests/r_leg_junction.js` does). Fixtures under `tests/fixtures/skeletons/`: `font.json` (the neutral
example's with `"skeletons": "skeletons.js"` and paths to the neutral `concepts.js` and
`requirements.json`), `empty.js` (a function that does nothing), `bract-shoulder.js` (B7, 4.2),
`driftwood-a-t.js` (the `a` and `t` of 2.7), `bad-*.js` (one per refusal), each free of site hostnames
(read: `tests/test_hygiene.py::test_no_forbidden_string_anywhere_in_the_tree`). Mutations go on a scratch
copy of `scripts/` named by `FONT_DESIGN_SK_GEN` (as `FONT_DESIGN_R_GEN` does), and the log goes into
`references/testing.md` section 8.

| | Test | Asserts | Mutations that must turn it red |
|---|---|---|---|
| a | `test_a_font_json_without_the_key_builds_as_today`, `test_an_empty_override_changes_only_its_own_record` | **(i)** the existing `tests/test_backward_compat.py` stays green on the unchanged `baseline.json` (the derivation registration and the new code paths leave every digest; this is the no-key proof, and the only one needed for it). **(ii)** the neutral example built with `build.py --out-dir --keep-masters` as it is, and again from the fixture `font.json` naming `empty.js` (review F001: the key is set, so the record differs by construction): the two exports are equal once `skeletons` and `skeletonsSha256` are deleted from the second, and those two fields are present there with the sha256 of `empty.js`; the **woff2 bytes are equal**, asserted on their own; the manifests differ in exactly three values: `skeletons` (absent → the name), `sources_sha256["skeletons.js"]` (absent → the file's sha256) and `sources_sha256["font.json"]` (the key changed the file; `build.py` line 1291 hashes it), and in nothing else | **M1** `derive(G, "Ñ", ...)` dropped: the compat test is red on the bract and neutral export and TTF digests (a glyph gone). **M2** the rerun assigns by delete-and-re-add instead of in place (the glyph order moves): (ii) is red on the woff2 bytes while the export glyph set is equal. **M3** `build.py` writes `"skeletons": null` when the key is absent: the compat manifest digest is red on all five groups. **M4** `export.js` writes `skeletons: null` when absent: (i)'s export digest is unchanged (the digest drops unknown fields; read: `export_digest`), so the mutation for the exporter half is M4' = the export written **with** the two fields but the woff2 differing by one advance when the key is set: (ii) red on the bytes. **M4''** `sources_sha256["font.json"]` not re-hashed (the previous manifest's value kept): (ii) red on "exactly three" |
| b | `test_an_override_reaches_every_master_and_nothing_else` | `bract-shoulder.js` on `examples/bract/font.json` (a copy with the key): in every master the glyphs whose `adv`/`polys`/`raw`/`runs`/`keptIdx`/`minw` differ from the bare export are exactly `{h, m, n, r, ñ}` (`ñ` through the rerun), no advance differs, `titles` and `space` are equal, and every kern pair that differs does so by at most 1 unit; the stderr carries `overrides G h, G m, G n, G r` and `re-derives G ñ`; the export's `skeletonsSha256` is the file's | **M5** the override applied to a deep copy of the tables, not the live ones: the changed set is empty. **M6** the rerun skipped: `ñ` leaves the changed set. **M7** the report built from reference equality instead of content: `G n` (edited in place) leaves the stderr line. **M7'** the hash taken of `concepts.js`: red on `skeletonsSha256` |
| c | `test_derived_glyphs_follow_an_overridden_base` (the Driftwood trap) | `driftwood-a-t.js` sets `G.a[1]` and `GI.a[1]` in place, assigns `G["ñ"]` whole, and edits `G["©"][1]` in place (review F004); drawn roman and italic at mult 1 and 1.5: the first two strokes' polygons of `á à â ä ā` equal the overridden `a`'s (roman) and of `GI` `á à â ä ā` the overridden italic `a`'s; `G["ñ"]` is the override's, not `G.n.concat(tilde)`; `©` is the override's (authored, never re-derived); `í` is unchanged (not derived from `i`, documented); the report lists `ñ` and `©` under `overridden` and `á à â ä ā` under `rederived`; and the key order of `G` after the call equals the key order before it | **M8** `fn` called with no rerun: the accents keep the old bowl, red. **M9** the rerun ignores the snapshot (re-derives every registered key): `ñ` is overwritten, red. **M10** `©` registered as a derivation (the F004 shape): the `©` edit is overwritten, red. **M10'** the rerun deletes and re-adds: the key-order assertion is red |
| d | `test_a_roman_override_reaches_the_italic_where_gi_has_no_entry` | `driftwood-a-t.js` also types `G.t`'s start `"s"`: the italic `t` at the neutral example's `text` concept records `serifA=` (a head serif on the slanted stem, through `diagSerifPoly`) and the roman `t` likewise; the italic `a` (which `GI` has) is the `GI` override, not the roman one; and the F009 limit: an override of `GI.A` (a distinct skeleton) leaves italic `Á` equal to the slanted roman `G["Á"]`, while an override assigning `GI["Á"]` is drawn | **M11** `glyph()`'s italic fallback reads the load-time snapshot of `G`: the italic `t` keeps `A=exit`, red. **M12** `applySkeletons` hands `fn` a copy of `GI`: the italic `a` and the `GI["Á"]` case are red. **M12'** a rerun that builds italic accented capitals from `GI.A` (a behaviour change the plan does not make): the `Á` equality is red, which pins the documented limit |
| e | `test_each_guardrail_refuses_its_input` (parametrised over the `bad-*.js` fixtures and in-process cases) | each exits 1 with the message naming the file, the table and the key: no function exported; `delete G.n`; a stroke whose `d` holds `Q`, a stray token, a `C` with five numbers, no `M` first, or an `M` alone; an end letter `"z"`; a dot with a string coordinate; a ring with `rx` 0 or a `d` that is not `ring()`'s; a new key `"ab"`; a new `GI["@"]` with no `G["@"]` (F003; the same file adding both is accepted and both groups export it, the italic drawing the `GI` entry); a second `applySkeletons` call; a `font.json` whose `skeletons` names a missing file, a `.json` file, `sub/skeletons.js` (F008: refused by `export.js`, by `build.py` and by the schema), or `gen.js` | one mutation per refusal, the check deleted: the bad input then draws, exports or builds (red on "exit 1"); for the `Q` case the validator replaced by a call to `sampleCounts` (the revision-1 design: green, which is F005's point, so this mutation is the one that proves the validator is needed); for the second-call case the mark dropped (two overrides applied in sequence: red) |
| f | `test_the_override_is_hashed_and_check_sees_an_edit`, `test_a_masters_json_drawn_with_another_override_is_refused` | after a build from the fixture, `--check` passes; after one comment character is appended to the override file, `--check` exits 1 and names `sources_sha256` in its manifest diff; the manifest's `skeletons` equals the key; `tests/test_copy_into_site.py` gains a variant that copies the fixture's `font.json` and override into the sample site and runs the site suite, whose manifest test (`scripts/tests/test_font.py::test_the_shipped_fonts_match_their_manifest`, line 525–532) now includes the override in `sources` when `cfg` names it. **F002:** an export kept with `--keep-masters`, then the override file edited (one coordinate), then `build.py --masters` that export: exit 1 naming the recorded and the current sha256; an export made with **no** key fed to a `font.json` that has one: exit 1 naming the disagreement; the reverse too; a matching export builds | **M13** the sources entry omitted: `--check` passes after the edit, red; and the site suite's manifest test is red on set equality (the manifest has a key the test's `sources` lacks), which is the mutation for the site-suite half too. **M14** the hash taken of `concepts.js` under the override's name: red on the sha256 comparison. **M14'** `load_masters`'s comparison dropped: the stale export builds, red on "exit 1". **M14''** the comparison checks presence only: the edited-file case builds, red |
| g | `test_build_page_splices_the_override_and_the_call` | `build-page.js --template round1 --skeletons bract-shoulder.js ...`: exit 0; the page holds the wrapped override once, `applySkeletons(SKELETONS);` once and the `data-fd-skeletons` line once, after `gen.js` and `render.js` and before `concepts.js`; the only top-level name the splice adds is `SKELETONS` (asserted by running `topNames` with the widened regex over the spliced text); a page built **without** the flag holds none of the three; `--skeletons` naming a file whose export block is malformed fails with `stripExports`'s message; a `bad-*.js` fixture fails **at build time** with the guardrail's message (the child-node application); an override file declaring a top-level `const DEG` builds (wrapped, no clash) while a template edited to declare `SKELETONS` is refused. **The whole assembled script executes** (review F006): where `find_chrome()` finds a browser (the rule `tests/test_shoot.py` uses), `shoot.py --dump-dom` on the built page asserts `data-fd-rendered > 0` and `data-fd-skeletons` equal to `G h,G m,G n,G r`; without Chrome the test **skips naming the reason**, and `scripts/smoke.sh` step 8 (the Chrome job in CI) builds and shoots the same page, so the skip is never the only run | **M15** the call appended without the splice: `SKELETONS` undefined; red at build time (the child-node application fails) and in Chrome (`data-fd-skeletons` absent). **M16** the splice placed after `concepts.js`: the order assertion is red. **M17** the call appended when the flag is absent: red on the no-flag page. **M17'** the wrapper dropped: the `const DEG` fixture is accepted and the page's script throws in Chrome (a duplicate declaration), red on `data-fd-rendered`. **M17''** the `data-fd-skeletons` line written before the call: a refused override still sets it; red on the `bad-*.js` build-time case only if the child-node application is also dropped, so both are one mutation pair, logged |
| h | `test_the_schema_accepts_the_key_and_rejects_a_non_js_value` (in `tests/test_schemas_and_concepts.py`) | the fixture `font.json` validates; `"skeletons": 3`, `"a.json"` and `"sub/skeletons.js"` are rejected; `templates/font.example.json` still validates without the key | **M18** the key removed from the schema: the valid case fails (`additionalProperties: false`), red. **M18'** the pattern loosened to `\\.js$`: the subdirectory case validates, red |
| i | hop-safari `tests/test_bract_font.py`: `test_the_shipped_font_matches_its_manifest` with `SOURCE_HOMES` gaining `"skeletons.js": TOOLS`; `test_font_json_names_the_skeleton_override` (the key is `skeletons.js`); **two** shoulder tests (review F007): `test_the_generator_with_the_named_override_draws_no_nick` runs `tests/bract_shoulder.js` (the probe of section 0, committed there because the property is Bract's) over the skill's `gen.js` with the override **resolved through `tools/bract/font.json`'s `skeletons` key** (the probe fails if the key is absent or names a missing file): nick ≤ 5 units on `n m r` at all four masters, arch peak within 510–512, join nub 0; and `test_the_shipped_font_has_no_nick_on_n_m_r`: the shipped woff2 instanced at the four master locations with fontTools, the top profile of `n m r` read from the TTF outlines (the same metric in font units), nick ≤ 5; plus the file-level probe `test_the_override_gives_h_the_arch_of_n` on `skeletons.js` alone: `G.h[1].d === G.n[1].d`; the submodule version floor in `test_the_font_design_submodule_is_pinned_and_checked_out` raised from 0.3.1 to 0.6.0 | **M19** the `skeletons` key removed from `font.json`: the generator test fails loudly (no key to resolve), red; and the font rebuilt without the key and shipped: the font-level test reads nick 28, red (the manifest test is also red on `font.json`'s hash, so the font-level test is the one that sees the OUTLINE). **M19'** the key pointing at a copy of the file with the `n` line deleted: the generator test red on `n`'s nick, the file-level probe green (it reads `skeletons.js`), which is why the two are separate. **M20** the override's `h` line deleted: the equality is red. **M21** `SOURCE_HOMES` without the sixth entry: set equality red once the manifest carries it |

Mutations are chosen as the weakest change that falsifies each assertion (M2, M7, M10', M17', M19' are
not inversions of the fix). Clear `__pycache__` between runs (testing.md section 7). Suite cost: one
neutral build and two exports for a, five exports for b, in-process draws for c–e, one build and three
`--masters` runs for f, one Chrome shot for g where a browser exists; about two minutes (inferred).

## 6. Fixtures and digests: nothing re-recorded

`tests/fixtures/baseline.json` is **unchanged** and stays the proof that a project without the key
builds as 0.5.0 did (test a). `docs/reviews/genres-2026-11-19.md`'s digests are unchanged (no shared
skeleton moves; the genres page is built without `--skeletons`). Nothing in `examples/` gains the key:
an override there would move the baseline, which is the opposite of what the examples prove. The
override fixtures live under `tests/fixtures/skeletons/`.

## 7. Docs to update in the same change

Skill:

- `references/generator.md`: the section "Adding glyphs in a site without forking the generator"
  (lines 596–619) is replaced by "Per-face skeletons: the `skeletons` file" — the contract (2.2), when it
  runs and what it sees (2.3), the derivation table (2.4) with the touched-or-followed rule, the italic
  fallback (2.5) and its limit on the accented capitals (F009), the six refusals (2.6), what cannot be
  overridden (the end-letter set, `LIGS`, `UPPERISH`, the mark helpers, the kerning reference), the
  kerning consequence of overriding `n` or `H` (4.2), the `--masters` refusal (F002), and the rule that
  a glyph that belongs to everyone still goes into `G` through the skill's own repository. Section 10's step 1
  ("add `G["@"] = ...`") points at the file for a site and at `G` for the skill. Section 11's
  compatibility promise gains "0.6.0 adds the `skeletons` key; without it the 0.5.0 digests hold".
- `SKILL.md`: phase 2 gate item 1 and the requirements table's `cmap` row (lines 162, 185–188:
  `extra-glyphs.js` and the three-line patch become `tools/<face>/skeletons.js` and `--skeletons`);
  phase 7 step 1 (lines 268–274: the copy's expected diff is now empty, the override is a project file);
  the tool table rows for `gen.js`, `export.js` and `build-page.js` (lines 449–465); the version lines.
- `references/process.md` lines 127–135 and 224–230 (the same two passages); `references/testing.md`
  section 7's last bullet (line 351–353) and section 8 (the mutation log); `references/traps.md` gains
  row 37 (symptom: a notch at the top of `n m r` where the wedge serif meets the arch, one pixel at 40 px;
  cause: the serif's height and the arch's departure are both pen-dependent while the skeleton is
  shared; detection: the shoulder probe; guard: a per-face override, section 4.2's numbers; where it bit:
  Bract, measured 2026-11-19); `references/variable-font-build.md` section 12's table (the `skeletons`
  row: a bare file name beside `font.json`), section 11 (the export's two optional keys) and section 14
  (`--masters` now refuses an export drawn with another override); `references/concept-pipeline.md`
  sections 3 and 8 (the `data-fd-skeletons` self-test attribute beside `data-fd-rendered`; the flag) and
  `scripts/concepts/README.md` (`tests/test_docs_commands.py` reads a node script's `--flag` tokens from
  its source, so the flag must appear in `build-page.js` before the docs name it); `scripts/smoke.sh`
  step 8 gains the round-1 page built with `--skeletons tests/fixtures/skeletons/bract-shoulder.js`
  and shot with `--dump-dom`.
- `templates/font-record.md`'s "Skeletons" bullet (line 66) names the file; `templates/plan.md` line 95.
- `CHANGELOG.md`: `## [0.6.0] — <date>`: Added (the key, the flag, `applySkeletons`, the derivation
  rerun, the report, the six-source manifest), Changed (the copy-and-patch convention retired from the
  docs; `--gen` kept), the Bract numbers of section 4 as the first use, and the pointer to this plan.
- `VERSION`, `SKILL.md` (frontmatter and the body line), `README.md` badge, `package.json`
  (`tests/test_versions_and_skill.py` checks all five; read).
- `scripts/gen.js` header (item 8), `scripts/build.py` module docstring (the hashed sources),
  `scripts/export.js` header (the key).

hop-safari, in the rollout commit (section 10):

- `tools/bract/skeletons.js` (new): the chosen candidate, with a header naming the measurement.
- `tools/bract/README.md`: the file list gains `skeletons.js`; "Changing a parameter safely" step 1 ("a
  skeleton ... is the skill's code, not Bract's") becomes "a shared skeleton is the skill's; Bract's own
  letterforms are `skeletons.js`"; "Bumping the skill" step 2 names six hashed sources.
- `docs/bract-font.md`: a dated section "The shoulders of n, m, h and r (0.6.0)" with section 0's and
  4's numbers for the chosen candidate, the `font-diff.py` summary, the one-unit kern list, and the
  statement that no advance, title, floor or other outline moved; the two "Open items" lines (286–289,
  428–429) closed.
- `tests/test_bract_font.py`: section 5 row i. `CLAUDE.md` "Display face: Bract": the sentence naming
  "the five sources" becomes six and names `skeletons.js`.

## 8. Version: 0.6.0

A new `font.json` key, a new build input hashed into the manifest, a new CLI flag and a retired
convention: a feature with a documented default. The default is byte-identical, so the compatibility
baseline does not move (unlike 0.5.0). A patch number would understate a new input that changes what
`--check` hashes.

## 9. Order of work

1. `gen.js`: `derive()` and `DERIVATIONS` in place of the base-built assignments; run
   `tests/test_backward_compat.py` (must stay green: the registration alone must change nothing); then
   the validator, `applySkeletons`, the refusals, the report.
2. `export.js` (the key, the two export fields), `build.py` (the manifest, the `--masters` guard),
   `build-page.js` (the child-node application, the wrapped splice, the widened clash check), the two
   schemas, `smoke.sh` step 8.
3. Tests of section 5 a–h, written against the finished code, each mutation run through
   `FONT_DESIGN_SK_GEN` and logged; `scripts/smoke.sh --full` (step 4 runs the site suite on the
   neutral fixture; step 6 builds the three rounds without the flag; step 7 the repo tests).
4. Docs and version (sections 7, 8).
5. Impasse review of the whole diff; reconcile; re-review once.
6. The gate of 4.3: the three scratch builds, `diff.py`, `shoot.py`, the crops; the operator's choice.
   This needs the skill half built (the override must go through the real `export.js`), so it runs after
   step 5 and before the merge, or after the merge as the first step of section 10; either order works,
   the second keeps the skill PR free of the choice.
7. Merge; section 10.

Serial. Step 6 can overlap step 5 (the crops depend on the build, not on the review).

## 10. Rollout

**The skill PR.** `feature/per-face-skeletons` onto `origin/main`. Another branch,
`fix/italic-bold-master` (the movingavg-website session's: `GI.w`'s first stroke moved to `x` 20, and
the italic opening quotes' advance in `build.py` made to hold their ink), is being opened first. If it
merges first, this branch rebases onto it: the two touch different lines of `gen.js` and `build.py`, and
`GI.w` and the quote advances are not planned here (section 1); a conflict would mean one of them moved
a line the other edits, to be resolved by hand, never by taking either side wholesale. The `GI.w` change
moves the compatibility baseline's italic digests; this plan's test a then holds against whatever
baseline `main` carries at rebase time.

**hop-safari**, after the merge (the site pins `tools/font-design` at `5d0b29f`, 0.5.0, as does
`~/.claude/skills/font-design`; read: `git log -1` in both). The pin must move **before** `font.json`
gains the key, because `test_font_json_validates_against_the_skills_schema` validates against the
pinned schema (read: `tests/test_bract_font.py` line 684):

1. `git -C tools/font-design fetch && git -C tools/font-design checkout <0.6.0 sha>`.
2. `.venv/bin/python3 tools/font-design/scripts/build.py --font tools/bract/font.json --check`: fails
   with "manifest DIFFERS" naming `gen.js`, `export.js` and `build.py` in `sources_sha256`, and the font
   identical (the default is byte-identical). Expected; it is the proof that the pin bump alone changed
   nothing in the font.
3. Add `tools/bract/skeletons.js` (the chosen candidate) and `"skeletons": "skeletons.js"` to `font.json`.
4. `git show HEAD:static-pages/fonts/bract/Bract-VF.woff2 > OLD.woff2`; rebuild; the build log carries
   `skeletons skeletons.js: overrides G h, G m, G n, G r; re-derives G ñ`;
   `.venv/bin/python3 tools/bract/font-diff.py OLD.woff2 static-pages/fonts/bract/Bract-VF.woff2 --locations 400,40 500,40 700,40 400,80 700,80`.
   For candidate B it exits 1 and must list: the default outlines and `gvar` tuples of `n`, `m`, `h`,
   `r` and `uni00F1`, those five instanced at the five locations, and GPOS pairs changed by exactly 1
   unit, between 7 and 29 per master on B7 (4.2; the count is read against the exported `kerns`, not
   guessed). It must list **no** hmtx or HVAR line, no cmap, fvar, avar, STAT, GSUB, gasp, prep, name,
   hhea, OS/2 or head line, and no shaping difference beyond the listed pairs. An unexplained line stops
   the bump. For candidate A the list would include hmtx, HVAR and most GPOS pairs, which is a design
   review of the spacing, not a bump; the gate (4.3) says so before A can be chosen.
5. `tests/test_bract_font.py` (row i), then the full suite with `RBENV_VERSION=3.2.8` (read: the site's
   `CLAUDE.md`). `HAIRLINE_FLOORS` hold (4.2); the size budget holds (inferred: four glyphs' point counts
   change by a few samples each).
6. One design-review crop at 1× of the shipped font on the pages of 4.3, recorded in
   `docs/bract-font.md`; the crops stay out of the repo.
7. Commit the pointer, `skeletons.js`, `font.json`, the woff2, `manifest.json`, the tests and the docs
   together, with the `font-diff.py` summary and the kern count in the message.
8. `~/.claude/skills/font-design`: `git checkout <same sha>` in the submodule, then a `~/.claude` commit
   of the pointer (`git add` and `git commit` as separate calls there; read: the global `CLAUDE.md`).

## 11. Risks and questions for the operator

Risks:

- The derivation refactor touches every composite's construction; test a's reliance on the unchanged
  baseline is what catches a slip, and M1/M2 prove it can.
- The one-unit kern changes under candidate B are a real change to shipped spacing, small and bounded
  but site-wide in principle (7–29 pairs per master). They are accepted here; a reviewer may disagree.
- `applySkeletons` also runs inside a concept page in the browser, where a thrown refusal shows only in
  the console. `build-page.js` therefore applies the override at build time in a child node (2.3), so
  every refusal fires with its message before a page exists, and the page carries `data-fd-skeletons`
  as evidence the browser call completed, read by `shoot.py --dump-dom` (test g, the smoke run). What is
  not caught: a runtime error in the override that only the browser's `gen.js` copy would throw
  (none is known: the spliced `gen.js` is the file node ran).
- The `--masters` guard (F002) makes a kept export unusable after any edit to the override, which is the
  intent; a workflow that edits the override and reuses an export was never sound.
- Round 1 cannot show structural alternatives side by side (2.1); a face wanting that builds one page
  per override file, which is workable and slow.

Questions, each with the recommendation:

1. **Candidate A or B for Bract** (4.3)? Decided on the crops; recommendation B7.
2. **Should `h` follow `n` under B?** Recommendation yes (one arch for the two shoulders; test i pins
   the equality). Under A, `h` is untouched.
3. **Accept the one-unit kern re-rounding** (4.2) or pin the kerning reference to a frozen `n`?
   Recommendation: accept, list the pairs in the record; pinning changes every face's kerning model.
4. **Expose the mark helpers (`acute`, `tilde`, `raise`, `exitStem`) to the override function now?**
   Recommendation: not in round 1; an override that needs a mark writes its own strokes. Revisit with
   Driftwood's file if it needs one.
5. **Version 0.6.0 or 0.5.1?** Recommendation 0.6.0 (section 8).
6. **Run the gate before or after the skill PR merges** (section 9 step 6)? Recommendation: after,
   as the first step of the hop-safari bump, so the skill PR carries no site decision.
7. **Per-concept skeletons (round-1 structural alternatives)**: record as a follow-on issue referencing
   2.1's list of what it needs, or leave on #9? Recommendation: a new issue, so #9 closes with this.

## 12. Independent review and what it changed

**Independent review of revision 1** (Impasse, Codex gpt-6-sol, run `skeleton-overrides-plan-review-1`,
2026-11-19). Nine findings; the coordinator checked each against the worktree's code and accepted all
nine; the author re-checked the line references named below before revising.

| # | Finding | Checked | Disposition and change to the plan |
|---|---|---|---|
| F001 (high) | test a contradicted itself: with `empty.js` the key is set, so the export gains its optional field and the manifest changes in three places, the third being `font.json`'s own hash | read: `build.py` line 1291 `sources["font.json"] = sha256(cfg["_path"])`; `baseline_digest.export_digest` keeps only named fields | accepted: test a is split: (i) the no-key proof is the unchanged baseline alone; (ii) the empty-override build asserts equal woff2 bytes on their own, equal exports once the two optional fields are removed, and exactly three manifest differences, named (section 1 item 5, section 5 a, M4', M4'') |
| F002 (high) | `--masters` could reuse an export drawn before an override edit and record the new file's hash, because `PARAMS_JS` neither applies nor hashes the override | read: `build.py` lines 944–952 (`params()` only); `load_masters` line 983 | accepted: the export carries `skeletons` and `skeletonsSha256` when set; `load_masters` refuses an export whose presence, name or hash disagrees with `font.json` and the file (2.3, section 3, test f with M14', M14''; the export schema gains both fields) |
| F003 (medium) | a key added only to `GI` is left out of the italic export in silence, since the glyph list is `Object.keys(m.G)` | read: `export.js` line 147 | accepted, the smaller option: a new `GI` key with no `G` counterpart is refused (2.6 item 5, test e; the both-tables case is asserted to export in both groups) |
| F004 (medium) | a before/after key-set comparison over lines 236–281 would list `©`, `™`, `•` as derived and a rerun would overwrite an override of them | read: `gen.js` lines 257–260 are plain assignments inside the block | accepted: derivations are registered one by one (`derive(table, key, build)`, `DERIVATIONS`), the three authored entries stay plain, the rerun assigns in place and skips keys whose content the override changed; the "composites absent during the call" rule of revision 1 is dropped for the touched-or-followed rule (2.2, 2.4, test c with the in-place `©` edit, M10, M10') |
| F005 (medium) | `sampleCounts` and `samplePath` skip an unknown token rather than throw, so the plan's claim that a `Q` "throws there today" was false and the guardrail needs its own validator | read: `gen.js` lines 298–333, the `while` loops match `M`, `L`, `C` only | accepted: an explicit path validator (leading `M`, `L`/`C` with two or six finite numbers, at least one segment, nothing else), dot and ring checks (2.6 item 3; test e's `Q`, stray-token, five-number, no-`M` and ring cases; the mutation that swaps the validator for `sampleCounts` is the one that proves it is needed) |
| F006 (medium) | `topNames` reads only `var`/`function` and compares the template against the sources, never the sources against each other, so an override's name clashing with `gen.js`, `render.js` or `concepts.js` passed; test g executed only a prefix | read: `build-page.js` lines 249–253; `concepts.js` and `gen.js` both declare `DEG`, so a pairwise check over existing sources would break every page | accepted, the wrapper: the override is spliced inside a function that returns `SKELETONS`, the only name it adds, and that name and `data-fd-skeletons` are checked against every source's `var`/`function`/`let`/`const`/`class` names; the whole assembled script is executed in Chrome where found (`--dump-dom`, `data-fd-skeletons`) and in the smoke run's Chrome job; refusals fire at build time through a child-node application (2.3, test g, M17', M17'') |
| F007 (medium) | test i's probe read `tools/bract/skeletons.js` directly, so it passed with the key absent and M19 could not turn it red | read: the revision-1 text of test i | accepted: the generator probe resolves the override through `font.json`'s key and fails if there is none; a second test reads the shipped font's `n m r` outlines at the four master locations; the file-level `h = n` probe stays separate and is named as such (test i, M19, M19') |
| F008 (medium) | a path with a directory part breaks the basename-keyed manifest entry and hop-safari's `SOURCE_HOMES[src] / src` | read: `build.py` `compose_manifest` keys sources by file name; hop-safari `tests/test_bract_font.py` line 51 | accepted, the restriction: the key is a bare file name beside `font.json`, refused by `export.js`, `build.py` and the schema pattern `^[^/\\\\]+\\.js$` otherwise (section 1, 2.3, section 3, tests e and h, M18') |
| F009 (low) | the accented capitals are built in `G` only, so an override of `GI.A` leaves italic `Á` on the slanted roman `G["Á"]` | read: `gen.js` lines 269–273 build `G[...]` from `G[base]`; `GI_CAPS` has `A` and no accented key | accepted as a stated limit, not a refusal: the contract (2.2) and `generator.md` say it, test d pins it with the `GI["Á"]` route as the remedy (M12'); the no-key output is unchanged |

### The review of the diff (Codex gpt-6-sol, `skeleton-overrides-code-review-1`, 2026-11-19)

Before the review, a mutation of my own that the implementation's log did not name survived every test: deleting
`applySkeletons`'s glyph-cache reset. No caller draws before applying, so nothing reached it;
`test_a_drawing_cached_before_the_override_is_not_served_after_it` was added and is red under that mutation. The review raised
five findings.

| # | Finding | Checked | Disposition and change |
|---|---|---|---|
| F001 (high) | a file whose export block exports an anonymous function passes node and the child-node check, but the page's wrapper returns `SKELETONS`, which such a file never declares | read: `build-page.js` `skeletonsSplice` (the wrapper ends `return SKELETONS;`); `stripExports` accepts any one-line `module.exports = ...` | accepted: `build-page.js` refuses an export block that does not export `SKELETONS` by name; fixture `export-only.js`, test g. A first version also required a top-level `SKELETONS` declaration; either half alone refused the fixture (two guards on one fixture), and the declaration half adds nothing, since a file that exports `SKELETONS` without setting it fails `require()` in the child node first, so it was dropped. Disabling the check turns test g red |
| F002 (medium) | the validator accepts an end letter a concept does not map | read: every concept in the five shipped concept files maps `s t u "" x`; `j` (the square end, 46 uses in the shared tables) and `i` (the T-join, made `tee` at `strokePolys`) are unmapped by design | **rejected**: an override's end letters are the shared table's seven with the shared table's meaning; refusing an unmapped letter per concept would refuse the shared table's own `j`. No change |
| F003 (medium) | a new key of one code point outside the Basic Multilingual Plane is accepted, but `layTitle` and `keysFor` index text by UTF-16 unit | read: `export.js` `layTitle` advances `w[i]`; the check was `Array.from(k).length` | accepted: a new key must be one UTF-16 unit (or a `LIGS` name); fixture `bad-key-astral.js`, test e; red with the check back on code points |
| F004 (medium) | a concept page records no identity for its override | read: phases 3–5 build pages before `font.json` exists (phase 7, `SKILL.md`), so binding a page to `font.json` is not possible there | accepted in part: the page records `data-fd-override-sha256`, the file's sha256, to match against an export's `skeletonsSha256`; test g asserts it; red with the line dropped. The `font.json` binding is not built, for the reason checked |
| F005 (medium) | a stroke carrying `dot` and a path is accepted and drawn as the dot alone | read: `strokeProblem` returned on a valid `dot`; `glyph()` takes `st.dot` first | accepted: the three shapes are exclusive (a dot is `dot` only, a ring `d closed r`, a stroke `d a b`); fixture `bad-dot-and-path.js`, test e; red without the check |

### The one re-review (Codex gpt-6-sol, `skeleton-overrides-code-review-2`, 2026-11-19)

The re-review found F005 complete and every named test red under its stated removal. It held four points:

| # | Finding | Checked | Disposition and change |
|---|---|---|---|
| F001 (high) | the export-name check still passes `if (typeof module !== "undefined") var SKELETONS = ...`, which node applies and a page, having no `module`, does not | read: the check matched only the export block's text | accepted: `build-page.js` no longer matches text. It runs the page's own wrapper in a `vm` context holding `gen.js`'s names and no `module`, and refuses the file unless `SKELETONS` is then a function. Fixture `conditional-var.js` in test g; red with the check off, and red when the sandbox is given a `module` (the weakest change that lets the conditional file through) |
| F002 (medium) | an override may use `u` or `x` on a concept that `params()` accepts without those mappings | measured: Driftwood's shipped concepts in movingavg-website (`tideline`, `dune`, `windswept`) map neither `u` nor `x`, while the shared tables end 31 strokes in `x` and 2 in `u`, so Driftwood draws unmapped ends today with no override | **rejected again**, on that evidence: an override's unmapped end draws exactly as the shared table's does on the same concept; a mapping check in `params()` or in `applySkeletons` would refuse Driftwood's current build. Whether `params()` should require mappings is a question about the generator for every face, not about this change |
| F003 (medium) | a lone UTF-16 surrogate passes the one-unit check | read: `k.length === 1` | accepted: a key containing a surrogate unit is refused; fixture `bad-key-surrogate.js` in test e; red without the check |
| F004 (medium) | recording the page's hash does not compare it with the export's `skeletonsSha256` | read: no tool reads both a concept page and an export; pages are built in phases 3 to 5, the export in phase 7 | **escalated to the operator** as a priority call: building the comparison needs a new step in a tool that today reads neither (for example a `shoot.py` option), and nothing in the process produces both files at once. Recommendation: do not build it in this change |


## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| W1 | `derive()` and `DERIVATIONS` registering the base-built composites in place; `©`, `™`, `•` stay authored; load-time tables and key order unchanged | code | `scripts/gen.js` | `tests/test_backward_compat.py` green on the unchanged baseline; M1, M2, M10 red |
| W2 | `applySkeletons`: deep snapshot, the call, the stroke/dot/ring validator and six refusals, rerun of untouched derivations in place, cache reset, once-only, report | code | `scripts/gen.js` | tests b–e |
| W3 | `export.js`: the `skeletons` key validated (bare `.js` name beside `font.json`), applied before `keys`, reported on stderr, `skeletons` and `skeletonsSha256` written when set | code | `scripts/export.js`, `templates/export.schema.json` | tests a, b, e, f |
| W4 | `build.py`: sixth source hash and `skeletons` name when set; name refusals; `load_masters` refuses an export whose override presence, name or hash disagrees | code | `scripts/build.py` | tests a, e, f (M14', M14'') |
| W5 | `build-page.js --skeletons`: child-node application, wrapped splice after gen/render, the call and `data-fd-skeletons`, clash check widened; `smoke.sh` step 8 shoots the page | code | `scripts/concepts/build-page.js`, `scripts/smoke.sh` | test g; `tests/test_docs_commands.py` |
| W6 | `font.schema.json` gains `skeletons` with the bare-name pattern | code | `templates/font.schema.json` | test h (M18, M18') |
| W7 | Override fixtures and the node probe | test-new | `tests/fixtures/skeletons/*`, `tests/skeleton_probe.js` | tests a–g run; `tests/test_hygiene.py` |
| W8 | `tests/test_skeleton_overrides.py` a–g with the mutation log (Chrome half of g skips, naming the reason, where no browser is found) | test-new | `tests/test_skeleton_overrides.py`, `references/testing.md` | every M1–M18 and the primed variants watched red and logged |
| W9 | Schema test h and the copy-into-site variant | test-new | `tests/test_schemas_and_concepts.py`, `tests/test_copy_into_site.py`, `scripts/tests/test_font.py` | M13, M18 red |
| W10 | Docs: generator.md section replaced, SKILL.md, process.md, testing.md, traps.md row 37, variable-font-build.md, concept-pipeline.md, concepts README, record and plan templates, headers | docs | `references/*.md`, `SKILL.md`, `scripts/concepts/README.md`, `templates/font-record.md`, `templates/plan.md`, `scripts/gen.js`, `scripts/export.js`, `scripts/build.py` | `tests/test_docs_commands.py`, `tests/test_versions_and_skill.py`; grep for `extra-glyphs` finds only the retirement note |
| W11 | CHANGELOG 0.6.0 and the five version guards | docs | `CHANGELOG.md`, `VERSION`, `SKILL.md`, `README.md`, `package.json` | `tests/test_versions_and_skill.py` |
| W12 | Impasse review of the diff, reconciliation, one re-review; section 12 of this plan | docs | `docs/plan-skeleton-overrides.md` | the review ids recorded |
| W13 | The gate: three scratch builds, diff.py, shoot.py, crops at 1×; the operator's choice | live-acceptance | | the choice recorded in `docs/bract-font.md` with the crops' paths |
| W14 | hop-safari bump: pin, `skeletons.js`, `font.json` key, rebuild, `font-diff.py` as section 10 step 4 lists, the three shoulder tests and the manifest test, docs, one commit | code | `tools/font-design` (pointer), `tools/bract/skeletons.js`, `tools/bract/font.json`, `tools/bract/manifest.json`, `static-pages/fonts/bract/Bract-VF.woff2`, `tools/bract/README.md`, `docs/bract-font.md`, `tests/test_bract_font.py`, `tests/bract_shoulder.js`, `CLAUDE.md` | `font-diff.py` lists only the glyphs and the one-unit pairs of section 10 step 4; the full suite green; M19, M19', M20, M21 red |
| W15 | `~/.claude/skills/font-design` pointer bump | code | `~/.claude` submodule pointer | `git -C ~/.claude/skills/font-design log -1` shows the 0.6.0 sha |
