"""The CI workflow runs the mutation harness and builds every fixture, not only the neutral one.

WHAT IT'S FOR: re-review finding code-b F010. The `test` job built the neutral example and ran the font
suite on it; the `chrome` job ran `smoke.sh --full --from 6`, which skips steps 1-5 (the export and build of
all three fixtures, the reproducibility check, the font suite and `mutate.py`). So CI could pass with the
precedent fixtures broken and every guard decorative. The workflow cannot be executed by the suite (it runs only on
GitHub), so this reads the file: a check on text, stated as such, kept because the text is
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


# ---- the cross-platform rendering shots (plan docs/plan-platform-shots.md, sections 5 and 7; work item C1t) ----
# Like the tests above, these read the workflow files: GitHub runs them, the suite cannot. A check on text (parsed as YAML where the
# structure matters), stated as such. What executes the template is the skill's own platform-shots workflow on a pull request.

TEMPLATE = REPO / "templates" / "platform-shots.yml"
PLATFORM = REPO / ".github" / "workflows" / "platform-shots.yml"
SLOTS = ("FD_SCRIPTS", "FD_SERVE", "FD_BUILD", "FD_FAMILY", "FD_FONT_URLS", "FD_PAGES", "FD_FONT_JSON", "FD_SCALES")
TOOLS = ("shoot.py", "specimen.py", "compare-shots.py")


def load(path):
    yaml = pytest.importorskip("yaml", reason="PyYAML is not installed (it comes with fontbakery in requirements-dev.txt)")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["on"] = doc.pop(True, doc.get("on"))  # YAML 1.1 reads the bare key `on` as the boolean true
    return doc


def steps(doc, job):
    return doc["jobs"][job]["steps"]


def runs(doc):
    return [(job, s) for job in doc["jobs"] for s in steps(doc, job) if "run" in s]


def test_the_platform_template_is_manual_runs_three_oses_and_two_browsers_without_fail_fast_and_compares_whatever_finished():
    """The template's structure, clause by clause (plan 5.1 and findings F001, F002, F004, F007, F013, H1): manual only, with the five
    dispatch inputs; three `-latest` systems by two browsers with `fail-fast: false`; timeouts on both jobs; a compare job that runs after
    any outcome of the shots, and uploads that run after a failure; bash everywhere; both shoot lines proving the family and writing rows
    and meta, the specimen 6000 px tall; the download keeping one directory per artifact under legs/, read by `legs/*/`; Firefox
    installed in its legs only; FD_BUILD and the specimen steps conditioned on their slots; every step after checkout conditioned on the
    browsers input. Mutations watched red on 2026-11-17: `--family` dropped from the pages shoot line (a picture, not evidence);
    `merge-multiple: true`; the download's `path` removed; `--height 6000` dropped; `if: always()` removed from the compare job; `--require-captured` dropped."""
    doc = load(TEMPLATE)
    assert list(doc["on"]) == ["workflow_dispatch"], f"the template must run by hand only: {list(doc['on'])}"
    assert set(doc["on"]["workflow_dispatch"]["inputs"]) == {"pages", "scales", "font_urls", "family", "browsers"}, \
        "the dispatch inputs must be pages, scales, font_urls, family and browsers (F013)"
    shots, compare = doc["jobs"]["shots"], doc["jobs"]["compare"]
    assert shots["strategy"]["fail-fast"] is False, "one leg's failure must not cancel the others"
    m = shots["strategy"]["matrix"]
    assert sorted(m["os"]) == ["macos-latest", "ubuntu-latest", "windows-latest"] and m["browser"] == ["chrome", "firefox"], m
    assert shots.get("timeout-minutes") and compare.get("timeout-minutes"), "both jobs need a timeout"
    assert compare.get("needs") == "shots" and compare.get("if") == "always()", "the compare job must run whatever the legs did (F007)"
    assert doc["defaults"]["run"]["shell"] == "bash" and not [s for _, s in runs(doc) if s.get("shell", "bash") != "bash"], \
        "every run step must be bash (Git Bash on Windows)"
    uploads = [s for j in ("shots", "compare") for s in steps(doc, j) if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert len(uploads) == 2 and all("always()" in s.get("if", "") for s in uploads), "both uploads must run after a failure (F007)"
    assert uploads[0]["with"]["path"] == "leg/", "a leg uploads its own directory, so meta*.json is at the artifact root (F001)"
    shoot = [s["run"] for _, s in runs(doc) if "shoot.py" in s["run"]]
    assert len(shoot) == 2, f"expected the specimen and the pages shoot steps: {len(shoot)}"
    for text in shoot:
        line = next(ln for ln in text.splitlines() if "shoot.py" in ln)
        for flag in ("--family ", "--rows", "--meta ", "--bands none", "--browser "):
            assert flag in line, f"a shoot line lacks {flag.strip()}: {line}"
    spec = next(t for t in shoot if "review/specimen.html" in t)
    assert "--height 6000" in spec, "the specimen must be shot 6000 px tall, or most rows are below the capture (F004)"
    assert "--require-captured" in spec, "the specimen must fail a row below its capture, not drop it (Impasse F002)"
    dl = next(s for s in steps(doc, "compare") if str(s.get("uses", "")).startswith("actions/download-artifact@"))
    assert dl["with"].get("pattern") == "platform-shots-*" and dl["with"].get("path") == "legs" and dl["with"].get("merge-multiple") is False, \
        f"the download must keep one directory per artifact under legs/ (F001): {dl['with']}"
    assert any("compare-shots.py" in s["run"] and "legs/*/" in s["run"] for _, s in runs(doc)), "the compare line must read legs/*/"
    ff = [s for s in steps(doc, "shots") if "playwright install" in s.get("run", "")]
    assert ff and all('if [ "$BROWSER" = "firefox" ]' in s["run"].split("playwright install")[0] for s in ff), \
        "Firefox must be installed in its legs only"
    shoots = [s["run"] for s in steps(doc, "shots") if "shoot.py" in s.get("run", "")]
    assert shoots and all("--launcher playwright" in r for r in shoots), \
        "every leg must shoot through Playwright: Chrome's command line on Windows measures rows on a narrower layout"
    build = [s for s in steps(doc, "shots") if 'eval "$FD_BUILD"' in s.get("run", "")]
    assert build and "env.FD_BUILD != ''" in build[0]["if"], "FD_BUILD must run, and only when the slot is set (F002)"
    specimen_steps = [s for s in steps(doc, "shots") if "specimen" in s.get("run", "")]
    assert len(specimen_steps) == 2 and all("env.FD_FONT_JSON != ''" in s["if"] for s in specimen_steps), \
        "the specimen render and shot must be skipped for a site with no font.json (H1)"
    leg_on = shots["env"]["LEG_ON"]
    assert "inputs.browsers" in leg_on and "matrix.browser" in leg_on, f"the browsers input must decide which legs run: {leg_on}"
    later = steps(doc, "shots")[1:]
    assert all("env.LEG_ON == 'true'" in s.get("if", "") for s in later), "every step after checkout must skip in a leg the browsers input left out"


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


def test_the_template_quotes_every_expansion():
    """Every shell expansion in the template's and the skill workflow's `run:` lines is inside double quotes (F008: a family name
    has spaces, and an unquoted list splits on them), the arrays are expanded only as "${NAME[@]}", and no `${{ }}` expression is
    pasted into a script (each reaches the shell through `env:`). The scanner is checked against two known lines first, so it cannot
    pass by seeing nothing. Mutations watched red on 2026-11-17: `--family "$FAMILY"` unquoted in the pages shoot line;
    `"${FONT_URL_ARGS[@]}"` unquoted; `--browser "${{ matrix.browser }}"` pasted into the run line."""
    assert unquoted_expansions('python x --family $FAMILY') == ["$FAMILY"]
    assert unquoted_expansions('R="$(dirname "$FD_FONT_JSON")/r" # $not') == []
    for path in (TEMPLATE, PLATFORM):
        for job, s in runs(load(path)):
            assert "${{" not in s["run"], f"{path.name} {job}: a ${{{{ }}}} expression inside a run script; pass it through env: {s.get('name')}"
            for line in s["run"].splitlines():
                bad = unquoted_expansions(line)
                assert not bad, f"{path.name} {job}: unquoted expansion {bad} in: {line.strip()}"
                for arr in re.findall(r"\$\{(\w+)\[@\]\}", line):
                    assert f'"${{{arr}[@]}}"' in line, f"{path.name}: the array {arr} must be expanded as \"${{{arr}[@]}}\": {line.strip()}"


def test_the_template_run_lines_use_flags_the_scripts_parse():
    """Every `--flag` in a `run:` step that names shoot.py, specimen.py or compare-shots.py is one that script registers, checked with
    `registered_flags()` imported from tests/test_docs_commands.py (the shipped checker, not a copy). The step that builds FONT_URL_ARGS
    names no script but feeds `--font-url` to shoot.py, so it is checked against shoot.py. Mutation watched red on 2026-11-17: `--meta`
    misspelled `--metta` in the pages shoot line. (Until work items A1 and B1 land, this is red for `--rows`, `--meta`, `--browser` and
    the missing compare-shots.py: the template is written to the plan's flag names.)"""
    from test_docs_commands import registered_flags
    for path in (TEMPLATE, PLATFORM):
        for job, s in runs(load(path)):
            named = [t for t in TOOLS if t in s["run"]] or (["shoot.py"] if "FONT_URL_ARGS+=" in s["run"] else [])
            if not named:
                continue
            assert len(named) == 1, f"{path.name} {job}: one step names several tools, so its flags cannot be attributed: {named}"
            script = REPO / "scripts" / named[0]
            assert script.is_file(), f"{path.name} runs scripts/{named[0]}, which does not exist"
            used = set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", s["run"])) - {"--with-deps"}
            unknown = sorted(used - registered_flags(script))
            assert not unknown, f"{path.name} {job}: {named[0]} does not register {unknown}"


def test_the_template_pins_what_the_requirements_files_pin():
    """The template's fontTools spec is requirements.txt's, and its fallback `playwright==` pin (used when a site did not copy
    requirements-platform.txt) is requirements-platform.txt's, so a pin bumped in one place cannot drift from the other. Mutation watched
    red on 2026-11-17: `fonttools==4.67.*` in the template. (Red until work item E1 writes requirements-platform.txt.)"""
    text = TEMPLATE.read_text(encoding="utf-8")
    req = (REPO / "requirements.txt").read_text(encoding="utf-8")
    ft = re.search(r"^fonttools(\S*)", req, re.M).group(1)
    assert re.findall(r"fonttools[=<>~!][^\"'\s]*", text) == [f"fonttools{ft}"], f"the template's fonttools pin must be requirements.txt's: fonttools{ft}"
    plat = REPO / "requirements-platform.txt"
    assert plat.is_file(), "requirements-platform.txt does not exist (work item E1)"
    pin = re.search(r"^playwright==(\S+)", plat.read_text(encoding="utf-8"), re.M)
    assert pin, "requirements-platform.txt pins no playwright== version"
    assert set(re.findall(r"playwright==([\w.]+)", text)) == {pin.group(1)}, f"the template's playwright pin must be {pin.group(1)}"


def test_the_skills_platform_workflow_is_the_template_with_the_neutral_slots_filled():
    """.github/workflows/platform-shots.yml is the template with its slots filled for the neutral fixture and exactly two additions: the
    `pull_request` trigger with its paths, and the per-leg `pytest tests/test_shoot.py -k ...` step (F010). Compared as parsed YAML, so
    the header comments may differ and nothing else may. Mutations watched red on 2026-11-17: `--jobs 2` changed to `--jobs 3` in the
    workflow only; `scripts/compare-shots.py` dropped from the paths; the pytest step removed; `scripts/specimen.html.tmpl` dropped from the
    paths (Impasse F006)."""
    tpl, wf = load(TEMPLATE), load(PLATFORM)
    env = wf["env"]
    assert env["FD_SCRIPTS"] == "scripts" and env["FD_FAMILY"] == "Sampler" and env["FD_FONT_JSON"] == "examples/neutral/font.json", env
    assert "scripts/build.py --font examples/neutral/font.json" in env["FD_BUILD"] and "tests/fixtures/site-sample" in env["FD_BUILD"], \
        "FD_BUILD must build the neutral font and stage the fixture site (F002)"
    pr = wf["on"].pop("pull_request")
    need = {"scripts/shoot.py", "scripts/shoot_playwright.py", "scripts/specimen.py", "scripts/specimen.html.tmpl", "scripts/compare-shots.py",
            "templates/platform-shots.yml", "requirements-platform.txt", ".github/workflows/platform-shots.yml"}
    assert need <= set(pr["paths"]), f"the pull_request paths lack {sorted(need - set(pr['paths']))}"
    extra = [s for s in steps(wf, "shots") if "pytest tests/test_shoot.py" in s.get("run", "")]
    assert len(extra) == 1 and " -k " in extra[0]["run"], "the per-leg pytest step (F010) is missing"
    wf["jobs"]["shots"]["steps"].remove(extra[0])
    for k in SLOTS:
        tpl["env"][k] = env[k]
    assert wf == tpl, "the skill's workflow differs from the template beyond the slots, the pull_request trigger and the pytest step"


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
