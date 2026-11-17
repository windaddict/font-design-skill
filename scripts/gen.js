"use strict";
/* gen.js: a parametric generator for a display typeface.
 *
 * WHAT IT'S FOR: the one source of every outline in a face built with this skill. Each letter is a
 * centre-line skeleton (G below; GI for the italic forms that differ in structure, not only slant);
 * strokePolys() strokes it with a broad-nib width model and adds serifs, beaks and teardrop
 * terminals, so one parameter set (a "concept", kept in the project's concepts.js) makes a whole
 * cut, and a weight is the same cut with W multiplied. export.js runs this for every master of a
 * group and build.py turns the result into one variable font per group.
 *
 * ORIGIN: John Knox's Driftwood generator (movingavg.com, driftwood-gen.js at commit 67a4e5b,
 * 2026-11-14) as forked and fixed for Bract (hopsafari.com, tools/bract/gen.js at commit 90a085c,
 * 2026-11-15), generalised here. Copyright 2026 John Knox. MIT licence (see LICENSE). Changes that
 * matter, in order of importance:
 *   1. Pinned sampling. Driftwood sampled each fitted skeleton at ceil(length/3) points and dropped
 *      points closer than 0.5 units, so every weight had its own point count and the masters could
 *      not interpolate. sampleCounts() fixes the count per segment from the UNFITTED skeleton, which
 *      is the same for every master, and the dedupe is gone.
 *   2. Branch-outcome recording. strokePolys() writes the outcome of every geometry-dependent branch
 *      (curved, taper, teardrop side, beak, corner/joint, partner identity) into g.sig, and export.js
 *      refuses masters whose outcomes differ.
 *   3. Edge runs. Every polygon carries the index ranges that are one continuous edge, so decimation
 *      can keep each run's endpoints and the fold guard can walk each edge.
 *   4. Fold pinning. Where a bend is tighter than half the stroke width the inside offset edge folds
 *      into a loop that the nonzero fill paints as a lump; such points are pinned, count unchanged.
 *   5. Minimum interior stroke width per stroke (g.minw), measured beyond the taper and teardrop reach.
 *   6. Concepts live outside this file (loadConcepts / the caller); dropAmt sets the teardrop size and
 *      params() refuses flareAmt beside tear:true, because the flare swell never applies then.
 *   7. The italic is restored from Driftwood as an opt-in third argument to params(): GI skeletons,
 *      the shear, the narrower set, shorter serifs, the sidebearing band and the J rule. Roman and
 *      italic are structurally different skeletons, so they are built as separate font files.
 */
/* ---------- Skeletons: centre lines in font units (1000/em, baseline 0, y up) ----------
   Each stroke: d = path (M/L/C absolute), a/b = start/end type.
   s = stem end (serif or cut), t = free terminal, '' = join. */
var K = 0.5523;
function ring(cx, cy, rx, ry) {
  return { d: "M " + cx + " " + (cy + ry) +
    " C " + (cx + rx * K) + " " + (cy + ry) + " " + (cx + rx) + " " + (cy + ry * K) + " " + (cx + rx) + " " + cy +
    " C " + (cx + rx) + " " + (cy - ry * K) + " " + (cx + rx * K) + " " + (cy - ry) + " " + cx + " " + (cy - ry) +
    " C " + (cx - rx * K) + " " + (cy - ry) + " " + (cx - rx) + " " + (cy - ry * K) + " " + (cx - rx) + " " + cy +
    " C " + (cx - rx) + " " + (cy + ry * K) + " " + (cx - rx * K) + " " + (cy + ry) + " " + cx + " " + (cy + ry),
    closed: true, r: [cx, cy, rx, ry] };
}
function S(d, a, b) { return { d: d, a: a || "", b: b || "" }; }
function D(x, y) { return { dot: [x, y] }; }

