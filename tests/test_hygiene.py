"""Publication hygiene: nothing in the tree may tie it to the author's machine, session or sites.

WHAT IT'S FOR: this repository is public and was extracted from two private site repositories by an
agent working in a session scratch directory. The failures this guards are quiet ones: an absolute
path that works only on one Mac, a font file that is licensed for one site only, a photograph from
a site, an email address, a session link. Each would publish without an error. These tests walk the
whole working tree (not `git ls-files`, so untracked files count) and fail naming the file.
"""
import re

import importlib.util as _ilu
import pathlib as _pl

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
tree_files = _mod.tree_files

# Built from pieces so this file does not match its own list.
FORBIDDEN = [
    "/Us" + "ers/",            # a macOS home path
    "/private/" + "tmp",       # the session temp root
    "scratch" + "pad",         # the session scratch directory
    "claude-" + "501",         # the per-user temp directory name
    "abaa" + "756b",           # the session id prefix
    "johnof" + "austin",       # the author's personal address
    "@gmail" + ".com",
    "@movingavg" + ".com",
    "Claude-" + "Session",
    "session_" + "0",
    "tool-" + "results",
]
# File types that must never be tracked: fonts (site-only licences), images (site photographs or
# review screenshots), archives.
FORBIDDEN_SUFFIXES = {".woff2", ".woff", ".ttf", ".otf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".zip", ".tar", ".gz", ".pyc"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".html", ".tmpl", ".txt", ".yml", ".yaml", ".toml", ".sh", ".css", ""}


def test_no_forbidden_string_anywhere_in_the_tree():
    hits = []
    for p in tree_files():
        if p.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            hits.append((p.relative_to(REPO).as_posix(), "not UTF-8 text"))
            continue
        for needle in FORBIDDEN:
            if needle in text:
                line = next(i + 1 for i, ln in enumerate(text.splitlines()) if needle in ln)
                hits.append((p.relative_to(REPO).as_posix(), f"line {line}: {needle!r}"))
    assert not hits, "machine-, session- or person-specific strings in the tree:\n" + "\n".join(f"  {f}: {w}" for f, w in hits)


def test_no_font_or_image_file_in_the_tree():
    bad = [p.relative_to(REPO).as_posix() for p in tree_files() if p.suffix.lower() in FORBIDDEN_SUFFIXES]
    assert not bad, f"binary assets must not be published from this repo: {bad}"


def test_every_html_and_js_file_is_free_of_site_photographs_and_hostnames():
    """The concept templates and the specimen were extracted from pages that carried site photographs
    under img/ and the sites' hostnames. The published page templates are neutral: images come from
    the content JSON, hostnames only from configuration. (Script headers may name the origin sites in
    their provenance line; the plan's licence-header rule asks for that.)"""
    offenders = []
    page_pat = re.compile(r"hopsafari\.com|movingavg\.com|live\.staticflickr")
    img_pat = re.compile(r"img/(sel-\d|ch-(food|drink|events|places)|front\.jpg|latest\.jpg|essay\.jpg)")
    for p in tree_files():
        if p.suffix in (".html", ".tmpl", ".js", ".json") and "examples" not in p.parts and "docs" not in p.parts:
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if img_pat.search(line) or (p.suffix in (".html", ".tmpl") and page_pat.search(line)):
                    offenders.append(f"{p.relative_to(REPO).as_posix()}:{i}: {line.strip()[:80]}")
    assert not offenders, "site-specific references in shipped templates/scripts:\n" + "\n".join(offenders)


def test_no_innerhtml_in_the_concept_templates():
    """Review finding F009: the earlier pages built markup from content strings with innerHTML and
    an escape that left quotes alone. The shipped templates build every node with DOM calls."""
    for p in sorted((REPO / "scripts" / "concepts").glob("*.html")):
        assert "innerHTML" not in p.read_text(encoding="utf-8"), f"{p.name} uses innerHTML"
    assert "innerHTML" not in (REPO / "scripts" / "render.js").read_text(encoding="utf-8")


def test_the_tree_walk_leaves_out_a_git_pointer_file(tmp_path, monkeypatch):
    """In a linked git worktree or a submodule `.git` is a FILE holding the path of the git directory. Git never tracks it, so it
    cannot be published, and the walk must skip it the way it skips the `.git` folder; read as text it would report the checkout's
    own path as a machine-specific string. The tree below holds one pointer file at the top and one in a sub-folder, beside two
    ordinary files, which the walk must still return."""
    conftest = _mod

    (tmp_path / ".git").write_text("gitdir: /srv/checkout/.git/worktrees/example\n", encoding="utf-8")
    (tmp_path / "a.md").write_text("a\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / ".git").write_text("gitdir: /srv/checkout/.git/modules/sub\n", encoding="utf-8")
    (tmp_path / "sub" / "b.md").write_text("b\n", encoding="utf-8")
    monkeypatch.setattr(conftest, "REPO", tmp_path)
    names = sorted(p.relative_to(tmp_path).as_posix() for p in conftest.tree_files())
    assert names == ["a.md", "sub/b.md"], f"HYGIENE-GIT-POINTER: tree_files() returned {names}, expected ['a.md', 'sub/b.md']: a file named .git is a pointer, not publishable content"
