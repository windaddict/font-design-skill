# Cut end comparison page, 0.13.0

WHAT IT'S FOR: the record of the before and after drawings the operator rules on (`design-acceptance`, part 2) for the change that places a `cut` end's shortened corner on the stroke's own edge (issue #27). The page was drawn from the final generator, not from the prototypes of the plan.

- Page (private to the operator's account): https://claude.ai/artifact/9JGNt49m9oKBtyyta15jd1
- Generator drawn from: `scripts/gen.js`, sha256 `a834d456d84f18afea16d4a8d0db0f7f14aa0860a99291d2e2ca23e3382e5999`. The "before" column is `scripts/gen.js` at commit 7170554 (0.12.0), sha256 `d47f32dc3c471cf03d1cff3f90234bb5c86e1f107093157f9dd2c46f00205898`.
- Recipes: `grot` and `geometric` of `templates/concepts.genres.js`, `field` of `examples/bract/concepts.js`, and the swelled fixture (the `grot` recipe with `swell` 0.35 and `cut` ends at 32 degrees).
- Glyphs: `c s e a f t r 9` and the accented `á à é è` for the three shipped recipes; `x X Y 7 k l n c` for the swelled fixture.
- Styles and multipliers: roman and italic (italic at 10 degrees) at 1, 1.5 and 1.65. That is 6 style and multiplier combinations per recipe, each drawn by both generators: 12 drawings per recipe, 48 on the page (12 each for `grot`, `geometric`, `field` and the swelled fixture; counted in the generated HTML before publishing).
- Simplification: each outline is simplified by 0.25 units to keep the page small; no measurement reads the page.
- Not on the page: the 0.13.0 "alternative" drawing (cut edge tilted) of the first page. This page compares 0.12.0 with what ships.

## Implementer's reading

The implementer did not view the rendered page; this record states what was measured, not what was seen. Measured with `tests/test_cut_step.py::all_rows()` on the final generator: 92 edge rows of the acute and grave accents of `grot` and `geometric` (multipliers 1.3 to 1.65) belong to a stroke shorter than its cut's reach (`exhausted`). None of them stops more than 0.05 units short of its cut line (`pastLine`), so on the shipped accents the measure finds no flat-topped terminal that stops short. The operator's reading of those terminals is `design-acceptance` part 2.

## Operator ruling

`design-acceptance` part 2: accepted on 2026-11-26, in the session that opened PR #31. The operator accepted the 0.13.0 cut terminals of `grot` and `geometric`, roman and italic at 1, 1.5 and 1.65, and the short acute and grave accents.
