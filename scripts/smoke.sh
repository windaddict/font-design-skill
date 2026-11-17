#!/usr/bin/env bash
# smoke.sh: the pre-publish run for this skill, and the manual check after any change to scripts/.
#
# WHAT IT'S FOR: proves the whole pipeline runs on the neutral fixture and that the two precedent
# configurations still export and build, so a change to the generator, exporter or builder cannot
# ship silently broken. Default: no browser (what the CI matrix job runs). --full adds the Chrome
# steps (what the CI chrome job runs from step 6 on): the three concept rounds built and executed in
# Chrome with a face switch, a font-load assertion and the comparison face proved visibly set in
# Sampler, the specimen shot at two widths and an enlarged root with its italic rows proved to resolve
# to the italic FontFace, the opsz measurement, the 360 px overflow check on a concept page, which passes
# only on a "fits" reading taken after the inner page's fonts settled, and (step 11) the phase-8 narrow
# reading on the fixture site with the Sampler font wired in, which must take the fonts-stage reading
# on both pages and must REPORT the index page's overflow (the frontispiece title that fits in Georgia
# and not in Sampler; second dry run, finding 3): the check is proved to go red on a real page.
#
#   bash scripts/smoke.sh [--full] [--out DIR] [--from STEP]
#
# --from N skips steps before N (for re-running the browser steps after a fix; the skipped steps are
# then assumed to have passed in an earlier run, and the log says so). Exit status is non-zero on the
# first failing step; every step prints what it ran. Nothing here deletes files outside OUT.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
FULL=0
FROM=1
OUT="$ROOT/out/smoke"
while [ $# -gt 0 ]; do
  case "$1" in
    --full) FULL=1 ;;
    --out) OUT="$2"; shift ;;
    --from) FROM="$2"; shift ;;
    *) echo "usage: bash scripts/smoke.sh [--full] [--out DIR] [--from STEP]" >&2; exit 2 ;;
  esac
  shift
done
# the interpreter: $FD_PY when set (CI sets it; SKILL.md spells the interpreter path in every command instead), else the
# skill's own venv, else whatever python3 is on PATH (second dry run, finding 13: the first version ignored $FD_PY)
if [ -n "${FD_PY:-}" ]; then PY="$FD_PY"; elif [ -x "$ROOT/.venv/bin/python3" ]; then PY="$ROOT/.venv/bin/python3"; else PY="$(command -v python3)"; fi
NEUTRAL="$ROOT/examples/neutral"
FONT_URL=/fonts/Sampler-VF.woff2
mkdir -p "$OUT"
step() { echo; echo "== $*"; }
# runs step N only when it is at or after --from
want() { if [ "$1" -ge "$FROM" ]; then return 0; else echo; echo "== $1. skipped (--from $FROM): assumed passed in an earlier run"; return 1; fi; }

step "tool check"
node --version
"$PY" --version
"$PY" -c 'import fontTools, brotli, pathops, PIL; print("fonttools", fontTools.version, "pillow", PIL.__version__, "skia-pathops", pathops.__version__)'
# with --full the browser steps need Chrome, so the whole toolchain report must pass; without it a missing Chrome is not a failure
if [ "$FULL" = 1 ]; then "$PY" "$HERE/check-env.py"; fi

if want 1; then
  step "1. export every group of the three fixtures (compatibility, folds, hairlines)"
  for ex in neutral bract driftwood; do
    for g in $("$PY" -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))['groups']))" "$ROOT/examples/$ex/font.json"); do
      REQ=(); [ -f "$ROOT/examples/$ex/requirements.json" ] && REQ=(--requirements "$ROOT/examples/$ex/requirements.json")
      # expanded as ${REQ[@]+"${REQ[@]}"}: an empty array is "unbound" to bash 3.2 (macOS /bin/bash) under set -u
      node "$HERE/export.js" --font "$ROOT/examples/$ex/font.json" --group "$g" ${REQ[@]+"${REQ[@]}"} "$OUT/$ex-$g.json"
    done
  done
fi

