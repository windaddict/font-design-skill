"""Every command the documentation shows is real: the script exists and every flag it uses is one the
script parses.

WHAT IT'S FOR: a cold dry run of SKILL.md found a documented flag that did not exist
(`mutate.py --all`) and hedges like "confirm the flag against the script". An agent following the
skill types these commands as written, so a wrong flag stops the run. This extracts every command
line that names a script under scripts/ from the fenced code blocks and indented command lines of
SKILL.md, README.md, references/*.md, examples/*/README.md and scripts/concepts/README.md, and
checks each `--flag` against the set of flags the script's source parses (argparse `add_argument`,
or the `--flag` tokens a JS script reads). Exact guarantee: a flag the script's source never mentions
is caught; a flag mentioned in the source but spelled right in the wrong place is not.
"""
import re
import subprocess
import sys

import pytest
from conftest import REPO

DOCS = [REPO / "SKILL.md", REPO / "README.md", *sorted((REPO / "references").rglob("*.md")), *sorted((REPO / "examples").glob("*/README.md")),
        REPO / "scripts" / "concepts" / "README.md", *sorted((REPO / "templates").glob("*.md"))]
# `<skill>/` is the documented prefix of a command typed from a site root (the site has no scripts/): the skill-root form
# `<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json` is checked against the real script's flags
# exactly as the repository-root form is. Without the optional prefix such a line would match nothing and go unchecked, silently.
SCRIPT = re.compile(r"(?:^|[\s`(])(?:bash\s+|node\s+|\S*python3?\s+(?:-m\s+pytest\s+)?)?(?:<skill>/)?"
                    r"((?:scripts/[A-Za-z0-9_./-]+\.(?:py|js|sh)(?![\w.]))|(?:scripts/tests(?![\w.])))(\s[^`\n]*)?")
HEDGE = re.compile(r"confirm (?:the|this) flag|written concurrently|re-verify (?:the|this) (?:flag|CLI)|flags? (?:was|were) written", re.I)


def commands():
    out = []
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            for m in SCRIPT.finditer(line):
                out.append((doc, i, m.group(1), m.group(2) or ""))
    return out


