"""The CI workflow runs the mutation harness and builds every fixture, not only the neutral one.

WHAT IT'S FOR: re-review finding code-b F010. The `test` job built the neutral example and ran the font
suite on it; the `chrome` job ran `smoke.sh --full --from 6`, which skips steps 1-5 (the export and build of
all three fixtures, the reproducibility check, the font suite and `mutate.py`). So CI could pass with the
precedent fixtures broken and every guard decorative. The workflow cannot be executed here (it has never run
on GitHub, see CHANGELOG), so this reads the file: a check on text, stated as such, kept because the text is
what GitHub runs. The `test` job must run `scripts/smoke.sh` without `--from`, which is steps 1-7.
"""
import re

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
