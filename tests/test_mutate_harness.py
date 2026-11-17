"""The mutation harness's verdict logic, fed crafted pytest output.

WHAT IT'S FOR: re-review finding code-a F008. The harness's rule (d) says every expected text must appear
in the assertion lines of the test it belongs to, but the first stricter harness searched one combined
string of every failure's `E` lines, so a mutation naming two tests with a text each was RED when each
test had failed on the OTHER test's assertion. These tests run the two pure functions of
scripts/tests/mutate.py on pytest output shaped as pytest prints it (`-q -rfE`), including the one-underscore
header pytest gives a long parametrised test name, which the first section pattern did not read.
"""
import importlib.util
import pathlib
import sys

from conftest import REPO

spec = importlib.util.spec_from_file_location("mutate", REPO / "scripts" / "tests" / "mutate.py")
mutate = importlib.util.module_from_spec(spec)
sys.modules["mutate"] = mutate
spec.loader.exec_module(mutate)

OUTPUT = """\
FF                                                                       [100%]
=================================== FAILURES ===================================
_________________________________ test_alpha __________________________________
    def test_alpha():
>       assert 1 == 2, "beta's text"
E       AssertionError: beta's text
E       assert 1 == 2
_ test_beta_with_a_name_long_enough_for_pytest_to_pad_with_one_underscore[roman-DisplayBold] _
    def test_beta_with_a_name_long_enough_for_pytest_to_pad_with_one_underscore(p):
>       assert p == "zzz", "alpha's text"
E       AssertionError: alpha's text
E       assert 'roman-DisplayBold' == 'zzz'
=========================== short test summary info ============================
FAILED t.py::test_alpha - AssertionError: beta's text
FAILED t.py::test_beta_with_a_name_long_enough_for_pytest_to_pad_with_one_underscore[roman-DisplayBold] - AssertionError
2 failed in 0.10s
"""
LONG = "test_beta_with_a_name_long_enough_for_pytest_to_pad_with_one_underscore"


def test_assertion_lines_are_split_per_test_including_a_one_underscore_header():
    """Mutation watched red: the section pattern requiring three underscores each side (the long name's
    section is then not read and its lines land under test_alpha)."""
    by_test = mutate.assertion_lines_by_test(OUTPUT)
    assert set(by_test) == {"test_alpha", LONG}, sorted(by_test)
    assert by_test["test_alpha"] == "E       AssertionError: beta's text\nE       assert 1 == 2"
    assert "alpha's text" in by_test[LONG] and "beta's text" not in by_test[LONG]


def test_a_text_found_only_in_the_other_tests_section_is_unproven_not_red():
    """The F008 case: two tests, a text each, each test failing on the other's assertion. The combined-string
    rule said RED; the per-test rule says UNPROVEN naming the text and the test. Mutation watched red:
    `missing` computed against the concatenation of every test's lines."""
    m = mutate.Mutation("x", ["test_alpha", LONG], lambda: None, expect={"test_alpha": "alpha's text", LONG: "beta's text"})
    by_test = mutate.assertion_lines_by_test(OUTPUT)
    verdict, detail = mutate.judge_tests(m, 1, ["test_alpha", LONG], [], by_test)
    assert verdict == "UNPROVEN", (verdict, detail)
    assert "alpha's text" in detail and "not in test_alpha's assertion lines" in detail, detail
    right = mutate.Mutation("y", ["test_alpha", LONG], lambda: None, expect={"test_alpha": "beta's text", LONG: "alpha's text"})
    assert mutate.judge_tests(right, 1, ["test_alpha", LONG], [], by_test)[0] == "RED"


def test_a_plain_expect_must_appear_in_every_named_test():
    m = mutate.Mutation("z", ["test_alpha", LONG], lambda: None, expect="AssertionError")
    by_test = mutate.assertion_lines_by_test(OUTPUT)
    assert mutate.judge_tests(m, 1, ["test_alpha", LONG], [], by_test)[0] == "RED"
    m = mutate.Mutation("w", ["test_alpha", LONG], lambda: None, expect="alpha's text")
    verdict, detail = mutate.judge_tests(m, 1, ["test_alpha", LONG], [], by_test)
    assert verdict == "UNPROVEN" and "test_alpha" in detail


def test_the_other_verdicts_still_hold():
    m = mutate.Mutation("v", ["test_alpha"], lambda: None, expect="beta's text")
    by_test = mutate.assertion_lines_by_test(OUTPUT)
    assert mutate.judge_tests(m, 0, [], [], {})[0] == "GREEN"
    assert mutate.judge_tests(m, 1, ["test_alpha"], ["t.py::test_other"], by_test)[0] == "UNPROVEN"
    assert mutate.judge_tests(m, 1, [LONG], [], by_test) == ("UNPROVEN", "named test(s) did not FAIL: ['test_alpha']; failed: ['" + LONG + "']")
    assert mutate.judge_tests(m, 1, ["test_alpha"], [], by_test)[0] == "RED"


def test_a_dict_expect_must_name_exactly_the_tests():
    import pytest
    with pytest.raises(AssertionError, match="expect names"):
        mutate.Mutation("u", ["test_alpha"], lambda: None, expect={"test_other": "x"})
    assert pathlib.Path(mutate.__file__).name == "mutate.py"


def test_a_project_with_one_italic_group_still_gets_the_italic_and_stat_mutations(tmp_path):
    """The derivation took the first group as `roman` even when it was italic, then looked for ANOTHER italic group, so
    a project with a single italic group got `italic = None` and `stat-fallback` (and the italic mutations) were SKIPPED;
    `stat-name` also read only that group's instances. Built here from a copy of the neutral example with the roman group
    removed from font.json and requirements.json. Weakest mutation watched red: the `and g != roman` filter put back in
    the `italics` list."""
    import json
    import shutil
    work = tmp_path / "neutral"
    shutil.copytree(REPO / "examples" / "neutral", work)
    font = json.loads((work / "font.json").read_text())
    req = json.loads((work / "requirements.json").read_text())
    for cfg in (font, req):
        del cfg["groups"]["roman"]
    (work / "font.json").write_text(json.dumps(font))
    (work / "requirements.json").write_text(json.dumps(req))
    h = mutate.Harness(work / "font.json", work / "requirements.json", "none")
    try:
        by_name = {m.name.split(":")[0]: m for m in mutate.mutations(h)}
    finally:
        shutil.rmtree(h.pristine)
    for name in ("stat-fallback", "stat-name", "italic-angle", "italic-bits", "italic-tick"):
        assert by_name[name].skip is None, f"{name} was skipped on a project whose only group is italic: {by_name[name].skip}"
