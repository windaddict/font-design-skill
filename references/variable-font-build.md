# Building the variable font: masters, axes, checks and the two JSON contracts

WHAT IT'S FOR: the reference for phase 6 (planning the build) and phase 7 (building). It explains
why the masters form a full rectangle, how the weight and optical-size axes are configured and
measured, what each self-check in `scripts/build.py` guarantees and what it does not, how the
build stays reproducible and under budget, how statics and the italic are produced, and every key
of `font.json` and `requirements.json`. Read it before writing a `font.json`, and again when a
self-check fails and you need to know whether the fix belongs in the design or in the budget.

Contents

1. The pipeline in one paragraph
2. Masters: a full rectangle, drawn not synthesised
3. The weight axis and the reviewed Medium (avar)
4. The optical-size axis: semantics and measurement
5. Pinned sampling and shared-index decimation
6. The self-checks, with exact guarantees
7. Reproducibility and the size budget
8. Statics from the instancer (`--static`)
9. The italic as a second variable font
10. One-axis builds
11. The export JSON contract (templates/export.schema.json)
12. font.json, key by key (templates/font.schema.json)
13. requirements.json, key by key
14. Commands
15. Site wiring: the fallback face with metric overrides and `text-wrap: balance`

## 1. The pipeline in one paragraph

`node scripts/export.js --font font.json --group roman OUT.json` draws every glyph of every
master of the group with `scripts/gen.js`, refuses the group unless the masters are compatible,
decimates with one kept-index set per edge run, measures hairlines and folds, lays the project's
titles, and writes one JSON. `scripts/build.py --font font.json` runs that export (or re-checks a
supplied `--masters` JSON), builds one TrueType master per entry with fontTools' `FontBuilder`
(`isTTF=True`), builds `kern` and `liga` with `feaLib`, calls `varLib.build` for `fvar`, `avar`,
`gvar` and the variable GPOS, adds STAT axis values, `gasp` with its smart-dropout `prep`, the name table
(Windows platform only) and vertical metrics, sets `fsType` from `font.json`, runs the
self-checks, and writes the woff2 plus `manifest.json`. Nothing is written if a check fails. One
pipeline, one set of checks: Driftwood's skia-pathops union is not a build mode here (it produced
master-dependent contour structure and kept folded loops as lumps, issues #22 and #24).

The flags and manifest keys named in this document are `scripts/build.py`'s own; the
command-extraction test in `tests/test_docs_commands.py` fails if a documented flag disappears.

## 2. Masters: a full rectangle, drawn not synthesised

A two-axis group needs a master at **every corner**: (wght min, opsz min), (wght max, opsz min),
(wght min, opsz max), (wght max, opsz max). Bract's plan had three; the independent review (plan
finding F003) showed the fourth corner, Bold at display size, is reachable even though no site rule
set Bold above 35.2 px at a 16 px root: a reader who raises the browser's default font size scales
every rem size, and at a 24 px root a 2.2 rem heading is 52.8 px, inside the optical-size range.
With three masters that corner would have been the sum of two sets of deltas that nobody drew.

So draw it. State the truth about it: Bract's (700, 80) corner is "built and self-checked, not
visually reviewed for use", because the review loop never reached it at the default root. The
record template has a slot for exactly that sentence; `shoot.py --root 150` is how the loop looks
at it (references/review-loop.md).

Master naming in font.json: any name matching `^[A-Za-z][A-Za-z0-9 ]*$`; the precedents use
`TextRegular`, `TextBold`, `DisplayRegular`, `DisplayBold` for a two-cut face and `Regular`,
`Bold` for one cut. Each master names its `concept` (an `id` in concepts.js), its `mult` (`W` is
`concept.W × mult`; 1.5 is the Bold in both shipped faces, 1.3 the generated Medium), and its
`location` on the group's axes. A group needs at least two masters.

## 3. The weight axis and the reviewed Medium (avar)

`wght` runs 400–700 with the Regular at the default. The Medium is not a master: it is an
interpolation, and the generator is not linear in weight (references/generator.md section 6), so
the mix that looked right in the concept pages (Bract: `W × 1.3`) does not sit at user weight 500
on a linear axis. `avar` fixes that: the axis `map` `[[400, 400], [500, 580], [700, 700]]` sends
user 500 to design 580, normalized 0.333 → 0.6, which is 0.6 of the way from the Regular to the
Bold and therefore `W × 1.3`. `font-weight: 500` then renders the reviewed Medium. Driftwood's
example uses `[500, 538]` because its Bold is `×1.65`, so `×1.3` is 0.46 of the way. The test for
it reads `requirements.json` `avar`, not font.json (finding F002).

