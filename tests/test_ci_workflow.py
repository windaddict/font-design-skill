"""The CI workflow runs the mutation harness and builds every fixture, not only the neutral one.

WHAT IT'S FOR: re-review finding code-b F010. The `test` job built the neutral example and ran the font
suite on it; the `chrome` job ran `smoke.sh --full --from 6`, which skips steps 1-5 (the export and build of
all three fixtures, the reproducibility check, the font suite and `mutate.py`). So CI could pass with the
precedent fixtures broken and every guard decorative. The workflow cannot be executed by the suite (it runs only on
GitHub), so this reads the file: a check on text, stated as such, kept because the text is
what GitHub runs. The `test` job must run `scripts/smoke.sh` without `--from`, which is steps 1-7.
"""
import os
import re
import subprocess

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


def test_the_record_baseline_workflow_is_manual_and_records_both_trees_on_both_oses_nodes_20_and_22():
    """The Linux and macOS digests the compat fixture needs are recorded by a workflow somebody runs by hand: `workflow_dispatch`, plus a pull
    request that touches the generator (workflow_dispatch needs the file on the default branch; --merge refuses a head entry), never `push`,
    ubuntu and macos, node 20 and 22, a worktree at the baseline commit (test_backward_compat.BASELINE_REV, a real sha) built with `--repo`
    (the guard then holds in the worktree), the current head's digests with `--print`, and one artifact per leg. A check on the workflow's
    text, stated as such. Mutations watched red: a `push:` trigger added; `--repo` dropped; the `--print` step removed; node 22 removed; the
    artifact upload removed; (0.5.0) macos removed; the worktree at another commit than the test's; the genre-digest step removed; its
    python piped into tee; pytest dropped from the install; the compare step's pipefail removed."""
    from test_backward_compat import BASELINE_REV
    text = RECORD.read_text(encoding="utf-8")
    on = re.search(r"^on:\n(.*?)(?=^[a-z]+:)", text, re.S | re.M).group(1)
    lines = [ln.strip() for ln in on.splitlines() if ln.strip()]
    assert lines[0] == "workflow_dispatch:" and "push:" not in lines, f"the triggers must be workflow_dispatch and pull_request, never push: {on!r}"
    assert lines[1:3] == ["pull_request:", "paths:"] and "- scripts/gen.js" in lines and "- tests/baseline_digest.py" in lines, \
        f"a pull request run must be limited to the generator and the tool: {on!r}"
    assert "runs-on: ${{ matrix.os }}" in text and "os: [ubuntu-latest, macos-latest]" in text and "node: [20, 22]" in text, \
        "the workflow must run on ubuntu and macos with node 20 and 22"
    assert "--print --out entry-head.json" in text, "the current head's digests are not computed"
    # 0.5.0: the genre record is keyed by node major too, and the machine that writes it may not run every major (npx was refused on the
    # author's), so each leg prints test_genres.current_digests() into the summary and the artifact; a leg without it leaves the genre
    # test red on that major with no way to record it but a runner. Mutation watched red (2026-11-19): the step removed. Checked before
    # the revision below, so the mutation is observable while the revision is still the placeholder of a tree before its commit
    assert "test_genres.current_digests()" in text and "genre-digests.json" in text, "the legs do not print the genre recipes' digests"
    # that step must not pipe python's output: GitHub runs `run:` with `bash -e` and no pipefail unless `shell: bash` is set, so a
    # failing python at the head of a pipe is masked (re-review of the diff, R4). Mutation watched red: the `| tee` form restored
    step = re.search(r"the genre recipes' outline digests.*?(?=\n      - name:)", text, re.S).group(0)
    assert not re.search(r"python[^\n]*\|", step) and "shell: bash" not in step or "set -o pipefail" in step, \
        f"the genre-digest step pipes python's output without pipefail: {step!r}"
    assert re.search(r"python - > genre-digests\.json <<'PY'", step) and "cat genre-digests.json >> \"$GITHUB_STEP_SUMMARY\"" in step, \
        "the genre digests must be written to the file first, then appended to the summary"
    # the genre-digest step imports tests/test_genres.py, which imports pytest, so the job must install it: the first PR run of 0.5.0
    # failed on every leg with ModuleNotFoundError before any artifact was uploaded. Mutation watched red: `pytest` dropped from the install
    install = re.search(r"- name: install\n(?:\s*#[^\n]*\n)*\s*run: ([^\n]*)", text).group(1)
    assert "pytest" in install.split() or "requirements-dev.txt" in install, f"the record job does not install pytest, which test_genres imports: {install!r}"
    # every step that pipes python into another command sets pipefail (GitHub's default `bash -e` has none). Mutation watched red: the
    # compare step's `set -o pipefail` removed
    for run in re.findall(r"run: \|\n((?:          [^\n]*\n)+)", text):
        if re.search(r"python[^\n]*\|", run):
            assert "set -o pipefail" in run, f"a step pipes python's output without pipefail: {run!r}"
    assert "upload-artifact" in text and "entry-baseline.json" in text and "entry-head.json" in text and text.count("genre-digests.json") >= 2, \
        "no artifact carries both entries and the genre digests"
    assert re.fullmatch(r"[0-9a-f]{7,40}", BASELINE_REV), f"BASELINE_REV is {BASELINE_REV!r}, not a git sha"
    assert f"git worktree add ../baseline {BASELINE_REV}" in text, f"no worktree at {BASELINE_REV}"
    assert re.search(rf"--record --rev {BASELINE_REV} --repo \.\./baseline --out entry-baseline\.json", text), "the baseline is not recorded from the worktree"


def test_every_ci_job_that_runs_the_repo_tests_checks_out_the_full_history():
    """tests/test_r_leg_join.py reads the 0.4.0 generator with `git show 598044b:scripts/gen.js`, so a job that runs the repo tests
    (smoke.sh runs them) needs that commit in its clone. actions/checkout fetches one commit by default, and the first CI run of
    0.5.0's commit C failed six tests in the chrome job on "invalid object name '598044b'" while record-baseline, which already
    fetched everything, passed."""
    doc = load(WORKFLOW)
    suite = [job for job, s in runs(doc) if "smoke.sh" in s["run"] or re.search(r"pytest\b[^\n]*tests/", s["run"])]
    assert {"test", "chrome"} <= set(suite), f"expected the test and chrome jobs to run the suite, found {sorted(set(suite))}"
    for job in sorted(set(suite)):
        checkouts = [s for s in steps(doc, job) if str(s.get("uses", "")).startswith("actions/checkout@")]
        assert len(checkouts) == 1, f"{job}: expected one checkout, found {len(checkouts)}"
        depth = (checkouts[0].get("with") or {}).get("fetch-depth")
        assert depth == 0, f"{job}: its checkout has fetch-depth {depth!r}; the repo tests need the full history (fetch-depth: 0)"


