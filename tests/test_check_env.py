"""scripts/check-env.py and the interpreter guards at the top of scripts/build.py, executed with pieces missing.

WHAT IT'S FOR: the skill needs Python >= 3.10 with fonttools and the other requirements, Node >= 20, Chrome
and bash. Before this, a machine without one of them failed in the middle of a phase with a traceback from
somewhere else (a `zip(strict=True)` TypeError on Python 3.9, an ImportError on `fontTools`, an `ENOENT` for
node). check-env.py names each missing piece with its fix command, and build.py refuses an old or wrong
interpreter with the venv command in the message. Nothing here edits the code under test: a missing node or
bash is a PATH without them, a missing Chrome is a $CHROME that names no file, an old Python and a missing
package are a wrapper that sets `sys.version_info` / `sys.modules[...] = None` and then runs the real script
file with runpy. Each guard was watched failing under the mutation named in its docstring.
"""
import ast
import os
import pathlib
import re
import subprocess
import sys

import pytest
from conftest import REPO

CHECK = REPO / "scripts" / "check-env.py"
BUILD = REPO / "scripts" / "build.py"

# Runs a script file as __main__ after pretending to be another Python, or after making an import fail.
WRAPPER = """
import runpy, sys
fake = {fake!r}
if fake:
    sys.version_info = fake
for name in {blocked!r}:
    sys.modules[name] = None
sys.argv = [{script!r}] + {args!r}
runpy.run_path({script!r}, run_name="__main__")
"""


def run_as(script, fake=None, blocked=(), args=(), env=None):
    code = WRAPPER.format(fake=fake, blocked=list(blocked), script=str(script), args=list(args))
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env or os.environ.copy())


def exe(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)
    return path


@pytest.fixture
def toolchain(tmp_path):
    """A PATH directory holding only a fake node (v22.1.0) and a fake bash, a fake Chrome file, and the
    environment that uses them: everything check-env.py looks for is present, so each test removes one thing."""
    bindir = tmp_path / "bin"
    exe(bindir / "node", 'echo "v22.1.0"')
    exe(bindir / "bash", "exit 0")
    chrome = exe(tmp_path / "chrome", "exit 0")
    env = {**os.environ, "PATH": str(bindir), "CHROME": str(chrome)}
    return bindir, chrome, env


def check_env(env, **kw):
    return subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, env=env, **kw)


def test_check_env_reports_everything_found_and_exits_zero(toolchain):
    r = check_env(toolchain[2])
    assert r.returncode == 0, r.stdout + r.stderr
    for line in ("found    node v22.1.0", "found    chrome " + str(toolchain[1]), "found    bash", "found    platform", "found    fonttools", "found    pillow",
                 "check-env: all 9 required pieces found"):
        assert line in r.stdout, f"{line!r} missing from:\n{r.stdout}"


def test_check_env_names_a_missing_node_and_exits_one(toolchain):
    """Mutation watched red: check_node returning (True, ...) when `which` finds nothing."""
    bindir, _chrome, env = toolchain
    pathlib.Path(bindir / "node").unlink()
    r = check_env(env)
    assert r.returncode == 1, r.stdout
    assert "MISSING  node: not on PATH" in r.stdout and "fix: install Node 20 or newer" in r.stdout, r.stdout
    assert "check-env: 1 required piece(s) missing" in r.stdout, r.stdout


def test_check_env_rejects_a_node_older_than_twenty(toolchain):
    """Mutation watched red: MIN_NODE lowered to 18. The fake node says v18.19.1."""
    bindir, _chrome, env = toolchain
    exe(bindir / "node", 'echo "v18.19.1"')
    r = check_env(env)
    assert r.returncode == 1 and "MISSING  node >= 20:" in r.stdout and "v18.19.1" in r.stdout, r.stdout


def test_check_env_names_a_missing_bash(toolchain):
    bindir, _chrome, env = toolchain
    pathlib.Path(bindir / "bash").unlink()
    r = check_env(env)
    assert r.returncode == 1 and "MISSING  bash: not on PATH" in r.stdout and "WSL" in r.stdout, r.stdout