Named instances (`instances`) are declared per group; the precedents name Regular, Medium, Bold,
Display and Display Bold.

## 4. The optical-size axis: semantics and measurement

`opsz` values are **a browser decision**. Under `font-optical-sizing: auto` a browser maps the
element's font size to an `opsz` value; whether it uses CSS px or points decides where the axis
must start and end (plan finding F002). Do not assume: measure. `scripts/opsz.py` renders
`scripts/opsz.html` at a given CSS px with row 0 under `auto`, row 1 with optical sizing off, and
rows for explicit `"opsz" N` in steps of 2, then reports which N's pixels equal row 0's. It exits 1
when a size has no exact match or an ambiguous one, so a broken page cannot report a mapping.

Measured for Bract with Chrome 157 headless on macOS (2026-11-15): 64 px rendered identically to
`"opsz" 64` and to nothing else; 80 px identically to 80 and the clamped values above; 32 and
40 px identically to every value ≤ 40. So Chrome maps CSS px to `opsz` one to one. **Safari and
Firefox were not measured**; the CSS Working Group's stated position is that all three use CSS px,
but that is not verified here. If a browser used points, 40 px would ask for opsz 30 (clamped to
the text cut, harmless) and 80 px for 60 (a blend, not the display cut).

The axis therefore starts where the text cut should stop being used unchanged: Bract 40–80, the
text cut below 40 px (the browser clamps), a smooth blend from 40 to 80 for the fluid H1s, and the
display cut at the 80 px frontispiece. State `font-optical-sizing: auto` explicitly in the CSS.

## 5. Pinned sampling and shared-index decimation

