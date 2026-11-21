"""The neutral example's README commands, run as written from the skill directory, write and read one static folder.

WHAT IT'S FOR: re-review finding docs F007. The README's build line said `--static examples/neutral/out/static`
and its test lines `--static-dir examples/neutral/out/static`, and the README said the two name the same
folder; build.py resolved `--static` from font.json's directory, so from the skill directory the statics
landed under examples/neutral/examples/neutral/out/static and the suite read an empty folder. The rule is
now: a command-line path resolves from the working directory in every tool. This copies the skill's scripts
and the neutral example into a temp directory laid out like the skill, runs the README's build line there
VERBATIM (its interpreter swapped for this one) with that directory as the working directory, and then its
pytest line's `--static-dir`, resolved the same way, must be the folder the build wrote.
"""
import re
import shutil
import subprocess
import sys

from conftest import REPO

README = REPO / "examples" / "neutral" / "README.md"
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc", "out")


def readme_commands():
    block = re.search(r"## Build.*?```\n(.*?)```", README.read_text(encoding="utf-8"), re.S)
    assert block, "the README has no fenced command block under Build"
    return [ln.strip() for ln in block.group(1).splitlines() if ln.strip()]


def test_the_readme_build_and_test_lines_name_the_same_static_folder(tmp_path):
    """Mutation watched red: build.py resolving --static from font.json's directory again (the statics then
    land under examples/neutral/examples/neutral/out/static, the README's pytest line finds none, and the
    static tests fail on "no static instances at")."""
    skill = tmp_path / "skill"
    shutil.copytree(REPO / "scripts", skill / "scripts", ignore=IGNORE)
    shutil.copy2(REPO / "VERSION", skill / "VERSION")  # build.py refuses to build without it (0.8.0)
    shutil.copytree(REPO / "examples" / "neutral", skill / "examples" / "neutral", ignore=IGNORE)
    cmds = readme_commands()
    build = next(c for c in cmds if "scripts/build.py" in c)
    pytest_line = next(c for c in cmds if "-m pytest" in c)
    assert build.startswith(".venv/bin/python3 ") and pytest_line.startswith(".venv/bin/python3 "), (build, pytest_line)
    static_arg = re.search(r"--static (\S+)", build).group(1)
    static_dir_arg = re.search(r"--static-dir (\S+)", pytest_line).group(1)
    assert static_arg == static_dir_arg, "the README's build and test lines must spell the static folder the same way"
    argv = build.split()
    argv[0] = sys.executable
    r = subprocess.run(argv, cwd=skill, capture_output=True, text=True)
    assert r.returncode == 0, f"the README build line failed:\n{r.stderr[-1500:]}"
    written = skill / static_arg
    assert (written / "Sampler-Regular.woff2").is_file(), f"the statics are not at {written} (the working-directory reading of --static)"
    assert not (skill / "examples" / "neutral" / "examples").exists(), "--static resolved from font.json's directory"
    argv = pytest_line.split()
    argv[0] = sys.executable
    r = subprocess.run([*argv, "-k", "static_instances", "-p", "no:cacheprovider"], cwd=skill, capture_output=True, text=True)
    assert r.returncode == 0, f"the README pytest line did not find the statics the build line wrote:\n{r.stdout[-2000:]}"
    assert "passed" in r.stdout.strip().splitlines()[-1]
