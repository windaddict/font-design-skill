"""scripts/fontbakery-gate.py: what it blocks, what it accepts, and what it does when FontBakery is not there.

WHAT IT'S FOR: the gate is the one check on the font FORMAT (code pages, name platforms, STAT, dropout
control, metrics that agree) that the font suite does not make. A gate that passes by accident is worse than
none, because phase 7 then reads "QA ran" as "QA found nothing". The decision logic (`judge`) is a pure
function fed crafted reports shaped like FontBakery's own JSON; the script is then executed end to end against a
stub `fontbakery` command that writes a canned report, and once against the real FontBakery on the neutral
example (skipped LOUDLY, never passed, when it is not installed). Mutations watched red are named in each
docstring.
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest
from conftest import REPO

GATE = REPO / "scripts" / "fontbakery-gate.py"
NEUTRAL = REPO / "examples" / "neutral"

spec = importlib.util.spec_from_file_location("fontbakery_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def check(cid, result, logs=()):
    """One FontBakery JSON check entry, shaped like the real report (key[1] is `<FontBakeryCheck:id>`)."""
    entries = logs or [(result, "x", "m")]
    return {"key": ["<Section: x>", f"<FontBakeryCheck:{cid}>", [["font", 0]]], "result": result,
            "logs": [{"status": st, "message": {"code": code, "message": msg}} for st, code, msg in entries]}


def report(*checks, unfinished=0):
    counts = {}
    for c in checks:
        counts[c["result"]] = counts.get(c["result"], 0) + 1
    if unfinished:
        counts["(not finished)"] = unfinished
    return {"result": counts, "sections": [{"key": "s", "result": {}, "checks": list(checks)}]}


def acc(*ids):
    return [{"id": i, "reason": f"reason for {i}"} for i in ids]


# ---- judge(): pure -------------------------------------------------------------------------------------------------
def test_an_unaccepted_fail_blocks_and_an_accepted_one_does_not():
    """Mutation watched red: `cid in ids` replaced by True (everything accepted)."""
    rep = report(check("case_mapping", "FAIL"), check("smart_dropout", "FAIL"))
    blockers, hits, stale, _warns = gate.judge(rep, acc("case_mapping"))
    assert [b[0] for b in blockers] == ["smart_dropout"] and [h[0] for h in hits] == ["case_mapping"] and stale == []


@pytest.mark.parametrize("result", ["FAIL", "ERROR", "FATAL"])
def test_fail_error_and_fatal_all_block(result):
    """Mutation watched red: ERROR (then FATAL) removed from BLOCKING. An ERROR is FontBakery failing to run a
    check, which the first fixture produced; a gate that passes it has not looked."""
    blockers, _h, _s, _w = gate.judge(report(check("c1", result)), [])
    assert [b[0] for b in blockers] == ["c1"]


def test_a_warn_does_not_block():
    """Mutation watched red: the WARN branch removed and WARN added to the blocking set."""
    blockers, _h, _s, warns = gate.judge(report(check("linegaps", "WARN"), check("x", "INFO"), check("y", "SKIP"), check("z", "PASS")), [])
    assert blockers == [] and warns == ["linegaps"]


def test_an_unfinished_report_blocks():
    """`(not finished)` in the result counts means FontBakery stopped before every check ran. Mutation watched red: the test deleted."""
    blockers, _h, _s, _w = gate.judge(report(check("a", "PASS"), unfinished=2), [])
    assert [b[0] for b in blockers] == ["(not finished)"]


@pytest.mark.parametrize("first,second", [("WARN", "FAIL"), ("FAIL", "WARN"), ("ERROR", "WARN"), ("WARN", "ERROR"), ("FAIL", "ERROR"), ("ERROR", "FAIL")])
def test_one_check_id_reported_for_two_files_takes_the_worst_result(first, second):
    """A family run reports a per-file check once per file. WARN in one file and FAIL in the other must block,
    whichever file comes first, and an ERROR outranks a FAIL (it is the more severe). Weakest mutation watched red:
    the worst-result tuple in judge() reordered to ("FATAL", "ERROR", "WARN", "FAIL"), which let WARN beat FAIL and
    hid the failure while every single-file test stayed green."""
    blockers, hits, _s, warns = gate.judge(report(check("c", first), check("c", second)), [])
    assert [b[0] for b in blockers] == ["c"] and warns == [] and hits == [], (blockers, warns)
    assert blockers[0][1] == next(r for r in ("FATAL", "ERROR", "FAIL", "WARN") if r in (first, second))


def test_a_report_whose_summary_claims_more_failures_than_its_sections_hold_blocks():
    """`{"result": {"FAIL": 1}, "sections": []}` produced no blocker: findings() read only the sections. The summary's
    FAIL, ERROR and FATAL counts may not exceed what the sections contain (a truncated or doctored report). Weakest
    mutation watched red: the reconciliation loop in judge() removed; the comparison made only when the sections are empty
    (`and not seen`), which the non-empty case below catches."""
    for status in ("FAIL", "ERROR", "FATAL"):
        blockers, _h, _s, _w = gate.judge({"result": {status: 1}, "sections": []}, [])
        assert [b[0] for b in blockers] == [f"(summary {status})"], (status, blockers)
    assert gate.judge(report(check("a", "PASS")), [])[0] == []  # an honest report still passes
    # a NON-empty sections list does not excuse the summary: it claims two FAILs, the sections hold one (the accepted one)
    short = {"result": {"FAIL": 2}, "sections": [{"checks": [check("a", "FAIL")]}]}
    blockers, hits, _s, _w = gate.judge(short, acc("a"))
    assert [b[0] for b in blockers] == ["(summary FAIL)"] and [h[0] for h in hits] == ["a"], (blockers, hits)


def test_accepted_codes_limit_which_failures_of_a_check_are_accepted():
    """An accepted id used to accept ANY failure of that check. With `codes`, a FAIL message whose code is not listed blocks
    (and only that message is shown), a listed code is accepted, and an entry without `codes` still takes the id alone.
    Weakest mutation watched red: the `lg[1] not in codes[cid]` test dropped, so the id alone is matched again."""
    rep = report(check("case_mapping", "FAIL", [("FAIL", "missing-case-counterparts", "m"), ("FAIL", "a-new-kind", "n")]))
    blockers, hits, _s, _w = gate.judge(rep, [{"id": "case_mapping", "reason": "r", "codes": ["missing-case-counterparts"]}])
    assert [b[0] for b in blockers] == ["case_mapping"] and [lg[1] for lg in blockers[0][2]] == ["a-new-kind"] and hits == []
    blockers, hits, _s, _w = gate.judge(rep, [{"id": "case_mapping", "reason": "r", "codes": ["missing-case-counterparts", "a-new-kind"]}])
    assert blockers == [] and [h[0] for h in hits] == ["case_mapping"]
    blockers, hits, _s, _w = gate.judge(rep, acc("case_mapping"))
    assert blockers == [] and len(hits) == 1
    # ERROR and FATAL messages are held to the codes too, not only FAIL. Mutation that survived until this case was
    # added (coordinator, 2026-11-16): `lg[0] in BLOCKING` narrowed to `lg[0] == "FAIL"`.
    for status in ("ERROR", "FATAL"):
        rep = report(check("case_mapping", status, [("FAIL", "missing-case-counterparts", "m"), (status, "a-new-kind", "n")]))
        blockers, hits, _s, _w = gate.judge(rep, [{"id": "case_mapping", "reason": "r", "codes": ["missing-case-counterparts"]}])
        assert [lg[1] for lg in blockers[0][2]] == ["a-new-kind"] and hits == [], status


def test_the_match_is_the_whole_check_id_not_a_prefix():
    """`opentype/code_pages` is not `opentype`, and an accepted `case_mapping` does not accept `case_mapping_x`.
    Mutation watched red: `cid in ids` replaced by a startswith over the accepted ids."""
    blockers, _h, _s, _w = gate.judge(report(check("opentype/code_pages", "FAIL"), check("case_mapping_x", "FAIL")), acc("opentype", "case_mapping"))
    assert sorted(b[0] for b in blockers) == ["case_mapping_x", "opentype/code_pages"]


def test_an_accepted_check_that_no_longer_fails_is_stale():
    """Mutation watched red: the stale list always empty."""
    _b, _h, stale, _w = gate.judge(report(check("a", "PASS")), acc("a"))
    assert stale == ["a"]


def test_findings_reads_the_check_id_from_the_key():
    """The id is what FontBakery prints, `<FontBakeryCheck:opentype/code_pages>` without the brackets. Mutation
    watched red: the regex group widened to the whole key string."""
    assert gate.findings(report(check("opentype/code_pages", "FAIL")))[0][0] == "opentype/code_pages"
    with pytest.raises(ValueError):
        gate.findings({"nope": 1})


# ---- load_accepted(): the list is validated ----------------------------------------------------------------------------
def write_req(tmp_path, **kw):
    p = tmp_path / "requirements.json"
    p.write_text(json.dumps(kw), encoding="utf-8")
    return p


def test_requirements_without_the_key_are_refused_not_read_as_empty(tmp_path):
    """Mutation watched red: a missing key returning []. The omission has to be a decision."""
    with pytest.raises(ValueError, match="no accepted_qa_findings"):
        gate.load_accepted(write_req(tmp_path, family="x"))
    assert gate.load_accepted(write_req(tmp_path, accepted_qa_findings=[])) == []


@pytest.mark.parametrize("entries,why", [
    ([{"id": "a"}], "keys id and reason"),
    ([{"id": "a", "reason": "r", "code": "c"}], "optionally codes"),
    ([{"id": "a", "reason": "r", "codes": []}], "non-empty list"),
    ([{"id": "a", "reason": "r", "codes": ["x", ""]}], "non-empty list"),
    ([{"id": "a", "reason": "r", "codes": "x"}], "non-empty list"),
    ([{"id": "", "reason": "r"}], "non-empty"),
    ([{"id": "a", "reason": "  "}], "non-empty"),
    ([{"id": "a", "reason": "r"}, {"id": "a", "reason": "s"}], "twice"),
    ("case_mapping", "list"),
])
def test_a_malformed_accepted_list_is_refused(tmp_path, entries, why):
    """Mutations watched red, one per row: the key check dropped, the emptiness check dropped, the duplicate check dropped."""
    with pytest.raises(ValueError, match=why):
        gate.load_accepted(write_req(tmp_path, accepted_qa_findings=entries))


# ---- the script, end to end, against a stub fontbakery ----------------------------------------------------------------------
STUB = """import json, os, sys
a = sys.argv[1:]
out = a[a.index("--json") + 1]
with open(os.environ["STUB_ARGV"], "w") as f:
    json.dump(a, f)