def test_check_env_reports_a_chrome_variable_that_names_no_file(toolchain):
    """The Chrome line is shoot.py's own find_chrome(): a $CHROME naming no file is an error naming $CHROME,
    and check-env reports it missing with the variable's fix. (A machine with Chrome installed would still find
    it by the default paths if $CHROME were unset, which is why the missing case is made with the variable.)
    Mutation watched red: check_chrome rewritten to catch nothing and return found."""
    _bindir, _chrome, env = toolchain
    r = check_env({**env, "CHROME": "/nonexistent/chrome"})
    assert r.returncode == 1 and "MISSING  chrome: $CHROME is set to '/nonexistent/chrome' but no file is there" in r.stdout, r.stdout
    assert "set CHROME to the browser binary" in r.stdout, r.stdout


def test_check_env_uses_shoots_own_chrome_discovery(toolchain, tmp_path):
    """The Chrome the check reports is the file shoot.find_chrome() returns, not a copy of its search. With
    $CHROME naming a fake file that is the only way to get that exact path back."""
    _bindir, chrome, env = toolchain
    r = check_env(env)
    assert f"found    chrome {chrome}" in r.stdout, r.stdout
    src = CHECK.read_text(encoding="utf-8")
    # source check, kept because the executed one above cannot tell a call from a copy that returns the same path
    assert "shoot.find_chrome()" in src and "CHROME_NAMES" not in src, "check-env.py must call shoot.py's find_chrome, not restate its search"


def test_check_env_reports_python_older_than_3_10(toolchain):
    """Runs the real file with sys.version_info set to (3, 9, 6). Mutation watched red: MIN_PYTHON (3, 9)."""
    r = run_as(CHECK, fake=(3, 9, 6, "final", 0), env=toolchain[2])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "MISSING  python >= 3.10: this interpreter is 3.9.6" in r.stdout and "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" in r.stdout, r.stdout


@pytest.mark.parametrize("module,dist", [("fontTools", "fonttools"), ("brotli", "brotli"), ("pathops", "skia-pathops"), ("PIL", "pillow")])
def test_check_env_names_each_missing_package_with_the_venv_command(toolchain, module, dist):
    """sys.modules[module] = None makes `import module` raise ImportError, which is what a bare system Python
    without the requirements does. Mutation watched red: PACKAGES losing the entry."""
    r = run_as(CHECK, blocked=[module], env=toolchain[2])
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"MISSING  {dist}: " in r.stdout and " is not importable by " in r.stdout and ".venv/bin/pip install -r requirements.txt" in r.stdout, r.stdout


