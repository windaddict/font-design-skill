# Genre render review, 2026-11-25 (the re-read after a `cut` end's shortened corner moved onto the stroke's own edge, 0.13.0)

WHAT IT'S FOR: the record behind the dated verdicts in `references/genres.md`, replacing `docs/reviews/genres-2026-11-25.md` as the one
`tests/test_genres.py` holds the recipes to. The 0.13.0 change (`docs/plan-cut-curved-step.md`: the corner a `cut` end shortens is placed on the
stroke's own edge, issue #27) redraws every glyph whose `cut` end moves a corner back. Two of the ten recipes draw a `cut` end: `grot` and
`geometric`. Their outline digests moved and the other eight did not. The rule in `genres.md` section 6 is that a stale digest means a new
reading and a new record, not an edited digest. The earlier record `genres-2026-11-25.md` stays as history. This record says what was read,
what was concluded per recipe, and the digests of the outlines as drawn now.

## What was reviewed

- The page built by `node scripts/concepts/build-page.js --template round1 --concepts templates/concepts.genres.js --content <content file>` with
  `scripts/gen.js` as 0.13.0 draws it, served with the built neutral Sampler beside it, and shot by `scripts/shoot.py` at 1280 px, 2x,
  `--height 16000 --dump-dom --family Sampler --font-url /fonts/Sampler-VF.woff2`, in headless Chrome 158. The DOM probe reported `bad 0`. The screenshots
  are not kept in the repository.
- The page's own specimen line does not set every key the change redraws. The reading therefore used a scratch copy of `content.genres.json` (not in the
  repository) whose lineup text was `CGJS acefgrst ff fi 123569 $&'*,;? šāéáóúíàèòùìâêäëç©ÁÀÉÈÍÓÚÇ`. That covers the keys
  `C G J S a c e f g r s t`, `ff fi`, `1 2 3 5 6 9`, `$ & ' * , ; ?` and the accented forms listed there. Three pages were built from it: lineup weight
  Regular (mult 1), Medium (mult 1.25) and Bold (mult 1.5), the last two by presetting the weight select in a scratch copy of the generated page, since the page
  has no query parameter for the weight. The `grot` and `geometric` lineup rows were cropped from the 2x shots and read at the cropped size (2200 px wide), without a further enlargement.
- Read by one model reviewer (the implementer, not a fresh reviewer), on 2026-11-25, `grot` and `geometric` only. The other eight recipes set no `cut` end and their digests equal the
  2026-11-25 (0.11.0) record's under every node major, so nothing was re-judged for them and their verdicts carry over with their old date.