def test_every_workflow_parses_as_yaml():
    """GitHub rejects a workflow that is not valid YAML before running anything, and a plain scalar such as `run: python -c "...; assert x, 'a: b'"`
    (a colon and a space inside) is the easy way to write one (this very file's first raqm step). PyYAML comes with fontbakery in
    requirements-dev.txt, so CI runs this; without it the test skips and says so. Mutation watched red: that step put back."""
    yaml = pytest.importorskip("yaml", reason="PyYAML is not installed (it comes with fontbakery in requirements-dev.txt)")
    for path in sorted([*(REPO / ".github" / "workflows").glob("*.yml"), *(REPO / "templates").glob("*.yml")]):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            pytest.fail(f"{path.name} is not valid YAML: {exc}")
        assert isinstance(doc, dict) and "jobs" in doc, f"{path.name} has no jobs"


def test_the_lint_job_runs_eslint_pinned_and_shellcheck_on_smoke():
    """Issue #3: `npm run check` only proved each file parses. The lint job runs ESLint (eslint.config.js) over
    scripts/*.js and scripts/concepts/*.js and shellcheck over scripts/smoke.sh. ESLint comes through npx, so its
    version must be exact: an unpinned npx resolves whatever is newest on the day, and a new release's rule
    changes would turn CI red on an unchanged tree. Reads the text, as the tests above do. Mutations watched red:
    either run line removed from the lint job; `eslint@10` for the exact version; lint:sh pointed at another file."""
    import json
    job = job_text("lint")
    for script in ("lint:js", "lint:sh"):
        assert f"npm run {script}" in job, f"the lint job never runs npm run {script}"
    scripts = json.loads((REPO / "package.json").read_text(encoding="utf-8"))["scripts"]
    assert re.fullmatch(r"npx --yes eslint@\d+\.\d+\.\d+", scripts["lint:js"]), f"lint:js must pin an exact ESLint: {scripts['lint:js']!r}"
    assert scripts["lint:sh"].split() == ["shellcheck", "scripts/smoke.sh"], scripts["lint:sh"]


# ---- the cross-platform rendering shots as a reusable workflow (docs/plan-reusable-shots.md sections 2-5 and 13; work item C1t) ----
# GitHub runs these files and the suite cannot, so most tests below read the parsed YAML, stated as such in each docstring; the real
# check of what only GitHub executes (which job calls which file, what `uses` resolves to, the matrix) is the skill's pull-request run
# and a site's dispatched run (plan section 9, steps 3 and 4). Three tests EXECUTE the shipped shell instead: run_step() takes a step's
# `run:` text out of the parsed YAML and runs it with bash the way GitHub does, under a controlled environment, with a stub `python`
# on PATH that records its arguments, so the guard, the slot script and the argument building are exercised as code, not matched as text.


REUSABLE = REPO / ".github" / "workflows" / "platform-shots-reusable.yml"
SKILL_CALLER = REPO / ".github" / "workflows" / "platform-shots.yml"
TEMPLATE = REPO / "templates" / "platform-shots.yml"
TOOLS = ("shoot.py", "specimen.py", "compare-shots.py")
SHA_CHECKOUT = {"repository": "${{ job.workflow_repository }}", "ref": "${{ job.workflow_sha }}", "path": "fd", "persist-credentials": False}


def load(path):
    yaml = pytest.importorskip("yaml", reason="PyYAML is not installed (it comes with fontbakery in requirements-dev.txt)")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["on"] = doc.pop(True, doc.get("on"))  # YAML 1.1 reads the bare key `on` as the boolean true
    return doc


def steps(doc, job):
    return doc["jobs"][job]["steps"]


def runs(doc):
    return [(job, s) for job in doc["jobs"] for s in doc["jobs"][job].get("steps", []) if "run" in s]


def step(doc, job, name_fragment):
    found = [s for s in steps(doc, job) if name_fragment in s.get("name", "")]
    assert len(found) == 1, f"expected one step in {job} named like {name_fragment!r}, found {len(found)}"
    return found[0]


def stub_python(tmp_path):
    """A `python` on PATH that writes its arguments, NUL-separated, to $ARGV_OUT and exits 0: the shoot and specimen steps then run
    their real shell up to the interpreter call, and the test reads the exact argument vector the step built."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    py = bindir / "python"
    py.write_text("#!/bin/sh\nprintf '%s\\0' \"$@\" > \"$ARGV_OUT\"\n", encoding="utf-8")
    py.chmod(0o755)
    return bindir


def run_step(doc, job, name_fragment, env, cwd, bindir=None):
    """Execute one shipped step: its `run:` text written to a file and run as GitHub's bash shell runs it
    (`bash --noprofile --norc -eo pipefail`). The environment is PATH and HOME, the workflow's and the job's literal `env:` values
    (FD, SITE, PYTHONUTF8; never a `${{ }}` value, which only GitHub can resolve), then `env` from the test standing in for them."""
    s = step(doc, job, name_fragment)
    script = cwd.parent / f"step-{abs(hash(name_fragment))}.sh"
    script.write_text(s["run"], encoding="utf-8")
    full = {"PATH": (f"{bindir}{os.pathsep}" if bindir else "") + os.environ["PATH"], "HOME": os.environ.get("HOME", str(cwd))}
    for scope in (doc.get("env") or {}, doc["jobs"][job].get("env") or {}):
        full.update({k: str(v) for k, v in scope.items() if "${{" not in str(v)})
    full.update(env)
    return subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)], cwd=cwd, env=full,
                          capture_output=True, text=True, timeout=60)


def argv(path):
    return path.read_text(encoding="utf-8").split("\0")[:-1]


def test_the_reusable_workflow_is_callable_only_and_declares_the_inputs_both_callers_pass():
    """The reusable workflow's contract with its two callers (plan 2.3). A YAML structure assertion is unavoidable: GitHub alone checks a
    call's `with:` against `on.workflow_call.inputs`, and it does so only when a caller runs (plan section 9, steps 3 and 4). Mutations
    watched red on 2026-11-18: `family` renamed `face` in the callee only; `required: true` dropped from `family`; `oses` dropped from the
    template's `with:`."""
    doc, caller, tpl = load(REUSABLE), load(SKILL_CALLER), load(TEMPLATE)
    assert list(doc["on"]) == ["workflow_call"], f"the reusable workflow must be callable only: {list(doc['on'])}"
    inputs = doc["on"]["workflow_call"]["inputs"]
    want = {"serve", "family", "font_urls", "pages", "font_json", "scales", "browsers", "oses", "build", "run_tool_tests"}
    assert set(inputs) == want, f"the inputs must be exactly {sorted(want)}: {sorted(inputs)}"
    for name, spec in inputs.items():
        assert spec["type"] == ("boolean" if name == "run_tool_tests" else "string"), f"{name} has type {spec['type']}"
    required = {n for n, s in inputs.items() if s.get("required") is True}
    assert required == {"serve", "family", "font_urls", "pages"}, f"the required inputs are {sorted(required)}"
    defaults = {n: inputs[n].get("default") for n in ("scales", "browsers", "oses", "font_json", "build", "run_tool_tests")}
    assert defaults == {"scales": "1 1.25", "browsers": "chrome firefox", "oses": "windows-latest macos-latest ubuntu-latest",
                        "font_json": "", "build": "", "run_tool_tests": False}, defaults
    for name, other in (("the skill's caller", caller), ("the template", tpl)):
        (job,) = other["jobs"].values()
        given = set(job["with"])
        assert given <= want, f"{name} passes inputs the reusable workflow does not declare: {sorted(given - want)}"
        assert required <= given, f"{name} omits required inputs: {sorted(required - given)}"
    (tjob,) = tpl["jobs"].values()
    assert {"browsers", "oses"} <= set(tjob["with"]), "the template must pass its browsers and oses dispatch inputs on"


