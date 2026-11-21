"""Names the released skill versions that cannot be told apart, and the notice to print for one.

WHAT IT'S FOR: `fetch-version.py` rebuilds the skill's code at a released version, and `update-check.py` compares a face with the
installed skill; both trust that a version number names ONE set of font sources. Version 0.6.0 does not: the tag `v0.6.0` is commit
1c032ad, but the unreleased code at c5b4abb also set VERSION to 0.6.0, and its gen.js and export.js differ. A face recorded at 0.6.0
cannot be rebuilt from the tag with any confidence, so the two scripts ask this one module whether a version is ambiguous and say
the same thing when it is. Standard library only: both scripts import it before they know the skill's venv is the interpreter.

AMBIGUOUS_VERSIONS maps a version string to the notice text; `ambiguity_notice(version)` returns that text, or None for a version
that names one source. `fetch_refusal(version)` is the longer text `fetch-version.py` refuses with: the notice plus how to get the
code by hand. Adding a version here makes both scripts treat it as ambiguous; the CHANGELOG's version-discipline rule exists so that
no new entry is ever needed.
"""

AMBIGUOUS_VERSIONS = {
    "0.6.0": ("0.6.0 is ambiguous: tag v0.6.0 is commit 1c032ad, and the unreleased code at c5b4abb records the same version "
              "(its gen.js and export.js differ from the tag's)"),
}


def ambiguity_notice(version):
    """The notice for `version` when it names more than one set of sources, else None."""
    return AMBIGUOUS_VERSIONS.get(str(version).strip())


def fetch_refusal(version):
    """The text fetch-version.py prints when it refuses `version`: the notice and the by-hand route. None when `version` is not ambiguous."""
    notice = ambiguity_notice(version)
    if notice is None:
        return None
    return (f"{notice}. fetch-version.py will not choose between them; get the code that built your face by hand from a git checkout "
            "of the skill: `git -C <skill folder> archive 1c032ad` or `git -C <skill folder> archive c5b4abb`, extracted into DIR")