Compatibility comes from the generator (references/generator.md sections 3 and 12). Decimation
must not break it, so `export.js` runs Ramer–Douglas–Peucker **per edge run** (a stroke's left
edge, its right edge, each serif, each cap: never across a contour's closing seam), takes the
**union of kept indices over all masters** of the group, and applies that one index set to every
master. Endpoints of every run are always kept; a polygon keeps at least three points. Default
tolerance 1 unit (`decimation_eps`; 0.08 px at 80 px). Bract: 155,042 → 28,457 points per master
at ship time (this repo's generator measures 156,184 → 28,547 on the same parameters; the
difference is exactly the trademark glyph `™`, restored here from Driftwood: 1,142 raw and 90 decimated points, measured; every other glyph and the four minimum strokes are identical).

`build.py` then checks what decimation could still break: each contour's signed-area sign is
unchanged and it has ≥ 3 points; and a FreeType raster of each glyph before and after decimation
at the sizes in `raster.sizes` differs by at most `raster.budget.decimation` grey levels (Bract
measured 44 against a budget of 48, on `five`).

## 6. The self-checks, with exact guarantees

Every check fails the build and nothing is written. The wording below is the exact guarantee; the
right-hand column is what the check does **not** prove.

| Check | Exact guarantee | Not proven |
|---|---|---|
| Masters compatible (export.js, re-checked in build.py) | same contour count, same point count per contour, same branch record, in every master; one `raw`, `runs`, `polys` and `keptIdx` record per polygon, every zip over them strict (re-review code-a F003) | that corresponding points are the same feature |
| Master parameters (build.py, the export path and `--masters` alike) | each master's `concept`, `W`, `thin` and `track` in the masters JSON equal what `gen.js params()` gives for the concept and multiplier `font.json` names, read back through node; the hairline recomputation's interior reach (1.1 × W / mult) uses that `W` (re-review code-a F002) | the advances, kern values, word space, title widths and branch records, which the font suite holds against a fresh export |
| Every contoured glyph varies | a `gvar` entry per glyph (`.notdef` exempt); the test adds plan finding F013: instancing at each master's location returns that master's exported polygons within 2 units (integer rounding plus IUP inference), advances exact | that intermediate locations look right |
| cmap | U+00A0 = U+0020 = `space` when `nbsp_to_space`; U+0027 = U+2019 = `quoteright` and `quotesingle` unmapped when `ascii_apostrophe_curly`; the set equals `requirements.json` `cmap` | that the pages' text is covered: that is the site-wiring coverage test |
| Hairline floors | the minimum interior stroke width over the generator's samples, further than the taper and teardrop reach from either end, per master, ≥ `hairline_floors[master]`; the test also requires the manifest's figure to equal the exporter's | anything about pixels, hinting or Windows |
| Fold guard | on the output polygons, every segment included, no stroke-body edge runs back against its centre line by more than `fold_units.raw` (4) on the undecimated edges or `fold_units.decimated` (10) on the decimated edges that ship, in any master; unequal edge runs throw rather than return 0 | that a fold under 4 units is invisible at every size: 4 was chosen because Bract's folds measured 4.9–90 and corner residue ≤ 3.6 |
| Size | woff2 ≤ `size_budget_bytes` | — |
| Round trip | the woff2 loads in fontTools and instances at the named instances | rendering |
| Overlap flag | `OVERLAP_SIMPLE` is set on every contoured glyph after compilation | that any rasteriser honours it |
| Decimation raster | each contour keeps its winding sign and ≥ 3 points; FreeType rasters before and after decimation at `raster.sizes` differ by ≤ `raster.budget.decimation` levels on any pixel | CoreText, DirectWrite |
| Overlap rendering | FreeType rasters of the overlapping outlines against their skia-pathops union differ by ≤ `raster.budget.union` levels on any pixel and ≤ `raster.budget.seam` on pixels the union covers fully (Bract measured 32 and 15 against 48 and 24) | the same: FreeType via Pillow only |
| Vertical metrics (F012; rewritten 2026-11-16) | OS/2 win ascent/descent are computed from every glyph of every master and no glyph exceeds them (the Bract mutation that copied Driftwood's constants failed on `À` at 947 against 940); `hhea` and OS/2 typo carry one ascender and descender, `typo_metrics` when `font.json` gives it, else the same measured extent, both with a line gap of 0; `USE_TYPO_METRICS` is set; the self-check prints `vertical metrics written: ...` with the `line-height: normal` they give | clipping at a given CSS `line-height`, which is a review item; what a given platform draws |
| `fsType` | `OS/2.fsType` equals `names.fs_type`, which the config must state (no default) | that the value is the right licence decision: it is the operator's |
| STAT | one format-1 axis value for every coordinate any named instance uses on each axis, plus the axis default; a weight takes its standard name (400 Regular, 500 Medium, 700 Bold), another value its number; the default is elidable; the elided fallback name is the style (Regular, or Italic for an italic group); statics carry no STAT (their names are rewritten, so its name IDs would point at nothing); the build's self-check refuses a value named other than the standard weight name (a table restated for the check), a default that is not the only elidable value, and a wrong fallback name | that an application composes the names as expected; no linked values (Bold is not linked to Regular); known limits below |
| `prep` and `gasp` | `prep` is the standard 7-byte smart-dropout program (PUSHW 0x01FF, SCANCTRL, PUSHB 4, SCANTYPE), `gasp` is `{65535: 15}`, `maxp.maxStackElements` is at least 1 | that a renderer runs `prep`: Windows GDI or DirectWrite may, FreeType here does not; unverifiable from a Mac |
| Name platforms | no Macintosh (platform 1) name records in the variable font or a static | — |
| Code page | `OS/2.ulCodePageRange1` has bit 0 (Latin 1) | any other code page |
| Reproducible | `--check` rebuilds to a temporary directory and compares bytes with the shipped woff2 and manifest | — |

**The rasters are FreeType via Pillow.** They prove FreeType renders the overlaps without seams
and that decimation moved nothing visible to FreeType; they say nothing about CoreText (Safari,
Chrome on macOS), DirectWrite (Windows) or Android. Pillow cannot turn FreeType's autohinter off,
which snapped whole glyphs by a pixel between the two outlines (209-level false differences), so
the throwaway raster fonts carry a one-instruction `fpgm` and FreeType takes the (empty) bytecode
path instead. Budgets are per machine (trap 31): the manifest records what each build measured,
and a Linux build may differ. Raise a budget only with the measured number recorded beside it.

Glyphs are built verbatim from the rounded points with `Glyph()`/`GlyphCoordinates`, not through
`TTGlyphPen`, because `TTGlyphPen` drops a closing point that rounds onto the first one, and does
so in one master only (Bract lost 16 ring glyphs on its first build, and the inner ring of `%` in
one master in round 3).

## 7. Reproducibility and the size budget

`SOURCE_DATE_EPOCH` is **assigned**, not `setdefault`-ed, from `font.json` `source_date_epoch`
in `main()` before any table is compiled (`build.py` imports fontTools at module load, so "before fontTools is imported" was never true), so the bytes never depend on who ran the build (the diff review's
finding F006; the re-review's F005 asked for the test to pass a foreign value in the environment,
which it does). The build sorts everything it emits; there is no timestamp in the woff2 except
`head`. `--check` is the proof and the test suite runs it. The interpreter is `sys.executable`,
never a hard-coded venv path.

Since 0.8.0 the manifest also records `skill_version`, the text of `VERSION` in the folder above `scripts/`, so a face
folder that carries no scripts still says which skill built it. A `build.py` whose folder has no `VERSION` refuses to build,
naming the path, before any export runs; `--check` against a manifest built by another version reports the difference.
The manifest's schema is `templates/manifest.schema.json` (`skill_version` is optional there: a manifest built before
0.8.0 has none). `references/face-folder.md` section 3 has the rest.

Budget: Bract shipped 86,580 bytes against 102,400 (Bodoni Moda 400 + 700 had been 53,980). The
biggest tables are `gvar` and `glyf`; GPOS carried 4,100 variable pairs. Lower `decimation_eps`
or widen `kerning.set` and the size follows; the budget test says when.

## 8. Statics from the instancer (`--static`)

`build.py --static DIR` (DIR relative to the working directory, like every command-line path; the
keys inside `font.json` are the ones that resolve from its directory) writes a static TTF and
woff2 at each named instance with `fontTools.varLib.instancer`, from the same reviewed variable
font, so what was reviewed is what ships. Exact guarantee per static (plan finding F012): no `fvar` or `gvar`; outlines and advances
equal the instancer's at that location; the overlap flag is kept; name, weight class and italic
metadata match the instance; one is rendered with Pillow. Statics are **for modern renderers,
overlaps kept**: no union is run, so a renderer that fills overlapping contours badly will show
seams. They exist for the cases a variable font cannot serve (email, print, an old embed), not as
a fallback for old browsers that also lack overlap support.

## 9. The italic as a second variable font

A group with `"italic": true` is exported with `params(..., italic_angle)` (default 10°) and built
as its own file, default `<Family>-Italic-VF.woff2`. Its metadata (plan finding F004): subfamily
and typographic subfamily "Italic" (and "Bold Italic" for the instance), `post.italicAngle` set
(negative for a right-leaning slant, as the OpenType specification defines it), the OS/2
`fsSelection` italic bit, `macStyle` italic, and a slanted straight tick
derived from the slanted apostrophe. The two opening quotes an italic group derives from it grow, since
0.7.0, to hold their slanted ink (`quoteleft` and `quotedblleft` advance by at least `round(xMax + max(xMin, 0))`
of their own polygons, so the right side bearing is never negative and equals the left wherever that value sets the advance); the closing quotes keep the
apostrophe-derived advances, and a roman group's quotes are unchanged (generator.md section 9). The CSS wires it as a second `@font-face` with
`font-style: italic` and the same family name; a page test checks `document.fonts.check` and the
computed font in Chrome. Status: pipeline-tested on the neutral example (compatibility, folds,
hairlines, build); **not design-reviewed in any shipped font** in this form. An unwired italic is
not advertised in the CSS.

## 10. One-axis builds

A group's `axes` may hold one axis (`wght` only). `build.py` derives axes and masters from the
config (plan finding F003 found Bract's builder hard-coded `axes[1] == opsz` and four names), and
the smoke run builds three fixtures: two-axis roman (the neutral example), wght-only roman and
wght-only italic (the Driftwood example). A one-axis group still needs two masters, and the
`avar` map still applies.

## 11. The export JSON contract (templates/export.schema.json)

One file per group, `schema: "font-design/export/v1"`. Top level: `family`, `group`, `italic`,
`italicAngle`, `eps`, `foldUnits`, `masters`, and, only when `font.json` names a `skeletons` file, `skeletons` (its
name) and `skeletonsSha256` (the sha256 of the file the export applied). Per master: `concept`, `mult`, `location`, `W`,
`thin`, `track`, `space` (the word space in units), `minStrokeWidth` and `minStrokeAt` (`"r stroke 1"`),
`foldedEdges`, `maxBackwardExcursion {raw, decimated}`, `worstFoldAt`, `glyphs`, `kerns`
(`[left, right, value]` triples, the same pair list in every master), `titles` (title → laid width
in units with the emitted kerns and space). Per glyph: `adv`, `polys` (decimated, shipped), `raw`
(undecimated, for the before/after raster), `runs` (edge runs per raw contour), `keptIdx` (the
raw index of each kept point), `sig` (the branch record per stroke), `minw` (`null` when a glyph
has no interior sample, since Infinity has no JSON form), `minwStroke`.

`build.py` re-checks what matters rather than trusting these figures: with `--masters JSON` it
compares branch records and point structure across masters and recomputes the fold measure in
Python from the polygons (re-review finding F001: the first `--masters` path bypassed both). It also
refuses an export whose `skeletons` differs from `font.json`'s key (present in one and not the other, or another
name) or whose `skeletonsSha256` is not the file's sha256 now, naming both values (0.6.0; review F002 of
`docs/plan-skeleton-overrides.md`): `--masters` never runs `export.js`, so without that an export drawn before an
edit of the override would be built and recorded under the new file's hash.