var G = {
  a: [S("M 110 420 C 140 490 210 510 270 510 C 380 510 440 460 440 360 L 440 0", "t", "s"),
      // the bowl joins the stem at 290, not 270, so the counter stays open in the Bold at 17.6px (round 1 review)
      S("M 440 290 C 350 300 90 280 90 140 C 90 40 150 -10 230 -10 C 320 -10 400 40 440 110")],
  b: [S("M 90 740 L 90 0", "s", "j"),
      S("M 90 380 C 150 470 220 510 300 510 C 430 510 510 400 510 250 C 510 100 430 -10 300 -10 C 220 -10 150 30 90 110")],
  c: [S("M 470 400 C 430 470 360 510 290 510 C 160 510 80 400 80 250 C 80 100 160 -10 290 -10 C 370 -10 440 30 480 110", "t", "t")],
  d: [S("M 470 740 L 470 0", "s", "s"),
      S("M 470 380 C 410 470 340 510 270 510 C 140 510 70 400 70 250 C 70 100 140 -10 270 -10 C 340 -10 410 30 470 110")],
  e: [S("M 90 260 L 480 260"),
      S("M 480 260 C 490 400 410 510 290 510 C 160 510 80 400 80 250 C 80 100 170 -10 300 -10 C 380 -10 440 30 480 100", "", "t")],
  f: [S("M 390 700 C 360 730 330 740 290 740 C 210 740 170 690 170 600 L 170 0", "t", "s"),
      S("M 60 490 L 340 490")],
  g: [S("M 460 500 L 460 20 C 460 -160 380 -230 260 -230 C 180 -230 120 -200 90 -150", "s", "t"),
      S("M 460 380 C 400 470 340 510 270 510 C 140 510 75 410 75 260 C 75 120 140 20 270 20 C 340 20 410 60 460 140")],
  h: [S("M 90 740 L 90 0", "s", "s"),
      S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s")],
  i: [S("M 110 500 L 110 0", "s", "s"), D(110, 680)],
  j: [S("M 130 500 L 130 -60 C 130 -180 80 -230 0 -230", "s", "t"), D(130, 680)],
  k: [S("M 90 740 L 90 0", "s", "s"), S("M 430 500 L 90 180", "s", ""), S("M 250 331 L 460 0", "j", "s")],
  l: [S("M 110 740 L 110 0", "s", "s")],
  m: [S("M 90 500 L 90 0", "s", "s"),
      S("M 90 390 C 135 470 190 510 260 510 C 360 510 405 450 405 350 L 405 0", "", "s"),
      S("M 405 390 C 450 470 505 510 575 510 C 675 510 720 450 720 350 L 720 0", "", "s")],
  n: [S("M 90 500 L 90 0", "s", "s"),
      S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s")],
  o: [ring(290, 250, 210, 260)],
  p: [S("M 90 500 L 90 -230", "s", "s"),
      S("M 90 380 C 150 470 220 510 300 510 C 430 510 510 400 510 250 C 510 100 430 -10 300 -10 C 220 -10 150 30 90 110")],
  q: [S("M 470 500 L 470 -230", "j", "s"),
      S("M 470 380 C 410 470 340 510 270 510 C 140 510 70 400 70 250 C 70 100 140 -10 270 -10 C 340 -10 410 30 470 110")],
  r: [S("M 90 500 L 90 0", "s", "s"),
      S("M 90 380 C 140 470 210 510 290 510 C 345 510 385 495 405 455", "", "t")],
  s: [S("M 410 430 C 380 480 330 510 260 510 C 170 510 110 460 110 385 C 110 230 430 290 430 130 C 430 40 360 -10 260 -10 C 170 -10 100 30 70 90", "t", "t")],
  // the t's stem starts with a tapered exit ("x"), not a head serif: above the crossbar the stem is
  // too short for a wedge, which read as a flag in the Bold (round 1 review)
  t: [S("M 170 640 L 170 110 C 170 30 210 -10 280 -10 C 320 -10 350 0 380 20", "x", "t"), S("M 50 490 L 350 490")],
  u: [S("M 90 500 L 90 170 C 90 60 150 -10 260 -10 C 340 -10 410 40 460 120", "s", ""), S("M 460 500 L 460 0", "s", "s")],
  v: [S("M 40 500 L 250 0", "s", ""), S("M 460 500 L 250 0", "s", "")],
  w: [S("M 30 500 L 200 0", "s", ""), S("M 200 0 L 360 440"), S("M 360 440 L 520 0"), S("M 690 500 L 520 0", "s", "")],
  x: [S("M 50 500 L 450 0", "s", "s"), S("M 450 500 L 50 0", "s", "s")],
  y: [S("M 40 500 L 260 0", "s", ""), S("M 470 500 L 220 -110 C 190 -190 150 -230 80 -230", "s", "t")],
  z: [S("M 70 500 L 430 500", "t", ""), S("M 430 500 L 70 0"), S("M 70 0 L 440 0", "", "t")],

  A: [S("M 40 0 L 330 700", "s", ""), S("M 330 700 L 620 0", "", "s"), S("M 150 240 L 510 240")],
  B: [S("M 100 700 L 100 0", "s", "s"),
      S("M 100 700 L 330 700 C 440 700 500 640 500 540 C 500 440 430 380 330 380 L 100 380"),
      S("M 100 380 L 350 380 C 480 380 540 310 540 195 C 540 70 470 0 350 0 L 100 0")],
  C: [S("M 600 560 C 550 650 470 710 370 710 C 200 710 80 560 80 350 C 80 140 200 -10 370 -10 C 480 -10 560 50 610 140", "t", "t")],
  D: [S("M 100 700 L 100 0", "s", "s"),
      S("M 100 700 L 300 700 C 500 700 600 550 600 350 C 600 150 500 0 300 0 L 100 0")],
  E: [S("M 100 700 L 100 0"), S("M 100 700 L 480 700", "", "t"), S("M 100 370 L 420 370", "", "t"), S("M 100 0 L 500 0", "", "t")],
  F: [S("M 100 700 L 100 0", "", "s"), S("M 100 700 L 470 700", "", "t"), S("M 100 370 L 410 370", "", "t")],
  G: [S("M 610 570 C 560 655 480 710 380 710 C 200 710 80 560 80 350 C 80 140 200 -10 370 -10 C 470 -10 560 20 610 70 L 610 330", "t", ""),
      S("M 430 330 L 610 330", "j", "")],
  H: [S("M 100 700 L 100 0", "s", "s"), S("M 580 700 L 580 0", "s", "s"), S("M 100 360 L 580 360")],
  I: [S("M 120 700 L 120 0", "s", "s")],
  J: [S("M 300 700 L 300 140 C 300 30 240 -10 160 -10 C 100 -10 60 20 30 60", "s", "t")],
  K: [S("M 100 700 L 100 0", "s", "s"), S("M 560 700 L 100 250", "s", ""), S("M 270 420 L 590 0", "j", "s")],
  L: [S("M 100 700 L 100 0", "s", ""), S("M 100 0 L 500 0", "", "t")],
  M: [S("M 90 0 L 110 700", "s", ""), S("M 110 700 L 390 0"), S("M 390 0 L 670 700"), S("M 670 700 L 690 0", "", "s")],
  N: [S("M 100 0 L 100 700", "s", ""), S("M 100 700 L 580 0"), S("M 580 0 L 580 700", "", "s")],
  O: [ring(380, 350, 300, 360)],
  P: [S("M 100 700 L 100 0", "s", "s"),
      S("M 100 700 L 330 700 C 470 700 540 630 540 520 C 540 410 470 340 330 340 L 100 340")],
  Q: [ring(380, 350, 300, 360), S("M 360 40 C 430 -50 530 -110 670 -130", "", "t")],
  R: [S("M 100 700 L 100 0", "s", "s"),
      S("M 100 700 L 330 700 C 470 700 540 630 540 520 C 540 410 470 340 330 340 L 100 340"),
      S("M 320 340 L 570 0", "", "s")],
  S: [S("M 520 600 C 480 670 410 710 320 710 C 200 710 120 640 120 530 C 120 330 540 400 540 180 C 540 60 450 -10 320 -10 C 210 -10 120 40 80 120", "t", "t")],
  T: [S("M 300 700 L 300 0", "j", "s"), S("M 40 700 L 560 700", "t", "t")],
  U: [S("M 100 700 L 100 240 C 100 80 200 -10 340 -10 C 480 -10 580 80 580 240 L 580 700", "s", "s")],
  V: [S("M 30 700 L 320 0", "s", ""), S("M 610 700 L 320 0", "s", "")],
  W: [S("M 20 700 L 220 0", "s", ""), S("M 220 0 L 450 620"), S("M 450 620 L 680 0"), S("M 880 700 L 680 0", "s", "")],
  X: [S("M 50 700 L 570 0", "s", "s"), S("M 570 700 L 50 0", "s", "s")],
  Y: [S("M 40 700 L 325 320", "s", "j"), S("M 580 700 L 295 320", "s", "j"), S("M 310 370 L 310 0", "j", "s")],
  Z: [S("M 70 700 L 540 700", "t", ""), S("M 540 700 L 70 0"), S("M 70 0 L 550 0", "", "t")],

  "0": [ring(280, 350, 200, 360)],
  "1": [S("M 150 580 L 290 700", "t", ""), S("M 290 700 L 290 0", "", "s")],
  "2": [S("M 90 560 C 120 650 190 710 280 710 C 390 710 460 640 460 540 C 460 380 280 280 90 0", "t", ""), S("M 90 0 L 480 0", "", "t")],
  "3": [S("M 100 600 C 140 670 200 710 280 710 C 390 710 450 640 450 550 C 450 450 380 400 270 400", "t", ""),
        S("M 270 400 C 400 400 480 330 480 210 C 480 80 390 -10 270 -10 C 180 -10 110 30 70 110", "", "t")],
  "4": [S("M 400 0 L 400 700", "s", ""), S("M 400 700 L 60 210"), S("M 60 210 L 500 210", "", "t")],
  "5": [S("M 460 700 L 150 700", "t", ""), S("M 150 700 L 120 380"),
        S("M 120 380 C 170 420 230 440 290 440 C 410 440 480 360 480 220 C 480 80 400 -10 270 -10 C 180 -10 110 30 70 110", "", "t")],
  "6": [S("M 420 640 C 385 690 340 710 290 710 C 160 710 85 570 85 260", "t", ""), ring(285, 215, 200, 225)],
  "7": [S("M 60 700 L 480 700", "t", ""), S("M 480 700 L 200 0", "", "s")],
  "8": [ring(280, 540, 170, 170), ring(280, 190, 200, 200)],
  "9": [ring(275, 485, 200, 225), S("M 475 450 C 475 140 400 -10 270 -10 C 230 -10 190 5 150 40", "", "t")],

  ".": [D(80, 45)],
  ",": [D(80, 45), S("M 102 40 C 102 -30 85 -80 50 -120", "", "t")],
  "'": [D(90, 655), S("M 112 650 C 112 585 95 540 60 505", "", "t")],
  ":": [D(90, 45), D(90, 420)],
  "!": [S("M 120 700 L 120 200", "s", "t"), D(120, 45)],
  "?": [S("M 90 600 C 120 680 190 720 270 720 C 370 720 440 660 440 570 C 440 470 360 430 300 380 C 270 350 260 320 260 230", "t", "t"), D(260, 45)],
  "-": [S("M 50 260 L 290 260")],
  "–": [S("M 40 260 L 460 260")],
  "—": [S("M 40 260 L 900 260")],
  ";": [D(90, 420), D(90, 45), S("M 112 40 C 112 -30 95 -80 60 -120", "", "t")],
  "…": [D(90, 45), D(310, 45), D(530, 45)],
  "[": [S("M 270 760 L 140 760", "j", ""), S("M 140 760 L 140 -170"), S("M 140 -170 L 270 -170", "", "j")],
  "]": [S("M 50 760 L 180 760", "j", ""), S("M 180 760 L 180 -170"), S("M 180 -170 L 50 -170", "", "j")],
  "/": [S("M 400 760 L 60 -120", "j", "j")],
  "(": [S("M 300 770 C 170 650 120 490 120 300 C 120 110 170 -50 300 -170", "j", "j")],
  ")": [S("M 60 770 C 190 650 240 490 240 300 C 240 110 190 -50 60 -170", "j", "j")],
  "%": [ring(160, 540, 100, 170), ring(560, 160, 100, 170), S("M 570 700 L 150 0", "j", "j")],
  "$": [S("M 480 590 C 445 655 385 690 300 690 C 195 690 125 625 125 530 C 125 340 500 400 500 185 C 500 70 420 10 300 10 C 205 10 125 55 90 125", "t", "t"),
        S("M 300 790 L 300 -90", "j", "j")],
  // # + * are new for Bract: "The Dessert Project #4", "Google+ SXSW Photowalk" and a literal
  // asterisk appear in real titles. Square-cut ends ("j"), like the slash and brackets.
  "#": [S("M 250 680 L 160 20", "j", "j"), S("M 490 680 L 400 20", "j", "j"), S("M 70 460 L 560 460", "j", "j"), S("M 50 240 L 540 240", "j", "j")],
  "+": [S("M 270 480 L 270 40", "j", "j"), S("M 50 260 L 490 260", "j", "j")],
  "*": [S("M 250 720 L 250 420", "t", "t"), S("M 120 645 L 380 495", "t", "t"), S("M 120 495 L 380 645", "t", "t")],
  "&": [S("M 640 0 L 270 420 C 200 500 160 545 160 600 C 160 670 225 710 305 710 C 390 710 445 665 445 600 C 445 520 370 480 255 425 C 150 375 80 315 80 205 C 80 80 170 -10 300 -10 C 430 -10 520 80 570 210 L 590 290", "s", "t")],

  fi: [S("M 170 0 L 170 600 C 170 690 220 740 300 740 C 380 740 430 700 450 640", "s", "t"), S("M 60 490 L 340 490"), S("M 450 500 L 450 0", "s", "s")],
  fl: [S("M 170 0 L 170 600 C 170 690 220 740 300 740 L 450 740", "s", ""), S("M 60 490 L 340 490"), S("M 450 740 L 450 0", "", "s")],
  ff: [S("M 150 0 L 150 600 C 150 690 190 740 260 740 C 320 740 370 715 395 680", "s", "j"),
       S("M 400 0 L 400 600 C 400 690 440 740 510 740 C 550 740 580 730 610 700", "s", "t"), S("M 50 490 L 590 490")]
};
var LIGS = ["fi", "fl", "ff"];
/* Italic: its own lowercase where an italic differs in structure, not just slant. Single-storey a,
   f with a descender, and stems that leave the baseline in a short exit stroke ("x" end) instead of a
   foot serif. Everything not listed here is the roman skeleton, slanted by xf(). A concept used for an
   italic must map the "x" end type (ends.x, normally "exit"). */
function exitStem(x, top, a) { return S("M " + x + " " + top + " L " + x + " 110 C " + x + " 35 " + (x + 30) + " -10 " + (x + 85) + " -10", a, "x"); }
var GI = {
  a: [exitStem(440, 500, "j"),
      S("M 440 380 C 390 470 330 510 260 510 C 140 510 70 400 70 250 C 70 100 140 -10 250 -10 C 330 -10 400 40 440 120")],
  d: [exitStem(470, 740, "s"),
      S("M 470 380 C 410 470 340 510 270 510 C 140 510 70 400 70 250 C 70 100 140 -10 270 -10 C 340 -10 410 30 470 110")],
  f: [S("M 400 700 C 370 730 340 740 300 740 C 220 740 180 690 180 600 L 180 -110 C 180 -190 140 -230 70 -230", "t", "t"),
      S("M 60 490 L 350 490")],
  h: [S("M 90 740 L 90 0", "s", "j"),
      S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 110 C 460 35 490 -10 545 -10", "", "x")],
  i: [exitStem(110, 500, "s"), D(110, 680)],
  l: [exitStem(110, 740, "s")],
  m: [S("M 90 500 L 90 0", "s", "j"),
      S("M 90 390 C 135 470 190 510 260 510 C 360 510 405 450 405 350 L 405 0", "", "j"),
      S("M 405 390 C 450 470 505 510 575 510 C 675 510 720 450 720 350 L 720 110 C 720 35 750 -10 805 -10", "", "x")],
  n: [S("M 90 500 L 90 0", "s", "j"),
      S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 110 C 460 35 490 -10 545 -10", "", "x")],
  r: [S("M 90 500 L 90 0", "s", "j"),
      S("M 90 380 C 140 470 210 510 290 510 C 330 510 360 500 380 480", "", "t")],
  v: [S("M 20 500 L 220 0", "s", ""), S("M 220 0 C 320 140 430 320 430 430 C 430 470 415 495 390 505", "", "t")],
  w: [S("M 10 500 L 170 0", "s", ""), S("M 170 0 L 340 400"), S("M 340 400 L 470 0"),
      S("M 470 0 C 560 140 650 320 650 430 C 650 470 635 495 610 505", "", "t")],
  y: [S("M 20 500 L 265 -5", "s", "j"),
      S("M 450 500 C 420 340 350 130 250 -60 C 200 -160 150 -230 60 -230", "s", "t")],
  k: [S("M 90 740 L 90 0", "s", "j"),
      S("M 90 190 C 190 330 320 510 410 460 C 470 425 440 320 320 300 C 280 293 240 295 205 305", "", ""),
      S("M 290 300 C 350 210 370 70 410 25 C 430 0 455 -10 500 -10", "j", "x")],
  e: [S("M 95 225 C 260 250 470 320 470 420 C 470 480 410 510 320 510 C 180 510 80 380 80 220 C 80 80 160 -10 290 -10 C 370 -10 430 30 470 100", "", "t")],
  u: [S("M 90 500 L 90 170 C 90 60 150 -10 260 -10 C 340 -10 410 40 460 120", "s", ""), exitStem(460, 500, "s")],
  fi: [S("M 180 -110 L 180 600 C 180 690 230 740 310 740 C 390 740 440 700 460 640", "", "t"), S("M 60 490 L 350 490"), exitStem(460, 500, "s")],
  fl: [S("M 180 -110 L 180 600 C 180 690 230 740 310 740 L 460 740", "", ""), S("M 60 490 L 350 490"), exitStem(460, 740, "")],
  ff: [S("M 160 -110 L 160 600 C 160 690 200 740 270 740 C 330 740 380 715 405 680", "", "j"),
       S("M 410 -110 L 410 600 C 410 690 450 740 520 740 C 560 740 590 730 620 700", "", "t"), S("M 50 490 L 600 490")]
};
/* Italic capitals. Book italics change the capitals less than the lowercase: round and straight
   letters are the slanted roman. The ones that change are those with diagonals or a free foot: the
   diagonals curve the way the pen swings, and a right-hand foot becomes an exit stroke like the n's. */
var GI_CAPS = {
  A: [S("M 30 0 C 130 210 240 460 340 700", "s", ""), S("M 340 700 L 560 100 C 580 35 605 -10 660 -10", "", "x"), S("M 165 250 L 500 250")],
  T: [S("M 300 672 L 300 0", "j", "s"), S("M 40 656 C 130 677 220 675 300 672 C 390 669 470 671 565 686", "u", "u")],
  W: [S("M 10 700 L 190 0", "s", ""), S("M 190 0 L 420 620"), S("M 420 620 L 620 0"),
      S("M 620 0 C 720 160 830 420 830 590 C 830 640 815 680 790 700", "", "t")],
  M: [S("M 40 0 C 70 210 100 460 120 700", "s", ""), S("M 120 700 L 385 0"), S("M 385 0 L 650 700"),
      S("M 650 700 L 650 100 C 650 35 672 -10 735 -10", "", "x")],
  R: [S("M 100 700 L 100 0", "s", "s"),
      S("M 100 700 L 330 700 C 470 700 540 630 540 520 C 540 410 470 340 330 340 L 100 340"),
      S("M 310 340 C 390 260 450 130 490 50 C 510 10 535 -10 590 -10", "", "x")],
  K: [S("M 100 700 L 100 0", "s", "s"), S("M 560 700 L 100 250", "s", ""),
      S("M 270 420 C 350 290 420 130 460 55 C 480 15 505 -10 560 -10", "j", "x")],
  V: [S("M 20 700 L 300 0", "s", ""), S("M 300 0 C 420 180 560 440 560 590 C 560 640 545 680 520 700", "", "t")],
  U: [S("M 100 700 L 100 240 C 100 80 200 -10 330 -10 C 450 -10 540 70 570 200", "s", ""),
      S("M 580 700 L 580 100 C 580 35 602 -10 665 -10", "s", "x")],
  N: [S("M 100 0 C 100 250 100 480 100 700", "s", ""), S("M 100 700 L 560 0"),
      S("M 560 0 C 575 230 585 460 600 700", "", "s")],
  Y: [S("M 20 700 L 315 300", "s", "j"), S("M 300 330 C 400 440 510 560 540 630 C 552 660 545 685 525 702", "", "t"),
      S("M 300 360 L 300 0", "j", "s")],
  J: [S("M 300 700 L 300 20 C 300 -130 230 -200 140 -200 C 80 -200 40 -170 20 -130", "s", "t")]
};
Object.keys(GI_CAPS).forEach(function (k) { GI[k] = GI_CAPS[k]; });
// accented letters: the base skeleton plus a mark drawn above the x-height
G["š"] = G.s.concat([S("M 150 700 L 260 610", "j", ""), S("M 260 610 L 370 700", "", "j")]);
G["ā"] = G.a.concat([S("M 130 650 L 420 650", "j", "j")]);
G["é"] = G.e.concat([S("M 250 610 L 350 720", "j", "t")]);
// marks, centred on cx above the x-height
function acute(cx) { return [S("M " + (cx - 40) + " 610 L " + (cx + 60) + " 720", "j", "t")]; }
function grave(cx) { return [S("M " + (cx + 40) + " 610 L " + (cx - 60) + " 720", "j", "t")]; }
function circ(cx) { return [S("M " + (cx - 110) + " 600 L " + cx + " 700", "j", ""), S("M " + cx + " 700 L " + (cx + 110) + " 600", "", "j")]; }
function diaer(cx) { return [D(cx - 95, 650), D(cx + 95, 650)]; }
function tilde(cx) { return [S("M " + (cx - 130) + " 620 C " + (cx - 90) + " 690 " + (cx - 40) + " 690 " + cx + " 655 C " + (cx + 40) + " 620 " + (cx + 90) + " 620 " + (cx + 130) + " 690", "j", "j")]; }
var DOTLESS_I = [S("M 110 500 L 110 0", "s", "s")];
var BASES = { a: 270, e: 280, o: 290, u: 275 };
[["á", acute], ["à", grave], ["â", circ], ["ä", diaer]].forEach(function (m) {
  ["a", "e", "o", "u"].forEach(function (b) {
    var k = { a: "aáàâä", e: "eéèêë", o: "oóòôö", u: "uúùûü" }[b]["áàâä".indexOf(m[0]) + 1];
    if (!G[k]) G[k] = G[b].concat(m[1](BASES[b]));
  });
  G[{ "á": "í", "à": "ì", "â": "î", "ä": "ï" }[m[0]]] = DOTLESS_I.concat(m[1](110));
});
G["ñ"] = G.n.concat(tilde(275));
G["ç"] = G.c.concat([S("M 290 -10 L 290 -70 C 350 -70 380 -100 380 -140 C 380 -190 330 -215 250 -205", "j", "t")]);
G["©"] = [ring(330, 330, 270, 300), S("M 425 425 C 400 465 370 485 333 485 C 265 485 220 420 220 330 C 220 240 265 175 333 175 C 370 175 400 195 428 235", "t", "t")];
G["™"] = [S("M 40 700 L 300 700"), S("M 170 700 L 170 430", "j", "j"),
          S("M 370 430 L 380 700", "j", ""), S("M 380 700 L 490 520"), S("M 490 520 L 600 700"), S("M 600 700 L 610 430", "", "j")];
G["•"] = [D(150, 300)];
function raise(strokes, dy) {
  return strokes.map(function (s) {
    if (s.dot) return D(s.dot[0], s.dot[1] + dy);
    var t = s.d.split(" "), out = [], k = 0;
    for (var i = 0; i < t.length; i++) { if (/^[MLC]$/.test(t[i])) { out.push(t[i]); k = 0; } else { out.push(k % 2 ? String(+t[i] + dy) : t[i]); k++; } }
    return { d: out.join(" "), a: s.a, b: s.b };
  });
}
var CAPS = { A: 330, E: 290, I: 120, O: 380, U: 340, N: 340 };
[["Á", "A", acute], ["À", "A", grave], ["Â", "A", circ], ["Ä", "A", diaer], ["É", "E", acute], ["È", "E", grave], ["Ê", "E", circ], ["Ë", "E", diaer],
 ["Í", "I", acute], ["Ï", "I", diaer], ["Ó", "O", acute], ["Ô", "O", circ], ["Ö", "O", diaer], ["Ú", "U", acute], ["Ü", "U", diaer], ["Ñ", "N", tilde]
].forEach(function (m) { G[m[0]] = G[m[1]].concat(raise(m[2](CAPS[m[1]]), 170)); });
G["Ç"] = G.C.concat([S("M 370 -10 L 370 -70 C 430 -70 460 -100 460 -140 C 460 -190 410 -215 330 -205", "j", "t")]);
// italic accented letters reuse the italic base where there is one
GI["ā"] = GI.a.concat([S("M 130 650 L 420 650", "j", "j")]);
GI["é"] = GI.e.concat([S("M 250 610 L 350 720", "j", "t")]);
"áàâä".split("").forEach(function (k, i) { GI[k] = GI.a.concat([acute, grave, circ, diaer][i](270)); });
"éèêë".split("").forEach(function (k, i) { GI[k] = GI.e.concat([acute, grave, circ, diaer][i](280)); });
"úùûü".split("").forEach(function (k, i) { GI[k] = GI.u.concat([acute, grave, circ, diaer][i](275)); });
GI["ñ"] = GI.n.concat(tilde(275));
"íìîï".split("").forEach(function (k, i) { GI[k] = [exitStem(110, 500, "s")].concat([acute, grave, circ, diaer][i](110)); });
var UPPERISH = /^[A-Z0-9!?&$%\/()\[\]#*©™ÁÀÂÄÉÈÊËÍÏÓÔÖÚÜÑÇ]$/;

/* ---------- Concepts live in the project's concepts.js ----------
   A concept is one parameter set: the pen (W, nib, thin, thinGrow, pow, xs, swell, wob, track), the
   stroke ends (ends: {s, t, u, "", x}, flareLen, flareAmt or dropAmt, taperLen, cut, serifLen, serifH,
   serifGrow, dot, leaf, overshoot, beak, tear, pebble) and the transforms (shear, bend, wonk). The
   full table with ranges and interactions is references/generator.md. Angles are written in degrees
   times DEG. */
var DEG = Math.PI / 180;
var DROP_AMT_DEFAULT = 0.55; // the outer teardrop swell Bract and Driftwood shipped with

/* ---------- Geometry helpers ---------- */
function dist(a, b) { return Math.hypot(b[0] - a[0], b[1] - a[1]); }
/* Points per segment, one entry per L or C: a line gets max(2, ceil(length/3)), a curve
   max(4, ceil(control polygon length/3)). Computed once from the unfitted skeleton and passed to
   samplePath() for every master, so the sampled point count never depends on the weight. */
function sampleCounts(d) {
  var t = d.trim().split(/[\s,]+/), i = 0, cur = null, counts = [];
  while (i < t.length) {
    var c = t[i++];
    if (c === "M") cur = [+t[i++], +t[i++]];
    else if (c === "L") { var p = [+t[i++], +t[i++]]; counts.push(Math.max(2, Math.ceil(dist(cur, p) / 3))); cur = p; }
    else if (c === "C") {
      var p1 = [+t[i++], +t[i++]], p2 = [+t[i++], +t[i++]], p3 = [+t[i++], +t[i++]];
      counts.push(Math.max(4, Math.ceil((dist(cur, p1) + dist(p1, p2) + dist(p2, p3)) / 3))); cur = p3;
    }
  }
  return counts;
}
function samplePath(d, counts) {
  var t = d.trim().split(/[\s,]+/), i = 0, cur = null, pts = [], seg = 0;
  while (i < t.length) {
    var c = t[i++];
    if (c === "M") { cur = [+t[i++], +t[i++]]; pts.push(cur); }
    else if (c === "L") {
      var p = [+t[i++], +t[i++]], n = counts[seg++];
      for (var k = 1; k <= n; k++) pts.push([cur[0] + (p[0] - cur[0]) * k / n, cur[1] + (p[1] - cur[1]) * k / n]);
      cur = p;
    } else if (c === "C") {
      var p1 = [+t[i++], +t[i++]], p2 = [+t[i++], +t[i++]], p3 = [+t[i++], +t[i++]];
      var m = counts[seg++];
      for (var j = 1; j <= m; j++) {
        var u = j / m, v = 1 - u;
        pts.push([v * v * v * cur[0] + 3 * v * v * u * p1[0] + 3 * v * u * u * p2[0] + u * u * u * p3[0],
                  v * v * v * cur[1] + 3 * v * v * u * p1[1] + 3 * v * u * u * p2[1] + u * u * u * p3[1]]);
      }
      cur = p3;
    }
  }
  if (seg !== counts.length) throw new Error("sample counts do not match the path: " + d);
  return pts;
}
/* ---------- The x-height map ----------
   WHAT IT'S FOR: skeletons are drawn with the x-line at 500, and `xh` moves it. The map is piecewise
   linear in y: descenders stay, the body (0..500) scales to 0..xh, the band between the x-line and the
   ascender (500..740) scales to xh..740, and ascenders stay. It applies to every key that is not
   UPPERISH, except the apostrophe (xhMapped). Every geometry-dependent DECISION is taken on the
   skeleton as fitted at xh 500 (glyph() samples it as well, "unmapped"), never on the mapped one, so
   xh cannot flip a branch: mapped coordinates draw, unmapped coordinates decide (see strokePolys). */
function ymap(y, xh) {
  if (y <= 0 || y >= 740) return y;
  if (y <= 500) return y * xh / 500;
  return xh + (y - 500) * (740 - xh) / 240;
}
function xhMapped(key, P) { return P.xh !== 500 && !UPPERISH.test(key) && key !== "'"; }
function xf(ch, P, p) {
  var x = p[0], y = p[1];
  if (P.wonk && P.wonk.indexOf(ch) >= 0) x -= 0.045 * y;
  x *= P.xs * (1 + 0.16 * ((P.W0 ? P.W / P.W0 : 1) - 1)) * (P.italic ? 0.95 : 1);
  if (P.shear) x += P.shear * y;
  if (P.bend && y > 350) x += P.bend * (y - 350) * (y - 350);
  if (P.italic) x += P.italic * y;
  return [x, y];
}
function circle(cx, cy, rx, ry, rot) {
  var pts = [], n = 64, c = Math.cos(rot || 0), s = Math.sin(rot || 0);
  for (var i = 0; i < n; i++) {
    var a = i / n * 2 * Math.PI, x = rx * Math.cos(a), y = ry * Math.sin(a);
    pts.push([cx + x * c - y * s, cy + x * s + y * c]);
  }
  return pts;
}
function quad(out, a, c, b) {
  for (var i = 1; i <= 6; i++) {
    var u = i / 6, v = 1 - u;
    out.push([v * v * a[0] + 2 * v * u * c[0] + u * u * b[0], v * v * a[1] + 2 * v * u * c[1] + u * u * b[1]]);
  }
}
function area(p) {
  var s = 0;
  for (var i = 0; i < p.length; i++) { var a = p[i], b = p[(i + 1) % p.length]; s += a[0] * b[1] - b[0] * a[1]; }
  return s / 2;
}

/* Curl for Tideline: continue the stroke's own turn as a shrinking spiral. Returns the curl's length, or 0 for a straight end. */
function addCurl(pts, P, dec, info) {
  // dec: the same stroke on the unmapped skeleton (absent when the x-height map is off); the curl is decided on it and drawn on pts
  var n = pts.length;
  if (n < 12) return 0;
  var E = pts[n - 1], A = pts[n - 4], B = pts[Math.max(0, n - 16)], C2 = pts[Math.max(0, n - 13)];
  var T = [E[0] - A[0], E[1] - A[1]], tl = Math.hypot(T[0], T[1]); T = [T[0] / tl, T[1] / tl];
  var T0 = [C2[0] - B[0], C2[1] - B[1]], t0 = Math.hypot(T0[0], T0[1]); T0 = [T0[0] / t0, T0[1] / t0];
  var cross = T0[0] * T[1] - T0[1] * T[0];
  var crossD = cross;
  if (dec) {
    var Ed = dec[n - 1], Ad = dec[n - 4], Bd = dec[Math.max(0, n - 16)], Cd = dec[Math.max(0, n - 13)];
    var Td = [Ed[0] - Ad[0], Ed[1] - Ad[1]], tld = Math.hypot(Td[0], Td[1]); Td = [Td[0] / tld, Td[1] / tld];
    var T0d = [Cd[0] - Bd[0], Cd[1] - Bd[1]], t0d = Math.hypot(T0d[0], T0d[1]); T0d = [T0d[0] / t0d, T0d[1] / t0d];
    crossD = T0d[0] * Td[1] - T0d[1] * Td[0];
  }
  if (Math.abs(crossD) < 0.06) return 0;
  // the handedness of the spiral is decided on the unmapped cross product too (it is recorded: info.sg), the geometry is drawn from the drawn tail
  var sg = crossD > 0 ? 1 : -1, N = sg > 0 ? [-T[1], T[0]] : [T[1], -T[0]];
  var r = P.W * 0.55 + 22, cx = E[0] + N[0] * r, cy = E[1] + N[1] * r;
  var a0 = Math.atan2(E[1] - cy, E[0] - cx), sweep = sg * 1.3 * Math.PI, len = 0, prev = E;
  for (var j = 1; j <= 30; j++) {
    var u = j / 30, a = a0 + sweep * u, rr = r * (1 - 0.42 * u), p = [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
    len += dist(prev, p); prev = p; pts.push(p);
  }
  if (info) info.sg = sg;
  // the unmapped copy gets its own spiral, built from its own tail, so that its tangents are the xh 500 ones
  if (dec) addCurl(dec, P);
  return len;
}
function endMod(mode, d, curlLen, P) {
  if (mode === "exit") { var ex = 0.9 * (P.W0 || P.W); return d < ex ? 1 - 0.5 * Math.pow(1 - d / ex, 1.2) : 1; }
  if (mode === "flare" && !P.tear && d < P.flareLen) { var u = 1 - d / P.flareLen; return 1 + P.flareAmt * u * u; }
  if (mode === "taper" && d < P.taperLen) return 1 - 0.62 * Math.pow(1 - d / P.taperLen, 1.3);
  if (mode === "curl" && curlLen && d < curlLen) return 1 - 0.45 * (1 - d / curlLen);
  return 1;
}
function cutSide(X, T, p, Dv, w) {
  var cr = T[0] * Dv[1] - T[1] * Dv[0];
  if (Math.abs(cr) < 0.25) return X;
  var t = ((p[0] - X[0]) * Dv[1] - (p[1] - X[1]) * Dv[0]) / cr;
  t = Math.max(-w, Math.min(w, t));
  return [X[0] + T[0] * t, X[1] + T[1] * t];
}
/* serifBracket: a serif is drawn between today's bracketed form (b = 1, the 0.1 code, unchanged) and a slab (b = 0), with the same
   number of points, so a bracket can interpolate between masters. mix(a, c, b) is b of the bracketed point a and 1 - b of the slab
   point c. The control of each quad() in the slab sits on its chord, so the six points of a quad lie on a straight segment. */
function mix(a, c, b) { return [c[0] + (a[0] - c[0]) * b, c[1] + (a[1] - c[1]) * b]; }
function mid(a, c) { return [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2]; }
/* the foot (sy +1) and the symmetric head (sy -1): two pushes and four quads, 26 points; a..f are the anchors, c the four controls */
function serifBlend(x, y, w, L, h, sy, b) {
  var A = [[x - w / 2, y + sy * h * 1.7], [x - L, y + sy * h * 0.42], [x - L + h * 0.45, y], [x + L - h * 0.45, y], [x + L, y + sy * h * 0.42], [x + w / 2, y + sy * h * 1.7]];
  var S = [[x - w / 2, y + sy * h], [x - L, y + sy * h], [x - L, y], [x + L, y], [x + L, y + sy * h], [x + w / 2, y + sy * h]];
  var a = A.map(function (q, i) { return mix(q, S[i], b); });
  var C = [[x - w / 2, y + sy * h * 0.55], [x - L - h * 0.1, y], [x + L + h * 0.1, y], [x + w / 2, y + sy * h * 0.55]];
  var chords = [mid(S[0], S[1]), mid(S[1], S[2]), mid(S[3], S[4]), mid(S[4], S[5])];
  var c = C.map(function (q, i) { return mix(q, chords[i], b); }), o = [a[0]];
  quad(o, a[0], c[0], a[1]); quad(o, a[1], c[1], a[2]);
  o.push(a[3]);
  quad(o, a[3], c[2], a[4]); quad(o, a[4], c[3], a[5]);
  return o;
}
function serifPoly(E, T, w, P, symmetric) {
  // serif reach follows the Regular, so the Bold does not grow slab serifs
  var SW = (P.W0 || P.W) * (P.serifGrow ? Math.pow(P.W / (P.W0 || P.W), P.serifGrow) : 1), L = w * 0.5 + SW * P.serifLen * (P.italic && symmetric ? 0.6 : 1), h = SW * P.serifH, x = E[0], y = E[1], o = [];
  var b = P.serifBracket;
  if (b !== 1 && (T[1] < 0 || symmetric)) return serifBlend(x, y, w, L, h, T[1] < 0 ? 1 : -1, b);
  if (b !== 1) { // lowercase head, blended: three pushes and two quads, 15 points
    var A = [[x + w / 2, y - h * 1.8], [x + w / 2, y + h * 0.18], [x - L + h * 0.5, y - h * 0.2], [x - L, y - h * 0.65], [x - w / 2, y - h * 1.9]];
    var S = [[x + w / 2, y - h], [x + w / 2, y], [x - L, y], [x - L, y - h], [x - w / 2, y - h]];
    var a = A.map(function (q, i) { return mix(q, S[i], b); });
    var c1 = mix([x - L - h * 0.05, y - h * 0.3], mid(S[2], S[3]), b), c2 = mix([x - w / 2, y - h * 0.8], mid(S[3], S[4]), b);
    o.push(a[0], a[1], a[2]);
    quad(o, a[2], c1, a[3]); quad(o, a[3], c2, a[4]);
    return o;
  }
  if (T[1] < 0) { // foot
    o.push([x - w / 2, y + h * 1.7]);
    quad(o, [x - w / 2, y + h * 1.7], [x - w / 2, y + h * 0.55], [x - L, y + h * 0.42]);
    quad(o, [x - L, y + h * 0.42], [x - L - h * 0.1, y], [x - L + h * 0.45, y]);
    o.push([x + L - h * 0.45, y]);
    quad(o, [x + L - h * 0.45, y], [x + L + h * 0.1, y], [x + L, y + h * 0.42]);
    quad(o, [x + L, y + h * 0.42], [x + w / 2, y + h * 0.55], [x + w / 2, y + h * 1.7]);
  } else if (symmetric) { // head, both sides
    o.push([x - w / 2, y - h * 1.7]);
    quad(o, [x - w / 2, y - h * 1.7], [x - w / 2, y - h * 0.55], [x - L, y - h * 0.42]);
    quad(o, [x - L, y - h * 0.42], [x - L - h * 0.1, y], [x - L + h * 0.45, y]);
    o.push([x + L - h * 0.45, y]);
    quad(o, [x + L - h * 0.45, y], [x + L + h * 0.1, y], [x + L, y - h * 0.42]);
    quad(o, [x + L, y - h * 0.42], [x + w / 2, y - h * 0.55], [x + w / 2, y - h * 1.7]);
  } else { // lowercase head: one wedge to the left, top sloping down leftward
    o.push([x + w / 2, y - h * 1.8]);
    o.push([x + w / 2, y + h * 0.18]);
    o.push([x - L + h * 0.5, y - h * 0.2]);
    quad(o, [x - L + h * 0.5, y - h * 0.2], [x - L - h * 0.05, y - h * 0.3], [x - L, y - h * 0.65]);
    quad(o, [x - L, y - h * 0.65], [x - w / 2, y - h * 0.8], [x - w / 2, y - h * 1.9]);
  }
  return o;
}

/* Serif for a slanted stroke (V, W, X, Y, v, w, x, y). The stroke has already been
   trimmed level, so Lk and Rk sit on the baseline or cap line. The brackets climb the
   stroke's own edges, and the serif reaches further on the open (obtuse) side than on
   the side the stroke leans into, as in a book face's V. */
function diagSerifPoly(E, T, Lk, Rk, P) {
  // every italic stem is slanted, so all italic serifs come through here; they are 60% length
  var SW = (P.W0 || P.W) * (P.serifGrow ? Math.pow(P.W / (P.W0 || P.W), P.serifGrow) : 1), h = SW * P.serifH, L = SW * P.serifLen * (P.italic ? 0.6 : 1), y = E[1], up = T[1] < 0 ? 1 : -1;
  var a = Lk[0] < Rk[0] ? Lk : Rk, b = Lk[0] < Rk[0] ? Rk : Lk;
  function onEdge(q, hh) { var s = hh / Math.abs(T[1]); return [q[0] - T[0] * s, q[1] - T[1] * s]; }
  var leansRight = -T[0] > 0; // going into the stroke, it heads right
  var extA = L * (leansRight ? 1.15 : 0.6), extB = L * (leansRight ? 0.6 : 1.15);
  var xa = a[0] - extA, xb = b[0] + extB, o = [];
  var bk = P.serifBracket;
  if (bk !== 1) { // blended with a slab: one push, four quads, one push, 26 points, as the bracketed form below
    var DA = [onEdge(a, h * 1.7), [xa, y + up * h * 0.42], [xa + h * 0.45, y], [xb - h * 0.45, y], [xb, y + up * h * 0.42], onEdge(b, h * 1.7)];
    var DS = [onEdge(a, h), [xa, y + up * h], [xa, y], [xb, y], [xb, y + up * h], onEdge(b, h)];
    var da = DA.map(function (q, i) { return mix(q, DS[i], bk); });
    var DC = [onEdge(a, h * 0.55), [xa - h * 0.1, y], [xb + h * 0.1, y], onEdge(b, h * 0.55)];
    var dch = [mid(DS[0], DS[1]), mid(DS[1], DS[2]), mid(DS[3], DS[4]), mid(DS[4], DS[5])];
    var dc = DC.map(function (q, i) { return mix(q, dch[i], bk); });
    o.push(da[0]);
    quad(o, da[0], dc[0], da[1]); quad(o, da[1], dc[1], da[2]);
    o.push(da[3]);
    quad(o, da[3], dc[2], da[4]); quad(o, da[4], dc[3], da[5]);
    return o;
  }
  var a2 = onEdge(a, h * 1.7), b2 = onEdge(b, h * 1.7);
  o.push(a2);
  quad(o, a2, onEdge(a, h * 0.55), [xa, y + up * h * 0.42]);
  quad(o, [xa, y + up * h * 0.42], [xa - h * 0.1, y], [xa + h * 0.45, y]);
  o.push([xb - h * 0.45, y]);
  quad(o, [xb - h * 0.45, y], [xb + h * 0.1, y], [xb, y + up * h * 0.42]);
  quad(o, [xb, y + up * h * 0.42], onEdge(b, h * 0.55), b2);
  return o;
}

function clipPast(arr, k, sg, T, Dv) {
  var C = arr[k], ref = Dv[0] * T[1] - Dv[1] * T[0];
  for (var j = k - sg, steps = 0; j >= 0 && j < arr.length && steps < 80; j -= sg, steps++) {
    var q = arr[j], side = Dv[0] * (q[1] - C[1]) - Dv[1] * (q[0] - C[0]);
    if (side * ref > 1e-6) arr[j] = [C[0], C[1]]; else if (steps > 6) break;
  }
}
function beakPoly(p, T, w, P, yU) {
  // yU: the end's y on the unmapped skeleton, which decides the beak's side (the thresholds are skeleton coordinates)
  var y = p[1], x = p[0], yd = yU === undefined ? y : yU, up = yd < 150 ? 1 : yd > 450 ? -1 : 0, SW = P.W0 || P.W, H = SW * 0.95, Bw = SW * 0.5, polys = [];
  function side(dir, hh) {
    var e = y + dir * w / 2, tip = [x, e + dir * hh], back = [x - T[0] * Bw, e], o = [back];
    quad(o, back, [x - T[0] * Bw * 0.15, e], tip);
    o.push([x, y]);
    polys.push(o);
  }
  if (up) side(up, H);
  return polys;
}

/* ---------- The width law ----------
   WHAT IT'S FOR: the one place a pen width is decided, so the stroke samples, the corner a stem runs
   out to, and the vertical fit (hwFlat) cannot disagree about how thick a stroke is. A fit that
   ignored an optical correction would move a level bar inward by the UN-corrected half width and
   leave its outer edge short of the line.
   th is the stroke direction (radians); cw is the curvature weight, 0 for a straight sample and 1
   for a sample on a curve of radius ROUND_GAIN_RADIUS * W0 or tighter. With no optical knob set
   (P.optical false) this is the 0.1 expression, verbatim. */
var ROUND_GAIN_RADIUS = 2.5;
function penWidth(th, P, cw) {
  var f = P.thin + (1 - P.thin) * Math.pow(Math.abs(Math.sin(th - P.nib)), P.pow);
  if (!P.optical) return f;
  var c = Math.cos(th), s2 = Math.sin(2 * th);
  return f * (1 - (1 - P.hzThin) * c * c)        // level strokes thinner: cos^2 is 1 level, 0 plumb
           * (1 - (1 - P.diagThin) * s2 * s2)    // diagonals thinner: sin^2(2 th) is 1 at 45 degrees
           * (1 + (P.roundGain - 1) * cw);       // curves heavier, by how much the sample curves
}

/* Turn one centre line into outline polygons for concept P. */
function strokePolys(pts, closed, flags, P, ch, out, joins, trace, joinIds, U) {
  // U carries the same stroke on the UNMAPPED skeleton (the x-height map undone): every geometry-dependent decision below reads pu
  // and ju and every drawn coordinate reads pts and joins, so xh cannot flip a branch. With the map off U is absent and
  // pu IS pts, ju IS joins: the 0.1 code path.
  var pu = U ? U.pts : pts, ju = U ? U.joins : joins;
  // the level cuts and squared corners where two stroke ends meet are a serif concept's; `joints: true` gives a sans concept the same pass
  var jointsOn = P.ends.s === "serif" || P.joints === true;
  var modeA = P.ends[flags[0]], modeB = P.ends[flags[1]], curlA = 0, curlB = 0, curlInfoA = {}, curlInfoB = {}, dropK = 1, first = out.length;
  // "flareS" is a free end with a half-size teardrop, for strokes where a full drop reads as a dot
  if (modeA === "flareS") { modeA = "flare"; dropK = 0.5; }
  if (modeB === "flareS") { modeB = "flare"; dropK = 0.5; }
  if (P.beak && !closed && pu.every(function (q) { return Math.abs(q[1] - pu[0][1]) < 0.5; })) {
    if (modeA === "flare") modeA = "beak";
    if (modeB === "flare") modeB = "beak";
  }
  if (!closed) {
    var dec = pu !== pts ? pu : undefined;
    if (modeB === "curl") { curlB = addCurl(pts, P, dec, curlInfoB); if (!curlB) modeB = "disk"; }
    if (modeA === "curl") { pts.reverse(); if (dec) pu.reverse(); curlA = addCurl(pts, P, dec, curlInfoA); pts.reverse(); if (dec) pu.reverse(); if (!curlA) modeA = "disk"; }
  }
  var n = pts.length, s = [0], i;
  var chord = [pu[n - 1][0] - pu[0][0], pu[n - 1][1] - pu[0][1]], cl = Math.hypot(chord[0], chord[1]) || 1;
  var curved = !closed && pu.some(function (q) {
    return Math.abs((q[0] - pu[0][0]) * chord[1] - (q[1] - pu[0][1]) * chord[0]) / cl > 3;
  });
  var tapA = curved && modeA === "disk" && !(joins && joins[0]), tapB = curved && modeB === "disk" && !(joins && joins[1]);
  var tapL = 0.9 * (P.W0 || P.W);
  function tap(d) { return d < tapL ? 1 - 0.3 * Math.pow(1 - d / tapL, 1.5) : 1; }
  for (i = 1; i < n; i++) s.push(s[i - 1] + dist(pts[i - 1], pts[i]));
  var total = s[n - 1], seed = ch.charCodeAt(0) * 1.7 + pts.length * 0.3;
  var Lp = [], Rp = [], Ws = [], Ts = [], minw = Infinity;
  // which edge of each free curved end is the outside of the curve: that edge swells into the teardrop
  var tearL = 1.1 * (P.W0 || P.W), tearA = null, tearB = null;
  function tang(j) { var a = pu[Math.max(0, j - 1)], b = pu[Math.min(n - 1, j + 1)], l = dist(a, b) || 1; return [(b[0] - a[0]) / l, (b[1] - a[1]) / l]; }
  if (P.tear && !closed && n > 30) {
    var span = Math.min(n - 2, Math.round(n / 4));
    if (modeB === "flare") { var t0 = tang(n - 1 - span), t1 = tang(n - 1), cb = t0[0] * t1[1] - t0[1] * t1[0]; tearB = Math.abs(cb) < 0.03 ? "S" : cb > 0 ? "R" : "L"; }
    if (modeA === "flare") { var u0 = tang(span), u1 = tang(0), ca = u0[0] * u1[1] - u0[1] * u1[0]; tearA = Math.abs(ca) < 0.03 ? "S" : ca > 0 ? "L" : "R"; }
  }
  // curvature weight per sample for roundGain: the turning angle at the sample over the mean chord
  // length, scaled by ROUND_GAIN_RADIUS * W0 and capped at 1; a ring is round by definition (cw 1)
  var cwOf = null;
  if (P.optical && P.roundGain !== 1 && !closed && n > 2) {
    cwOf = [];
    for (i = 0; i < n; i++) {
      var jc = Math.min(n - 2, Math.max(1, i)), p0 = pts[jc - 1], p1 = pts[jc], p2 = pts[jc + 1];
      var ux = p1[0] - p0[0], uy = p1[1] - p0[1], vx = p2[0] - p1[0], vy = p2[1] - p1[1];
      var ds = (Math.hypot(ux, uy) + Math.hypot(vx, vy)) / 2;
      var kappa = ds > 0 ? Math.abs(Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)) / ds : 0;
      cwOf.push(Math.min(1, kappa * ROUND_GAIN_RADIUS * (P.W0 || P.W)));
    }
  }
  // crotch: at each end that resolves as a JOINT (not a corner) between two arms meeting at an acute angle, the edge on the partner's
  // side thins over the last crotchLen (the teardrop's reach, so the hairline floor never sees it). Decided on the unmapped skeleton.
  // The outcome is recorded whether or not the knob is set, so two masters that disagree about an angle are refused.
  var crotchLen = tearL, cr = null;
  function crotchEnd(side) {
    var pdU = jointsOn && ju && !flags[side] ? ju[side] : null;
    var t = tang(side ? n - 1 : 0), sg = side ? 1 : -1;
    var isJoint = !!pdU && Math.abs(t[1]) > 0.5 && Math.abs(pdU[1]) > 0.5;
    var acute = isJoint && -(t[0] * sg * pdU[0] + t[1] * sg * pdU[1]) > 0.3;
    return { acute: acute, left: pdU ? -t[1] * pdU[0] + t[0] * pdU[1] > 0 : true };
  }
  if (!closed && n > 1) cr = [crotchEnd(0), crotchEnd(1)];
  for (i = 0; i < n; i++) {
    var a = closed ? pts[(i - 1 + n) % n] : pts[Math.max(0, i - 1)];
    var b = closed ? pts[(i + 1) % n] : pts[Math.min(n - 1, i + 1)];
    var tx = b[0] - a[0], ty = b[1] - a[1], tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
    var th = Math.atan2(ty, tx);
    var f = penWidth(th, P, closed ? 1 : cwOf ? cwOf[i] : 0);
    var m = 1;
    if (!closed) { m *= endMod(modeA, s[i], curlA, P); m *= endMod(modeB, total - s[i], curlB, P); }
    if (tapA) m *= tap(s[i]);
    if (tapB) m *= tap(total - s[i]);
    if (P.swell && !closed) m *= 1 + P.swell * (0.5 - Math.sin(Math.PI * s[i] / total));
    if (P.wob) m *= 1 + P.wob * Math.sin(s[i] / 37 + seed) * Math.sin(s[i] / 91 + seed * 0.37);
    var w = P.W * f * m, nx = -ty, ny = tx, wl = w, wr = w;
    if (P.tear) {
      [[0, s[i], tearA], [1, total - s[i], tearB]].forEach(function (t) {
        if (!t[2] || t[1] >= tearL) return;
        var u = 1 - t[1] / tearL, e = u * u * (3 - 2 * u), wk = P.W0 ? Math.pow(P.W0 / P.W, 1.5) : 1;
        // dropAmt scales the whole teardrop: the outer swell, the inner thinning and the symmetric
        // (S) case together, relative to the 0.55 / 0.28 / 0.30 the two shipped faces used
        var dk = P.dropAmt / DROP_AMT_DEFAULT;
        var out = 1 + 0.55 * dk * wk * dropK * e, inn = 1 - 0.28 * dk * dropK * e;
        if (t[2] === "L") { wl *= out; wr *= inn; } else if (t[2] === "R") { wr *= out; wl *= inn; } else { wl *= 1 + 0.3 * dk * e; wr *= 1 + 0.3 * dk * e; }
      });
    }
    if (P.crotch && cr) {
      [[s[i], cr[0]], [total - s[i], cr[1]]].forEach(function (c) {
        if (!c[1].acute || c[0] >= crotchLen) return;
        var u = 1 - c[0] / crotchLen, e = u * u * (3 - 2 * u), fc = 1 - P.crotch * e;
        if (c[1].left) wl *= fc; else wr *= fc;
      });
    }
    Lp.push([pts[i][0] + nx * wl / 2, pts[i][1] + ny * wl / 2]);
    Rp.push([pts[i][0] - nx * wr / 2, pts[i][1] - ny * wr / 2]);
    Ws.push(w); Ts.push([tx, ty]);
    // the interior: further from either end than the teardrop (1.1 W0) and taper (0.9 W0) reach,
    // so a terminal's deliberate thinning is not reported as a hairline
    if (closed || (s[i] >= Math.max(tearL, tapL) && total - s[i] >= Math.max(tearL, tapL))) {
      if (Math.min(wl, wr) < minw) minw = Math.min(wl, wr);
    }
  }
  // Where a bend is tighter than half the stroke width, the inside offset edge runs backwards and
  // folds into a loop, which the nonzero fill paints as a lump (the Bold t's foot, round 1 review).
  // Pin any point that would step against the centre line's direction to the point before it; the
  // count of points is unchanged, so the masters stay compatible.
  if (!closed) {
    [Lp, Rp].forEach(function (E) {
      for (var j = 1; j < n; j++) {
        if ((E[j][0] - E[j - 1][0]) * Ts[j][0] + (E[j][1] - E[j - 1][1]) * Ts[j][1] < 0) E[j] = [E[j - 1][0], E[j - 1][1]];
      }
    });
  }
  var sig = (closed ? "ring" : "open") + " n=" + n + " A=" + modeA + " B=" + modeB + " curved=" + curved +
            " tap=" + (tapA ? 1 : 0) + (tapB ? 1 : 0) + " tear=" + tearA + "/" + tearB +
            " joins=" + (joinIds ? joinIds[0] + "/" + joinIds[1] : "-/-");
  if (closed) {
    out.push({ pts: Lp, ring: true, runs: [[0, n - 1]] }); out.push({ pts: Rp, ring: true, runs: [[0, n - 1]] });
    trace.push({ sig: sig, minw: minw }); return;
  }
  var ends = [[0, modeA, -1], [n - 1, modeB, 1]];
  ends.forEach(function (e) {
    var k = e[0], mode = e[1], sg = e[2], T = [Ts[k][0] * sg, Ts[k][1] * sg], TU = pu === pts ? T : [tang(k)[0] * sg, tang(k)[1] * sg];
    if (mode === "cut") {
      var Dv = [Math.cos(P.cut), Math.sin(P.cut)];
      Lp[k] = cutSide(Lp[k], T, pts[k], Dv, Ws[k]); Rp[k] = cutSide(Rp[k], T, pts[k], Dv, Ws[k]);
    }
    // a serifed diagonal ends level with the baseline or cap line, not square to the stroke
    // only the serifed concept gets level joints; the others keep their own round or cut ends
    var side = e[2] < 0 ? 0 : 1, pd = jointsOn && joins && !flags[side] ? joins[side] : null;
    var pdU = pd ? ju[side] : null;
    var vert = Math.abs(TU[1]) > 0.5;
    if (pd && vert !== (Math.abs(pdU[1]) > 0.5)) {
      // a corner (E, F, L, Z, the spur of G): square it off by running this stroke out
      // to the far edge of its partner, cut level or plumb
      var pth = Math.atan2(pd[1], pd[0]);
      var pw = P.W * penWidth(pth, P, 0);
      var reach = pw / 2 / Math.max(0.3, vert ? Math.abs(pd[0]) : Math.abs(pd[1]));
      var Dc = vert ? [1, 0] : [0, 1], at = [pts[k][0] + T[0] * reach / Math.abs(vert ? T[1] : T[0]), pts[k][1] + T[1] * reach / Math.abs(vert ? T[1] : T[0])];
      Lp[k] = cutSide(Lp[k], T, at, Dc, Ws[k] + reach * 3); Rp[k] = cutSide(Rp[k], T, at, Dc, Ws[k] + reach * 3);
      clipPast(Lp, k, sg, T, Dc); clipPast(Rp, k, sg, T, Dc);
      e[1] = "corner"; return;
    }
    if (pd && vert) e[1] = "joint";
    if ((mode === "serif" && Math.abs(TU[0]) > 0.1 || e[1] === "joint") && Math.abs(TU[1]) > 0.5) {
      Lp[k] = cutSide(Lp[k], T, pts[k], [1, 0], Ws[k]); Rp[k] = cutSide(Rp[k], T, pts[k], [1, 0], Ws[k]);
      clipPast(Lp, k, sg, T, [1, 0]); clipPast(Rp, k, sg, T, [1, 0]);
    }
  });
  var poly = Lp.concat(Rp.slice().reverse());
  out.push({ pts: poly, runs: [[0, n - 1], [n, 2 * n - 1]] });
  sig += " ends=" + ends[0][1] + "/" + ends[1][1];
  // recorded only when crotch is set, so a 0.1 project's masters, which may fall on either side of the acute test, are not newly refused
  if (P.crotch > 0) sig += " crotch=" + (cr && cr[0].acute ? 1 : 0) + "/" + (cr && cr[1].acute ? 1 : 0);
  // the handedness of a curl's spiral (1 or -1 per end, 0 for none) is a decision the map must not flip
  if (curlA || curlB) sig += " curlsg=" + (curlA ? curlInfoA.sg : 0) + "/" + (curlB ? curlInfoB.sg : 0);
  ends.forEach(function (e) {
    var k = e[0], mode = e[1], sg = e[2], T = [Ts[k][0] * sg, Ts[k][1] * sg], p = pts[k], w = Ws[k];
    var TU = pu === pts ? T : [tang(k)[0] * sg, tang(k)[1] * sg];
    if (mode === "taper") {
      var Dv = [Math.cos(P.cut), Math.sin(P.cut)];
      // tapered ends also take the wind cut
      var l2 = cutSide(Lp[k], T, p, Dv, w), r2 = cutSide(Rp[k], T, p, Dv, w);
      out.push({ pts: [Lp[k], l2, r2, Rp[k]] });
    } else if (mode === "beak") {
      var beaks = beakPoly(p, T, w, P, pu[k][1]);
      sig += " beak" + (sg < 0 ? "A" : "B") + "=" + beaks.length;
      beaks.forEach(function (o) { out.push({ pts: o }); });
    } else if (mode === "flare" && P.tear) {
      sig += " tearcap" + (sg < 0 ? "A" : "B");
      // half-round across the end's own edges, bulging outward along the stroke
      var A = Lp[k], B = Rp[k], c = [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2], r = dist(A, B) / 2, a0 = Math.atan2(A[1] - c[1], A[0] - c[0]);
      var dirS = (Math.cos(a0 + Math.PI / 2) * T[0] + Math.sin(a0 + Math.PI / 2) * T[1]) > 0 ? 1 : -1, arc = [A];
      for (var q = 1; q < 24; q++) { var aa = a0 + dirS * Math.PI * q / 24; arc.push([c[0] + r * Math.cos(aa), c[1] + r * Math.sin(aa)]); }
      arc.push(B, [c[0] - T[0] * r * 0.5, c[1] - T[1] * r * 0.5]);
      out.push({ pts: arc });
    } else if (mode === "flare") {
      // balls grow more slowly than stems, or the Bold's terminals swallow its counters
      var rb = w / 2 * (1 - 0.4 * ((P.W0 ? P.W / P.W0 : 1) - 1));
      if (P.pebble) {
        // worn terminal: no ball. The stroke flares and ends in a cut that the build's wear pass rounds off,
        // with a half-round cap so the end reads as worn wood rather than a sawn edge
        out.push({ pts: circle(p[0], p[1], w / 2, w / 2 * 0.55, Math.atan2(T[1], T[0])) });
      } else out.push({ pts: circle(p[0], p[1], rb, rb) });
    } else if (mode === "disk") {
      // a hidden join: keep the cap inside the stroke it meets, or it shows as a nub
      out.push({ pts: circle(p[0], p[1], w * 0.42, w * 0.42) });
    } else if (mode === "curl") {
      out.push({ pts: circle(p[0], p[1], P.W * 0.36, P.W * 0.36) });
    } else if (mode === "serif") {
      var kind = Math.abs(TU[1]) > 0.5 && Math.abs(TU[0]) > 0.1 ? "diag" : Math.abs(TU[1]) > 0.5 ? (TU[1] < 0 ? "foot" : "head") : "ball";
      sig += " serif" + (sg < 0 ? "A" : "B") + "=" + kind;
      if (kind === "diag") out.push({ pts: diagSerifPoly(p, T, Lp[k], Rp[k], P) });
      else if (kind !== "ball") out.push({ pts: serifPoly(p, T, w, P, UPPERISH.test(ch)) });
      else out.push({ pts: circle(p[0], p[1], w / 2, w / 2) });
    }
  });
  // every polygon this stroke added is one edge run unless it said otherwise (the stroke body)
  for (var z = first; z < out.length; z++) if (!out[z].runs) out[z].runs = [[0, out[z].pts.length - 1]];
  trace.push({ sig: sig, minw: minw });
}

/* ---------- Vertical fit ----------
   The skeletons are centre lines, so a stroke drawn on the baseline hangs half its width below it.
   Flat strokes on the baseline, x-height, cap line or ascender move inward by half the horizontal
   stroke width; round extremes move so that their outer edge overshoots by P.overshoot. Anything
   that shared a moved point moves with it, except a serifed stem end, whose serif covers the joint. */
var FLAT = { "0": 1, "500": -1, "700": -1, "740": -1 };
var ROUND = { "510": [500, 1], "-10": [0, -1], "710": [700, 1], "720": [700, 1], "-230": [-230, -1] };
function hwFlat(P) {
  // a level stroke's half width; with an optical knob set it is the corrected width, or a flat bar's outer edge misses the line
  if (P.optical) return P.W * penWidth(0, P, 0) / 2;
  return P.W * (P.thin + (1 - P.thin) * Math.pow(Math.abs(Math.sin(P.nib)), P.pow)) / 2;
}
function fitSkeleton(src, P, key) {
  // the x-height map (above) applies before the fit's early return, so a project without the fit still gets its x-height
  var mapOn = key !== undefined && xhMapped(key, P), fit = !!P.overshoot;
  if (!fit && !mapOn) return src;
  // Y maps a literal skeleton y to the drawn one: the identity unless the map is on. The FLAT and ROUND tables keep their
  // literal keys (a point AT 500 is "on the x-line"), and their TARGETS go through Y.
  var Y = mapOn ? function (y) { return ymap(y, P.xh); } : function (y) { return y; };
  // hwRound: the half width of a stroke at a round extreme, where the curve is at its tightest, so the outer edge
  // lands at the line plus `overshoot` whatever roundGain is; without an optical knob it is hwFlat, as in 0.1
  var hw = hwFlat(P), O = P.overshoot, moved = {}, segs = [];
  var hwRound = P.optical ? P.W * penWidth(0, P, 1) / 2 : hw;
  function parse(d) {
    var t = d.trim().split(/[\s,]+/), pts = [], i = 0, cmd = "";
    while (i < t.length) {
      if (/^[MLC]$/.test(t[i])) { cmd = t[i++]; continue; }
      pts.push({ x: +t[i], y: +t[i + 1], cmd: cmd, ix: i }); i += 2;
    }
    return { t: t, pts: pts };
  }
  var parsed = src.map(function (st) { return st.d ? parse(st.d) : null; });
  parsed.forEach(function (pp) {
    if (!pp || !fit) return;
    pp.pts.forEach(function (p, j) {
      var fk = String(p.y);
      if (!(fk in FLAT)) return;
      var prev = pp.pts[j - 1], next = pp.pts[j + 1];
      if ((prev && prev.y === p.y) || (next && next.y === p.y)) {
        p.ny = Y(p.y) + FLAT[fk] * hw; moved[p.x + "," + p.y] = p.ny;
        if (next && next.y === p.y) segs.push([Math.min(p.x, next.x), Math.max(p.x, next.x), p.y, p.ny]);
      }
    });
  });
  return src.map(function (st, si) {
    if (st.r) {
      var top = st.r[1] + st.r[3], bot = st.r[1] - st.r[3];
      if (fit && String(top) in ROUND && ROUND[top][1] > 0) top = Y(ROUND[top][0]) + O - hwRound;
      else if (mapOn) top = Y(top);
      if (fit && String(bot) in ROUND && ROUND[bot][1] < 0) bot = Y(ROUND[bot][0]) - O + hwRound;
      else if (mapOn) bot = Y(bot);
      var r = ring(st.r[0], (top + bot) / 2, st.r[2], (top - bot) / 2);
      return r;
    }
    var pp = parsed[si];
    if (!pp) return st;
    var last = pp.pts.length - 1;
    pp.pts.forEach(function (p, j) {
      var ny = p.ny;
      if (ny === undefined) {
        var serifEnd = (j === 0 && st.a === "s") || (j === last && st.b === "s");
        var k = p.x + "," + p.y;
        if (k in moved && !serifEnd) ny = moved[k];
        else if (!serifEnd) segs.forEach(function (s) { if (p.y === s[2] && p.x > s[0] && p.x < s[1]) ny = s[3]; });
      }
      if (ny === undefined && fit && p.cmd === "C" && String(p.y) in ROUND) {
        var R = ROUND[p.y]; ny = Y(R[0]) + R[1] * (O - hwRound);
      }
      if (ny === undefined && mapOn) ny = Y(p.y);
      if (ny !== undefined) pp.t[p.ix + 1] = String(+ny.toFixed(2));
    });
    return { d: pp.t.join(" "), a: st.a, b: st.b };
  });
}

/* ---------- Glyph building, spacing and kerning ---------- */
var BIN = 20, BMIN = -260, NB = 54;
function binOf(y) { return Math.floor((y - BMIN) / BIN); }
var cache = {};
function stable(v) {
  // undefined and null are different parameters to params() (dropAmt: undefined takes the default, null
  // does not), so they must serialise differently (independent re-review, code-a F001)
  if (v === undefined) return "undefined";
  if (v === null || typeof v !== "object") return typeof v === "number" ? (Object.is(v, -0) ? "0" : String(v)) : JSON.stringify(v);
  if (Array.isArray(v)) return "[" + v.map(stable).join(",") + "]";
  return "{" + Object.keys(v).sort().map(function (k) { return JSON.stringify(k) + ":" + stable(v[k]); }).join(",") + "}";
}
function cacheKey(concept, mult, deg) { return stable(concept) + "|" + String(mult) + "|" + String(deg); }
/* The parameters of one master: concept with W multiplied by mult. `italic` is false, true (a 10
   degree slant) or the slant in degrees. Throws on a concept this generator cannot honour, so a
   dead knob is a loud error rather than a silent no-op. */
function params(concept, mult, italic) {
  if (!concept || typeof concept !== "object" || !concept.id) throw new Error("params: a concept needs an id");
  if (!concept.ends || typeof concept.ends !== "object") throw new Error("params: concept " + concept.id + " has no ends table");
  if (!(concept.W > 0) || !(mult > 0)) throw new Error("params: concept " + concept.id + " needs W > 0 and mult > 0");
  if (concept.tear && concept.flareAmt !== undefined) {
    throw new Error("params: concept " + concept.id + " sets flareAmt with tear: true; flareAmt has no effect with teardrop terminals, set dropAmt instead");
  }
  if (!concept.tear && concept.dropAmt !== undefined) {
    throw new Error("params: concept " + concept.id + " sets dropAmt without tear: true; dropAmt only sizes teardrop terminals");
  }
  // the optical corrections (item 3): a loud refusal outside the range, so a typo is not a silent change
  [["hzThin", 0.5, 1.5], ["diagThin", 0.5, 1.5], ["roundGain", 0.8, 1.25]].forEach(function (k) {
    var v = concept[k[0]];
    if (v !== undefined && !(typeof v === "number" && v > k[1] && v < k[2])) {
      throw new Error("params: concept " + concept.id + " sets " + k[0] + " to " + JSON.stringify(v) + "; it must be a number strictly between " + k[1] + " and " + k[2] +
                      " (references/generator.md, section 4)");
    }
  });
  if (concept.xh !== undefined && !(typeof concept.xh === "number" && concept.xh >= 400 && concept.xh <= 600)) {
    throw new Error("params: concept " + concept.id + " sets xh to " + JSON.stringify(concept.xh) + "; it must be a number from 400 to 600 (references/generator.md, section 4)");
  }
  if (concept.serifBracket !== undefined && !(typeof concept.serifBracket === "number" && concept.serifBracket >= 0 && concept.serifBracket <= 1)) {
    throw new Error("params: concept " + concept.id + " sets serifBracket to " + JSON.stringify(concept.serifBracket) + "; it must be a number from 0 to 1 (references/generator.md, section 4)");
  }
  if (concept.apex !== undefined) {
    throw new Error("params: concept " + concept.id + " sets apex; apex is designed but not built in 0.2 (references/generator.md, 'Designed, not built: apex'); remove it");
  }
  if (concept.joints !== undefined && typeof concept.joints !== "boolean") {
    throw new Error("params: concept " + concept.id + " sets joints to " + JSON.stringify(concept.joints) + "; it must be true or false (references/generator.md, section 4)");
  }
  if (concept.crotch !== undefined && !(typeof concept.crotch === "number" && concept.crotch >= 0 && concept.crotch <= 0.6)) {
    throw new Error("params: concept " + concept.id + " sets crotch to " + JSON.stringify(concept.crotch) + "; it must be a number from 0 to 0.6 (references/generator.md, section 4)");
  }
  var P = Object.assign({}, concept);
  P.xh = concept.xh === undefined ? 500 : concept.xh;
  P.serifBracket = concept.serifBracket === undefined ? 1 : concept.serifBracket;
  P.hzThin = concept.hzThin === undefined ? 1 : concept.hzThin;
  P.diagThin = concept.diagThin === undefined ? 1 : concept.diagThin;
  P.roundGain = concept.roundGain === undefined ? 1 : concept.roundGain;
  P.optical = !(P.hzThin === 1 && P.diagThin === 1 && P.roundGain === 1);
  // `cut` is the angle of cut/taper ends and the rotation of leaf dots; unset means 0 rad, a horizontal cut (generator.md section 4).
  // Left undefined it reached Math.cos() as NaN and every glyph with a cut end had non-finite coordinates.
  P.cut = concept.cut === undefined ? 0 : concept.cut;
  P.W = concept.W * mult; P.W0 = concept.W;
  if (P.dropAmt === undefined) P.dropAmt = DROP_AMT_DEFAULT;
  // hairlines grow more slowly than stems (W x mult^thinGrow rather than W x mult), or the Bold's
  // contrast collapses and it reads as another family beside the Regular (Bract round 2 review)
  if (P.thinGrow !== undefined) P.thin = concept.thin * Math.pow(mult, P.thinGrow - 1);
  var deg = italic === true ? 10 : italic ? +italic : 0;
  P.italicAngle = deg;
  P.italic = deg ? Math.tan(deg * DEG) : 0;
  // The glyph cache is keyed by EVERY parameter at full precision (a stable serialisation of the
  // concept, the exact multiplier and the slant), not by id|mult: a concept edited in place without
  // a new id, or two multipliers that round alike, drew stale glyphs until an independent review of
  // this repo caught it (finding C3).
  P.key = cacheKey(concept, mult, deg);
  return P;
}
function glyph(key, P) {
  var c = cache[P.key] || (cache[P.key] = { g: {}, k: {} });
  if (key in c.g) return c.g[key];
  var raw = (P.italic && GI[key]) || G[key];
  if (!raw) { c.g[key] = null; return null; }
  // sample counts come from the unfitted skeleton, so every master gets the same points per segment
  var counts = raw.map(function (st) { return st.d ? sampleCounts(st.d) : null; });
  var src = fitSkeleton(raw, P, key), mapOn = xhMapped(key, P);
  // the same skeleton fitted at xh 500: with the map on, the decisions read this one (sampled with the same counts, so point for point)
  var src500 = mapOn ? fitSkeleton(raw, Object.assign({}, P, { xh: 500 }), key) : src;
  var items = [], trace = [];
  // stroke ends that meet another stroke's end (the points of V, W, A) are joints, not terminals
  // each end records the direction its partner stroke leaves the shared point in
  var ends = [];
  // the sampled, transformed points of stroke si on the unmapped skeleton; with the map off they are the drawn points, so the default
  // path is the 0.1 one
  function unmapped(si) { return samplePath(src500[si].d, counts[si]).map(function (p) { return xf(key, P, p); }); }
  src.forEach(function (st, si) {
    if (st.dot || st.closed) return;
    var q = samplePath(st.d, counts[si]).map(function (p) { return xf(key, P, p); }), m = q.length - 1;
    // directions are taken on the unmapped skeleton (qU), positions on the drawn one: mapped coordinates draw, unmapped decide
    var qU = mapOn ? unmapped(si) : q;
    ends.push({ p: qU[0], si: si, end: "a", dir: unit(qU[0], qU[Math.min(3, m)]), dirM: unit(q[0], q[Math.min(3, m)]) });
    ends.push({ p: qU[m], si: si, end: "b", dir: unit(qU[m], qU[Math.max(m - 3, 0)]), dirM: unit(q[m], q[Math.max(m - 3, 0)]) });
  });
  function unit(a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1; return [dx / l, dy / l]; }
  // the partner is another stroke's end within 2 units; which stroke and which end goes into the
  // branch record, so masters that pair a point differently fail the compatibility check (F005)
  function partner(e, si) {
    var o = ends.filter(function (x) { return x.si !== si && dist(x.p, e) < 2; });
    return o.length ? { dir: o[0].dir, dirM: o[0].dirM, id: o[0].si + o[0].end } : null;
  }
  src.forEach(function (st, si) {
    if (st.dot) {
      var r = P.W * P.dot, dy = st.dot[1];
      // the dot rule reads the UNMAPPED dy: a baseline dot, an x-height dot (the colon's upper dot at 420; the i's at 680 is not one),
      // else the dot is carried by the map. With the map on, the x-height dot sits at xh, not 500.
      if (P.overshoot && dy < 100) dy = r - 4;
      else if (P.overshoot && dy > 380 && dy < 460) dy = (mapOn ? P.xh : 500) - r + 4;
      else if (mapOn) dy = ymap(dy, P.xh);
      var q = xf(key, P, [st.dot[0], dy]);
      items.push({ pts: P.leaf ? circle(q[0], q[1], r * 1.3, r * 0.72, P.cut) : circle(q[0], q[1], r, r), runs: [[0, 63]] });
      trace.push({ sig: "dot", minw: Infinity });
      return;
    }
    var pts = samplePath(st.d, counts[si]).map(function (p) { return xf(key, P, p); }), ptsU = mapOn ? unmapped(si) : pts;
    // a ring ends where it began; the repeated point would round onto its twin in some masters and
    // not others, so TTGlyphPen would drop it unevenly. Drop it here, the same way in every master.
    if (st.closed && pts.length > 1 && pts[0][0] === pts[pts.length - 1][0] && pts[0][1] === pts[pts.length - 1][1]) { pts.pop(); if (ptsU !== pts) ptsU.pop(); }
    var pA = st.closed ? null : partner(ptsU[0], si), pB = st.closed ? null : partner(ptsU[ptsU.length - 1], si);
    var joins = [pA ? pA.dirM : null, pB ? pB.dirM : null], joinsU = [pA ? pA.dir : null, pB ? pB.dir : null];
    strokePolys(pts, !!st.closed, [st.a || "", st.b || ""], P, key, items, joins, trace, [pA ? pA.id : "-", pB ? pB.id : "-"], { pts: ptsU, joins: joinsU });
  });
  // orient: ring loops pair up; the larger loop of each pair fills, the smaller cuts the hole
  var polys = [], runs = [];
  function flip(pts, rs) { // reversing a polygon maps index i to len-1-i, so each run flips too
    var L = pts.length;
    return { pts: pts.slice().reverse(), runs: rs.map(function (r) { return [L - 1 - r[1], L - 1 - r[0]]; }) };
  }
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    if (it.ring) {
      var o = it, inn = items[i + 1]; i++;
      if (Math.abs(area(o.pts)) < Math.abs(area(inn.pts))) { var t = o; o = inn; inn = t; }
      if (area(o.pts) < 0) o = flip(o.pts, o.runs);
      if (area(inn.pts) > 0) inn = flip(inn.pts, inn.runs);
      polys.push(o.pts, inn.pts); runs.push(o.runs, inn.runs);
    } else {
      var f = area(it.pts) < 0 ? flip(it.pts, it.runs) : it;
      polys.push(f.pts); runs.push(f.runs);
    }
  }
  var minX = Infinity, maxX = -Infinity, Lb = new Array(NB).fill(Infinity), Rb = new Array(NB).fill(-Infinity);
  polys.forEach(function (p) { p.forEach(function (q) {
    if (q[0] < minX) minX = q[0]; if (q[0] > maxX) maxX = q[0];
    var b = binOf(q[1]); if (b >= 0 && b < NB) { if (q[0] < Lb[b]) Lb[b] = q[0]; if (q[0] > Rb[b]) Rb[b] = q[0]; }
  }); });
  var top = UPPERISH.test(key) ? 700 : P.xh, b0 = binOf(0), b1 = binOf(top), Dmax = 0.2 * top;
  if (P.italic) {
    // the italic measures only the band between the baseline and the x-height or cap height, so f
    // hooks and tails overhang their neighbours instead of being spaced
    var cMin = Infinity, cMax = -Infinity;
    for (var bb = b0; bb < b1; bb++) { if (isFinite(Lb[bb])) cMin = Math.min(cMin, Lb[bb]); if (isFinite(Rb[bb])) cMax = Math.max(cMax, Rb[bb]); }
    // J's descender hook may hang only partway into the previous letter's space, or it collides
    if (isFinite(cMin)) { minX = key === "J" ? Math.max(minX, cMin - 90) : cMin; maxX = cMax; }
  }
  var mL = 0, mR = 0, cnt = 0;
  for (var b = b0; b < b1; b++) {
    mL += isFinite(Lb[b]) ? Math.min(Lb[b] - minX, Dmax) : Dmax;
    mR += isFinite(Rb[b]) ? Math.min(maxX - Rb[b], Dmax) : Dmax;
    cnt++;
  }
  mL /= cnt; mR /= cnt;
  // heavier weights get less extra space than their stems grow, or the bold looks letterspaced
  var W0 = P.W0 || P.W, T = 30 + 0.36 * W0 - 0.25 * (P.W - W0) + P.track - (P.italic ? 6 : 0);
  var sbL = Math.max(8, T - 0.5 * mL), sbR = Math.max(8, T - 0.5 * mR), sh = sbL - minX;
  var minw = Infinity, minwAt = null;
  trace.forEach(function (t, ti) { if (t.minw < minw) { minw = t.minw; minwAt = ti; } });
  var g = {
    key: key, upper: UPPERISH.test(key), adv: (maxX - minX) + sbL + sbR,
    polys: polys.map(function (p) { return p.map(function (q) { return [q[0] + sh, q[1]]; }); }),
    runs: runs,
    sig: trace.map(function (t) { return t.sig; }),
    minw: minw, minwStroke: minwAt,
    L: Lb.map(function (v) { return isFinite(v) ? v + sh : null; }),
    R: Rb.map(function (v) { return isFinite(v) ? v + sh : null; })
  };
  c.g[key] = g;
  return g;
}
function pairGap(a, b, top) {
  var sum = 0, n = 0, minRaw = Infinity;
  for (var i = 0; i < NB; i++) {
    if (a.R[i] === null || b.L[i] === null) continue;
    var raw = (a.adv - a.R[i]) + b.L[i];
    if (raw < minRaw) minRaw = raw;
    var y = BMIN + i * BIN;
    if (y >= 0 && y < top) { sum += raw; n++; }
  }
  return { mean: n ? sum / n : null, minRaw: minRaw };
}
function coverage(g, top) { // share of the bins between the baseline and `top` where the glyph has ink
  var b0 = binOf(0), b1 = binOf(top), n = 0;
  for (var i = b0; i < b1; i++) if (g.L[i] !== null) n++;
  return n / (b1 - b0);
}
function kern(a, b, P) {
  var c = cache[P.key], id = a.key + "|" + b.key;
  if (id in c.k) return c.k[id];
  var both = a.upper && b.upper, ref = both ? glyph("H", P) : glyph("n", P);
  var top = (a.upper || b.upper) ? 700 : P.xh;
  var rg = pairGap(ref, ref, both ? 700 : P.xh).mean, g = pairGap(a, b, top), k = 0;
  if (g.mean !== null && g.mean - rg > 8) k = -0.75 * (g.mean - rg - 8);
  k = Math.max(k, -170);
  // A sparse glyph (hyphen, dash, period, quotes: ink in only a few of the bins between the baseline
  // and the x-height or cap line) sees the other glyph's edge only where it has ink, so the mean gap
  // is measured at one height and can be huge: the hyphen before S hit the -170 clamp and crowded the
  // S in a cold dry run of this skill (Driftwood and Bract needed hand pairs like r|. for the same
  // reason). When either glyph covers under 35% of the band the automatic kern is capped at -50.
  var covA = coverage(a, top), covB = coverage(b, top);
  if (Math.min(covA, covB) < 0.35) k = Math.max(k, -50);
  var minClear = 14 + 0.05 * P.W;
  if (isFinite(g.minRaw)) k = Math.max(k, minClear - g.minRaw);
  k = Math.min(k, 80);
  c.k[id] = k;
  return k;
}

/* ---------- Text layout ---------- */
function keysFor(word, liga) {
  var out = [], w = word.replace(/[‘’]/g, "'");
  for (var i = 0; i < w.length; i++) {
    if (liga) {
      var two = w.substr(i, 2);
      if (LIGS.indexOf(two) >= 0) { out.push(two); i++; continue; }
    }
    out.push(w[i]);
  }
  return out;
}
function layWord(word, P, opt) {
  var x = 0, prev = null, items = [];
  keysFor(word, opt.liga).forEach(function (k) {
    var g = glyph(k, P);
    if (!g) { x += 200; prev = null; return; }
    if (prev && opt.kern) x += kern(prev, g, P);
    items.push({ g: g, x: x }); x += g.adv; prev = g;
  });
  return { items: items, w: x };
}
function wrap(words, P, opt, max) {
  var space = 210 + 0.3 * P.W + P.track * 2, laid = words.map(function (w) { return layWord(w, P, opt); });
  function greedy(limit) {
    var lines = [], cur = [], cw = 0;
    laid.forEach(function (lw) {
      var add = cur.length ? space + lw.w : lw.w;
      if (cur.length && cw + add > limit) { lines.push({ words: cur, w: cw }); cur = [lw]; cw = lw.w; }
      else { cur.push(lw); cw += add; }
    });
    if (cur.length) lines.push({ words: cur, w: cw });
    return lines;
  }
  var best = greedy(max), n = best.length;
  if (n > 1) { // balance the lines like text-wrap: balance
    for (var lim = max * 0.97; lim > max * 0.4; lim *= 0.97) {
      var t = greedy(lim);
      if (t.length !== n) break;
      best = t;
    }
  }
  return { lines: best, space: space };
}
/* Concepts: a concepts.js is a CommonJS module exporting an array of concept objects (it may define
   its own DEG). In the browser the same file is spliced into a page as a script that leaves a global
   CONCEPTS, which is why it is JavaScript and not JSON. */
function loadConcepts(file) {
  var list = require(require("path").resolve(file));
  if (!Array.isArray(list) || !list.length) throw new Error("concepts.js must export a non-empty array: " + file);
  var seen = {};
  list.forEach(function (c) { if (seen[c.id]) throw new Error("duplicate concept id " + c.id); seen[c.id] = true; });
  return list;
}
function conceptById(list, id) {
  var c = list.filter(function (x) { return x.id === id; })[0];
  if (!c) throw new Error("no concept with id " + JSON.stringify(id) + " (have " + list.map(function (x) { return x.id; }).join(", ") + ")");
  return c;
}
if (typeof module !== "undefined") {
  module.exports = { G: G, GI: GI, LIGS: LIGS, DEG: DEG, DROP_AMT_DEFAULT: DROP_AMT_DEFAULT, S: S, D: D, ring: ring, params: params, glyph: glyph, kern: kern,
    layWord: layWord, wrap: wrap, keysFor: keysFor, UPPERISH: UPPERISH, sampleCounts: sampleCounts, loadConcepts: loadConcepts, conceptById: conceptById };
}