- What was seen, per recipe, in the lineup row at Regular, Medium and Bold: no thin spike at a cut corner and no step where a curved terminal meets its cut corner,
  on `t`, `r`, `f`, `J`, `c`, `e`, `s` and `a`, in either recipe. The 0.11.0 record's thorn at the foot of `t`, under the `r` terminal, at the top of `f` and at the tail of
  `J` is not visible at this size. What remains is the hooked terminal of `r f t J 9` named in `genres.md` section 7 (issue #1): a small hook or beak, larger at Bold, and the top flick of the
  `f` of `ff` and `fi`. The accents sit hard against the letter at Bold, and the cedilla of `ç Ç` is heavy; those are accent placement and weight collisions, not cut corners, and the
  0.11.0 record named them too. The reading is at the cropped size only, so a step smaller than about 2 px at 2x could be missed. `CUT-STEP` and `CUT-STEP-SWELL` in `tests/test_cut_step.py`
  hold the corner to the edge by measurement (0.05 units), which this reading does not replace.
- Limits of the reading: one reviewer, who is the implementer; one pass at the cropped size. The page sets no italic and no multiplier 1.65.
  `docs/reviews/comparison-0.13.0.md` names the page that sets roman and italic at 1, 1.5 and 1.65, which the operator reads under `design-acceptance`. The lineup text sets every one of the 53 keys per recipe named in the plan, and each was read in the same line at all three weights, with no per-key enlargement.
- The reading changed no verdict word. `grot` stays **partly** and `geometric` stays **no**; both take the date of this reading and a sentence about the cut terminals.
- Operator ruling: not yet given (`genre-review-acceptance`).

## Verdicts

| recipe | verdict | date | what was seen |
|---|---|---|---|
| didone | partly | 2026-11-22 | Moderate contrast because of the hairline floor, and equal-weight diagonals on A V W M N v w x y, so it reads as a light modern, not a Didone. The diagonals need an expansion model, which is out of scope |
| fatface | no | 2026-11-22 | Stems are about 1/6 of the cap height even at the Bold; W past its range cannot reach 1/3-cap stems without collapsing the counters. It needs new shapes |
| scotch | reaches | 2026-11-22 | A near-twin of the Didone at these sizes; the bracket and the a terminal are what differ. Also shipped and reviewed as Bract's foil on hopsafari.com (2026-11-15). The italic is refused (section 4) |
| clarendon | no | 2026-11-22 | The serifs are short pointed wedges, not square bracketed slabs, so it reads as a wedge serif. A longer serifLen with serifGrow 0 might fix it; untested. Rendering defects: section 7 |
| slab | reaches | 2026-11-22 | Square unbracketed slabs at stem weight, low contrast, in Rockwell or Memphis proportion. Rendering defects: section 7 |
| grot | partly | 2026-11-25 | A monoline neo-grotesque with level-cut joints and a straight-leg R; the double-storey g with its sharp ear and the hooked a read humanist, which needs skeleton work. Seen after the cut default was fixed (section 7). The cut terminals were re-read on 2026-11-25 after 0.13.0 placed the shortened corner on the stroke's own edge: no spike and no step at the corner on t, r, f and J, but the terminals of f, r and t end in a small hook or beak, more at Bold (section 7) |
| geometric | no | 2026-11-25 | A wide humanist sans, not Futura-like: it needs a circular O, a single-storey a and pointed apexes, all unbuilt. The cut terminals were re-read on 2026-11-25 after 0.13.0 placed the shortened corner on the stroke's own edge: no spike and no step at the corner on t, r and f, but the terminals end in a small hook or beak, more at Bold (section 7) |
| reverse | partly | 2026-11-22 | Reverse contrast, but light, at typewriter weight; a larger W and a lower thin might reach a French Clarendon (untested). Rendering defects, and a lump where the bowls of P, B and R meet the thin stem: section 7 |
| opsz-text | reaches | 2026-11-22 | As a pair: a wider, looser text cut with a taller x-height beside a narrower, higher-contrast display cut. The display cut is close to the Didone |
| opsz-display | reaches | 2026-11-22 | As a pair: a wider, looser text cut with a taller x-height beside a narrower, higher-contrast display cut. The display cut is close to the Didone |

## Outline digests

For each recipe: sha256 over `[mult, key, polygons]` for every key of `G` in sorted order, roman, mult 1, 1.25 then 1.5, each coordinate rounded to 0.01, as
`tests/test_genres.py::current_digests()` computes it, from `scripts/gen.js` as 0.13.0 draws. Eight digests equal the 2026-11-25 (0.11.0) record's (`didone`, `fatface`,
`scotch`, `clarendon`, `slab`, `reverse`, `opsz-text`, `opsz-display`) and two differ (`grot`, `geometric`). The node 26 digests come from `current_digests()` under node 26.13.1.
The node 20 and 22 digests come from the same `DIGEST` script (read from the test module) and the same `GEN` and `GENRES_JS` arguments, run on this machine, not on CI, under node 20.20.2
and node 22.23.5, each fetched with `npx --yes -p node@<version> node -e "$DIGEST" <gen.js> <concepts.genres.js>` and run twice with byte-equal output. All three majors agree on every
digest. The first CI run of `tests/test_genres.py` on the branch (`release-acceptance`) is the check on a CI machine. The test recomputes the digests under the running node and fails with
"the genre verdict for <id> is stale" when the digest recorded for that node major differs, and with instructions to record it when the major is not listed. If it fails after a deliberate change
to a recipe or to `gen.js`, the remedy is a new render review (`genres.md` section 6) and a new record, not editing the digest.