## 12. font.json, key by key (templates/font.schema.json)

The schema forbids unknown keys, so this table is the documentation; `templates/font.example.json`
is a valid instance. Paths are relative to the file.

| Key | Required | Meaning |
|---|---|---|
| `$comment`, `$schema` | no | free text and the schema reference; both ignored by the scripts |
| `family` | yes | the family name in the name table and the default file name (`<Family>-VF.woff2`); no path characters |
| `version` | yes | `major.minor[.patch]`; the name table's version string |
| `concepts` | yes | path to `concepts.js` |
| `skeletons` | no | the face's skeleton override (0.6.0): a **bare** `.js` file name beside `font.json`, no directory part, not one of `gen.js`, `export.js`, `build.py`, `font.json`, `concepts.js`; its function edits the generator's skeleton tables before anything is drawn (`references/generator.md`, "Per-face skeletons"). Hashed into the manifest's `sources_sha256` under its name, beside the five sources, and named in the manifest's `skeletons`. Absent: neither appears and the build is what 0.5.0 built |
| `out_dir` | yes | where the woff2 (and `--ttf`) land; `manifest` overrides the manifest path (default `<out_dir>/manifest.json`) |
| `groups` | yes | one entry per font file, lowercase names (`roman`, `italic`) |
| `groups.*.italic` | yes | `true` builds the group with the italic skeletons and metadata |
| `groups.*.italic_angle` | no | degrees, default 10 |
| `groups.*.file` | no | output path override (`.woff2`) |
| `groups.*.axes[]` | yes | `tag` (four letters), `name`, `min`, `default`, `max`, optional `map` of `[user, design]` pairs for `avar` (must include both ends) |
| `groups.*.masters` | yes | name → `{ concept, mult, location }`; at least two |
| `groups.*.instances[]` | yes | `{ name, location }`; the named instances in `fvar` and the `--static` outputs |
| `groups.*.hairline_floors` | yes | master name → minimum interior stroke width in units; the build fails below it. Set it to the measured minimum rounded down, and copy it into `requirements.json` |
| `charset.required` | yes | every character the display face must set; `export.js --requirements` fails early on a missing skeleton |
| `charset.nbsp_to_space` | yes | map U+00A0 to `space` (83 of 93 Bract titles carried one) |
| `charset.ascii_apostrophe_curly` | yes | U+0027 draws the curly apostrophe; the straight tick stays unmapped (55 of 56 Bract apostrophes were typed straight) |
| `kerning.set` | yes | regex over single-character generator keys; ligatures always join |
| `kerning.threshold` | yes | a pair enters the list when its automatic value reaches this in any master |
| `kerning.hand`, `kerning.space` | yes | hand pairs (`"L|V": -60`; 0 suppresses a pair) and word-space triples |
| `kerning.italic_hand`, `kerning.italic_space` | no | added for an italic group |
| `kerning.sparse_cap` | no | integer ≤ 0 or `null`: the automatic kern of a pair where either glyph covers under 35 % of the band is capped here; default −50; `null` = no cap (export.js refuses any other value) |
| `titles` | no | real titles the exporter lays and the kerning test checks at every reviewed location (plan finding F010) |
| `size_budget_bytes` | yes | the woff2 ceiling |
| `raster` | no | `budget {decimation, union, seam}` in grey levels and `sizes` in px for the FreeType checks |
| `fold_units` | no | `{raw, decimated}` overrides of the exporter's 4 / 10; `build.py` checks the two agree |
| `decimation_eps` | no | RDP tolerance in units, default 1 |
| `typo_metrics` | no | an override: `ascender` and `descender` (≤ 0) written to hhea AND OS/2 typo; `line_gap`, if present, must be 0. Absent, both are the measured extent of every glyph, so macOS (hhea) and Windows or Chrome with `USE_TYPO_METRICS` (typo) draw one line height. OS/2 win is always measured |
| `names` | yes | `fs_type`, `copyright`, `manufacturer`, `designer`, `vendor_id` (1–4 characters), `vendor_url`, `licence`, optional `licence_url`, `description`. **No defaults**: the skill asks the operator for copyright, licence and `fs_type` every time. `fs_type` is `OS/2.fsType`: 4 (Preview & Print) is the usual setting for a proprietary face and 0 (installable) for an open one; 2 (Restricted) makes some tools refuse the font; 8 is editable; +256 forbids subsetting; +512 (bitmap-only embedding) is refused, because the build writes no embedded bitmaps; browsers ignore the field for web fonts. The build refuses a config without it. The examples built from MIT parameters (`neutral`, the template) say 0; `bract` and `driftwood`, whose sites licence them privately, say 4 |
| `source_date_epoch` | yes | `head.created`/`modified`; assigned unconditionally |
| `review.sizes` | yes | CSS px the site sets the face at; `specimen.py` renders every one |
| `review.medium_below_px` | no | sizes under this render at weight 500 in the specimen (0: never) |
| `review.surfaces[]` | yes | `{ name, background, foreground }` hex colours; the specimen's grounds |
| `review.comparison_faces[]` | no | `{ name, family, url?, css_url?, weights? }`: a local woff2 served by `shoot.py` or a Google Fonts stylesheet URL to be re-verified at publish; the "unique" row |
| `review.body_face` | no | the body face the specimen sets beside the display face |

