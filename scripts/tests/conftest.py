"""Fixtures for the font test-suite template (test_font.py): which project, which expectations, and the
built things under test.

WHAT IT'S FOR: the suite is a template a project copies beside its font.json. This file is where it
learns which font.json to read and which requirements.json to hold it to, and it parametrises every
test over the groups, masters and instances the REQUIREMENTS name (review finding F002), never the ones
font.json or the manifest name, so a font.json that drops an axis, a master or a character goes red
instead of shrinking the suite to match.

    pytest scripts/tests/test_font.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json
    FONT_JSON=... REQUIREMENTS_JSON=... pytest scripts/tests/test_font.py      # the same through the environment
    --static-dir DIR        where build.py --static wrote the instances (default <out_dir>/static);
                            --static-dir none skips those tests, and says so
    --scripts=DIR           where gen.js, export.js and build.py live (or env FD_SCRIPTS); default: the
                            parent of this file's directory. Write it WITH the equals sign: pytest reads a
                            space-separated value as a test path before it knows this option, and if that
                            folder has a tests/ child it loads that conftest too and fails with
                            "option names {'--font'} already added"

WHERE THE SUITE LIVES IN A SITE (dry-run finding W1): the suite needs the generator, the exporter and
the builder beside it, so a site copies the WHOLE scripts/ folder, tests included, to something like
tools/<face>/scripts/ and runs

    pytest tools/<face>/scripts/tests --font tools/<face>/font.json --requirements tools/<face>/requirements.json

Copying test_font.py and conftest.py alone into the site's own tests directory breaks the default
(`SCRIPTS = HERE.parent` would then be the site's root); a site that wants the tests elsewhere all the
same points `--scripts=DIR` or `FD_SCRIPTS` at the folder holding gen.js, export.js and build.py, and the
fixtures refuse to start when that folder lacks them, naming the missing file.

Exact guarantee: what the fixtures read from font.json is only WHERE the built things are (out_dir,
file names, the concepts path for a fresh export); every expected VALUE comes from requirements.json.

Copyright 2026 John Knox. MIT licence.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

try:
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
except ImportError as exc:  # pragma: no cover - environment guard, not a test outcome
    raise ImportError("the font tests need fonttools and brotli: pip install -r requirements.txt") from exc

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT_FILES = ("gen.js", "export.js", "build.py")


def scripts_dir():
    """The folder holding gen.js, export.js and build.py: FD_SCRIPTS when set, else the parent of this
    file's directory (the layout of the skill repo and of a whole-folder copy into a site)."""
    env = os.environ.get("FD_SCRIPTS")
    return pathlib.Path(env).resolve() if env else HERE.parent


SCRIPTS = scripts_dir()  # module-level for `from conftest import SCRIPTS`; pytest_configure re-points it from --scripts


def pytest_addoption(parser):
    g = parser.getgroup("font-design")
    g.addoption("--font", default=os.environ.get("FONT_JSON"), help="the project's font.json (or env FONT_JSON)")
    g.addoption("--requirements", default=os.environ.get("REQUIREMENTS_JSON"), help="the reviewed requirements.json (or env REQUIREMENTS_JSON)")
    g.addoption("--static-dir", default=os.environ.get("STATIC_DIR"),
                help="where build.py --static wrote the instances; default <out_dir>/static; 'none' skips the static tests")
    g.addoption("--scripts", default=None,
                help="the folder holding gen.js, export.js and build.py, written --scripts=DIR (or env FD_SCRIPTS); default: the parent of the tests folder")


def pytest_configure(config):
    """Resolve --scripts once, before collection, so every `from conftest import SCRIPTS` sees the same
    folder, and refuse to start when the folder lacks a script rather than failing one test at a time."""
    global SCRIPTS
    value = config.getoption("--scripts")
    if value:
        SCRIPTS = pathlib.Path(value).resolve()
    missing = [f for f in SCRIPT_FILES if not (SCRIPTS / f).is_file()]
    if missing:
        raise pytest.UsageError(f"the scripts folder {SCRIPTS} lacks {missing}; copy the whole scripts/ folder of the skill, or pass --scripts DIR / set FD_SCRIPTS")
    config._font_design_scripts = SCRIPTS


def _option_path(config, name, env):
    value = config.getoption(name)
    if not value:
        raise pytest.UsageError(f"pass {name} PATH (or set {env}); the font tests need the project's file to know what to test")
    path = pathlib.Path(value).resolve()
    if not path.is_file():
        raise pytest.UsageError(f"{name} {path} does not exist")
    return path


def requirements_of(config):
    """requirements.json, loaded once per session and cached on the pytest config."""
    cached = getattr(config, "_font_design_requirements", None)
    if cached is None:
        path = _option_path(config, "--requirements", "REQUIREMENTS_JSON")
        cached = json.loads(path.read_text())
        for k in ("groups", "cmap", "names", "size_budget_bytes", "fold_units", "hand_kerns", "titles", "gasp", "tables"):
            if k not in cached:
                raise pytest.UsageError(f"{path} lacks the key {k!r}; the suite cannot hold the font to an expectation it does not have")
        config._font_design_requirements = cached
    return cached