if want 2; then
  step "2. build the three fixtures with every self-check; statics for the neutral one"
  "$PY" "$HERE/build.py" --font "$NEUTRAL/font.json" --static "$NEUTRAL/out/static"
  # the two precedent configurations carry no requirements.json (their sites' reviewed expectations live
  # in the sites' own test files), so the required-character check is declined explicitly (C6)
  "$PY" "$HERE/build.py" --font "$ROOT/examples/bract/font.json" --no-requirements
  "$PY" "$HERE/build.py" --font "$ROOT/examples/driftwood/font.json" --no-requirements
  # 2b. diff.py: the neutral build against a copy of itself must report no change (a renderer that differs
  # between two loads of one file would make every round's "what changed" noise)
  mkdir -p "$OUT/diff-before" && cp -R "$NEUTRAL/out/." "$OUT/diff-before/"
  "$PY" "$HERE/diff.py" "$OUT/diff0" --font "$NEUTRAL/font.json" --before "$OUT/diff-before" --sizes 16 40
  grep -Eq '^\*\*0 of [0-9]+ renders changed\*\*' "$OUT/diff0/diff.md" || { echo "diff.py reported a change between a font and its copy" >&2; exit 1; }
fi

if want 3; then
  step "3. the neutral build is reproducible (--check with a foreign SOURCE_DATE_EPOCH)"
  SOURCE_DATE_EPOCH=1000000000 "$PY" "$HERE/build.py" --font "$NEUTRAL/font.json" --check
fi

if want 4; then
  step "4. the font suite template on the neutral fixture"
  "$PY" -m pytest "$HERE/tests/test_font.py" -q -p no:cacheprovider --font "$NEUTRAL/font.json" --requirements "$NEUTRAL/requirements.json" --static-dir "$NEUTRAL/out/static"
  # the FontBakery gate (phase 7): every FAIL/ERROR must be in the requirements' accepted_qa_findings. Exit 3 means FontBakery is
  # not installed; that is SKIPPED, NOT PASSED (the gate prints why), not a failure of the skill, so the run goes on and says so.
  step "4b. the FontBakery gate on the neutral fixture (skipped, loudly, when fontbakery is not installed)"
  rc=0
  "$PY" "$HERE/fontbakery-gate.py" --font "$NEUTRAL/font.json" --requirements "$NEUTRAL/requirements.json" || rc=$?
  if [ "$rc" -eq 3 ]; then echo "smoke: the FontBakery gate was SKIPPED, NOT PASSED (install requirements-dev.txt to run it)"; elif [ "$rc" -ne 0 ]; then exit "$rc"; fi
fi

if want 5; then
  step "5. every mutation goes RED and is restored"
  "$PY" "$HERE/tests/mutate.py" --font "$NEUTRAL/font.json" --requirements "$NEUTRAL/requirements.json" --static-dir "$NEUTRAL/out/static"
fi

if want 6; then
  step "6. the three concept rounds build and parse"
  mkdir -p "$OUT/pages"
  for r in round1 round2 round3; do
    node "$HERE/concepts/build-page.js" --template "$r" --concepts "$NEUTRAL/concepts.js" --content "$NEUTRAL/content.json" "$OUT/pages/$r.html"
  done
  # 6b. the genre recipes (references/genres.md) as one round-1 page, with each recipe's limit in its risk line
  node "$HERE/concepts/build-page.js" --template round1 --concepts "$ROOT/templates/concepts.genres.js" --content "$HERE/concepts/content.genres.json" "$OUT/pages/genres.html"
fi

if want 7; then
  step "7. the repo's own tests"
  "$PY" -m pytest "$ROOT/tests" -q -p no:cacheprovider
fi