## 13. requirements.json, key by key

Written at the guideline phase, changed only with the operator; the tests compare the built font
against this file so that a `font.json` edit cannot make the suite agree with itself (plan finding
F002). Shape as in `examples/neutral/requirements.json`:

| Key | Meaning |
|---|---|
| `family` | must equal the name table's family |
| `groups.*.axes` | tag → `[min, default, max]` as `fvar` must report them |
| `groups.*.avar` | tag → list of `[normalized user, normalized design]` pairs the `avar` segment map must contain (`[[0.333, 0.6]]` is the reviewed Medium) |
| `groups.*.masters`, `groups.*.instances` | name → location; the instancing test (F013) and the `fvar` instance test read these |
| `groups.*.hairline_floors` | the floors the hairline test asserts; **fixed here**, not read from the manifest |
| `groups.*.interpolated_check` | `location`, `between` two masters, `t`: the kerning and advance test expects the interpolated values within a unit of the mix at `t` |
| `groups.*.display_masters_tighter_than` | display master → text master whose advances it must undercut (the `track` term lives in advances, F005) |
| `groups.*.italic_angle` | the `post.italicAngle` magnitude the italic group's metadata test expects |
| `cmap` | the exact character set the cmap must equal |
| `required_characters` | what `export.js --requirements` checks skeletons for, and the coverage test's floor; holds U+00A0 beside the space whenever a title carries it (`mine-charset.py` writes it so), because `nbsp_to_space` maps it to the space glyph and `test_every_required_character_is_mapped` checks the mapping |
| `hand_kerns` | pairs whose emitted value must match, at every master |
| `titles` | laid widths are compared with the exporter's at every master |
| `size_budget_bytes`, `fold_units`, `gasp` | the budget, the fold thresholds and the `gasp` ranges (`65535: 15`) the tests assert |
| `names` | `family`, `copyright`, `manufacturer`, `vendor_id`, `vendor_url`, `licence_contains`, `fs_type` (the embedding permission the font must carry) |
| `groups.*.vertical_metrics` | `ascender`, `descender`, `line_gap`: what hhea and OS/2 typo must carry, the reviewed line height. Read it from the first build's `vertical metrics written` line and review it |
| `tables` | `code_page_range1` (the exact `ulCodePageRange1`), `prep_hex` (the `prep` program's bytes, hex), `mac_names` (`false`: no platform-1 name records) |
| `accepted_qa_findings` | `[{ id, reason, codes? }]`: the FontBakery FAIL or ERROR check ids the project accepts, each with why (`scripts/fontbakery-gate.py`; required there, `[]` when nothing is accepted). `codes` (optional) lists the FontBakery message codes accepted: a FAIL, ERROR or FATAL message of that check with another code blocks, so a new kind of failure is not hidden (a new failure with an accepted code, such as one more letter without a capital, still passes and shows only in the printed messages: the match is never on message text, which FontBakery rewords between versions); without `codes` the match is the check id alone and the reason names what was seen. The neutral example lists the real codes |

The exact test names that read each key are listed in `references/testing.md`, which is kept to
`scripts/tests/test_font.py`'s function names.

### Known limits of the STAT table the build writes

- Axis values other than weights are named by number: the neutral roman's `opsz` values are `24` and `72`. A tool
  that composes an instance name from STAT therefore calls the fvar instance "Display" (wght 400, opsz 72) "72",
  and "Display Bold" "Bold 72". The fvar instance names, which browsers and font pickers read, are the ones in
  `font.json`; only STAT-composing tools see the numbers.
- An italic group's STAT has no `ital` axis (FontBakery's `opentype/STAT/ital_axis`, accepted in the neutral
  example). A tool composing a name from the italic file's STAT leaves the style out, so "Medium Italic" composes
  as "Medium"; the elided fallback name is "Italic" only for the case where every axis value is elided.