def pytest_generate_tests(metafunc):
    """Parametrise from requirements.json only (F002). A test asking for `master` runs once per
    (group, master); `instance_name` once per (group, named instance); `italic_group` once per group
    whose requirements carry an italic_angle; `group` once per group."""
    req = requirements_of(metafunc.config)
    names = metafunc.fixturenames
    groups = list(req["groups"])
    if "master" in names:
        pairs = [(g, m) for g in groups for m in req["groups"][g]["masters"]]
        metafunc.parametrize(("group", "master"), pairs, ids=[f"{g}-{m}" for g, m in pairs])
    elif "instance_name" in names:
        pairs = [(g, i) for g in groups for i in req["groups"][g]["instances"]]
        metafunc.parametrize(("group", "instance_name"), pairs, ids=[f"{g}-{i}" for g, i in pairs])
    elif "italic_group" in names:  # `group` is bound too, so the font fixture resolves
        metafunc.parametrize("group", [g for g in groups if "italic_angle" in req["groups"][g]])
    elif "group" in names:
        metafunc.parametrize("group", groups)


@pytest.fixture
def italic_group(group):
    """The current group, which pytest_generate_tests limited to the groups with an italic_angle."""
    return group


@pytest.fixture(scope="session")
def req(request):
    return requirements_of(request.config)


@pytest.fixture(scope="session")
def req_path(request):
    """The requirements file's path, for tests that run build.py and must hand it the real requirements."""
    return _option_path(request.config, "--requirements", "REQUIREMENTS_JSON")


@pytest.fixture(scope="session")
def scripts(request):
    """The folder holding gen.js, export.js and build.py (see the module header)."""
    return request.config._font_design_scripts


@pytest.fixture(scope="session")
def cfg(request):
    """font.json with the paths the suite needs resolved: _path, _dir, _out_dir, _manifest, _concepts."""
    path = _option_path(request.config, "--font", "FONT_JSON")
    cfg = json.loads(path.read_text())
    cfg["_path"], cfg["_dir"] = path, path.parent
    cfg["_out_dir"] = (path.parent / cfg["out_dir"]).resolve()
    cfg["_manifest"] = (cfg["_out_dir"] / cfg["manifest"]).resolve() if cfg.get("manifest") else cfg["_out_dir"] / "manifest.json"
    cfg["_concepts"] = (path.parent / cfg["concepts"]).resolve()
    return cfg


def group_woff2(cfg, group):
    """Where build.py put the group's font (its own naming rule, mirrored here from font.json only)."""
    g = cfg["groups"].get(group)
    if g is None:
        pytest.fail(f"requirements name group {group!r}, which font.json does not define")
    fam = cfg["family"].replace(" ", "")
    if g.get("file"):
        return (cfg["_out_dir"] / g["file"]).resolve()
    return cfg["_out_dir"] / (f"{fam}-Italic-VF.woff2" if g.get("italic") else f"{fam}-VF.woff2")


@pytest.fixture(scope="session")
def manifest(cfg):
    assert cfg["_manifest"].is_file(), f"no manifest at {cfg['_manifest']}; build first: python3 scripts/build.py --font {cfg['_path']}"
    return json.loads(cfg["_manifest"].read_text())


@pytest.fixture(scope="session")
def _font_cache():
    return {}


@pytest.fixture
def font(cfg, group, _font_cache):
    """TTFont of the group's shipped woff2, loaded once per session."""
    if group not in _font_cache:
        path = group_woff2(cfg, group)
        assert path.is_file(), f"no built font at {path}; build first: python3 scripts/build.py --font {cfg['_path']}"
        _font_cache[group] = TTFont(path)
    return _font_cache[group]


@pytest.fixture(scope="session")
def _export_cache():
    return {}


@pytest.fixture
def export(cfg, group, _export_cache, tmp_path_factory):
    """The generator's own masters for the group, exported afresh by node into a temp dir: advances,
    kern pairs, title widths, fold figures and the measured minimum stroke widths. Independent of
    build.py and of the shipped files. The whole export JSON (masters under "masters")."""
    if group not in _export_cache:
        node = shutil.which("node")
        assert node, "node is not on PATH; the export fixture needs it"
        out = tmp_path_factory.mktemp("export") / f"{group}.json"
        r = subprocess.run([node, str(SCRIPTS / "export.js"), "--font", str(cfg["_path"]), "--group", group, str(out)],
                           cwd=SCRIPTS, capture_output=True, text=True)
        assert r.returncode == 0, f"export.js failed for group {group}:\n{r.stderr[-2000:]}"
        _export_cache[group] = json.loads(out.read_text())
    return _export_cache[group]


@pytest.fixture(scope="session")
def _instance_cache():
    return {}


@pytest.fixture
def instance(cfg, _instance_cache):
    """instance(group, location) -> a static instance of the shipped font at a user location, with the
    GPOS values resolved. Cached per (group, location) for the session."""
    def make(group, location):
        key = (group, tuple(sorted(location.items())))
        if key not in _instance_cache:
            _instance_cache[key] = instancer.instantiateVariableFont(TTFont(group_woff2(cfg, group)), dict(location), inplace=False)
        return _instance_cache[key]
    return make


@pytest.fixture(scope="session")
def static_dir(request, cfg):
    """Where build.py --static wrote the instances. Missing is a failure, not a skip: a static the CSS
    names and nobody built would 404. --static-dir none records the decision not to ship statics."""
    value = request.config.getoption("--static-dir")
    if value == "none":
        pytest.skip("static instance tests disabled with --static-dir none")
    path = pathlib.Path(value).resolve() if value else cfg["_out_dir"] / "static"
    assert path.is_dir(), f"no static instances at {path}; build them: python3 scripts/build.py --font {cfg['_path']} --static {path}"
    return path