# ---- build.py's two guards, run through the real file ------------------------------------------------------------
def test_build_py_refuses_python_3_9_naming_the_venv_command():
    """build.py uses zip(strict=True), which is a TypeError mid-build on 3.9. The guard must stop before any
    fontTools import with the command that makes a venv. Mutation watched red: the guard's comparison set to (3, 8)."""
    r = run_as(BUILD, fake=(3, 9, 18, "final", 0), args=["--font", "x"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "build.py needs Python >= 3.10 and this is 3.9" in r.stderr and "python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr


def test_build_py_names_the_install_command_when_fonttools_is_missing():
    """A system Python without fonttools. Mutation watched red: the ImportError handler deleted (the raw ImportError
    traceback then reaches the operator)."""
    r = run_as(BUILD, blocked=["fontTools"], args=["--font", "x"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "build.py cannot import fontTools" in r.stderr and "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr


def test_every_script_that_needs_python_3_10_carries_the_version_guard():
    """An AST read, not a regex: a script whose syntax needs 3.10 (a match statement, a parenthesised context
    manager) or that calls zip(..., strict=...) must test sys.version_info before it goes on, or an old Python
    fails with a SyntaxError or a TypeError that names nothing useful. (Source analysis is unavoidable here: the
    scripts cannot be run on a 3.9 this machine may not have; the executed test above covers build.py's guard.)
    Mutation watched red: the guard deleted from build.py."""
    offenders = []
    for path in sorted((REPO / "scripts").glob("*.py")):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        try:
            ast.parse(src, feature_version=(3, 9))
            needs = False
        except SyntaxError:
            needs = True
        needs = needs or any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "zip" and any(k.arg == "strict" for k in n.keywords) for n in ast.walk(tree))
        guarded = any(isinstance(n, ast.Compare) and re.search(r"sys\.version_info", ast.unparse(n)) and "(3, 10)" in ast.unparse(n) for n in ast.walk(tree))
        if needs and not guarded:
            offenders.append(path.name)
    assert not offenders, f"these scripts need Python 3.10 and do not test sys.version_info < (3, 10): {offenders}"


def test_check_env_refuses_native_windows(toolchain):
    """`os.name` is "nt" for the duration of the real `check_platform()` (a wrapper swaps it in; the rest of the real
    main() runs unedited; WSL reports posix, so it is never refused).
    Before this piece existed the script reported "all 8 found" on native Windows, where the bash scripts and the
    `.venv/bin` paths cannot work. Weakest mutation watched red: `os.name == "nt"` changed to `== "never"`."""
    code = ("import runpy, sys, os\n"
            f"g = runpy.run_path({str(CHECK)!r}, run_name='not_main')\n"
            "real = g['check_platform']\n"
            "def as_windows():\n"
            "    os.name = 'nt'  # only while the platform check runs: pathlib and subprocess need the real value elsewhere\n"
            "    try:\n        return real()\n    finally:\n        os.name = 'posix'\n"
            "g['main'].__globals__['check_platform'] = as_windows\n"
            "sys.exit(g['main']())\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=toolchain[2])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "MISSING  platform: native Windows" in r.stdout and "native Windows is not supported; install WSL" in r.stdout, r.stdout
    assert "all 9" not in r.stdout, r.stdout


@pytest.fixture
def scripts_copy(tmp_path):
    """check-env.py and shoot.py copied beside a requirements.txt of the test's own, in a folder whose name has a space."""
    import shutil as sh
    root = tmp_path / "skill folder"
    (root / "scripts").mkdir(parents=True)
    for name in ("check-env.py", "shoot.py"):
        sh.copyfile(REPO / "scripts" / name, root / "scripts" / name)
    return root


def test_check_env_compares_installed_versions_with_requirements_txt(toolchain, scripts_copy):
    """requirements.txt wants fonttools==99.0.* here; the installed 4.x is older, so it must be MISSING with the pip
    command, while pillow, brotli and skia-pathops (no spec) stay found. This is the case the system Python 3.9 showed:
    fonttools 4.60.2 reported as found against ==4.68.*. Weakest mutation watched red: `spec_ok` returning True."""
    (scripts_copy / "requirements.txt").write_text("fonttools==99.0.*\nbrotli\nskia-pathops\npillow\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(scripts_copy / "scripts" / "check-env.py")], capture_output=True, text=True, env=toolchain[2])
    assert r.returncode == 1, r.stdout
    assert "MISSING  fonttools " in r.stdout and "requirements.txt wants fonttools==99.0.*" in r.stdout, r.stdout
    assert "pip install -r requirements.txt" in r.stdout and "found    pillow" in r.stdout and "MISSING  pillow" not in r.stdout, r.stdout


def test_check_env_accepts_the_version_the_repo_pins():
    """The repo's own requirements.txt, read as shipped, is satisfied by the venv the tests run in. Weakest mutation
    watched red: the `==X.Y.*` branch comparing the whole version (4.68.0 against the prefix 4.68)."""
    r = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, env={**os.environ, "CHROME": sys.executable})
    assert "found    fonttools 4.68" in r.stdout and "MISSING  fonttools" not in r.stdout, r.stdout


def load_check_env():
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_env_mod", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("version,spec,ok", [
    ("4.68.0", "==4.68.*", True), ("4.68", "==4.68.*", True), ("4.69.0", "==4.68.*", False), ("4.6.8", "==4.68.*", False),
    ("4.60.2", "==4.68.*", False), ("5.0", "==4.68.*", False), ("1.2.1", "==1.2.1", True), ("1.2.2", "==1.2.1", False),
    ("1.2.1", ">=1.2", True), ("1.2", ">=1.2", True), ("1.1.9", ">=1.2", False), ("10.0", ">=9.5", True), ("1.0", "", True), ("?", "", True), ("?", "==4.68.*", False),
])
def test_spec_ok_reads_the_operators_requirements_txt_uses(version, spec, ok):
    """Mutations watched red, one per row family: the wildcard branch comparing the whole version; versions
    compared as strings ("10.0" < "9.5"); `>=` read as `>` (the row at equality)."""
    assert load_check_env().spec_ok(version, spec) is ok


def test_the_fix_command_quotes_a_skill_path_with_a_space(scripts_copy, toolchain):
    """The fix line is meant to be pasted: `cd /a b && ...` runs `cd` with two arguments. Blocked fontTools makes
    the script print the venv command for the copy in `skill folder`. Weakest mutation watched red: `shlex.quote`
    removed from venv_fix()."""
    (scripts_copy / "requirements.txt").write_text("fonttools==4.68.*\n", encoding="utf-8")
    r = run_as(scripts_copy / "scripts" / "check-env.py", blocked=["fontTools"], env=toolchain[2])
    assert f"cd '{scripts_copy}' && python3 -m venv .venv" in r.stdout, r.stdout


# ---- every script that imports fontTools or PIL says what to install -----------------------------------------------------
NEUTRAL = REPO / "examples" / "neutral"
CALL = """
import runpy, sys
sys.modules[{blocked!r}] = None
g = runpy.run_path({script!r}, run_name="not_main")
g[{func!r}](*{args!r})
"""


@pytest.mark.parametrize("script,blocked,func,args", [
    ("fallback-metrics.py", "fontTools", "load_font", ("X", {})),
    ("specimen.py", "fontTools", "cmap_of", ("X",)),
    ("shoot.py", "PIL", "crop_bands", ("x.png", 1, {"a": (0, 1)})),
    ("opsz.py", "PIL", "measure", (None, 0, 0, None, "", "", "", 400, 1, 2, 1, None, (1, 2))),
])
def test_a_script_run_on_the_wrong_interpreter_names_the_install_command(script, blocked, func, args):
    """The lazy imports inside these functions raised a bare ModuleNotFoundError traceback. Each now exits with the
    script's name, the module, the interpreter and the venv command, the same message build.py gives. The module is
    blocked with `sys.modules[name] = None` and the real function is called (the functions are reached directly
    so no browser or built font is needed). Weakest mutation watched red, per script: the `except ImportError`
    narrowed to `except KeyError`."""
    code = CALL.format(blocked=blocked, script=str(REPO / "scripts" / script), func=func, args=args)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"{script} cannot import {blocked}" in r.stderr and ".venv/bin/pip install -r requirements.txt" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr


def test_a_missing_requirements_file_is_missing_not_passed(scripts_copy, toolchain):
    """check-env used to read a missing or unreadable requirements.txt as "no specs" and report every package found. The
    scripts are copied beside NO requirements.txt: the piece is MISSING and the exit is 1. Weakest mutation watched red:
    `requirement_specs()` catching OSError and returning {} again."""
    r = subprocess.run([sys.executable, str(scripts_copy / "scripts" / "check-env.py")], capture_output=True, text=True, env=toolchain[2])
    assert r.returncode == 1 and "MISSING  requirements.txt: cannot read" in r.stdout, r.stdout


def test_an_unreadable_version_fails_a_pinned_package(scripts_copy, toolchain):
    """`dist_version` answers "?" when the metadata cannot be read, and `spec_ok("?", spec)` returned True. With a spec in
    requirements.txt it is False now. Executed here through the real script with importlib.metadata.version made to raise.
    Weakest mutation watched red: `if version == "?": return False` removed."""
    (scripts_copy / "requirements.txt").write_text("fonttools==4.68.*\n", encoding="utf-8")
    code = ("import importlib.metadata as md, runpy, sys\n"
            "def boom(name): raise md.PackageNotFoundError(name)\n"
            "md.version = boom\n"
            f"g = runpy.run_path({str(scripts_copy / 'scripts' / 'check-env.py')!r}, run_name='not_main')\n"
            "sys.exit(g['main']())\n")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=toolchain[2])
    assert "MISSING  fonttools ? is installed, requirements.txt wants fonttools==4.68.*" in r.stdout, r.stdout


@pytest.mark.parametrize("module,dist", [("PIL.ImageChops", "pillow"), ("PIL.Image", "pillow"), ("fontTools.varLib.instancer", "fonttools"),
                                         ("fontTools.designspaceLib", "fonttools"), ("fontTools.ttLib", "fonttools")])
def test_check_env_imports_the_submodules_the_tools_use(toolchain, module, dist):
    """Only a submodule is blocked, so the package root still imports: the old check, which imported `PIL` and `fontTools`,
    called both found. Weakest mutation watched red: PACKAGES reduced to the package roots."""
    r = run_as(CHECK, blocked=[module], env=toolchain[2])
    # a module that another listed module imports first is the one named (instancer imports designspaceLib): the dist and
    # "is not importable" are the claim
    assert r.returncode == 1 and f"MISSING  {dist}: " in r.stdout and " is not importable by " in r.stdout, r.stdout


def test_a_fontbakery_that_fails_to_import_is_reported_not_a_crash(toolchain, tmp_path):
    """The optional line caught only ImportError, so a fontbakery that raised anything else on import crashed the whole
    report. A package of that name that raises RuntimeError is put first on PYTHONPATH. The run must finish, name the
    failure on the optional line and keep its exit status (it is optional). Weakest mutation watched red: the
    `except Exception` branch removed."""
    fake = tmp_path / "fake" / "fontbakery"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text('raise RuntimeError("boom")\n', encoding="utf-8")
    r = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, env={**toolchain[2], "PYTHONPATH": str(fake.parent)})
    assert "optional: fontbakery is installed but fails to import (RuntimeError: boom)" in r.stdout and "Traceback" not in r.stderr, r.stdout + r.stderr
    assert r.returncode == 0, r.stdout


