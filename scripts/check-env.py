#!/usr/bin/env python3
"""Reports which pieces of the toolchain this machine has, each with the exact command that fixes a missing one.

WHAT IT'S FOR: the skill needs five things the operator's machine may lack: a Python of 3.10 or newer with the
packages in requirements.txt (the builder and the review tools), Node 20 or newer (the generator and the
exporter), Chrome or Chromium (every screenshot), and bash (smoke.sh). Without them a run fails somewhere in
the middle of a phase with a traceback. This prints one line per piece, found or missing, and for each
missing piece the command to run; it exits 1 when any required piece is missing. Run it first, on the
interpreter the skill will use:

    .venv/bin/python3 scripts/check-env.py

It uses only the standard library and no Python 3.10 syntax, so an old interpreter can still run it and say
that it is too old. Chrome is found by shoot.py's own find_chrome() (imported, so this and every screenshot
agree on which browser): $CHROME, the macOS app, the Windows install paths, then google-chrome, chromium and
the like on PATH. FontBakery is listed as optional: phase 7's gate uses it and it is installed from
requirements-dev.txt.

Exact guarantee: each line says what THIS process saw: this interpreter's version and imports, `node` and
`bash` as PATH resolves them here, and the Chrome file find_chrome() returns. A piece that is present but
broken (a Chrome that will not start, a Node whose version string cannot be read) is reported as found or as
missing by those facts alone. The network the independent review and the name check need is not tested.

Copyright 2026 John Knox. MIT licence.
"""
import importlib
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
MIN_PYTHON = (3, 10)
MIN_NODE = 20
# distribution -> the modules the skill's tools import from it (submodules, not only the package root: a damaged install can
# import `PIL` and still lack `PIL.Image`, which is the module the screenshot crops use)
PACKAGES = [("fonttools", ["fontTools.ttLib", "fontTools.varLib.instancer", "fontTools.designspaceLib", "fontTools.fontBuilder"]),
            ("brotli", ["brotli"]), ("skia-pathops", ["pathops"]),
            ("pillow", ["PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageChops"])]


def venv_fix():
    """The command that makes the skill's venv with the requirements, spelled with the interpreter path."""
    return f"cd {shlex.quote(SKILL)} && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   (python3 here must be 3.10 or newer)"


def check_platform():
    """Native Windows is not supported (bash scripts, POSIX venv paths); WSL reports as Linux."""
    if os.name == "nt":
        return False, "platform: native Windows", "native Windows is not supported; install WSL (wsl --install) and run the skill inside it"
    return True, f"platform {sys.platform} (os.name {os.name})", None


