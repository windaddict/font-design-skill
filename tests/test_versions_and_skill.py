"""The skill's own metadata agrees with itself, and SKILL.md points at files that exist.

WHAT IT'S FOR: a Claude Code skill is loaded from SKILL.md; its version is announced to the operator
and must match the VERSION file, the README badge and the CHANGELOG's top entry, or the operator
cannot tell which copy answered. SKILL.md stays under 500 lines (the authoring guide's limit for what
loads into context) and must name only reference files that exist; a long reference carries a table
of contents so a reader can find the section the skill sends them to.
"""
import json
import re

from conftest import REPO


def frontmatter():
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "SKILL.md has no YAML frontmatter"
    return m.group(1), text


def test_version_is_the_same_everywhere():
    version = (REPO / "VERSION").read_text().strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
    fm, text = frontmatter()
    assert re.search(rf"^\s*version:\s*{re.escape(version)}\s*$", fm, re.M), f"SKILL.md frontmatter metadata.version is not {version}"
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert f"version-{version}-" in readme, f"README badge does not carry {version}"
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    first = re.search(r"^## \[?(\d+\.\d+\.\d+)", changelog, re.M)
    assert first and first.group(1) == version, f"CHANGELOG top entry is {first and first.group(1)}, VERSION is {version}"
    assert f"**Version {version}**" in text, "SKILL.md body must state its version so the operator hears which copy answered"
    package = json.loads((REPO / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == version, f"package.json says {package['version']}, VERSION is {version}"


def test_frontmatter_has_name_and_a_pushy_description():
    fm, _ = frontmatter()
    assert re.search(r"^name:\s*font-design\s*$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    assert desc and len(desc.group(1)) > 200, "the description carries every 'when to use' cue; it is the only triggering mechanism"
    for cue in ("custom", "typeface", "variable", "wordmark", "Not for"):
        assert cue in desc.group(1), f"description lacks the cue {cue!r}"


def test_the_description_fits_the_limit_the_hosts_enforce():
    """claude.ai and the API refuse a skill whose description is over 1,024 characters (the Agent Skills
    specification's maximum); the first version was 1,223 and no test looked at the upper bound. Measured on
    the frontmatter line itself. Mutation watched red: one sentence of 10 characters appended to the description."""
    fm, _ = frontmatter()
    desc = re.search(r"^description:\s*(.+)$", fm, re.M).group(1)
    assert len(desc) <= 1024, f"the description is {len(desc)} characters; the limit is 1,024"
    for cue in ("Not for", "frontend-design", "body-text", "CSS-only"):  # the non-trigger intent survives the cut
        assert cue in desc, f"the description lost the non-trigger cue {cue!r}"


def test_the_frontmatter_declares_licence_and_what_the_skill_needs():
    """`license` and `compatibility` (at most 500 characters) are the specification's two fields for a reader
    that has not loaded the body: they say MIT and what the machine must have. The compatibility line must name
    each requirement the skill has and the platform statement (macOS and Linux supported, native Windows not, WSL is).
    Mutation watched red: `Node.js 20` removed from the line."""
    fm, _ = frontmatter()
    assert re.search(r"^license:\s*MIT\s*$", fm, re.M), "SKILL.md frontmatter lacks `license: MIT`"
    m = re.search(r"^compatibility:\s*(.+)$", fm, re.M)
    assert m, "SKILL.md frontmatter lacks `compatibility:`"
    line = m.group(1)
    assert len(line) <= 500, f"compatibility is {len(line)} characters; the limit is 500"
    for need in ("Node.js 20", "Python 3.10", "Chrome", "bash", "macOS", "Linux", "Windows", "WSL", "Network"):
        assert need in line, f"compatibility does not mention {need!r}: {line}"


def test_skill_md_says_how_to_find_the_skill_folder_on_each_host():
    """Nothing told the agent where `scripts/` is: `<skill dir>` was never resolved. The section names the
    Claude Code variable, Codex's surfaced path and the directory of the loaded SKILL.md for any other host, and
    the interpreter is spelled in the commands, not set once in a variable a later Bash call would not have."""
    _, text = frontmatter()
    section = text[text.index("### Finding the skill folder"):]
    section = section[:section.index("\n## ")]
    for need in ("${CLAUDE_SKILL_DIR}", "Codex", "Any other host", ".venv/bin/python3"):
        assert need in section, f"'Finding the skill folder' does not mention {need!r}"
    assert "FD_PY" not in text, "SKILL.md still tells the agent to set an interpreter variable once"


def test_skill_md_is_under_500_lines():
    n = len((REPO / "SKILL.md").read_text(encoding="utf-8").splitlines())
    assert n <= 500, f"SKILL.md is {n} lines; move detail into references/"


def test_every_file_skill_md_names_exists():
    _, text = frontmatter()
    missing = []
    for ref in sorted(set(re.findall(r"`((?:references|templates|scripts|examples|tests|docs)/[A-Za-z0-9_./\-]+)`", text))):
        if not (REPO / ref).exists():
            missing.append(ref)
    assert not missing, f"SKILL.md names files that do not exist: {missing}"


def test_long_reference_files_carry_a_table_of_contents():
    long_without_toc = []
    for p in sorted((REPO / "references").rglob("*.md")):
        lines = p.read_text(encoding="utf-8").splitlines()
        if len(lines) > 300 and not any(re.match(r"^(#{1,3}\s*)?(Contents|Table of contents)\s*$", ln, re.I) for ln in lines[:40]):
            long_without_toc.append(f"{p.relative_to(REPO).as_posix()} ({len(lines)} lines)")
    assert not long_without_toc, f"reference files over 300 lines need a table of contents near the top: {long_without_toc}"


def test_the_plan_is_kept_and_names_the_review_findings():
    """docs/plan.md is part of the record: the plan the repo was built from, with the independent
    review's findings and what each changed. It stays in the repo, scrubbed of machine paths."""
    plan = (REPO / "docs" / "plan.md").read_text(encoding="utf-8")
    for tag in ("F001", "F015", "## 12.", "## 13."):
        assert tag in plan


def test_the_current_versions_changelog_entry_states_whether_font_output_changes():
    """Two installs with one VERSION must be the same skill, and a reader of the CHANGELOG deciding whether to rebuild a shipped face
    needs to know whether this release can change a woff2. So the entry for the current VERSION carries a line that starts
    `Font output: unchanged` or `Font output: changes`. The block read is the one under `## [<VERSION>]` up to the next `## `
    heading; the failure names the version looked at. Weakest mutation to watch red: the line deleted from the entry."""
    version = (REPO / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
    assert m, f"CHANGELOG.md has no entry headed '## [{version}]'"
    assert re.search(r"^Font output: (unchanged|changes)\b", m.group(1), re.M), (
        f"the CHANGELOG entry for {version} does not state whether font output changes "
        "(a line starting 'Font output: unchanged' or 'Font output: changes')")