if [ "$FULL" = 1 ]; then
  if want 8; then
    step "8. the concept rounds executed in Chrome: face switch, font-load assertion, the comparison face visibly in Sampler (dumped DOM)"
    mkdir -p "$OUT/pages/fonts"
    cp "$NEUTRAL/out/Sampler-VF.woff2" "$OUT/pages/fonts/Sampler-VF.woff2"
    for r in round1 round2 round3; do
      # Round 1's lineup shows the comparison face (the built Sampler) on every shot; rounds 2 and 3 show it only
      # with ?face=comparison, so --family (which now requires a VISIBLE element set in the family) goes on the
      # shots that show it. The plain and face=display shots of rounds 2 and 3 still prove the font was served
      # to that shot (--font-url) and the page's own data-fd-font self-test is read from the dumped DOM.
      FAM=(); if [ "$r" = round1 ]; then FAM=(--family Sampler); fi  # expanded as ${FAM[@]+"${FAM[@]}"}: an empty array is "unbound" to bash 3.2 under set -u
      "$PY" "$HERE/shoot.py" "$OUT/shots" --serve "$OUT/pages" --pages "$r.html" --widths 500 1280 --scales 1 --dump-dom ${FAM[@]+"${FAM[@]}"} --font-url "$FONT_URL"
      "$PY" "$HERE/shoot.py" "$OUT/shots-display" --serve "$OUT/pages" --pages "$r.html" --widths 1280 --scales 1 --dump-dom ${FAM[@]+"${FAM[@]}"} --font-url "$FONT_URL" --query face=display
      "$PY" "$HERE/shoot.py" "$OUT/shots-comparison" --serve "$OUT/pages" --pages "$r.html" --widths 1280 --scales 1 --dump-dom --family Sampler --font-url "$FONT_URL" --query face=comparison
    done
    "$PY" - "$HERE" "$OUT/shots" "$OUT/shots-display" "$OUT/shots-comparison" <<'EOF'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from shoot import html_attrs
faces = set()
for d in sorted(p for a in sys.argv[2:] for p in pathlib.Path(a).glob("*.dom.html")):
    a = html_attrs(d.read_text(encoding="utf-8"))
    where = d.parent.name
    face, rendered, err = a.get("data-fd-face"), a.get("data-fd-rendered"), a.get("data-fd-error")
    # data-fd-font is the final verdict for Sampler (the page's own when no --family was given, the sentinel's when it
    # was; both mean the built Sampler loaded); data-fd-page-font is the sentinel's snapshot of the page's own value,
    # which can predate the page's probe ("none") but must never say "missing"
    font, snapshot = a.get("data-fd-font"), a.get("data-fd-page-font")
    assert face and rendered and int(rendered) > 0 and font == "loaded" and snapshot != "missing" and err is None, (d, face, rendered, font, snapshot, err)
    if where == "shots-comparison":
        assert int(a.get("data-fd-probe-count", 0)) > 0 and a.get("data-fd-probe-bad") == "0" and a.get("data-fd-missing-chars") == "", \
            (d, "the comparison face is not visibly set in Sampler", {k: v for k, v in a.items() if k.startswith("data-fd-probe") or k.endswith("chars")})
    faces.add((where, face))
    print(f"{where}/{d.name}: face={face} rendered={rendered} font={font} probe={a.get('data-fd-probe-count')} bad={a.get('data-fd-probe-bad')}")
assert {f for where, f in faces if where == "shots-display"} == {"display"}, faces
# round 1's lineup has no face named comparison (it shows every concept and the comparison face at once, so it reports
# "all"); rounds 2 and 3 switch to it. The probe counts above are what prove the comparison face was visibly set in Sampler.
assert {f for where, f in faces if where == "shots-comparison"} == {"comparison", "all"}, faces
assert len({f for _, f in faces}) >= 2, f"the face switch did not change the face: {faces}"
print("face switch observed:", sorted(faces))
EOF
    # 8b. the genres page executes in Chrome and every recipe renders: per recipe, its <section id="concept-<id>"> in the dumped
    #     DOM holds drawn paths (>= 10, each a real outline, none with NaN or Infinity); data-fd-rendered alone only sums glyphs
    #     over the whole page. (its comparison face is Georgia, so no --family)
    "$PY" "$HERE/shoot.py" "$OUT/shots-genres" --serve "$OUT/pages" --pages genres.html --widths 500 1280 --scales 1 --dump-dom
    "$PY" - "$HERE" "$OUT/shots-genres" "$HERE/concepts/content.genres.json" <<'EOF'