### Changing the vertical metrics changes `line-height: normal`

Until 2026-11-16 the build wrote hhea from the measured glyph extent (the neutral roman: 957/-255, line
gap 0) and OS/2 typo from `typo_metrics` (default 760/-240 with a line gap of 200). macOS reads hhea;
Windows and Chrome with `USE_TYPO_METRICS` read typo; so one font gave 1.212 em on a Mac and 1.2 em
elsewhere for any element left at `line-height: normal`. The build now writes one set to both. With no
`typo_metrics` key that set is the measured extent, so macOS is unchanged and the typo platforms move
to it; with a `typo_metrics` override both platforms take the override, which moves macOS if it differs
from the extent. A face already live whose CSS leaves `line-height` at `normal` anywhere (the audit
misses some, a form control, a caption) must compare before and after: the `vertical metrics written`
line prints the figure to compare. Elements with an explicit `line-height` are not affected.

## 14. Commands

```
node scripts/export.js --font font.json [--group roman] [--eps 1] [--requirements requirements.json] out/roman.json
.venv/bin/python3 scripts/build.py --font font.json                 # export, build, self-check, write woff2 + manifest
.venv/bin/python3 scripts/build.py --font font.json --check         # rebuild to a temp dir; exit 1 if the shipped bytes differ
.venv/bin/python3 scripts/build.py --font font.json --group roman --masters out/roman.json   # reuse an export; it is re-checked, never trusted, and refused when drawn with another skeletons file (or none)
.venv/bin/python3 scripts/build.py --font font.json --static out/static        # static instances for modern renderers, overlaps kept
.venv/bin/python3 scripts/build.py --font font.json --group roman --ttf out/Family-VF.ttf    # also write the TTF for inspection; never ship it
.venv/bin/python3 scripts/build.py --font font.json --out-dir /tmp/try          # a whole build elsewhere: woff2s AND manifest in that directory (the `manifest` key is ignored)
.venv/bin/python3 scripts/opsz.py OUT_DIR --serve DIR --font-url /fonts/F-VF.woff2 --family F --axis 24 72 --px 24 48 72   # which opsz Chrome applies at each CSS px; --axis is the fvar range
.venv/bin/python3 scripts/check-env.py                                  # is the toolchain here; the fix command for each missing piece
.venv/bin/python3 scripts/fontbakery-gate.py --font font.json --requirements requirements.json   # FontBakery on each group's TTF; fails on a finding not accepted
.venv/bin/python3 scripts/fallback-metrics.py --font font.json --location opsz=72   # size-adjust and overrides for a local() fallback face
.venv/bin/python3 scripts/diff.py work/diff --font font.json --before work/round-3   # renders AND values; --after defaults to the shipped files where font.json puts them
.venv/bin/python3 scripts/fetch-version.py 0.7.1 work/skill-0.7.1   # the skill's own code at a released version, from the git tag or the GitHub tag archive
.venv/bin/python3 scripts/update-check.py work/update --font font.json   # what the installed skill would change in a shipped face; writes update.md, never the face folder
```

