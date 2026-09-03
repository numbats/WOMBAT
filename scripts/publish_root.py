#!/usr/bin/env python3
"""Mirror the active event's submodule content to the gh-pages site root.

GitHub Pages serves a repo from its branch root, but the active event lives
in a /<year>/ submodule alongside the archived years. This copies that
submodule's content up to the root (so the current event is what visitors
land on) while leaving every /<year>/ folder untouched.

Run from inside a checkout of the gh-pages branch, after submodules have
been synced/updated:

    python scripts/publish_root.py path/to/wombat-events.yml
"""
import pathlib
import subprocess
import sys

import yaml


def git_dir():
    """Absolute path the current directory's `.git` resolves to, or None."""
    result = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <wombat-events.yml>")

    with open(sys.argv[1]) as f:
        config = yaml.safe_load(f)

    active = str(config["active"])
    years = [str(y) for y in config["events"]]

    # Resolve the real git-dir now, and again after the rsync below, so a
    # sync that clobbers our own git metadata (e.g. an exclude pattern that
    # lets a submodule's `.git` gitlink *file* slip through and overwrite our
    # `.git`) is caught immediately instead of silently corrupting the repo.
    # This works whether `.git` here is a plain repo (a directory) or a
    # worktree/submodule (a `gitdir:` pointer file) -- either way it must
    # keep resolving to the same place.
    git_dir_before = git_dir()
    if git_dir_before is None:
        sys.exit("Refusing to run: current directory is not a git checkout.")

    src = pathlib.Path(active)
    if not src.is_dir() or not any(src.iterdir()):
        sys.exit(
            f"Active year directory '{active}' is missing or empty -- "
            "did the submodule update step run and succeed?"
        )

    # NOTE: submodule checkouts have a `.git` *file* (a gitlink pointer), not
    # a directory, so excludes here must match it regardless of type -- do
    # NOT add a trailing slash (which restricts a pattern to directories
    # only), or the source's .git file will slip through and overwrite the
    # destination's real .git directory.
    excludes = []
    for year in years:
        excludes += ["--exclude", f"/{year}/"]
    excludes += [
        "--exclude", "/.git",
        "--exclude", "/.gitmodules",
        "--exclude", "/.gitignore",
        # The active year's own repo may carry its own CNAME (or none at
        # all); the site root's CNAME must always stay wombat.numbat.space
        # regardless, so it's excluded here and written explicitly below.
        "--exclude", "/CNAME",
        # An event repo may publish its own notify-wombat-hub workflow (see
        # docs/source-repo-workflow.yml) to its gh-pages branch so that a
        # push there is enough for GitHub to recognise and trigger it. That
        # file has no meaning here and must not land in this repo's
        # gh-pages branch: our commit/push step only has `contents: write`,
        # and GitHub refuses any push that creates or modifies a
        # `.github/workflows/*` file without the separate `workflows`
        # permission.
        "--exclude", "/.github/",
    ]

    subprocess.run(
        ["rsync", "-a", "--delete", *excludes, f"{src}/", "./"],
        check=True,
    )

    if git_dir() != git_dir_before:
        sys.exit(
            "FATAL: this checkout's git metadata changed (or disappeared) "
            f"during rsync (was {git_dir_before!r}, now {git_dir()!r}). Do "
            "not commit or push from this checkout -- restore it from a "
            "fresh checkout instead."
        )

    pathlib.Path("CNAME").write_text("wombat.numbat.space")

    print(f"Published {active}/ to site root")


if __name__ == "__main__":
    main()