def test_the_reusable_workflow_runs_three_oses_and_two_browsers_without_fail_fast_and_compares_whatever_finished():
    """The legs' structure, clause by clause, moved from the 0.3 template test (plan 5): three `-latest` systems by two browsers with
    `fail-fast: false`; timeouts; a compare job that runs after any outcome and uploads after a failure; bash everywhere; both shoot lines
    proving the family through Playwright and writing rows and meta, the specimen 6000 px tall with --require-captured; the download
    keeping one directory per artifact under legs/, read by `legs/*/`; Firefox installed in its legs only; the build and specimen steps
    conditioned on their inputs; LEG_ON deciding from both inputs.browsers and inputs.oses; every step after the checkouts and the verify
    step conditioned on it; no FD_SCRIPTS left. A YAML structure assertion is unavoidable: only GitHub runs a matrix (plan section 9 step
    3). Mutations watched red on 2026-11-18: `--family` dropped from the pages shoot line; `merge-multiple: true`; `--height 6000` dropped;
    `if: always()` removed from the compare job."""
    doc = load(REUSABLE)
    text = REUSABLE.read_text(encoding="utf-8")
    shots, compare = doc["jobs"]["shots"], doc["jobs"]["compare"]
    assert shots["strategy"]["fail-fast"] is False, "one leg's failure must not cancel the others"
    m = shots["strategy"]["matrix"]
    assert sorted(m["os"]) == ["macos-latest", "ubuntu-latest", "windows-latest"] and m["browser"] == ["chrome", "firefox"], m
    assert shots.get("timeout-minutes") and compare.get("timeout-minutes"), "both jobs need a timeout"
    assert compare.get("needs") == "shots" and compare.get("if") == "always()", "the compare job must run whatever the legs did (F007)"
    assert doc["defaults"]["run"]["shell"] == "bash" and not [s for _, s in runs(doc) if s.get("shell", "bash") != "bash"], \
        "every run step must be bash (Git Bash on Windows)"
    for k, v in (("PYTHONUTF8", "1"), ("MSYS_NO_PATHCONV", "1"), ("MSYS2_ARG_CONV_EXCL", "*")):
        assert doc["env"].get(k) == v, f"the workflow env must set {k}={v} (the Windows fixes of 0.3)"
    uploads = [s for j in ("shots", "compare") for s in steps(doc, j) if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert len(uploads) == 2 and all("always()" in s.get("if", "") for s in uploads), "both uploads must run after a failure (F007)"
    assert uploads[0]["with"]["path"] == "leg/", "a leg uploads its own directory, so meta*.json is at the artifact root (F001)"
    shoots = [ln for s in steps(doc, "shots") for ln in s.get("run", "").splitlines()
              if "shoot.py" in ln and not ln.lstrip().startswith("#") and "pytest" not in ln]
    assert len(shoots) == 2, f"expected the specimen and the pages shoot lines: {len(shoots)}"
    for line in shoots:
        for flag in ("--family ", "--rows", "--meta ", "--bands none", "--browser ", "--launcher playwright", '--serve "$SITE/$IN_SERVE"'):
            assert flag in line.split("#", 1)[0], f"a shoot line lacks {flag.strip()}: {line.strip()}"
    spec = next(ln for ln in shoots if "review/specimen.html" in ln)
    assert "--height 6000" in spec, "the specimen must be shot 6000 px tall, or most rows are below the capture (F004)"
    assert "--require-captured" in spec, "the specimen must fail a row below its capture, not drop it (Impasse F002)"
    dl = next(s for s in steps(doc, "compare") if str(s.get("uses", "")).startswith("actions/download-artifact@"))
    assert dl["with"].get("pattern") == "platform-shots-*" and dl["with"].get("path") == "legs" and dl["with"].get("merge-multiple") is False, \
        f"the download must keep one directory per artifact under legs/ (F001): {dl['with']}"
    assert any('"$FD/scripts/compare-shots.py"' in s["run"] and "legs/*/" in s["run"] for _, s in runs(doc)), \
        "the compare line must run the skill checkout's compare-shots.py on legs/*/"
    ff = [s for s in steps(doc, "shots") if "playwright install" in s.get("run", "")]
    assert ff and all('if [ "$BROWSER" = "firefox" ]' in s["run"].split("playwright install")[0] for s in ff), \
        "Firefox must be installed in its legs only"
    build = [s for s in steps(doc, "shots") if 'eval "$IN_BUILD"' in s.get("run", "")]
    assert build and "env.IN_BUILD != ''" in build[0]["if"] and 'cd "$SITE"' in build[0]["run"], \
        "the build input must run, in the caller's checkout, and only when it is set (F002)"
    specimen_steps = [s for s in steps(doc, "shots") if "specimen" in s.get("run", "")]
    assert len(specimen_steps) == 2 and all("env.IN_FONT_JSON != ''" in s["if"] for s in specimen_steps), \
        "the specimen render and shot must be skipped for a site with no font.json (H1)"
    assert "LEG_ON" not in (shots.get("env") or {}), "LEG_ON is decided by the shell step, not a contains() expression (diff review F004)"
    assert "decide whether this leg runs" in steps(doc, "shots")[4].get("name", ""), "step 5 of the shots job must decide LEG_ON"
    later = steps(doc, "shots")[5:]
    assert [s.get("uses", s.get("name", ""))[:20] for s in steps(doc, "shots")[1:3]] == ["actions/checkout@v4"] * 2, \
        "steps 2 and 3 of the shots job must be the two checkouts"
    assert all("env.LEG_ON == 'true'" in s.get("if", "") for s in later), \
        "every step after the checkouts and the verify step must skip in a leg the browsers or oses input left out"
    assert "FD_SCRIPTS" not in text, "the scripts are the skill checkout's; FD_SCRIPTS must be gone"


def test_the_reusable_workflow_checks_out_its_own_scripts_at_job_workflow_sha_and_never_a_branch(tmp_path):
    """The self-checkout fails closed (plan 2.2). In both jobs: the guard step comes first and takes job.workflow_sha through env:,
    the skill checkout follows with repository/ref from job.workflow_*, path fd and no persisted credentials, and a verify step after
    it compares `git rev-parse HEAD` with WF_SHA. The order and the `with:` are YAML assertions because only GitHub runs a checkout
    (plan section 9 step 5(c) is the live red). The guard script itself is EXECUTED with bad and good SHAs. The plan's "no `@v` anywhere"
    clause cannot hold beside `actions/checkout@v4`, so the branch check is on `ref:` values and the skill's own `uses:` lines.
    Mutations watched red on 2026-11-18: the regex quantifier `{40}` changed to `+`; the guard moved after the skill checkout; the
    `ref:` line removed from the shots job's skill checkout; the verify step's `!=` turned into `=` (it then refused the right commit and
    accepted the wrong one). The verify step is EXECUTED too, against a one-commit git repository at fd/."""
    doc = load(REUSABLE)
    text = REUSABLE.read_text(encoding="utf-8")
    for job in ("shots", "compare"):
        st = steps(doc, job)
        guard = [i for i, s in enumerate(st) if "WF_SHA" in (s.get("env") or {}) and "=~" in s.get("run", "")]
        fd = [i for i, s in enumerate(st) if str(s.get("uses", "")).startswith("actions/checkout@") and (s.get("with") or {}).get("path") == "fd"]
        verify = [i for i, s in enumerate(st) if "rev-parse HEAD" in s.get("run", "") and "WF_SHA" in s.get("run", "")]
        assert guard == [0], f"{job}: the SHA guard must be the job's first step: {guard}"
        assert st[0]["env"]["WF_SHA"] == "${{ job.workflow_sha }}", f"{job}: the guard must read job.workflow_sha through env:"
        assert len(fd) == 1 and fd[0] > guard[0], f"{job}: one skill checkout, after the guard: {fd}"
        assert st[fd[0]]["with"] == SHA_CHECKOUT, f"{job}: the skill checkout must be {SHA_CHECKOUT}: {st[fd[0]]['with']}"
        assert verify and verify[0] > fd[0] and all(i < 4 for i in verify), f"{job}: a verify step must follow the skill checkout: {verify}"
        assert st[verify[0]]["env"]["WF_SHA"] == "${{ job.workflow_sha }}", f"{job}: the verify step must compare with job.workflow_sha"
    refs = re.findall(r"^\s*ref:\s*(.+)$", text, re.M)
    assert refs and all(r.strip() == "${{ job.workflow_sha }}" for r in refs), f"every ref: must be job.workflow_sha: {refs}"
    assert not re.search(r"font-design-skill/\S*@", text) and "ref: main" not in text and "ref: master" not in text, \
        "the reusable workflow must never name a branch or tag of the skill"
    work = tmp_path / "work"
    work.mkdir()
    sha = "0123456789abcdef0123456789abcdef01234567"
    for bad in ("", "main", sha[:39], sha[:39] + "A"):
        r = run_step(doc, "shots", "refuse to run unless", {"WF_SHA": bad, "WF_REPO": "o/r", "WF_REF": "o/r/x@refs/heads/main"}, work)
        assert r.returncode == 1 and "refused: job.workflow_sha is" in r.stderr, f"the guard let WF_SHA={bad!r} through: {r.returncode} {r.stderr!r}"
    r = run_step(doc, "shots", "refuse to run unless", {"WF_SHA": sha, "WF_REPO": "o/r", "WF_REF": "o/r/x@refs/heads/main"}, work)
    assert r.returncode == 0 and f"skill: o/r @ {sha}" in r.stdout, f"the guard refused a full SHA: {r.stderr!r}"
    for job in ("shots", "compare"):
        assert step(doc, job, "refuse to run unless")["run"] == step(doc, "shots", "refuse to run unless")["run"], \
            "the compare job's guard must be the same script as the one executed above"
    git = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    for cmd in (["init", "-q", "fd"], ["-C", "fd", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "x"]):
        subprocess.run(["git", *cmd], cwd=work, check=True, env={"PATH": os.environ["PATH"], **git})
    head = subprocess.run(["git", "-C", "fd", "rev-parse", "HEAD"], cwd=work, capture_output=True, text=True, check=True).stdout.strip()
    for job in ("shots", "compare"):
        ok = run_step(doc, job, "verify the skill checkout", {"WF_SHA": head, **git}, work)
        assert ok.returncode == 0 and head in ok.stdout, f"{job}: the verify step refused the checkout's own HEAD: {ok.stderr!r}"
        bad = run_step(doc, job, "verify the skill checkout", {"WF_SHA": sha, **git}, work)
        assert bad.returncode == 1 and "refused: the skill checkout is at" in bad.stderr, f"{job}: the verify step accepted another SHA: {bad.returncode}"


def slot_env(**over):
    env = {"IN_SERVE": "static-pages", "IN_FAMILY": "Driftwood MA", "IN_PAGES": "index.html essays/a-b.html about.html",
           "IN_SCALES": "1 1.25", "IN_FONT_JSON": "", "BROWSER": "chrome",
           "IN_FONT_URLS": "/fonts/d/A-Regular.woff2\n/fonts/d/A-Italic.woff2\n/fonts/d/A-Medium.woff2?v=1.001\n/fonts/d/A-Bold.woff2\n"
                           "/fonts/d/A-MediumItalic.woff2\n"}
    env.update(over)
    return env


def test_the_slot_script_reads_the_inputs_into_quoted_arrays_and_the_shoot_line_passes_them_whole(tmp_path):
    """EXECUTES the slot step and then the pages shoot step (with a stub `python` that records its arguments): a two-word family stays
    one argument all the way to shoot.py, five newline-separated font URLs become five `--font-url` pairs, three space-separated pages
    become three `--pages` values, `--serve` is the site checkout's root, and an empty input fails the slot step naming it. Plan F004:
    quoting the assignment cannot fail (Bash does not word-split an assignment), so the mutation is on the use. Mutations watched red on
    2026-11-18: `--family $FAMILY` unquoted on the pages shoot line (the family split in two); the emptiness check removed (exit 0)."""
    doc = load(REUSABLE)
    work = tmp_path / "work"
    work.mkdir()
    r = run_step(doc, "shots", "resolve the inputs", slot_env(), work)
    assert r.returncode == 0, r.stderr
    probe = work.parent / "probe.sh"
    probe.write_text('source .fd-slots.sh\nprintf "%s\\n" "$FAMILY" "${#FONT_URLS[@]}" "${#FONT_URL_ARGS[@]}" "${#PAGES[@]}" '
                     '"${FONT_URL_ARGS[0]}" "${FONT_URL_ARGS[2]}" "${FONT_URL_ARGS[5]}"\n', encoding="utf-8")
    out = subprocess.run(["bash", str(probe)], cwd=work, env={"PATH": os.environ["PATH"], **slot_env()}, capture_output=True, text=True)
    assert out.stdout.splitlines() == ["Driftwood MA", "5", "10", "3", "--font-url", "--font-url", "/fonts/d/A-Medium.woff2?v=1.001"], out
    bindir = stub_python(tmp_path)
    got = work.parent / "argv"
    r = run_step(doc, "shots", "shoot the pages", {**slot_env(), "ARGV_OUT": str(got)}, work, bindir)
    assert r.returncode == 0, r.stderr
    a = argv(got)
    assert a[0] == "fd/scripts/shoot.py", f"the pages must be shot by the skill checkout's shoot.py: {a[0]}"
    assert a[a.index("--family") + 1] == "Driftwood MA" and "MA" not in a, f"the family must reach shoot.py as one argument: {a}"
    assert a[a.index("--serve") + 1] == "site/static-pages", a
    assert a[a.index("--pages") + 1:a.index("--pages") + 4] == ["index.html", "essays/a-b.html", "about.html"], a
    assert a.count("--font-url") == 5 and a[a.index("--browser") + 1] == "chrome", a
    for empty in ("IN_PAGES", "IN_FAMILY", "IN_FONT_URLS"):
        r = run_step(doc, "shots", "resolve the inputs", slot_env(**{empty: ""}), work)
        name = empty[3:].lower()
        assert r.returncode == 1 and f"an input is empty: {name}" in r.stderr, f"an empty {name} passed the slot step: {r.returncode} {r.stderr!r}"


def test_the_specimen_step_reads_font_json_and_requirements_from_the_site_checkout(tmp_path):
    """EXECUTES the specimen render step (plan F003): with font_json `tools/FACE/font.json` and a requirements.json beside it in the
    site checkout, specimen.py gets `--font site/tools/FACE/font.json` and `--requirements site/tools/FACE/requirements.json`; with no
    requirements.json there it gets no --requirements, even though a decoy requirements.json sits at the same path relative to the
    workspace root (where the 0.3 form would have looked). Mutation watched red on 2026-11-18: the old form
    `REQS="$(dirname "$IN_FONT_JSON")/requirements.json"` (it took the decoy)."""
    doc = load(REUSABLE)
    work = tmp_path / "work"
    (work / "site" / "tools" / "FACE").mkdir(parents=True)
    (work / "tools" / "FACE").mkdir(parents=True)
    (work / "site" / "tools" / "FACE" / "font.json").write_text("{}", encoding="utf-8")
    (work / "site" / "tools" / "FACE" / "requirements.json").write_text("{}", encoding="utf-8")
    (work / "tools" / "FACE" / "requirements.json").write_text('{"decoy": true}', encoding="utf-8")
    env = slot_env(IN_FONT_JSON="tools/FACE/font.json", IN_FONT_URLS="/fonts/F-VF.woff2 /fonts/F-Italic-VF.woff2")
    assert run_step(doc, "shots", "resolve the inputs", env, work).returncode == 0
    bindir = stub_python(tmp_path)
    got = work.parent / "argv"
    r = run_step(doc, "shots", "render the review specimen", {**env, "ARGV_OUT": str(got)}, work, bindir)
    assert r.returncode == 0, r.stderr
    assert argv(got) == ["fd/scripts/specimen.py", "--font", "site/tools/FACE/font.json", "--font-url", "/fonts/F-VF.woff2",
                         "--requirements", "site/tools/FACE/requirements.json", "--italic-url", "/fonts/F-Italic-VF.woff2",
                         "site/static-pages/review/specimen.html"], argv(got)
    assert (work / "site" / "static-pages" / "review").is_dir(), "the step must create the review directory in the served root"
    (work / "site" / "tools" / "FACE" / "requirements.json").unlink()
    r = run_step(doc, "shots", "render the review specimen", {**env, "ARGV_OUT": str(got)}, work, bindir)
    assert r.returncode == 0 and "--requirements" not in argv(got), f"a requirements.json outside the site checkout was passed: {argv(got)}"


def unquoted_expansions(line):
    """The `$` expansions of one shell line that stand outside double quotes: a small scanner that knows single and double quotes,
    backslash escapes, comments and `$( )` (whose inside starts unquoted again). A `$` in single quotes is literal and not reported."""
    out, stack, i = [], ["none"], 0
    while i < len(line):
        c, top = line[i], stack[-1]
        if top == "single":
            if c == "'":
                stack.pop()
        elif c == "\\":
            i += 1
        elif c == '"':
            if top == "double":
                stack.pop()
            else:
                stack.append("double")
        elif c == "'" and top != "double":
            stack.append("single")
        elif c == "#" and top in ("none", "cmd") and (i == 0 or line[i - 1] in " \t"):
            break
        elif c == "$" and line[i + 1:i + 2] == "(":
            stack.append("cmd")
            i += 1
        elif c == ")" and top == "cmd":
            stack.pop()
        elif c == "$" and re.match(r"[A-Za-z_{@*#?0-9]", line[i + 1:i + 2]) and top != "double":
            out.append(line[i:i + 24])
        i += 1
    return out


def shell_texts(path):
    """Every piece of shell a workflow file carries: each `run:` script, and a caller's `with.build` (the reusable workflow runs it with
    `eval`, so it is shell too)."""
    doc = load(path)
    out = [(job, s.get("name", s["run"][:40]), s["run"]) for job, s in runs(doc)]
    for job, spec in doc["jobs"].items():
        build = (spec.get("with") or {}).get("build")
        if build:
            out.append((job, "with.build", build))
    return out


def test_the_workflows_quote_every_expansion():
    """Every shell expansion in the three files' shell (the reusable workflow's `run:` lines, the skill caller's `build`) is inside
    double quotes (F008: a family name has spaces, and an unquoted list splits on them), the arrays are expanded only as "${NAME[@]}",
    and no `${{ }}` expression is pasted into a script (each reaches the shell through `env:`). A source assertion because the expressions
    are resolved by GitHub, not by bash; the executed slot test above covers the family's quoting as code. The scanner is checked against
    two known lines first, so it cannot pass by seeing nothing. Mutations watched red on 2026-11-18: `"${FONT_URL_ARGS[@]}"` unquoted;
    `--serve "$SITE/${{ inputs.serve }}"` pasted into the pages shoot line."""
    assert unquoted_expansions('python x --family $FAMILY') == ["$FAMILY"]
    assert unquoted_expansions('R="$(dirname "$SITE/$IN_FONT_JSON")/r" # $not') == []
    texts = [(p, *t) for p in (REUSABLE, SKILL_CALLER, TEMPLATE) for t in shell_texts(p)]
    assert len([t for t in texts if t[0] == REUSABLE]) >= 10 and any(t[2] == "with.build" for t in texts), "the scan found too little shell"
    for path, job, name, text in texts:
        assert "${{" not in text, f"{path.name} {job}: a ${{{{ }}}} expression inside shell; pass it through env: {name}"
        for line in text.splitlines():
            bad = unquoted_expansions(line)
            assert not bad, f"{path.name} {job}: unquoted expansion {bad} in: {line.strip()}"
            for arr in re.findall(r"\$\{(\w+)\[@\]\}", line):
                assert f'"${{{arr}[@]}}"' in line, f"{path.name}: the array {arr} must be expanded as \"${{{arr}[@]}}\": {line.strip()}"


def test_the_workflow_run_lines_use_flags_the_scripts_parse():
    """Every `--flag` in a reusable-workflow `run:` step that names shoot.py, specimen.py or compare-shots.py is one that script
    registers, checked with `registered_flags()` imported from tests/test_docs_commands.py (the shipped checker, not a copy). The step
    that builds FONT_URL_ARGS names no script but feeds `--font-url` to shoot.py; the tool-tests step names tests/test_shoot.py and runs
    pytest, so it is left out. A source assertion: these lines run only on GitHub's runners. Mutation watched red on 2026-11-18: `--meta`
    misspelt `--metta` in the pages shoot line."""
    from test_docs_commands import registered_flags
    checked = 0
    for job, s in runs(load(REUSABLE)):
        if "pytest" in s["run"]:
            continue
        named = [t for t in TOOLS if t in s["run"]] or (["shoot.py"] if "FONT_URL_ARGS+=" in s["run"] else [])
        if not named:
            continue
        assert len(named) == 1, f"{job}: one step names several tools, so its flags cannot be attributed: {named}"
        script = REPO / "scripts" / named[0]
        assert script.is_file(), f"the workflow runs scripts/{named[0]}, which does not exist"
        used = set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", s["run"])) - {"--with-deps"}
        unknown = sorted(used - registered_flags(script))
        assert not unknown, f"{job}: {named[0]} does not register {unknown}"
        checked += 1
    assert checked >= 5, f"only {checked} tool steps were checked"


def test_the_workflow_pins_what_the_requirements_files_pin():
    """The reusable workflow's fontTools spec is requirements.txt's and its one `playwright==` literal is requirements-platform.txt's,
    so a pin bumped in one place cannot drift from the other; the 0.3 fallback branch (a second literal, used when a site had not
    copied requirements-platform.txt) is gone, since the skill checkout always carries the file. A source assertion: pip runs on the
    runner. Mutations watched red on 2026-11-18: `fonttools==4.67.*` in the workflow; the `if [ -f "$REQ" ]` fallback put back with
    `pip install -r "$REQ"` and the literal moved into its else branch (one literal still, so the count alone let it through: the
    `-r` clause is what fails it); a second `playwright==1.64.1` literal added."""
    text = REUSABLE.read_text(encoding="utf-8")
    req = (REPO / "requirements.txt").read_text(encoding="utf-8")
    ft = re.search(r"^fonttools(\S*)", req, re.M).group(1)
    assert re.findall(r"fonttools[=<>~!][^\"'\s]*", text) == [f"fonttools{ft}"], f"the workflow's fonttools pin must be requirements.txt's: fonttools{ft}"
    pin = re.search(r"^playwright==(\S+)", (REPO / "requirements-platform.txt").read_text(encoding="utf-8"), re.M)
    assert pin, "requirements-platform.txt pins no playwright== version"
    assert re.findall(r"playwright==([\w.]+)", text) == [pin.group(1)], f"the workflow must carry exactly one playwright=={pin.group(1)}"
    installs = [ln.strip() for ln in text.splitlines() if "pip install" in ln and not ln.lstrip().startswith("#")]
    assert installs and not [ln for ln in installs if " -r " in ln], \
        f"a leg installs named pins only; a requirements file (the 0.3 fallback's -r requirements-platform.txt) pulls requirements.txt onto every leg: {installs}"


def test_the_skills_own_platform_workflow_calls_the_reusable_one_at_the_same_commit_with_the_neutral_fixture():
    """The skill's release proof is a local caller (plan section 3): by hand and on a pull request touching the tools, the template or
    either workflow; one job whose `uses:` is the local path, so a pull request runs its own scripts rather than main's; the neutral
    fixture's inputs; the tool tests switched on. A YAML structure assertion is unavoidable: which file a job calls is resolved by
    GitHub (plan section 9 step 3 reads the guard's SHA line). Mutations watched red on 2026-11-18: `uses:` changed to
    `windaddict/font-design-skill/.github/workflows/platform-shots-reusable.yml@<40 hex>`; `run_tool_tests: false`; the reusable file
    dropped from `paths`."""
    doc = load(SKILL_CALLER)
    assert set(doc["on"]) == {"workflow_dispatch", "pull_request"} and "push" not in doc["on"], f"triggers: {list(doc['on'])}"
    need = {"scripts/shoot.py", "scripts/shoot_playwright.py", "scripts/specimen.py", "scripts/specimen.html.tmpl", "scripts/compare-shots.py",
            "templates/platform-shots.yml", "requirements-platform.txt", "tests/test_shoot.py", "tests/test_shoot_playwright.py",
            ".github/workflows/platform-shots.yml", ".github/workflows/platform-shots-reusable.yml"}
    paths = set(doc["on"]["pull_request"]["paths"])
    assert need <= paths, f"the pull_request paths lack {sorted(need - paths)}"
    assert list(doc["jobs"]) == ["neutral"], f"one job: {list(doc['jobs'])}"
    job = doc["jobs"]["neutral"]
    assert job["uses"] == "./.github/workflows/platform-shots-reusable.yml", f"the call must be local, at this commit: {job['uses']}"
    w = job["with"]
    assert "scripts/build.py --font examples/neutral/font.json" in w["build"] and "tests/fixtures/site-sample" in w["build"], \
        "build must build the neutral font and stage the fixture site (F002)"
    assert w["font_json"] == "examples/neutral/font.json" and w["family"] == "Sampler" and w["serve"] == "out/platform/site", w
    assert w["run_tool_tests"] is True, "the skill's own call must run the tool tests on every leg (F010)"


def test_the_template_caller_pins_a_full_commit_sha_and_overrides_only_through_dispatch_inputs():
    """The caller template a site copies (plan section 4 and F005): manual only, the six dispatch inputs and no `build` among them; the
    job's `uses:` names the skill's reusable workflow at a 40-hex SHA (the zeros placeholder), never a tag or branch; each overridable
    value falls back to the committed one with `||`; browsers and oses pass straight through; the header states the pin rule, the cost
    billed to this repository, the default-branch note, GHES as unsupported and the copy route that deletes the guard and verify steps,
    and names no consumer site. A YAML structure assertion is unavoidable: the call is resolved by GitHub. Mutations watched red on
    2026-11-18: `@main`; a 7-character SHA; `build` added to the dispatch inputs; `inputs.pages` wired to `family`."""
    doc = load(TEMPLATE)
    text = TEMPLATE.read_text(encoding="utf-8")
    assert list(doc["on"]) == ["workflow_dispatch"], f"the template must run by hand only: {list(doc['on'])}"
    assert list(doc["on"]["workflow_dispatch"]["inputs"]) == ["pages", "scales", "font_urls", "family", "browsers", "oses"], \
        list(doc["on"]["workflow_dispatch"]["inputs"])
    (job,) = doc["jobs"].values()
    assert re.fullmatch(r"windaddict/font-design-skill/\.github/workflows/platform-shots-reusable\.yml@[0-9a-f]{40}", job["uses"]), \
        f"the template must pin the reusable workflow by a full commit SHA: {job['uses']}"
    w = job["with"]
    assert isinstance(w.get("build"), str), "the build slot must be present (empty), so the operator sees it"
    for name in ("family", "font_urls", "pages", "scales"):
        assert re.fullmatch(rf"\$\{{\{{ inputs\.{name} \|\| '[^']+' \}}\}}", str(w[name])), f"{name} must be ${{{{ inputs.{name} || '…' }}}}: {w[name]!r}"
    for name in ("browsers", "oses"):
        assert w[name] == f"${{{{ inputs.{name} }}}}", f"{name} must pass the dispatch input through: {w[name]!r}"
    header = " ".join(ln.lstrip("#").strip() for ln in text[:text.index("\non:")].splitlines())
    for phrase in ("billed to this repository", "Never a tag or a branch", "default branch", "GITHUB ENTERPRISE SERVER is not supported",
                   "delete its guard and verify steps", "uses: ./", "review-loop.md section 9"):
        assert phrase in header, f"the template header lacks {phrase!r}"
    for name in ("driftwood", "movingavg", "bract", "hopsafari", "hop-safari"):
        assert name not in text.lower(), f"the template names a consumer site ({name})"


def test_the_tool_tests_step_runs_only_when_asked_and_from_the_skill_checkout():
    """The per-leg pytest step (0.3's F010) lives in the reusable workflow behind inputs.run_tool_tests, so a site's call never runs
    the skill's tests, and it runs from the skill checkout so tests/conftest.py's REPO is the skill. A source assertion: the step runs
    only on GitHub's runners. Mutations watched red on 2026-11-18: the `inputs.run_tool_tests` clause removed from its `if:`; the
    `cd "$FD"` line dropped."""
    doc = load(REUSABLE)
    found = [s for s in steps(doc, "shots") if "tests/test_shoot.py" in s.get("run", "")]
    assert len(found) == 1, f"expected one tool-tests step: {len(found)}"
    s = found[0]
    assert "inputs.run_tool_tests == true" in s.get("if", ""), f"the tool tests must run only when asked: {s.get('if')}"
    lines = [ln.strip() for ln in s["run"].splitlines()]
    cd = [i for i, ln in enumerate(lines) if ln in ('cd "$FD"', "cd fd")]
    py = [i for i, ln in enumerate(lines) if "pytest tests/test_shoot.py" in ln]
    assert cd and py and cd[0] < py[0], "pytest must run after cd into the skill checkout"
    assert "tests/test_shoot_playwright.py" in lines[py[0]] and 'K="$K or lays_the_page_out"' in s["run"], \
        "the Chrome legs must run the Playwright Chrome test (Impasse review of bd24d55, F006)"


def test_the_chrome_job_runs_compare_shots_on_the_tall_specimen_leg():
    """smoke.sh step 9 shoots one platform leg of the specimen with `--rows --meta --height 6000`, runs compare-shots.py on it with
    `--min-legs 1`, and reads every rows file for `captured` (F004 on the fixture), and the CI chrome job runs smoke.sh from a step at
    or before 9. Reads smoke.sh's text. Mutations watched red on 2026-11-17: `--rows` dropped; `--height 6000` dropped; the
    compare-shots.py line removed; the captured check removed."""
    text = (REPO / "scripts" / "smoke.sh").read_text(encoding="utf-8")
    step9 = text[text.index("if want 9; then"):text.index("if want 10; then")]
    leg = [ln for ln in step9.splitlines() if "$HERE/shoot.py" in ln and "--rows" in ln]
    assert len(leg) == 1, "step 9 must shoot one specimen leg with --rows"
    for flag in ("--meta ", "--height 6000", "--family Sampler", "--bands none"):
        assert flag in leg[0], f"the specimen leg lacks {flag.strip()}: {leg[0].strip()}"
    cmp = [ln for ln in step9.splitlines() if "$HERE/compare-shots.py" in ln]
    assert cmp and "--min-legs 1" in cmp[0], "step 9 must run compare-shots.py on the single leg with --min-legs 1"
    after = step9[step9.index(cmp[0]):]
    assert ".rows.json" in after and 'r["captured"]' in after, "step 9 must check every row is captured"
    m = re.search(r"scripts/smoke\.sh --full --from (\d+)", job_text("chrome"))
    assert m and int(m.group(1)) <= 9, "the chrome job must run smoke.sh step 9"


def test_the_leg_decision_matches_whole_words_and_refuses_an_unknown_one(tmp_path):
    """Which legs run is decided by a shell step from the browsers and oses inputs (diff review F004, 2026-11-18): it used to be
    `contains(inputs.browsers, matrix.browser)`, which on a string is a substring test, so "nochrome" ran the Chrome legs. EXECUTED:
    the shipped step runs with bash for each case and its $GITHUB_ENV line is read. Mutations watched red on 2026-11-18: the
    allowed-words check made a substring match (`*"$w"*`, so "ubuntu" passed); the unknown-word refusal removed; the empty-input
    refusal removed. One survives and is equivalent: the exact comparison made a substring one, because once the allowed-words
    check holds, both sides are words of the same list and none of chrome, firefox or the three runner names contains another."""
    doc = load(REUSABLE)
    work = tmp_path / "w"
    work.mkdir()

    def decide(browsers, oses, browser="chrome", os_="ubuntu-latest"):
        envfile = tmp_path / "github_env"
        envfile.write_text("", encoding="utf-8")
        out = run_step(doc, "shots", "decide whether this leg runs",
                       {"IN_BROWSERS": browsers, "IN_OSES": oses, "BROWSER": browser, "LEG_OS": os_, "GITHUB_ENV": str(envfile)}, work)
        return out.returncode, envfile.read_text(encoding="utf-8").strip(), out.stderr

    all_oses = "windows-latest macos-latest ubuntu-latest"
    assert decide("chrome firefox", all_oses)[:2] == (0, "LEG_ON=true")
    assert decide("firefox", all_oses)[:2] == (0, "LEG_ON=false"), "a browser left out must skip its legs"
    assert decide("chrome", "macos-latest")[:2] == (0, "LEG_ON=false"), "an OS left out must skip its legs"
    assert decide("chrome\nfirefox", "ubuntu-latest\nmacos-latest", browser="firefox")[:2] == (0, "LEG_ON=true"), \
        "newline-separated words must work like spaces"
    code, line, err = decide("nochrome", all_oses)
    assert code == 1 and line == "" and "'nochrome'" in err, f"an unknown word must fail the leg, not match by substring: {code} {line!r} {err!r}"
    code, line, err = decide("chrome", "ubuntu")
    assert code == 1 and "'ubuntu'" in err, f"a partial OS name must fail the leg: {code} {err!r}"
    code, line, err = decide("", all_oses)
    assert code == 1 and "empty" in err, f"an empty browsers input must fail the leg: {code} {err!r}"


def test_ci_lints_pull_request_pushes_that_touch_linted_files_and_runs_the_long_jobs_only_by_hand():
    """The test matrix and the chrome job take 47-81 minutes each (run 44771965331, 2026-11-20), and `push` plus `pull_request` ran them twice
    for every pull request branch. So: no `push` trigger; `workflow_dispatch` for the long jobs, which are gated on it. Lint takes seconds and
    is ungated: it runs on every push to a pull request (`synchronize`) whose diff touches a file it lints, its config, package.json or this
    workflow, so a later commit is checked and a docs-only push runs nothing. A YAML structure assertion is unavoidable: GitHub evaluates
    the triggers, the path filter and the `if:`, the suite cannot. Mutations watched red on 2026-11-20: `push:` added;
    the `types` line removed; the chrome job's `if:` removed; `synchronize` removed; `scripts/smoke.sh` dropped from `paths`; `paths` removed."""
    doc = load(WORKFLOW)
    on = doc["on"]
    assert "push" not in on, f"ci.yml must not run on push: {list(on)}"
    assert set(on) == {"pull_request", "workflow_dispatch"}, f"triggers: {list(on)}"
    pr = on["pull_request"] or {}
    assert pr.get("types") == ["opened", "reopened", "synchronize"], f"lint must run on every push to a pull request: {pr!r}"
    want = {"scripts/*.js", "scripts/concepts/*.js", "scripts/smoke.sh", "eslint.config.js", "package.json", ".github/workflows/ci.yml"}
    assert set(pr.get("paths") or []) == want, f"the path filter must be exactly what lint reads: {pr.get('paths')!r}"
    jobs = doc["jobs"]
    for job in ("test", "chrome"):
        assert jobs[job].get("if") == "github.event_name == 'workflow_dispatch'", f"the {job} job must run only on a manual run"
    assert "if" not in jobs["lint"], "the lint job must run on every trigger"


def test_the_lint_path_filter_covers_every_file_eslint_lints():
    """The path filter and eslint.config.js's `files` are two lists of the same thing; a glob added to the config and not to the filter
    would leave those files unlinted on a pull request. Reads the config's first `files` array as text.
    Mutation watched red on 2026-11-20: `templates/*.js` added to the config's `files` and not to the filter."""
    text = (REPO / "eslint.config.js").read_text(encoding="utf-8")
    files = re.search(r"files:\s*\[([^\]]*)\]", text).group(1)
    globs = set(re.findall(r'"([^"]+)"', files))
    paths = set(load(WORKFLOW)["on"]["pull_request"]["paths"])
    assert globs <= paths, f"eslint lints {sorted(globs - paths)} but the pull request path filter does not list them"
