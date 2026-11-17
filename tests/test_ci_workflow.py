"""The CI workflow runs the mutation harness and builds every fixture, not only the neutral one.

WHAT IT'S FOR: re-review finding code-b F010. The `test` job built the neutral example and ran the font
suite on it; the `chrome` job ran `smoke.sh --full --from 6`, which skips steps 1-5 (the export and build of
all three fixtures, the reproducibility check, the font suite and `mutate.py`). So CI could pass with the
precedent fixtures broken and every guard decorative. The workflow cannot be executed here (it has never run
on GitHub, see CHANGELOG), so this reads the file: a check on text, stated as such, kept because the text is
what GitHub runs. The `test` job must run `scripts/smoke.sh` without `--from`, which is steps 1-7.
"""
import re

import pytest
from conftest import REPO

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"


def job_text(name):
    text = WORKFLOW.read_text(encoding="utf-8")
    m = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z]+:\n|\Z)", text, re.S | re.M)
    assert m, f"no job named {name} in ci.yml"
    return m.group(1)


def test_the_test_job_runs_the_smoke_script_from_step_one():
    """Mutation watched red: `--from 6` added to the test job's smoke.sh line; the line removed."""
    job = job_text("test")
    runs = [ln.strip() for ln in job.splitlines() if "scripts/smoke.sh" in ln]
    assert runs, "the test job never runs scripts/smoke.sh, so mutate.py and the precedent fixture builds are not in CI"
    assert all("--from" not in ln for ln in runs), f"the test job skips smoke steps: {runs}"


def test_the_chrome_job_still_runs_the_browser_steps():
    job = job_text("chrome")
    assert "scripts/smoke.sh --full" in job, "the chrome job must run the browser steps of smoke.sh"


def test_the_test_job_installs_fribidi_on_macos_before_pip_and_asserts_raqm():
    """The first macOS CI run failed at smoke step 2b: diff.py refused because the runner's Pillow reported no raqm (the wheel carries the engine
    and loads libfribidi at run time; a bare runner has none). The `test` job must install fribidi on macOS BEFORE the pip install, and must
    assert `features.check('raqm')` after it, so a regression names its cause instead of failing a later step. A check on the workflow's text,
    stated as such. Mutations watched red: the brew step removed; moved after the pip install; the `if: runner.os == 'macOS'` condition removed
    (it would fail on Ubuntu, which has no brew); the assertion removed."""
    job = job_text("test")
    brew = job.find("brew install fribidi")
    pip = job.find("pip install -r requirements-dev.txt")
    assert brew != -1, "the test job never installs fribidi, so the macOS Pillow has no raqm and smoke step 2b fails"
    assert 0 < brew < pip, "fribidi must be installed before pip install (and the pip install must exist)"
    step = job[job.rfind("- name:", 0, brew):brew]
    assert "runner.os == 'macOS'" in step, f"the fribidi step must be macOS only (Ubuntu has no brew): {step!r}"
    assert "assert features.check('raqm')" in job[pip:], "the test job never asserts (not just prints) the raqm feature after the install"


RECORD = REPO / ".github" / "workflows" / "record-baseline.yml"


def test_the_record_baseline_workflow_is_manual_and_records_both_trees_on_linux_nodes_20_and_22():
    """The Linux digests the compat fixture needs are recorded by a workflow somebody runs by hand: `workflow_dispatch`, plus a pull request
    that touches the generator (workflow_dispatch needs the file on the default branch; --merge refuses a head entry), never `push`, ubuntu, node 20 and 22, a
    worktree at 0fc4314 built with `--repo` (the guard then holds in the worktree), the current head's digests with `--print`, and one artifact
    per node. A check on the workflow's text, stated as such. Mutations watched red: a `push:` trigger added; `--repo` dropped; the `--print`
    step removed; node 22 removed; the artifact upload removed."""
    text = RECORD.read_text(encoding="utf-8")
    on = re.search(r"^on:\n(.*?)(?=^[a-z]+:)", text, re.S | re.M).group(1)
    lines = [ln.strip() for ln in on.splitlines() if ln.strip()]
    assert lines[0] == "workflow_dispatch:" and "push:" not in lines, f"the triggers must be workflow_dispatch and pull_request, never push: {on!r}"
    assert lines[1:3] == ["pull_request:", "paths:"] and "- scripts/gen.js" in lines and "- tests/baseline_digest.py" in lines, \
        f"a pull request run must be limited to the generator and the tool: {on!r}"
    assert "runs-on: ubuntu-latest" in text and "node: [20, 22]" in text, "the workflow must run on ubuntu with node 20 and 22"
    assert "git worktree add ../baseline-0.1.0 0fc4314" in text, "no worktree at 0fc4314"
    assert re.search(r"--record --rev 0fc4314 --repo \.\./baseline-0\.1\.0 --out entry-baseline\.json", text), "the baseline is not recorded from the worktree"
    assert "--print --out entry-head.json" in text, "the current head's digests are not computed"
    assert "upload-artifact" in text and "entry-baseline.json" in text and "entry-head.json" in text, "no artifact carries both entries"


def test_every_workflow_parses_as_yaml():
    """GitHub rejects a workflow that is not valid YAML before running anything, and a plain scalar such as `run: python -c "...; assert x, 'a: b'"`
    (a colon and a space inside) is the easy way to write one (this very file's first raqm step). PyYAML comes with fontbakery in
    requirements-dev.txt, so CI runs this; without it the test skips and says so. Mutation watched red: that step put back."""
    yaml = pytest.importorskip("yaml", reason="PyYAML is not installed (it comes with fontbakery in requirements-dev.txt)")
    for path in sorted((REPO / ".github" / "workflows").glob("*.yml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            pytest.fail(f"{path.name} is not valid YAML: {exc}")
        assert isinstance(doc, dict) and "jobs" in doc, f"{path.name} has no jobs"