import json, pathlib, re, sys
sys.path.insert(0, sys.argv[1])
from shoot import html_attrs
ids = sorted(json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))["concepts"])
assert len(ids) >= 10, ids
doms = sorted(pathlib.Path(sys.argv[2]).glob("*.dom.html"))
assert len(doms) == 2, f"expected the genres page at two widths, found {[d.name for d in doms]}"
for d in doms:
    html = d.read_text(encoding="utf-8")
    a = html_attrs(html)
    rendered, err, font = a.get("data-fd-rendered"), a.get("data-fd-error"), a.get("data-fd-font")
    assert rendered and int(rendered) > 0 and err is None and font == "loaded", (d.name, rendered, font, err)
    sections = {}
    for chunk in re.split(r'(?=<section class="part concept)', html)[1:]:
        m = re.search(r'id="concept-([a-z-]+)"', chunk)
        if m:
            sections[m.group(1)] = chunk
    bad = []
    for i in ids:
        paths = re.findall(r'<path [^>]*?\bd="([^"]*)"', sections.get(i, ""))
        if len(paths) < 10 or min(map(len, paths)) < 500 or any(re.search(r"NaN|Infinity", q) for q in paths):
            bad.append(f"{i}: {len(paths)} paths")
    assert not bad, f"{d.name}: recipes that did not draw: {bad}"
    print(f"shots-genres/{d.name}: rendered={rendered} font={font} recipes drawn={len(ids)}")
EOF
  fi

  if want 9; then
    step "9. the specimen (italic rows must resolve to the italic FontFace) and the opsz measurement on the neutral font"
    mkdir -p "$OUT/review/fonts"
    cp "$NEUTRAL/out/Sampler-VF.woff2" "$NEUTRAL/out/Sampler-Italic-VF.woff2" "$OUT/review/fonts/"
    "$PY" "$HERE/specimen.py" --font "$NEUTRAL/font.json" --requirements "$NEUTRAL/requirements.json" --group roman --font-url "$FONT_URL" --italic-url /fonts/Sampler-Italic-VF.woff2 "$OUT/review/specimen.html"
    grep -q 'class="f fi" data-fd-probe="italic"' "$OUT/review/specimen.html" || { echo "specimen.py emitted no italic probe row although --italic-url was given" >&2; exit 1; }
    for kind in lower upper figures punct; do
      grep -q "data-fd-spacing=\"$kind\"" "$OUT/review/specimen.html" || { echo "specimen.py wrote no spacing control row of kind $kind" >&2; exit 1; }
    done
    grep -q 'data-fd-legibility="true"' "$OUT/review/specimen.html" || { echo "specimen.py wrote no legibility row" >&2; exit 1; }
    grep -q 'data-fd-junctions="true"' "$OUT/review/specimen.html" || { echo "specimen.py wrote no junction row" >&2; exit 1; }
    "$PY" "$HERE/shoot.py" "$OUT/shots-specimen" --serve "$OUT/review" --pages specimen.html --widths 500 1280 --scales 1 2 --dump-dom --family Sampler --font-url "$FONT_URL"
    "$PY" "$HERE/shoot.py" "$OUT/shots-specimen" --serve "$OUT/review" --pages specimen.html --widths 1280 --scales 1 --root 150 --dump-dom --family Sampler --font-url "$FONT_URL"
    "$PY" - "$HERE" "$OUT/shots-specimen" <<'EOF'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from shoot import DEFAULT_HEIGHT, html_attrs
doms = sorted(pathlib.Path(sys.argv[2]).glob("*.dom.html"))
assert doms, "no dumped DOM for the specimen"
for d in doms:
    a = html_attrs(d.read_text(encoding="utf-8"))
    print(f"{d.name}: probe-count={a.get('data-fd-probe-count')} bad={a.get('data-fd-probe-bad')} italic={a.get('data-fd-probe-italic')} missing={a.get('data-fd-missing-chars')!r}")
    assert a.get("data-fd-probe-italic") == "loaded", f"{d.name}: the italic rows did not resolve to a loaded italic FontFace: data-fd-probe-italic={a.get('data-fd-probe-italic')!r}"
    assert int(a.get("data-fd-probe-count", 0)) > 0 and a.get("data-fd-probe-bad") == "0" and a.get("data-fd-missing-chars") == "", (d.name, a)
    # the proof rows (spacing strings, legibility) must lie inside the captured height, or the review PNG does not contain them
    bottom = int(a.get("data-fd-proof-bottom", 0))
    assert a.get("data-fd-proof-count") == "6" and 0 < bottom <= DEFAULT_HEIGHT, f"{d.name}: proof rows end at {bottom} px of a {DEFAULT_HEIGHT} px capture ({a.get('data-fd-proof-count')} rows)"
