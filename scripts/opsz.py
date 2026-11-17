#!/usr/bin/env python3
"""Measures which opsz value Chrome applies under font-optical-sizing: auto at given CSS font sizes.

WHAT IT'S FOR: the opsz axis of a variable font is in whatever units the browser decides to feed it
(CSS px in Chrome, but that is a browser decision, not a property of the font), so the axis
endpoints a build should use come from a measurement, not an assumption. For each font size this
shoots opsz.html (row 0: optical sizing auto; row 1: optical sizing none, so the axis default; rows
2..: explicit "opsz" N from --range lo hi in --step steps), crops every row and reports the N whose
pixels equal row 0's. The shot goes through shoot.py, so the page must prove it rendered with
--family (a fallback serif would make every row identical and "match" everything).

    opsz.py OUT_DIR --serve DIR --font-url /fonts/Family-VF.woff2 --family Family
            --axis 24 72 [--title "..."] [--px 24 48 72] [--range 20 96] [--step 2] [--weight 400]

Verdict, per size: auto must match at least one explicit value; a size strictly inside the FONT's
opsz axis (--axis MIN MAX, the fvar range) must match exactly one; a size at or beyond an axis end
must match only values on that side of the end, the end included, because every value past the axis
end is clamped to the same instance (the first version judged "inside" by the probed --range instead
and refused a correct measurement at both axis ends). Anything else means
the page, the font or the comparison is broken, and the run prints "no mapping can be reported" and
exits 1 rather than reporting a mapping. A JSON summary line is printed last on stdout.

Exact guarantee: this is Chrome's headless renderer on this machine today. Safari and Firefox are
not measured; the review record must say so. Copyright 2026 John Knox. MIT licence.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shoot import find_chrome, serve, shoot, with_query  # noqa: E402

ROW = 100  # px, must equal .row height in opsz.html
PAGE = "__fd/opsz.html"


def measure(out, port, px, server, family, font_url, title, weight, lo, hi, step, chrome, axis):
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        sys.exit(f"opsz.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
                 "Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/opsz.py ...")
    ns = list(range(lo, hi + 1, step))
    png = out / f"opsz-{px}px.png"
    url = with_query(f"http://127.0.0.1:{port}/{PAGE}", {"px": px, "family": family, "url": font_url, "title": title,
                                                           "weight": weight, "lo": lo, "hi": hi, "step": step})
    shoot(url, png, 1000, 1, height=ROW * (len(ns) + 2) + 20, profile_root=out, server=server,
          require_family=family, font_url=font_url, chrome=chrome)
    with Image.open(png) as im:
        rows = [im.crop((0, i * ROW, im.width, (i + 1) * ROW)).convert("L") for i in range(len(ns) + 2)]
    auto, none = rows[0], rows[1]
    diffs = {n: ImageChops.difference(auto, rows[i + 2]).getextrema()[1] for i, n in enumerate(ns)}
    exact = [n for n, d in diffs.items() if d == 0]
    nearest = min(diffs, key=diffs.get)
    none_eq = [n for i, n in enumerate(ns) if ImageChops.difference(none, rows[i + 2]).getextrema()[1] == 0]
    amin, amax = axis
    clamped = None
    if not exact:
        problem = "auto matched no explicit opsz value"
    elif amin < px < amax:
        problem = None if len(exact) == 1 else f"auto matched {len(exact)} values, expected exactly one for a size inside the axis {amin}-{amax}"
    elif px <= amin:
        ok = all(n <= amin for n in exact) and (amin not in ns or amin in exact)
        problem = None if ok else f"auto matched {exact}, expected only values <= the axis start {amin} (clamped)"
        clamped = "start"
    else:
        ok = all(n >= amax for n in exact) and (amax not in ns or amax in exact)
        problem = None if ok else f"auto matched {exact}, expected only values >= the axis end {amax} (clamped)"
        clamped = "end"
    if exact and len(exact) == len(ns):
        # every row identical: the axis did nothing at this size (no opsz axis, or a face that ignores it)
        problem = (problem + "; " if problem else "") + "every explicit value rendered identically, so opsz has no effect here"
    return {"px": px, "auto_equals_opsz": exact, "clamped_to_axis": clamped, "nearest": nearest, "nearest_diff": diffs[nearest],
            "optical_sizing_none_equals_opsz": none_eq, "png": str(png), "problem": problem}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out")
    ap.add_argument("--serve", required=True, metavar="DIR", help="directory served at /, holding the font")
    ap.add_argument("--font-url", required=True, help="root-relative path of the woff2 under DIR")
    ap.add_argument("--family", required=True)
    ap.add_argument("--title", default="Harbour Review at Dawn 48")
    ap.add_argument("--px", nargs="+", type=float, default=[24, 48, 72])
    ap.add_argument("--axis", nargs=2, type=float, required=True, metavar=("MIN", "MAX"),
                    help="the font's opsz axis range (fvar): where a size counts as clamped")
    ap.add_argument("--range", nargs=2, type=int, default=[20, 96], metavar=("LO", "HI"))
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--weight", type=int, default=400)
    args = ap.parse_args(argv)
    lo, hi = args.range
    if hi < lo or args.step < 1:
        sys.exit("--range wants LO <= HI and --step >= 1")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        chrome = find_chrome()
        server, port = serve(args.serve, family=args.family)
    except (FileNotFoundError, NotADirectoryError) as exc:
        sys.exit(str(exc))
    results, problems = [], []
    try:
        for px in args.px:
            px = int(px) if float(px).is_integer() else px
            try:
                r = measure(out, port, px, server, args.family, args.font_url, args.title, args.weight, lo, hi, args.step, chrome, tuple(args.axis))
            except RuntimeError as exc:
                r = {"px": px, "problem": f"shot failed: {exc}"}
                print(f"{px}px: PROBLEM: {r['problem']}")
                problems.append(f"{px}px: {r['problem']}")
                results.append(r)
                continue
            print(f"{px}px: auto == opsz {r['auto_equals_opsz']} (nearest {r['nearest']}, diff {r['nearest_diff']}); "
                  f"optical-sizing none == opsz {r['optical_sizing_none_equals_opsz']}  [{r['png']}]"
                  + (f"  PROBLEM: {r['problem']}" if r["problem"] else ""))
            if r["problem"]:
                problems.append(f"{px}px: {r['problem']}")
            results.append(r)
    finally:
        server.shutdown()
    summary = {"family": args.family, "font_url": args.font_url, "axis": args.axis, "range": [lo, hi, args.step], "weight": args.weight,
               "results": results, "mapping_reported": not problems, "renderer": "Chrome headless on this machine; Safari and Firefox unmeasured"}
    print(json.dumps(summary))
    if problems:
        print("no mapping can be reported: " + "; ".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