def requirement_specs():
    """{normalised distribution name: spec} from requirements.txt beside the scripts' folder, e.g. {'fonttools': '==4.68.*'}.
    A line with no operator has the spec '' (any version); comments, blanks and `-r` lines are ignored. Raises OSError
    when the file cannot be read: a check that cannot see the requirements must not pass them."""
    out = {}
    lines = open(os.path.join(SKILL, "requirements.txt"), encoding="utf-8").read().splitlines()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*((?:==|>=|<=|>|<|~=|!=)\s*[^\s;]+)?", line)
        if m and not line.startswith("-"):
            out[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = (m.group(2) or "").replace(" ", "")
    return out


def version_key(text):
    """The leading dotted integers of a version, as a tuple: '4.68.0' -> (4, 68, 0); '1.2.1rc1' -> (1, 2)."""
    parts = []
    for piece in text.split("."):
        m = re.match(r"\d+", piece)
        if not m:
            break
        parts.append(int(m.group(0)))
        if m.group(0) != piece:
            break
    return tuple(parts)


def spec_ok(version, spec):
    """Whether `version` satisfies `spec` (== with a trailing .* wildcard, ==, >=, <=, >, <, !=; '' is any). An unknown version
    ("?") satisfies no spec: a check that cannot read the version must not pass it. An operator this does not know is treated
    as satisfied, not failed: it cannot say."""
    if not spec:
        return True
    if version == "?":
        return False
    op, want = re.match(r"(==|>=|<=|>|<|~=|!=)(.*)", spec).groups()
    have = version_key(version)
    if op == "==" and want.endswith(".*"):
        prefix = version_key(want[:-2])
        return have[:len(prefix)] == prefix
    w = version_key(want)
    return {"==": have == w, ">=": have >= w, "<=": have <= w, ">": have > w, "<": have < w, "!=": have != w}.get(op, True)


def check_python():
    v = tuple(sys.version_info[:3])
    if v >= MIN_PYTHON:
        return True, f"python {'.'.join(map(str, v))} ({sys.executable})", None
    return False, f"python >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}: this interpreter is {'.'.join(map(str, v))} ({sys.executable})", \
        f"install Python 3.10 or newer (brew install python@3.12, or apt install python3.12-venv), then {venv_fix()}"


def dist_version(dist, module):
    """The installed distribution's version, else the module's own attribute, else a question mark."""
    try:
        from importlib import metadata
        return metadata.version(dist)
    except Exception:
        return getattr(module, "__version__", None) or "?"


def check_packages():
    """One result per distribution of requirements.txt: every module the tools use imports, at the pinned version."""
    try:
        specs = requirement_specs()
    except OSError as exc:
        return [(False, f"requirements.txt: cannot read {os.path.join(SKILL, 'requirements.txt')} ({exc})", "restore requirements.txt in the skill folder")]
    out = []
    for dist, modules in PACKAGES:
        first, failure = None, None
        for module in modules:
            try:
                m = importlib.import_module(module)
            except ImportError:
                failure = (f"{dist}: {module} is not importable by {sys.executable}", f"{venv_fix()}   then run the skill with .venv/bin/python3, never a bare python3")
                break
            except Exception as exc:  # a compiled package built for another Python fails on import with something else
                failure = (f"{dist}: importing {module} failed under {sys.executable} ({type(exc).__name__}: {exc})", venv_fix())
                break
            first = first or m
        if failure:
            out.append((False, *failure))
            continue
        have, spec = dist_version(dist, first), specs.get(dist, "")
        if not spec_ok(have, spec):
            out.append((False, f"{dist} {have} is installed, requirements.txt wants {dist}{spec}", venv_fix()))
            continue
        out.append((True, f"{dist} {have}", None))
    return out


def check_node():
    node = shutil.which("node")
    if not node:
        return False, "node: not on PATH", f"install Node {MIN_NODE} or newer (https://nodejs.org, or brew install node)"
    try:
        text = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"node: {node} did not run ({exc})", "reinstall Node (https://nodejs.org)"
    m = re.match(r"v(\d+)\.", text)
    if not m:
        return False, f"node: {node} printed {text!r}, not a version", "reinstall Node (https://nodejs.org)"
    if int(m.group(1)) < MIN_NODE:
        return False, f"node >= {MIN_NODE}: {node} is {text}", f"install Node {MIN_NODE} or newer (https://nodejs.org, or brew install node)"
    return True, f"node {text} ({node})", None


def check_chrome():
    """Chrome through shoot.py's own find_chrome(), imported from the file beside this one."""
    fix = "install Google Chrome or Chromium, or set CHROME to the browser binary (export CHROME=/path/to/chrome)"
    try:
        spec = importlib.util.spec_from_file_location("fd_shoot", os.path.join(HERE, "shoot.py"))
        shoot = importlib.util.module_from_spec(spec)
        sys.modules["fd_shoot"] = shoot
        spec.loader.exec_module(shoot)
        path = shoot.find_chrome()
    except FileNotFoundError as exc:
        return False, f"chrome: {exc}", fix
    except Exception as exc:  # shoot.py itself needs a newer Python than the one running this check
        return False, f"chrome: shoot.py could not be loaded by this interpreter ({type(exc).__name__}: {exc})", f"run this check on the skill's venv: {venv_fix()}"
    return True, f"chrome {path}", None


def check_bash():
    bash = shutil.which("bash")
    if bash:
        return True, f"bash ({bash})", None
    return False, "bash: not on PATH", "native Windows is not supported; install WSL (wsl --install) and run the skill inside it, where bash is present"


def check_fontbakery():
    pip = shlex.quote(SKILL + "/.venv/bin/pip")
    reqs = shlex.quote(os.path.join(SKILL, "requirements-dev.txt"))
    fix = f"{pip} install -r {reqs}"
    try:
        spec = importlib.util.find_spec("fontbakery")
    except (ImportError, ValueError):
        spec = None
    if spec is None:  # find_spec tells "not installed" apart from "installed but raises on import" (a missing dependency of it is an ImportError too)
        return f"optional: fontbakery not installed (phase 7's QA gate is skipped until it is): {fix}"
    try:
        m = importlib.import_module("fontbakery")
    except Exception as exc:  # optional, so a broken install is reported, not fatal
        return f"optional: fontbakery is installed but fails to import ({type(exc).__name__}: {exc}); reinstall it: {fix}"
    return f"optional: fontbakery {dist_version('fontbakery', m)}"


def main():
    results = [check_platform(), check_python(), *check_packages(), check_node(), check_chrome(), check_bash()]
    missing = 0
    for found, what, fix in results:
        if found:
            print(f"found    {what}")
        else:
            missing += 1
            print(f"MISSING  {what}\n         fix: {fix}")
    print(check_fontbakery())
    if missing:
        print(f"check-env: {missing} required piece(s) missing")
        return 1
    print(f"check-env: all {len(results)} required pieces found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