EOF
    "$PY" "$HERE/opsz.py" "$OUT/opsz" --serve "$OUT/review" --font-url "$FONT_URL" --family Sampler --axis 24 72 --title "The Quiet Harbour at Dawn 48" --px 24 48 72
  fi

  if want 10; then
    step "10. the 360 px overflow check on a concept page (narrow.html inside a 500 px shot): fits, read after the fonts settled"
    "$PY" "$HERE/shoot.py" "$OUT/shots-narrow" --serve "$OUT/pages" --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/round1.html --query width=360
    "$PY" - "$HERE" "$OUT/shots-narrow" <<'EOF'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from shoot import narrow_verdict
doms = sorted(pathlib.Path(sys.argv[2]).glob("*.dom.html"))
assert doms, "no dumped DOM from narrow.html"
for d in doms:
    overflow, stage = narrow_verdict(d.read_text(encoding="utf-8"))
    print(f"{d.name}: data-fd-overflow={overflow!r} data-fd-narrow-stage={stage!r}")
    # only the reading taken after the inner fonts settled counts; "true" is an overflow, "error" or a
    # missing attribute means narrow.html could not measure, and a "load" stage is a pre-font reading
    assert (overflow, stage) == ("false", "fonts"), f"{d.name}: expected data-fd-overflow='false' at data-fd-narrow-stage='fonts', got overflow={overflow!r} stage={stage!r}"
EOF
  fi

  if want 11; then
    step "11. the phase-8 narrow reading on the fixture site with Sampler wired in: the fonts-stage reading on every page, and the index's overflow reported"
    # The fixture site (tests/fixtures/site-sample) fits at 360 px in Georgia and overflows in Sampler: its
    # frontispiece title is NBSP-joined and 48 px at the clamp minimum. Phase 8 repeats the phase-1 narrow
    # reading with the wired font for exactly this case, so this step proves the reading sees it (index
    # overflow=true) and passes a page that fits (essay overflow=false), both at stage "fonts".
    SITE="$OUT/site-narrow"
    mkdir -p "$SITE/fonts/sampler"
    cp -R "$ROOT/tests/fixtures/site-sample/." "$SITE/"
    cp "$NEUTRAL/out/Sampler-VF.woff2" "$SITE/fonts/sampler/Sampler-VF.woff2"
    cat >> "$SITE/css/site.css" <<'CSS'
@font-face { font-family: 'Sampler'; src: url('/fonts/sampler/Sampler-VF.woff2') format('woff2'); font-weight: 400 700; font-style: normal; font-display: swap; }
h1, h2, h3, .plate-title, .frontis-title, .wordmark { font-family: 'Sampler', Georgia, serif; font-optical-sizing: auto; }
CSS
    for page in index essay; do
      "$PY" "$HERE/shoot.py" "$OUT/shots-narrow-site" --serve "$SITE" --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/$page.html --query width=360
    done
    "$PY" - "$HERE" "$OUT/shots-narrow-site" <<'EOF'
import pathlib, sys
sys.path.insert(0, sys.argv[1])
from shoot import html_attrs, narrow_verdict
expected = {"index": "true", "essay": "false"}  # the index overflows in Sampler (measured 384 px against 360), the essay fits
seen = {}
for d in sorted(pathlib.Path(sys.argv[2]).glob("*.dom.html")):
    a = html_attrs(d.read_text(encoding="utf-8"))
    overflow, stage = narrow_verdict(d.read_text(encoding="utf-8"))
    page = a.get("data-fd-narrow-url", "").strip("/").removesuffix(".html")
    print(f"{d.name}: url={a.get('data-fd-narrow-url')} scrollWidth={a.get('data-fd-scroll-width')} clientWidth={a.get('data-fd-client-width')} overflow={overflow!r} stage={stage!r}")
    assert stage == "fonts", f"{d.name}: the reading was not taken after the fonts settled (stage={stage!r}); a load-stage reading does not count"
    seen[page] = overflow
assert seen == expected, f"narrow readings {seen}, expected {expected}: the phase-8 check must report the index overflow and pass the essay"
print("the phase-8 narrow reading reports the index overflow in Sampler and passes the essay")
EOF
  fi
fi

echo; echo "smoke: every step from $FROM passed. Output in $OUT"
