#!/usr/bin/env python3
"""Runs FontBakery's universal profile on a TTF built from the project and fails on any finding the
project has not accepted.

WHAT IT'S FOR: the font suite (scripts/tests/test_font.py) pins what the project decided; it cannot know
what the font FORMAT expects. FontBakery is the community's checker for that: on the first fixture it found
six FAILs the 30-test suite had never seen (no code-page bit, Mac name records, a missing smart-dropout
`prep`, STAT without axis values, hhea and typo metrics that disagree). This is phase 7's gate on it. It
builds each group's variable TTF (build.py --ttf, into a temporary directory, so nothing lands in the
project's out_dir), runs `fontbakery check-universal`, reads the JSON report and exits 1 on every FAIL,
ERROR or FATAL whose check id is not listed in requirements.json `accepted_qa_findings`. The groups' TTFs go
through ONE FontBakery run, because some checks are about the family (an italic must find its roman).

    fontbakery-gate.py --font font.json --requirements requirements.json [--group roman ...]
    fontbakery-gate.py --font font.json --requirements requirements.json --profile googlefonts
    fontbakery-gate.py --font font.json --requirements requirements.json --ttf built.ttf   # check this TTF; no build
    --fontbakery CMD    the command to run instead of `<this python> -m fontbakery` (or env FONTBAKERY)
    --report-dir DIR    keep the JSON report there

`accepted_qa_findings` is a REQUIRED key of requirements.json (an empty list when nothing is accepted):
a list of {"id": "<check id as FontBakery prints it>", "reason": "<why this finding stays>", "codes": [...]}.
`codes` is optional: the FontBakery message codes (the `[missing-case-counterparts]` in the output) that are
accepted. With `codes`, a FAIL, ERROR or FATAL message of that check with another code blocks, so a NEW kind of
failure of an accepted check is not hidden; without it the match is on the check id alone and any failure of that
check passes, which only a reason naming what was seen (which glyphs, which value) limits. The match is on the
code, never on the message text or the items it names: a new failure that reuses an accepted code (an eighth
lowercase letter without a capital under `missing-case-counterparts`) passes, and only the printed messages show
it. That is deliberate (operator decision, 2026-11-16): FontBakery rewords its messages between versions, so
matching the text would block an unchanged font after an upgrade. Read the accepted messages on every run. An entry whose check
no longer fails is reported as STALE and does not fail the run; delete it. A WARN never fails the gate.

Exit status: 0 every FAIL, ERROR and FATAL is accepted; 1 at least one is not, the report is unreadable or
unfinished, or requirements.json is malformed; 3 FontBakery is not installed, which is SKIPPED, NOT PASSED
(`pip install -r requirements-dev.txt`, or the operator waives the gate in writing).

Exact guarantee: FontBakery's universal profile at the version recorded in requirements-dev.txt found no
failure outside the accepted list in the TTF that build.py writes with --ttf, which is the variable font
before woff2 compression; the shipped woff2 is that same font compressed, not separately checked. Not a
proof the font is good: the checks are the community's, the profile is the universal one (a vendor profile
such as googlefonts adds checks, including `googlefonts/fstype`, which a deliberate non-zero fsType fails:
list it with that reason), and `--skip-network` leaves out the ones that need the network.

Copyright 2026 John Knox. MIT licence.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BLOCKING = ("FATAL", "ERROR", "FAIL")  # a check that did not run properly blocks like one that failed
CHECK_KEY = re.compile(r"^<FontBakeryCheck:(.+)>$")
EXIT_NOT_INSTALLED = 3


def load_accepted(requirements_path):
    """The validated accepted_qa_findings list of a requirements.json: [{"id", "reason"}], ids unique.
    Raises ValueError saying what is wrong, so a malformed list can never read as an empty one."""
    req = json.loads(pathlib.Path(requirements_path).read_text(encoding="utf-8"))
    if "accepted_qa_findings" not in req:
        raise ValueError(f"{requirements_path} has no accepted_qa_findings; add it ([] when no finding is accepted) so the omission is a decision")
    entries = req["accepted_qa_findings"]
    if not isinstance(entries, list):
        raise ValueError("accepted_qa_findings must be a list of {id, reason}")
    seen = set()
    for i, e in enumerate(entries):
        if not (isinstance(e, dict) and {"id", "reason"} <= set(e) <= {"id", "reason", "codes"}):
            raise ValueError(f"accepted_qa_findings[{i}] must be an object with the keys id and reason, and optionally codes: {e!r}")
        if "codes" in e and not (isinstance(e["codes"], list) and e["codes"] and all(isinstance(c, str) and c.strip() for c in e["codes"])):
            raise ValueError(f"accepted_qa_findings[{i}]: codes must be a non-empty list of non-empty strings (the FontBakery message codes accepted)")
        if not (isinstance(e["id"], str) and e["id"].strip()) or not (isinstance(e["reason"], str) and e["reason"].strip()):
            raise ValueError(f"accepted_qa_findings[{i}]: id and reason must be non-empty strings")
        if e["id"] in seen:
            raise ValueError(f"accepted_qa_findings lists {e['id']!r} twice")
        seen.add(e["id"])
    return entries


def findings(report):
    """[(check id, result, [(status, code, message)...])] for every check of a FontBakery JSON report that is
    not PASS, SKIP or INFO. Raises ValueError on a report that is not a FontBakery report."""
    if not (isinstance(report, dict) and isinstance(report.get("sections"), list) and isinstance(report.get("result"), dict)):
        raise ValueError("the JSON is not a FontBakery report (no `sections` and `result`)")
    out = []
    for sec in report["sections"]:
        for c in sec["checks"]:
            if c["result"] in ("PASS", "SKIP", "INFO"):
                continue
            m = CHECK_KEY.match(str(c["key"][1]))
            cid = m.group(1) if m else str(c["key"][1])
            logs = [(lg["status"], lg["message"].get("code", ""), str(lg["message"].get("message", ""))) for lg in c.get("logs", []) if lg["status"] != "PASS"]
            out.append((cid, c["result"], logs))
    return out


def judge(report, accepted):
    """(blockers, accepted_hits, stale, warns) for one report. A blocker is a FAIL/ERROR/FATAL whose id is
    not accepted, or a report that says some checks never finished; `stale` lists accepted ids that did not
    fail. Pure, so tests/test_fontbakery_gate.py can feed it crafted reports."""
    ids = {a["id"] for a in accepted}
    merged = {}  # one entry per check id: a family run reports a per-file check once for each file
    for cid, result, logs in findings(report):
        old = merged.get(cid)
        if old is None:
            merged[cid] = (result, list(logs))
        else:
            worst = next(r for r in ("FATAL", "ERROR", "FAIL", "WARN") if r in (old[0], result))
            merged[cid] = (worst, old[1] + [lg for lg in logs if lg not in old[1]])
    codes = {a["id"]: a.get("codes") for a in accepted}
    blockers, hits, warns = [], [], []
    for cid, (result, logs) in merged.items():
        if result == "WARN":
            warns.append(cid)
        elif result in BLOCKING:
            if cid not in ids:
                blockers.append((cid, result, logs))
                continue
            new = [lg for lg in logs if codes[cid] and lg[0] in BLOCKING and lg[1] not in codes[cid]]
            (blockers if new else hits).append((cid, result, new or logs))
    # the summary must not claim more FAIL, ERROR or FATAL results than the sections hold (a truncated or doctored report)
    seen = {}
    for sec in report["sections"]:
        for c in sec["checks"]:
            seen[c["result"]] = seen.get(c["result"], 0) + 1
    for status in BLOCKING:
        claimed = report["result"].get(status, 0)
        if claimed > seen.get(status, 0):
            blockers.append((f"(summary {status})", status, [(status, "", f"the summary counts {claimed} {status}, the sections hold {seen.get(status, 0)}")]))
    unfinished = report["result"].get("(not finished)", 0)
    if unfinished:
        blockers.append(("(not finished)", "ERROR", [("ERROR", "", f"{unfinished} check(s) never finished")]))
    failed = {cid for cid, _r, _l in hits}
    stale = sorted(ids - failed)
    return blockers, hits, stale, warns


def fontbakery_command(arg):
    """The argv that runs FontBakery, or None when it is not installed."""
    text = arg or None
    if text is None:
        text = os.environ.get("FONTBAKERY") or None
    if text:
        return shlex.split(text)
    if importlib.util.find_spec("fontbakery") is None:
        return None
    return [sys.executable, "-m", "fontbakery"]


def ttf_name(font, group):
    """The file name the group's font would have, as build.py names the woff2 (`<Family>-VF`, `<Family>-Italic-VF`, or the
    group's `file` key), with `.ttf`. FontBakery reads the STYLE from the file name (an upright font in a file called
    `italic.ttf` fails its italic checks), so the temporary TTF carries the real name, in a folder of its own."""
    cfg = json.loads(pathlib.Path(font).read_text(encoding="utf-8"))
    spec = cfg["groups"][group]
    if spec.get("file"):
        return pathlib.Path(spec["file"]).with_suffix(".ttf").name
    token = cfg["family"].replace(" ", "")
    return f"{token}-Italic-VF.ttf" if spec.get("italic") else f"{token}-VF.ttf"


def build_ttf(font, requirements, group, out):
    """build.py --ttf for one group into a temporary build directory; returns the TTF path."""
    ttf = out / "ttf" / ttf_name(font, group)  # one folder for every group: FontBakery pairs an italic with the roman beside it
    ttf.parent.mkdir(exist_ok=True)
    cmd = [sys.executable, str(HERE / "build.py"), "--font", str(font), "--group", group, "--out-dir", str(out / "build"), "--ttf", str(ttf),
           "--requirements", str(requirements)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"build.py failed for group {group} (exit {r.returncode}):\n{r.stderr[-1500:]}")
    return ttf


def run_group(cmd, profile, ttfs, report_path):
    """Runs FontBakery once on every file of `ttfs`; returns the parsed report. Raises RuntimeError when it wrote none."""
    full = [*cmd, f"check-{profile}", "--skip-network", "-n", "-C", "--json", str(report_path), *map(str, ttfs)]
    pathlib.Path(report_path).unlink(missing_ok=True)  # a report left by an earlier run (--report-dir) must never be read as this run's
    r = subprocess.run(full, capture_output=True, text=True)
    # fontbakery 1.1.0, fontbakery/cli.py: the process exits 0 when no check reached the error threshold (FAIL by default)
    # and 1 when one did (`return 1 if tr.worst_check_status ... >= args.error_code_on.weight`, also 1 for an argument
    # error); 2 is "no subcommand"; the SIGINT handler exits -1. Only 0 and 1 mean "ran"; anything else is a crash.
    if r.returncode not in (0, 1):
        raise RuntimeError(f"FontBakery exited {r.returncode}, not 0 or 1 (cli.py: 0 clean, 1 findings): {' '.join(full)}\n{(r.stderr or r.stdout)[-1500:]}")
    if not pathlib.Path(report_path).is_file():
        raise RuntimeError(f"FontBakery wrote no report (exit {r.returncode}): {' '.join(full)}\n{(r.stderr or r.stdout)[-1500:]}")
    return json.loads(pathlib.Path(report_path).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font", help="the project's font.json (needed unless --ttf is given)")
    ap.add_argument("--requirements", required=True, help="requirements.json, whose accepted_qa_findings are the accepted failures")
    ap.add_argument("--group", action="append", default=[], help="a group to check (repeatable; default: every group in font.json)")
    ap.add_argument("--profile", default="universal", help="the FontBakery profile: check-<profile> (default universal)")
    ap.add_argument("--ttf", help="check this already built TTF instead of building; one file, reported under the name `ttf`")
    ap.add_argument("--fontbakery", help="the command to run instead of `<this python> -m fontbakery` (or env FONTBAKERY)")
    ap.add_argument("--report-dir", help="keep the JSON report in this directory")
    args = ap.parse_args(argv)
    try:
        accepted = load_accepted(args.requirements)
    except (OSError, ValueError) as exc:
        print(f"fontbakery-gate.py: {exc}", file=sys.stderr)
        return 1
    cmd = fontbakery_command(args.fontbakery)
    if cmd is None:
        print("fontbakery-gate.py: SKIPPED, NOT PASSED: fontbakery is not installed in this interpreter "
              f"({sys.executable}); install the dev requirements: .venv/bin/pip install -r requirements-dev.txt. "
              "Phase 7's gate holds only when this ran, or the operator waived it in writing.", file=sys.stderr)
        return EXIT_NOT_INSTALLED
    if not args.ttf and not args.font:
        ap.error("--font is required unless --ttf is given")
    if args.ttf:
        groups = ["ttf"]
    else:
        font = pathlib.Path(args.font).resolve()
        try:
            groups = args.group or list(json.loads(font.read_text(encoding="utf-8"))["groups"])
        except (OSError, ValueError, KeyError) as exc:
            print(f"fontbakery-gate.py: cannot read the groups of {args.font}: {exc}", file=sys.stderr)
            return 1
    status, used = 0, set()
    label = "+".join(groups)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        keep = pathlib.Path(args.report_dir).resolve() if args.report_dir else tmp
        keep.mkdir(parents=True, exist_ok=True)
        try:
            # ONE FontBakery run over every group's TTF: some checks are about the family (an italic must find its roman,
            # `opentype/STAT/ital_axis`), and a run per file would report each italic as missing its roman.
            req_path = pathlib.Path(args.requirements).resolve()
            ttfs = [pathlib.Path(args.ttf).resolve()] if args.ttf else [build_ttf(font, req_path, g, tmp) for g in groups]
            report = run_group(cmd, args.profile, ttfs, keep / f"fontbakery-{args.profile}-{label}.json")
            blockers, hits, _stale, warns = judge(report, accepted)
        except (RuntimeError, ValueError, KeyError, OSError) as exc:
            print(f"fontbakery-gate.py: {label}: {exc}", file=sys.stderr)
            return 1
        counts = ", ".join(f"{k} {v}" for k, v in sorted(report["result"].items()))
        for cid, result, logs in hits:
            reason = next(a["reason"] for a in accepted if a["id"] == cid)
            print(f"ACCEPTED {label}: {cid} {result}: {reason}")
            used.add(cid)
        for cid in warns:
            print(f"WARN {label}: {cid} (does not fail the gate)")
        for cid, result, logs in blockers:
            print(f"{result} {label}: {cid} is not in accepted_qa_findings")
            for st, code, msg in logs:
                print(f"    {st} [{code}] {' '.join(msg.split())[:300]}")
        print(f"FONTBAKERY GATE {args.profile} {label}: {'FAILED' if blockers else 'ok'}: {len(blockers)} unaccepted, {len(hits)} accepted ({counts})")
        if blockers:
            status = 1
    for a in accepted:
        if a["id"] not in used:
            print(f"STALE: {a['id']} is accepted but did not fail in this run; delete it from accepted_qa_findings, "
                  "unless a run on another set of groups needs it")
    return status


if __name__ == "__main__":
    sys.exit(main())
