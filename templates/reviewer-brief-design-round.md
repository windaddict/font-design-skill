# Brief: design-review round {{N}} of {{Family}} on {{site}}

<!-- WHAT THIS TEMPLATE IS FOR: the instruction the host gives a FRESH strong-model subagent for
each round of phase 8. A new subagent each round; it has not seen the build or the previous
round's findings. Fill the {{slots}} with the goal sentence verbatim, the checklist, the crop
directory, and what changed since the last round as parameters and numbers. Do not include the
previous reviewer's verdicts. -->

You are reviewing a built web font on the pages it was drawn for. You have not seen the earlier
rounds or the build. Read-only: you review, the host changes.

## The operator's goal, verbatim

> "{{goal sentence, exactly as the operator wrote it}}"

The tests, in order: readable at every size the site uses; unique, not mistakable for {{old
face}}, {{body face}} or a stock face; complements {{the brand sources}}.

## What to read

- Crops and full pages: `{{directory}}`, named `<page>-<width>@<scale>x[-<band>].png`. Pages:
  {{list}}. Widths: {{500 667 889 1280 1600}} ({{which widths are where the fluid headings cross
  the optical-size axis}}). Scales 1× and 2×. `{{--root 150 shots}}`: the pages as a reader with a
  24 px default font size sees them.
- The specimen: `{{specimen PNGs}}`: real titles at {{sizes}}, the surfaces ({{names}}), the face
  beside {{comparison faces}} at {{sizes}}, the optical-size crossing rows ({{39 40 44 48}}) and
  intermediate instances ({{wght 550 / opsz 60}}), a kerning row, an NBSP-wrap row, a quotes row, the
  spacing control strings (each lowercase between nn and oo, each capital between HH and OO, each figure
  between 00 and 11, each punctuation mark after r, f and y) and the legibility row `Il1 O0 B8 rn m cl d`
  at {{the smallest size}}, and the junction row `1 4 5 v w A M N V W AVAWMNW vwvwv` in the Bold at the
  same size.
- The font's configuration: `{{font.json}}`; the masters and floors: `{{manifest.json}}`.
- What changed since round {{N−1}}: `{{diff dir}}/diff.md` ({{N}} of {{M}} renders changed; the changed renders
  sorted by the share of ink that moved) and its before / after / diff PNGs, `{{diff dir}}/<group>-<instance>-<size>px-<title>.png`
  (red: more ink after, blue: less). They are FreeType renders of the project's titles on one machine,
  unhinted: not Chrome, not the page. {{For round 1: "first build, no diff".}} Then the parameter changes, as numbers: {{e.g. "serifGrow 0.6 → 0.35; the
  fold pin added; the t's top end s → x; the a bowl joins at 290"}}. {{For round 1: "first build".}}
- {{Optional, only when the platform run was made for this build; otherwise delete this item.}} The
  platform run's comparison: `{{compare dir}}/compare.md` and its PNGs, one per row, each stacking the same
  row from every leg (Windows Server, macOS and Ubuntu runners; headless Chrome and Playwright's Firefox),
  labelled with the OS, browser version, scale and ClearType setting. Read "Refused" and "Mismatched" first,
  then the rows, smallest size first. These are GitHub-hosted runners, not a reader's machine; the colour
  fringes in a Chrome-on-Windows crop are ClearType's subpixel rendering, not a defect by themselves. A
  stroke that breaks up or drops out at 1× on a real page in any leg is a finding at 1× on a real page;
  one that only reads lighter is not a defect.

## The checklist, in order

1. **Readable**: the smallest sizes ({{15.2 and 16.8 px, Medium}}) on {{the main surface}}: open
   counters, hairlines present, the NBSP honoured, curly apostrophes. The Bold at {{heading sizes}}:
   no clogging, serifs grown but not slab, the wordmark on {{the dark surface}}. The Regular at
   {{large sizes}}: reads as intended, not brittle; descenders clear at the site's `line-height`.
2. **Smooth across the optical-size axis**: {{39 vs 40 vs 44 vs 48}}; the fluid H1 at the widths
   where it crosses.
3. **Unique**: beside {{old face}} and {{body face}} at {{two sizes}}.
4. **Complements**: the surfaces and the chrome the face sits in; harmony with the body face.
5. **Spacing, then kerning**: read the control strings for rhythm first; a letter that crowds or gaps
   between nn/oo, HH/OO or 00/11 is a spacing finding, reported before any kern finding. Then punctuation
   after r, f and y, the pair row and the real titles.
6. **Rendering integrity**: no seams at overlaps at 2×, no tofu, no dropouts at the intermediate
   instances.
7. **The italic** ({{omit this row when no italic group is built}}): read real words that use the
   redrawn italic letters — a, e, f, k, v, w, y (and d, h, i, l, m, n, r, u) — and the x, at {{the
   italic sizes}}, not an alphabet row. Precedent: Driftwood's cursive italic x read as a Greek chi
   in running text and was replaced by a slanted roman x; say if any letter reads as another letter
   or another script. Check that the exit strokes of adjacent letters do not collide at the
   tightest kerned pairs ({{the italic hand pairs}}), and that the italic serifs, 60 % of the
   roman's length, still read at {{the smallest italic size}}.

8. **Legibility at {{the smallest size}}**: the row `Il1 O0 B8 rn m cl d`: say which pairs read as one
   another and whether {{the site}} can tolerate that at that size. Do not ask for a dyslexia-specific
   face (the research behind this skill found no evidence that one helps).
9. **Junctions at {{the smallest size}}**: the junction row, in the Bold: say which of `1 4 5 v w A M N V W`
   close up or darken where two strokes meet (a blot, a filled crotch) and whether {{the site}} can tolerate
   that at that size. `y` and `k` are not in the row: their strokes cross, they do not end on each other.

## What to produce

Findings **ranked by visibility at 1× on a real page**, then visible at 2×, then visible only in
the specimen. Each finding: the crop file name; the element and size; what you see; what it
changes for the font (a parameter, a skeleton, a kern) or for the site (a CSS rule); your
confidence. Then one sentence: does the face meet the goal, and is anything visible at 1× on a
real page? If nothing is, say so plainly; that is the stop condition.

## Rules

- A crop name per finding. A finding without one is not a finding.
- Say when you are uncertain, and what would settle it (a zoom, a measurement, a different width).
- Do not propose a redesign; propose the smallest change that removes what you see.
- Do not edit anything. Do not infer what the previous round found.