if os.environ.get("STUB_WRITE", "1") == "1":
    json.dump(json.load(open(os.environ["STUB_REPORT"])), open(out, "w"))
if os.environ.get("STUB_EXIT") == "SIGTERM":
    import signal
    os.kill(os.getpid(), signal.SIGTERM)  # a real death by signal: the parent sees returncode -15
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
"""


@pytest.fixture
def stub(tmp_path):
    (tmp_path / "stub.py").write_text(STUB, encoding="utf-8")
    ttf = tmp_path / "x.ttf"
    ttf.write_bytes(b"not a font; the stub never opens it")

    def run(rep, accepted, extra=(), profile=None, env_extra=None):
        (tmp_path / "report.json").write_text(json.dumps(rep), encoding="utf-8")
        req = write_req(tmp_path, accepted_qa_findings=accepted)
        env = {**os.environ, "STUB_REPORT": str(tmp_path / "report.json"), "STUB_ARGV": str(tmp_path / "argv.json"), **(env_extra or {})}
        args = [sys.executable, str(GATE), "--requirements", str(req), "--ttf", str(ttf), "--fontbakery", f"{sys.executable} {tmp_path / 'stub.py'}"]
        if profile:
            args += ["--profile", profile]
        r = subprocess.run([*args, *extra], capture_output=True, text=True, env=env)
        argv = json.loads((tmp_path / "argv.json").read_text()) if (tmp_path / "argv.json").exists() else None
        return r, argv
    return run


def test_the_script_exits_one_naming_an_unaccepted_failure(stub):
    """Mutation watched red: main() returning 0 whatever the blockers."""
    r, _argv = stub(report(check("smart_dropout", "FAIL", [("FAIL", "lacks-smart-dropout", "no prep program")])), [])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL ttf: smart_dropout is not in accepted_qa_findings" in r.stdout and "[lacks-smart-dropout]" in r.stdout and "FAILED" in r.stdout, r.stdout


def test_the_script_exits_zero_and_prints_each_acceptance_with_its_reason(stub):
    r, argv = stub(report(check("case_mapping", "FAIL")), acc("case_mapping"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ACCEPTED ttf: case_mapping FAIL: reason for case_mapping" in r.stdout and "FONTBAKERY GATE universal ttf: ok: 0 unaccepted, 1 accepted" in r.stdout, r.stdout
    assert argv[:1] == ["check-universal"] and "--skip-network" in argv and argv[-1].endswith("x.ttf"), argv


def test_a_vendor_profile_accepts_a_deliberate_fstype_with_its_reason(stub):
    """The operator's decision for a proprietary face: fsType 4 is a deliberate non-zero value, which the vendor
    profiles fail (`googlefonts/fstype`); the gate takes it as an accepted finding with the licence as the reason,
    and runs the profile asked for. Mutation watched red: --profile ignored (the stub then sees check-universal)."""
    reason = "the face is licensed to this site only; fsType 4 (Preview & Print) is the deliberate setting"
    rep = report(check("googlefonts/fstype", "FAIL", [("FAIL", "drm", "Bad fsType value")]))
    r, argv = stub(rep, [{"id": "googlefonts/fstype", "reason": reason}], profile="googlefonts")
    assert r.returncode == 0 and reason in r.stdout, r.stdout + r.stderr
    assert argv[0] == "check-googlefonts", argv
    r2, _ = stub(report(check("googlefonts/fstype", "FAIL")), [], profile="googlefonts")
    assert r2.returncode == 1 and "googlefonts/fstype is not in accepted_qa_findings" in r2.stdout


def test_a_stale_report_from_an_earlier_run_is_never_read(stub, tmp_path):
    """With --report-dir an earlier run's report sat at the path the next run writes. FontBakery crashing before it wrote one
    (here: exit 1 with nothing written) made the gate read the old, passing report. The path is removed first, so it is "wrote
    no report" and exit 1. Weakest mutation watched red: the `unlink` before the run removed."""
    keep = tmp_path / "rep"
    keep.mkdir()
    (keep / "fontbakery-universal-ttf.json").write_text(json.dumps(report(check("a", "PASS"))), encoding="utf-8")
    r, _argv = stub(report(check("a", "PASS")), [], extra=["--report-dir", str(keep)], env_extra={"STUB_WRITE": "0", "STUB_EXIT": "1"})
    assert r.returncode == 1 and "wrote no report" in r.stderr, r.stdout + r.stderr