These lines are typed from the skill folder for a face kept beside it. For a face in a site they are typed from the site
root with `<skill>/.venv/bin/python3 <skill>/scripts/<tool>.py` and `--font tools/<face>/font.json`
(`references/face-folder.md`, section 2).

`.venv/bin/python3` is the skill venv's interpreter, run from the skill folder (`SKILL.md`, "Finding the skill folder"); the scripts themselves use `sys.executable`
for anything they run in turn. Node ≥ 20.

## 15. Site wiring: the fallback face with metric overrides and `text-wrap: balance`

Two optional guards of `scripts/tests/test_site_wiring.py.tmpl` (slots `fallback_family` and
`balance_selectors`; an empty slot skips its guard with the reason printed).

**Fallback face (guard t).** With `font-display: swap` the first paint is set in the fallback and then
laid out again in the font, so a wider font, or one with a taller line, moves every headline. A
`local()` face with `size-adjust` and the three overrides makes the fallback take the font's room:

```css
@font-face { font-family: "Sampler Fallback"; src: local("Georgia");
  size-adjust: 96.43%; ascent-override: 99.2%; descent-override: 26.4%; line-gap-override: 0%; }
h1 { font-family: "Sampler", "Sampler Fallback", Georgia, serif; }
```

(The numbers show the shape; they are not Sampler's.) The values come from two fonts, so
`scripts/fallback-metrics.py --font font.json --location opsz=72` prints them for Georgia, Times New
Roman and Arial (or any `--fallback NAME=PATH`) from the built font and each fallback's file:

- `size-adjust` = the mean advance of the titles' characters in the web font, in em, divided by the same
  mean in the fallback, over the characters both map, with the web font at `--location`;
- each override = the web font's hhea ascent, descent (as a positive number) or line gap, divided by its
  unitsPerEm and by `size-adjust`: the overrides are shares of the font size after it is scaled.

What it does not do: kerning, the visitor's own copy of the fallback (Georgia on another OS is another
file), and one location only, so a face with an `opsz` axis wants the run at the headline size and a
screenshot of the swap to confirm. The guard holds the DECLARATION to the shipped font: a `local()` face with
all four properties whose overrides times `size-adjust` equal the font's hhea metrics within 0.5 points of
the em, and a display stack that lists the family and then the fallback face. It cannot hold `size-adjust`
to the fallback's real widths without the fallback's file, and a rebuilt font with other metrics fails it
until the overrides are recomputed. The descriptors are CSS Fonts 5; this repository ran them in Chrome only.
One measurement, to show the size of the effect and that the formula is the right way round (Chrome on
macOS, 2026-11-16, the neutral roman at 40 px, `line-height: normal`, the string "The Quiet Harbour at
Dawn"): the web font set 521.0 × 48.0 px, bare Georgia 493.3 × 46.0, and Georgia through the face this script
printed (`size-adjust` 107.45%) 530.1 × 48.0. The height matches; the width is 1.7 % wide of the font because
the average ignores kerning, which the swap would still move by that much.

**`text-wrap: balance` (guard u).** On a wrapped headline it spreads the words over equal lines, so the last
line is not one short word; a title then needs no hand-placed no-break space as a widow guard (83 of Bract's
93 titles carry one, and the no-break space is a charset trap the whole pipeline carries: keep the
`nbsp_to_space` mapping, because other content still has them). The guard requires every `text-wrap` value
declared for each listed selector to be `balance`. It reads declarations on the listed selectors only; it does not compute the
cascade, so `.hero { text-wrap: wrap }` overriding `h1` on `<h1 class="hero">` passes. The fallback guard likewise holds the
vertical overrides and the stack, not the horizontal `size-adjust` (above). A browser that does not know the property ignores it and
wraps as before, and it does not change a title that already fits on one line.
