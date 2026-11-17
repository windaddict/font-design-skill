# Plan: {{site}}'s own display face, shipped as a variable web font

<!-- WHAT THIS TEMPLATE IS FOR: the build plan a run writes at phase 6, in the shape of Bract's
docs/plan-display-font.md, for independent review (Impasse) before any code and for the record
afterwards. Fill every {{slot}}, delete the HTML comments, keep the section order, and keep the
markers: a reviewer and the operator must be able to tell a checked claim from a guess. Section
"Independent review and what it changed" starts EMPTY and is filled after the review; where it
conflicts with an earlier section, it wins. -->

WHAT IT'S FOR: the implementation plan for replacing {{old face}} with a typeface drawn for this
site, written by {{model}} on {{YYYY-MM-DD}} before any code, for independent review and then
implementation. The design was chosen across {{N}} rounds of generator sketches; the record of those
rounds is {{where}}.

Status: **{{planned | built (date) after N review rounds; not yet deployed | deployed (date)}}.**
{{After the build: where the as-built differs from the sections below, in one paragraph, and the
pointer to the record (docs/<face>-font.md).}}

**Markers.** **(read)** = checked against the named file. **(measured)** = run or counted here.
**(inferred)** = not verified; the implementer must check before relying on it.

## 0. Success criterion (the operator's words)

> "{{goal sentence, verbatim}}"

Every review round judges the built font against these tests, in order:

1. **Readable** at every size the site uses: {{sizes per element, from mine-sizes.py}}, on
   {{surfaces}}, at 1× and 2×.
2. **Unique**: not mistakable for {{old face}}, {{body face}} or {{a stock face}}. {{The features that
   must survive at the heading size, not only at the largest.}}
3. **Complements the design and brand**: {{the brand sources}}.

{{Time and cost: what the operator said; how many review rounds are budgeted.}}

## 1. Decision: variable font, TrueType glyf + gvar, {{N}} axes, {{N}} masters

### 1.1 Why the generator can be made interpolation-compatible

{{The chosen concept's parameters (read: concepts.js). Which branches in the generator depend on
geometry and which on parameters; the pinned-sampling and branch-record guarantees; the measured
result of exporting the planned masters (measured): N incompatible glyphs. The project's font.json
does not exist yet (phase 7 creates it from this plan), so the export runs from a scratch font.json
in the project, at tools/<face>/work/plan-check.json (templates/font.example.json copied, `concepts`
pointed at the project's concepts.js, the planned masters and axes written in; work/ is scratch and not
committed, and nothing is written into the installed skill): name that file and the export command here.}}

### 1.2 Point budget and decimation

{{Points per master before decimation (measured, from the same scratch export as 1.1); the
tolerance; the estimated size (inferred until built); the budget.}}

### 1.3 Axes, masters, instances

| Axis | Range | Default | Masters | Notes |
|---|---|---|---|---|
| `wght` | {{400–700}} | {{400}} | {{400 = text ×1.0, 700 = text ×1.5}} | avar user 500 → design {{580}} (normalized 0.333 → {{0.6}}), the reviewed Medium |
| {{`opsz`}} | {{40–80}} | {{40}} | {{40 = text cut, 80 = display cut}} | endpoints to be set from `opsz.py`'s measurement, not assumed |

**Masters: a full rectangle** ({{the four corners}}). {{Which corners no site rule reaches at a 16 px
root, and why they are reachable anyway (rem sizes scale with the reader's root).}}

Hairlines per size (nominal `W × thin`; the exporter measures the real minimum):

| Size | Weight | Thin stroke (units) | px |
|---|---|---|---|
| {{15.2}} | {{500}} | {{…}} | {{…}} |

### 1.4 Tooling

{{Node for the generator and exporter; the Python venv and its pinned packages; FontBuilder isTTF,
varLib.build, feaLib for kern and liga; the fact that varLib skips incompatible glyphs with a
warning, hence the pre-check; SOURCE_DATE_EPOCH assigned.}}

### 1.5 Static fallback (only if 1.1 fails in practice)

{{The contingency in one paragraph, and the statement that if it is invoked it gets its own plan
and review before code (Bract plan finding F011).}}

## 2. Where the code lives

```
{{tools/<face>/}}
  gen.js  export.js  build.py  bounds.js  font.json  requirements.json  concepts.js
  README.md  manifest.json  concepts/  review/
```

### 2.1 Fork header and licence

{{The skill version; the origin line; name-table copyright and licence per the operator's answer in
section 8.}}

### 2.2 gen.js changes

{{New skeletons needed by real titles (measured from the built pages); cmap decisions (U+0027,
U+00A0) with counts; anything else.}}

### 2.3 export.js and font.json

{{Groups, masters, kern set and threshold, hand pairs, titles.}}

### 2.4 build.py

{{Self-checks that fail the build, each with its exact guarantee; outputs; --check.}}

## 3. Output and the exact stylesheet / template changes

### 3.1 Files
{{Add; remove with git rm; what already serves woff2 (read).}}

### 3.2 Stylesheet
{{One @font-face with the weight range and font-display; the stacks to change (read: line
numbers); font-optical-sizing: auto; weight 500 on the small titles; letter-spacing removed on
display rules; font-synthesis: none (a recommendation).}}

### 3.3 Templates
{{The preload link, with crossorigin, before the stylesheet, in every template.}}

## 4. Earlier review suggestions included above

{{From the concept rounds.}}

## 5. Tests

| | Test | Asserts | Mutation |
|---|---|---|---|
| a | {{…}} | {{…}} | {{…}} |

{{Current suite count; how many this adds.}}

## 6. Docs to update

{{The record (templates/font-record.md); the tool README; the site's CLAUDE.md; the repo README.}}

## 7. The review loop ({{≤ 6}} rounds)

{{Tooling: shoot.py pages, widths (where the fluid sizes cross the axis), scales; the specimen's
rows. Each round. The checklist (readable; smooth across opsz; unique; complements; kerning;
rendering integrity). The stop rule.}}

## 8. Risks and questions for the operator

Risks:
- {{…}}

Questions:
1. {{Name, and the collision check.}}
2. {{Remove the old face's files, or keep them unused?}}
3. {{Name-table owner and licence text.}}
4. {{Content traps: fix the content or carry the glyph?}}
5. {{…}}

## 9. Order of work and parallelism

{{Numbered; what runs in parallel and why it shortens the critical path.}}

## 10. Independent review and what it changed

<!-- Leave empty until the review has run. Then: the backend and provider, the date, the
artifact's contents (the plan PLUS the generator, the precedent build and the stylesheet: both
sides of every relational claim), the artifact revision from the result, the independence notice
if any. One row per finding: what it claimed, how the host checked it (read / measured), and the
change to the plan. A rejection needs contradicting evidence. Then the operator's answers to
section 8. -->

Artifact: {{…}}; revision `{{sha256…}}`. {{N}} findings; each checked against the code by the host.
{{Accepted / rejected with evidence / deadlocked and escalated.}} {{Independence notice, verbatim,
if the result carried one.}}

| # | Finding | Checked | Change to the plan |
|---|---|---|---|
| F001 | {{…}} | {{read / measured, where}} | {{…}} |

Operator answers ({{date}}): {{…}}.