@pytest.mark.parametrize("code", [2, 3, 255])
def test_an_exit_code_other_than_zero_or_one_is_a_crash_even_with_a_report(stub, code):
    """fontbakery 1.1.0 (fontbakery/cli.py) exits 0 clean or 1 with findings (or a bad argument); 2 is "no subcommand" and its
    SIGINT handler exits -1. A process that wrote a report and then exited 2 did not finish normally. Weakest mutation
    watched red: the allowed codes `(0, 1)` widened to `(0, 1, 2)` (code 2 row) or the check removed (all rows)."""
    r, _argv = stub(report(check("a", "PASS")), [], env_extra={"STUB_EXIT": str(code)})
    assert r.returncode == 1 and "FontBakery exited" in r.stderr, r.stdout + r.stderr


def test_a_fontbakery_killed_by_a_signal_is_a_crash(stub):
    """A process that dies from a signal reports a NEGATIVE return code in Python (SIGTERM is -15); the old `-1` row of the
    parametrisation actually passed 255. The stub really kills itself after writing a good report. Weakest mutation
    watched red: the check allowing negative codes (`r.returncode not in (0, 1) and r.returncode >= 0`)."""
    r, _argv = stub(report(check("a", "PASS")), [], env_extra={"STUB_EXIT": "SIGTERM"})
    assert r.returncode == 1 and "FontBakery exited -15" in r.stderr, r.stdout + r.stderr