```json digests
{
 "by_node_major": {
  "20": {
   "didone": "6f15d5e8e7164e5d634c39f2846da4ad87e3427a4a367f33daa8f2eb4f319ebc",
   "fatface": "4c43ece96ea733baa19761490458581dd53f7f7d06b7dcc04cc9bcf37b5ca355",
   "scotch": "a99d88b6e1ff672096bb3b45b31bad272e6287e3119c9afe759cce94fc72410e",
   "clarendon": "ebf2241c782ffbaa5223706a680c6c8d6ce09389ccaf2c68762342d56f6e51e5",
   "slab": "24064d667b7619b73775f3c34aaf75f974a700dca6172dda2bcdaec7e9c67ff0",
   "grot": "ce6e654421e0aed8377a76d0f5a94e1a1b490494239a100d5208aa46f08a674a",
   "geometric": "a4d8ac5f9df6efe766a6d29e77b28f012000bddae639a95ef1a555a986123881",
   "reverse": "25aa8b4473dd3c4a2bb18eb2241f82918c6712fa069c557b464ce3da67c370b8",
   "opsz-text": "65a46ebf1e7695218dbddffaeccffc5bc383b8c84e441d75bff3310ef2fa699f",
   "opsz-display": "1631998bc218a56116337a0e81c9927d521dfa42aa42f47b3550b9b4dfa94127"
  },
  "22": {
   "didone": "6f15d5e8e7164e5d634c39f2846da4ad87e3427a4a367f33daa8f2eb4f319ebc",
   "fatface": "4c43ece96ea733baa19761490458581dd53f7f7d06b7dcc04cc9bcf37b5ca355",
   "scotch": "a99d88b6e1ff672096bb3b45b31bad272e6287e3119c9afe759cce94fc72410e",
   "clarendon": "ebf2241c782ffbaa5223706a680c6c8d6ce09389ccaf2c68762342d56f6e51e5",
   "slab": "24064d667b7619b73775f3c34aaf75f974a700dca6172dda2bcdaec7e9c67ff0",
   "grot": "ce6e654421e0aed8377a76d0f5a94e1a1b490494239a100d5208aa46f08a674a",
   "geometric": "a4d8ac5f9df6efe766a6d29e77b28f012000bddae639a95ef1a555a986123881",
   "reverse": "25aa8b4473dd3c4a2bb18eb2241f82918c6712fa069c557b464ce3da67c370b8",
   "opsz-text": "65a46ebf1e7695218dbddffaeccffc5bc383b8c84e441d75bff3310ef2fa699f",
   "opsz-display": "1631998bc218a56116337a0e81c9927d521dfa42aa42f47b3550b9b4dfa94127"
  },
  "26": {
   "didone": "6f15d5e8e7164e5d634c39f2846da4ad87e3427a4a367f33daa8f2eb4f319ebc",
   "fatface": "4c43ece96ea733baa19761490458581dd53f7f7d06b7dcc04cc9bcf37b5ca355",
   "scotch": "a99d88b6e1ff672096bb3b45b31bad272e6287e3119c9afe759cce94fc72410e",
   "clarendon": "ebf2241c782ffbaa5223706a680c6c8d6ce09389ccaf2c68762342d56f6e51e5",
   "slab": "24064d667b7619b73775f3c34aaf75f974a700dca6172dda2bcdaec7e9c67ff0",
   "grot": "ce6e654421e0aed8377a76d0f5a94e1a1b490494239a100d5208aa46f08a674a",
   "geometric": "a4d8ac5f9df6efe766a6d29e77b28f012000bddae639a95ef1a555a986123881",
   "reverse": "25aa8b4473dd3c4a2bb18eb2241f82918c6712fa069c557b464ce3da67c370b8",
   "opsz-text": "65a46ebf1e7695218dbddffaeccffc5bc383b8c84e441d75bff3310ef2fa699f",
   "opsz-display": "1631998bc218a56116337a0e81c9927d521dfa42aa42f47b3550b9b4dfa94127"
  }
 }
}
```
