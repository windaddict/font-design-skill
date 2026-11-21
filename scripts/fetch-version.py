#!/usr/bin/env python3
"""fetch-version.py VERSION DIR puts the skill's own code at a released version into DIR, so an old build can be reproduced.

WHAT IT'S FOR: a face records the skill version that built it (`skill_version` in manifest.json), and a face folder carries no
scripts. To rebuild or compare a face at that version the operator needs that version's code. This script gets it, by one of
two routes, tried in this order:

  1. the skill folder is the top folder of a git checkout (not a copy inside another repository, whose tags are that
     repository's): `git -C <skill folder> archive v<VERSION>`, the tree at the tag;
  2. otherwise, or when route 1 fails: the tag archive from GitHub,
     https://github.com/windaddict/font-design-skill/archive/refs/tags/v<VERSION>.tar.gz (`--archive-url URL` replaces the whole
     URL; a file:// URL works, which is how the tests stay offline).

Whatever the route, the code is extracted into a temporary folder beside DIR (`.fetch-*`) and moved to DIR only after the
temporary folder's VERSION file reads exactly VERSION. On any failure the temporary folder is removed, DIR is not created, and
the script exits 1 saying what each route reported. DIR must not exist, or be empty.

Version 0.6.0 is refused before either route is tried: it names two different font sources (see versions.py), and a face built
by the unreleased one cannot be rebuilt from the tag. The refusal prints how to get the code by hand.

Running the fetched code: use the installed skill's venv, which holds the pinned packages, e.g.
`.venv/bin/python3 DIR/scripts/build.py --font <face>/font.json --out-dir <elsewhere>`. The fetched folder has no venv of its own.

The exact guarantee: DIR holds the tree at the tag as the git checkout or the remote served it, and its VERSION file reads the
requested version. It is not a signature check and not proof that the tag is the code that built any particular face.
Exit 0 on success, 1 on any failure, 2 on a usage error.
"""
import argparse
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
DEFAULT_URL = "https://github.com/windaddict/font-design-skill/archive/refs/tags/v{version}.tar.gz"

sys.path.insert(0, str(HERE))
import versions  # noqa: E402  (stdlib-only module beside this script)


class RouteFailed(Exception):
    """One route could not produce a tree for the version; the message says why."""


def extract(data, into):
    """Extracts tar bytes into `into` with the `data` filter (no absolute paths, no links out, no devices)."""
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(into, filter="data")
        else:
            for m in tar.getmembers():
                target = (pathlib.Path(into) / m.name).resolve()
                if not target.is_relative_to(pathlib.Path(into).resolve()) or m.issym() or m.islnk() or m.isdev():
                    raise RouteFailed(f"the archive holds a member this script will not extract: {m.name}")
            tar.extractall(into)


def check_version(root, version, where):
    """The tree at `root` must have a VERSION file reading exactly `version`."""
    path = root / "VERSION"
    if not path.is_file():
        raise RouteFailed(f"the archive at {where} holds no VERSION file")
    found = path.read_text(encoding="utf-8").strip()
    if found != version:
        raise RouteFailed(f"the archive at {where} reports version {found}, not {version}")


def route_git(version, stage):
    """Extracts `git archive v<version>` of the skill's own checkout into `stage`; returns the tree's root."""
    try:
        probe = subprocess.run(["git", "-C", str(SKILL), "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    except OSError:
        raise RouteFailed("not a git checkout: git not on PATH") from None
    if probe.returncode != 0:
        raise RouteFailed(f"not a git checkout: {probe.stderr.strip() or 'git rev-parse failed'}")
    # git searches upward, so a copy of the skill inside another repository (a site that vendors it) answers too; that
    # repository's tags are its own releases, not the skill's.
    top = pathlib.Path(probe.stdout.strip()).resolve()
    if top != SKILL.resolve():
        raise RouteFailed(f"not a git checkout of the skill: {SKILL} is inside another git repository ({top}), whose tags are not the skill's")
    tag = f"v{version}"
    arc = subprocess.run(["git", "-C", str(SKILL), "archive", "--format=tar", tag], capture_output=True)
    if arc.returncode != 0:
        raise RouteFailed(f"git has no usable tag {tag} in {SKILL}: {arc.stderr.decode('utf-8', 'replace').strip()}")
    try:
        extract(arc.stdout, stage)
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise RouteFailed(f"git archive {tag} could not be extracted: {type(exc).__name__}: {exc}") from exc
    check_version(stage, version, f"git tag {tag}")
    return stage, f"from git tag {tag}"


def route_download(version, url, stage):
    """Downloads the tag archive, extracts it into `stage` and returns its single top folder."""
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = resp.read()
        extract(data, stage)
    except RouteFailed:
        raise
    except Exception as exc:  # reported, not swallowed: a download or archive failure of any kind is this route's reason
        raise RouteFailed(f"{url}: {type(exc).__name__}: {exc}") from exc
    tops = list(stage.iterdir())
    if len(tops) != 1 or not tops[0].is_dir():
        raise RouteFailed(f"the archive at {url} does not hold a single top folder (found {len(tops)} top-level entries)")
    check_version(tops[0], version, url)
    return tops[0], f"downloaded from {url}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("version", help="the released version to fetch, N.N.N (the tag is v<version>)")
    ap.add_argument("dir", help="the folder to put the code in; it must not exist or must be empty")
    ap.add_argument("--archive-url", metavar="URL",
                    help="the archive to download instead of the GitHub tag archive for the version (file:// works)")
    args = ap.parse_args(argv)
    version = args.version
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        ap.error(f"VERSION must read N.N.N, not {version!r}")
    refusal = versions.fetch_refusal(version)
    if refusal:
        sys.stderr.write(f"fetch-version.py: {refusal}\n")
        return 1
    dest = pathlib.Path(args.dir)
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        sys.stderr.write(f"fetch-version.py: {dest} exists and is not an empty folder; choose a new DIR\n")
        return 1
    url = args.archive_url or DEFAULT_URL.format(version=version)
    parent = dest.resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    reasons = []
    for route in ("git", "download"):
        stage_dir = pathlib.Path(tempfile.mkdtemp(dir=parent, prefix=".fetch-"))
        try:
            stage = stage_dir / "tree"
            stage.mkdir()
            root, how = route_git(version, stage) if route == "git" else route_download(version, url, stage)
            existed = dest.exists()  # an empty folder, checked above
            try:
                if existed:
                    dest.rmdir()
                os.replace(root, dest)
            except OSError as exc:
                if existed and not dest.exists():
                    dest.mkdir()  # put back the empty folder the operator gave
                sys.stderr.write(f"fetch-version.py: {version} {how}, but it could not be moved into {dest}: {exc}; "
                                 f"nothing was written to {dest}\n")
                return 1
            print(f"fetch-version.py: {version} {how} into {dest}")
            return 0
        except RouteFailed as exc:
            reasons.append(str(exc))
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)
    sys.stderr.write(f"fetch-version.py: could not fetch {version}; nothing was written to {dest}\n"
                     f"  route 1 (git tag): {reasons[0]}\n  route 2 (download): {reasons[1]}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