def test_a_stale_acceptance_is_reported_and_does_not_fail(stub):
    r, _argv = stub(report(check("a", "PASS")), acc("a"))
    assert r.returncode == 0 and "STALE: a is accepted but did not fail in this run" in r.stdout, r.stdout


def test_a_report_that_is_not_a_fontbakery_report_exits_one(stub):
    r, _argv = stub({"hello": 1}, [])
    assert r.returncode == 1 and "not a FontBakery report" in r.stderr, r.stdout + r.stderr


def test_fontbakery_not_installed_is_skipped_not_passed_with_its_own_exit_code(tmp_path):
    """sys.modules['fontbakery'] = None is what an environment without the package looks like to find_spec().
    Mutation watched red: the exit code 3 changed to 0 (a skipped gate would read as a pass)."""
    req = write_req(tmp_path, accepted_qa_findings=[])
    code = ("import runpy, sys; sys.modules['fontbakery'] = None; sys.argv = ['g', '--requirements', %r, '--ttf', %r]; "
            "runpy.run_path(%r, run_name='__main__')" % (str(req), str(tmp_path / "x.ttf"), str(GATE)))
    env = {k: v for k, v in os.environ.items() if k != "FONTBAKERY"}
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert r.returncode == 3, r.stdout + r.stderr
    assert "SKIPPED, NOT PASSED: fontbakery is not installed" in r.stderr and "pip install -r requirements-dev.txt" in r.stderr, r.stderr