def registered_flags(path):
    """The `--flag` strings a Python file REGISTERS: every string argument starting with `--` of a call to `add_argument` (argparse)
    or `addoption` (pytest), found by walking the syntax tree. A flag that only appears in a docstring, a comment or a help
    text is not a registration, so deleting `add_argument("--font-url")` while the docstring still mentions it is seen. Weakest mutation
    watched red: that exact line deleted from scripts/specimen.py (the old token search still found `--font-url` in its docstring)."""
    import ast
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in ("add_argument", "addoption"):
            out |= {a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--")}
    return out


def flags_in(script):
    """The --flags a script accepts. A Python script: the registrations in its syntax tree (`registered_flags`); a pytest file under
    scripts/tests/ also takes the options its conftest.py registers (--font, --requirements, --static-dir, --scripts). A node
    script has no tree here, so its source's `--flag` tokens are read (comments included: the one place this remains a text match)."""
    if script.suffix == ".py":
        found = registered_flags(script)
        if script.parent.name == "tests" and (script.parent / "conftest.py").is_file() and script.name.startswith("test_"):
            found |= registered_flags(script.parent / "conftest.py")
        return found
    return set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", script.read_text(encoding="utf-8")))


@pytest.mark.parametrize("doc,line,script,rest", commands(), ids=lambda v: str(v)[:40] if not hasattr(v, "name") else v.name)
def test_every_documented_command_names_a_real_script_and_real_flags(doc, line, script, rest):
    path = REPO / script
    assert path.exists(), f"{doc.name}:{line} names {script}, which does not exist"
    if path.is_dir():
        return
    used = set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", rest))
    if not used:
        return
    known = flags_in(path)
    if script.endswith("smoke.sh"):
        known |= {"--full", "--out", "--from"}
    unknown = sorted(f for f in used if f not in known)
    assert not unknown, f"{doc.name}:{line}: {script} does not parse {unknown} (its source never mentions them): {rest.strip()[:120]}"


def documented_flags_by_python_script():
    out = {}
    for _doc, _line, script, rest in commands():
        path = REPO / script
        if path.suffix == ".py" and path.is_file() and not path.name.startswith("test_"):
            out.setdefault(script, set()).update(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", rest))
    return {k: v for k, v in out.items() if v}


@pytest.mark.parametrize("script", sorted(documented_flags_by_python_script()))
def test_every_documented_flag_is_in_the_scripts_own_help(script):
    """The registration walk cannot see that a registration is dead code: an `add_argument` inside `if False:` still counts.
    The script is RUN with `--help` (the venv's Python, 60 s limit) and every flag the docs use must be in what it prints.
    Weakest mutation watched red: the `--font-url` registration of scripts/specimen.py wrapped in `if False:`."""
    r = subprocess.run([sys.executable, str(REPO / script), "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"{script} --help exited {r.returncode}: {r.stderr[-400:]}"
    missing = sorted(f for f in documented_flags_by_python_script()[script] if f not in r.stdout and f not in ("--help",))
    assert not missing, f"{script} --help does not list {missing}, which the documentation uses"


def test_no_doc_hedges_about_unverified_flags():
    hits = []
    for doc in DOCS:
        for i, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if HEDGE.search(line):
                hits.append(f"{doc.relative_to(REPO)}:{i}: {line.strip()[:100]}")
    assert not hits, "documented commands must be verified, not hedged:\n" + "\n".join(hits)


def test_the_commands_set_is_not_empty():
    assert len(commands()) > 20, "the extractor found almost no commands; its pattern is broken"


# Any python interpreter token that is not the skill venv's: `python3`, `python3.12` and an absolute
# system path such as `/opt/homebrew/bin/python3` all lack fonttools. The first version matched only a
# bare `python3 `, and a host mutation to `python3.12 scripts/...` passed it (2026-11-16). A token with
# `=` in it is an environment assignment, not the command.
BARE_PYTHON = re.compile(r"(?:^|[\s`(])(?![^\s`]*\.venv/bin/)(?![^\s`]*=)[^\s`]*\bpython3?(?:\.\d+)?\s+(?!-m\s+venv\b)\S")


def test_no_documented_command_runs_a_bare_python():
    """Second dry run, finding 12: `references/variable-font-build.md` and `references/concept-pipeline.md`
    showed `python3 scripts/...` while SKILL.md says every Python command runs as `.venv/bin/python3 scripts/...`,
    the skill venv's interpreter; a bare python3 on a Homebrew Mac has no fonttools. Every command line in
    the documentation that runs a Python script must name the interpreter as .venv/bin/python3.
    The one bare python3 allowed is `python3 -m venv .venv`, which creates that venv. Executes nothing:
    this is a check on the text the agent will type, which is the thing that failed."""
    hits = []
    for doc in DOCS:
        for i, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if BARE_PYTHON.search(line):
                hits.append(f"{doc.relative_to(REPO)}:{i}: {line.strip()[:100]}")
    assert not hits, "documented commands must run on .venv/bin/python3, never a bare python3:\n" + "\n".join(hits)


def test_no_documented_command_depends_on_an_interpreter_variable():
    """The first SKILL.md told the agent to set FD_PY once and write `$FD_PY scripts/...`; on a host where each
    Bash call is a fresh shell the variable is empty and every command fails or runs a bare interpreter. The docs
    spell `.venv/bin/python3`. A variable ASSIGNMENT in front of a command (`FD_PY=... bash scripts/smoke.sh`) is
    not a use, so only `$FD_PY` and `${FD_PY}` are refused. Mutation watched red: `$FD_PY ` put back in testing.md."""
    uses = re.compile(r"\$\{?FD_PY\b")
    hits = [f"{d.relative_to(REPO)}:{i}: {ln.strip()[:90]}" for d in DOCS for i, ln in enumerate(d.read_text(encoding="utf-8").splitlines(), 1) if uses.search(ln)]
    assert not hits, "documented commands must spell the interpreter, not rely on $FD_PY:\n" + "\n".join(hits)


def test_the_docs_state_the_path_rule_build_py_implements():
    """Second dry run, finding 4, reversed by the independent re-review (docs F007): the docs once said
    `--static` and `--out-dir` resolve from the working directory while the code resolved them from
    font.json's directory, so the docs were changed to the code; the re-review then showed the code's rule
    made the neutral README's own commands write and read two different folders. The rule is now the
    shell's: a command-line path resolves from the working directory in every tool, and only the paths
    written inside font.json resolve from font.json's directory. tests/test_neutral_readme_commands.py
    executes it; this is the text check, kept because the sentence is what an agent reads: no document may
    say the two flags resolve from font.json's directory, and SKILL.md and process.md must state the rule."""
    wrong = re.compile(r"(`--out-dir`|--static DIR` and `--out-dir`)\s+resolve relative to the\s+`font\.json`'s directory|"
                       r"--static DIR` resolves relative to\s+`font\.json`'s directory")
    hits = [f"{d.relative_to(REPO)}:{i}" for d in DOCS for i, line in enumerate(d.read_text(encoding="utf-8").splitlines(), 1) if wrong.search(line)]
    assert not hits, f"the docs contradict build.py's path rule: {hits}"
    for name in ("SKILL.md", "references/process.md"):
        text = re.sub(r"\s+", " ", (REPO / name).read_text(encoding="utf-8"))
        assert "every path given on the command line (`--static`, `--out-dir`" in text and "resolves relative to the working directory" in text, \
            f"{name} must state that command-line paths such as --static and --out-dir resolve from the working directory"