def test_a_fontbakery_whose_own_import_raises_importerror_is_broken_not_missing(toolchain, tmp_path):
    """A fontbakery whose `__init__` raises ImportError (a dependency it needs is gone) used to read as "not installed",
    which sends the operator to install what is already there. `find_spec` finds the package, so it is reported broken. A
    second case with no such package still says "not installed". Weakest mutation watched red: the `find_spec` test
    removed, so an ImportError from the import alone means "not installed"."""
    fake = tmp_path / "fake" / "fontbakery"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("import a_dependency_that_is_not_there\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, env={**toolchain[2], "PYTHONPATH": str(fake.parent)})
    assert "fontbakery is installed but fails to import (ModuleNotFoundError" in r.stdout and "not installed" not in r.stdout.split("optional:")[1], r.stdout
    gone = run_as(CHECK, blocked=["fontbakery"], env=toolchain[2])
    assert "optional: fontbakery not installed" in gone.stdout, gone.stdout


def test_the_fontbakery_fix_command_uses_absolute_quoted_paths(scripts_copy, toolchain):
    """`pip install -r requirements-dev.txt` was relative: run from another directory it names no file. Both the pip and the
    requirements path are absolute and shell-quoted (the copy lives in a folder with a space). Weakest mutation watched
    red: the requirements path left relative."""
    (scripts_copy / "requirements.txt").write_text("fonttools\n", encoding="utf-8")
    r = run_as(scripts_copy / "scripts" / "check-env.py", blocked=["fontbakery"], env=toolchain[2])
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("optional: fontbakery"))
    assert f"install -r '{scripts_copy}/requirements-dev.txt'" in line and f"'{scripts_copy}/.venv/bin/pip'" in line, line