def test_the_gate_builds_the_groups_ttf_and_hands_that_file_to_fontbakery(tmp_path):
    """No --ttf: the gate runs build.py --ttf for the group into a temp directory (named as the woff2 is,
    `<Family>-Italic-VF.ttf`, because FontBakery reads the style from the file name) and the stub receives the path
    of a real variable TTF (sfnt version 0x00010000 with an fvar table), not the woff2 and not nothing. Slow (one
    group is built), and the project's out_dir is left untouched. Mutation watched red: the build step passing
    --ttf nowhere; the TTF named after the group (`italic.ttf`, which FontBakery reads as an upright font)."""
    (tmp_path / "stub.py").write_text("import json, os, sys\na = sys.argv[1:]\nout = a[a.index('--json') + 1]\n"
                                      "d = open(a[-1], 'rb').read()\nopen(os.environ['STUB_SEEN'], 'w').write(a[-1] + '|' + d[:4].hex() + '|' + str(b'fvar' in d))\n"
                                      "json.dump({'result': {'PASS': 1}, 'sections': [{'checks': []}]}, open(out, 'w'))\n", encoding="utf-8")
    out_dir = NEUTRAL / "out"  # may not exist (a fresh clone): the gate builds into a temp folder and must not create it
    before = sorted(p.name for p in out_dir.iterdir()) if out_dir.is_dir() else None
    env = {**os.environ, "STUB_SEEN": str(tmp_path / "seen.txt")}
    r = subprocess.run([sys.executable, str(GATE), "--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--group", "italic",
                        "--fontbakery", f"{sys.executable} {tmp_path / 'stub.py'}"], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    path, magic, has_fvar = (tmp_path / "seen.txt").read_text().split("|")
    assert path.endswith("Sampler-Italic-VF.ttf") and magic == "00010000" and has_fvar == "True", (path, magic, has_fvar)
    after = sorted(p.name for p in out_dir.iterdir()) if out_dir.is_dir() else None
    assert after == before, "the gate wrote into the project's out_dir"


# ---- the real FontBakery on the neutral example --------------------------------------------------------------------------------
def real_fontbakery_or_skip():
    if importlib.util.find_spec("fontbakery") is None:
        pytest.skip("SKIPPED, NOT PASSED: fontbakery is not installed; `.venv/bin/pip install -r requirements-dev.txt`. "
                    "The CI job installs it and runs this test.")


@pytest.fixture(scope="module")
def neutral_ttf(tmp_path_factory):
    real_fontbakery_or_skip()
    out = tmp_path_factory.mktemp("fbttf")
    ttf = out / "roman.ttf"
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "build.py"), "--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"),
                        "--group", "roman", "--out-dir", str(out / "b"), "--ttf", str(ttf)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1500:]
    return ttf


