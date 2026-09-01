#!/usr/bin/env python3
"""Reconcile the gh-pages branch's git submodules with wombat-events.yml.

Run from inside a checkout of the gh-pages branch, e.g.:

    python scripts/sync_config.py path/to/wombat-events.yml

For each year in the config this adds a missing submodule, updates the
tracked branch/url of an existing one, or removes a submodule that's no
longer listed. It only edits .gitmodules and the git index/config -- it
does not fetch or check out commits (that's `git submodule sync` /
`git submodule update --init --remote`, run separately).
"""
import subprocess
import sys

import yaml


def sh(*args, **kwargs):
    kwargs.setdefault("check", True)
    return subprocess.run(args, **kwargs)


def git_config_get_all(path):
    """Return {name: {key: value}} for all submodule.* entries in .gitmodules."""
    try:
        out = subprocess.run(
            ["git", "config", "-f", ".gitmodules", "--list"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return {}
    entries = {}
    for line in out.splitlines():
        key, _, value = line.partition("=")
        # keys look like submodule.<name>.<field>
        parts = key.split(".")
        if len(parts) != 3 or parts[0] != "submodule":
            continue
        _, name, field = parts
        entries.setdefault(name, {})[field] = value
    return entries


def main():
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <wombat-events.yml>")

    with open(sys.argv[1]) as f:
        config = yaml.safe_load(f)

    desired = {}
    for year, event in config["events"].items():
        year = str(year)
        desired[year] = {
            "path": year,
            "url": f"https://github.com/{event['repo']}.git",
            "branch": event["branch"],
        }

    existing = git_config_get_all(".")

    # Remove submodules that are no longer in the config.
    for name, fields in existing.items():
        if name not in desired:
            path = fields.get("path", name)
            print(f"Removing submodule {name} (no longer in config)")
            sh("git", "submodule", "deinit", "-f", "--", path, check=False)
            sh("git", "rm", "-f", "--", path, check=False)

    # Add or update submodules from the config.
    for name, wanted in desired.items():
        current = existing.get(name)
        if current is None:
            print(f"Adding submodule {name} -> {wanted['url']} @ {wanted['branch']}")
            sh(
                "git",
                "submodule",
                "add",
                "--force",
                "-b",
                wanted["branch"],
                "--name",
                name,
                wanted["url"],
                wanted["path"],
            )
        else:
            changed = False
            if current.get("url") != wanted["url"]:
                sh("git", "config", "-f", ".gitmodules", f"submodule.{name}.url", wanted["url"])
                changed = True
            if current.get("branch") != wanted["branch"]:
                sh("git", "config", "-f", ".gitmodules", f"submodule.{name}.branch", wanted["branch"])
                changed = True
            if changed:
                print(f"Updated submodule {name} -> {wanted['url']} @ {wanted['branch']}")
            else:
                print(f"Submodule {name} already up to date")


if __name__ == "__main__":
    main()
