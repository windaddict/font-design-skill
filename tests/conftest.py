"""Fixtures for the skill repository's OWN tests (not the font suite a project copies; that is
scripts/tests/).

WHAT IT'S FOR: one place that knows where the repo is, which interpreter and node to use, and which
files count as "the tree" for hygiene checks, so every test file here agrees on them.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
# Each name here is a folder git ignores (`.gitignore`), so nothing in it can be published.
SKIP_DIRS = {".git", ".venv", "venv", "out", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".claude"}


def tree_files():
    """Every file under the repo that would be published: the working tree minus ignored and build
    directories. Walking the tree rather than `git ls-files` means an untracked new file is checked
    too, which is what matters before the first commit."""
    out = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f == ".DS_Store":
                continue
            # In a linked worktree or a submodule `.git` is a file that holds the path of the git
            # directory; git never tracks it, so it cannot be published, like the `.git` folder in SKIP_DIRS.
            if f == ".git":
                continue
            out.append(pathlib.Path(root) / f)
    return out


def node():
    n = shutil.which("node")
    if not n:
        pytest.fail("node is not on PATH; the generator and the exporter need it")
    return n


def run(cmd, **kw):
    kw.setdefault("cwd", REPO)
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return subprocess.run(cmd, **kw)


@pytest.fixture(scope="session")
def repo():
    return REPO


@pytest.fixture(scope="session")
def python():
    return sys.executable