def run_real(ttf, requirements, tmp_path):
    cmd = [sys.executable, str(GATE), "--requirements", str(requirements), "--ttf", str(ttf), "--report-dir", str(tmp_path / "rep")]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_the_real_fontbakery_passes_the_neutral_family_with_its_recorded_acceptances(neutral_ttf, tmp_path):
    """The whole path, both groups: build.py writes each group's TTF, ONE FontBakery run reads the roman and the
    italic together, and every FAIL is one the neutral requirements accept (`case_mapping`: seven lowercase accented letters
    without capitals; `opentype/STAT/ital_axis`: no `ital` axis; the one-axis italic beside the two-axis roman, twice;
    the roman's and the italic's glyph extents differing by a unit). Run on the roman alone the family checks are
    skipped, so those acceptances read STALE there. Mutation watched red: a FontBakery run per file
    (the italic then reports `missing-roman`, a finding the family run does not have). Slow: two builds."""
    cmd = [sys.executable, str(GATE), "--font", str(NEUTRAL / "font.json"), "--requirements", str(NEUTRAL / "requirements.json"), "--report-dir", str(tmp_path / "rep")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("ACCEPTED roman+italic: case_mapping FAIL") == 1, "a check FontBakery reports once per file is listed once"
    assert "ACCEPTED roman+italic: case_mapping FAIL" in r.stdout and "ACCEPTED roman+italic: opentype/STAT/ital_axis FAIL" in r.stdout, r.stdout
    assert "FONTBAKERY GATE universal roman+italic: ok: 0 unaccepted, 5 accepted" in r.stdout and "STALE" not in r.stdout, r.stdout


def test_the_real_fontbakery_fails_the_neutral_example_when_nothing_is_accepted(neutral_ttf, tmp_path):
    """The same font with the accepted list emptied: the case_mapping FAIL is now a blocker, so the gate can fail
    on a real report and not only on a crafted one. (Adversarial input: the requirements are the neutral file with
    `accepted_qa_findings` set to [], nothing else changed.)"""
    req = json.loads((NEUTRAL / "requirements.json").read_text(encoding="utf-8"))
    req["accepted_qa_findings"] = []
    p = tmp_path / "requirements.json"
    p.write_text(json.dumps(req), encoding="utf-8")
    r = run_real(neutral_ttf, p, tmp_path)
    assert r.returncode == 1 and "FAIL ttf: case_mapping is not in accepted_qa_findings" in r.stdout and "missing-case-counterparts" in r.stdout, r.stdout + r.stderr
