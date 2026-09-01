# WOMBAT

Archive and hub site for **W**orkshop **O**rganised by the **M**onash **B**usiness **A**nalytics **T**eam
(WOMBAT) events, published at <https://numbats.github.io/WOMBAT/>.

Every WOMBAT event lives in its own repo (`numbats/WOMBAT<YEAR>`) with its
own website. This repo aggregates those sites into one place:

- the current event's site is served at the root, so
  `numbats.github.io/WOMBAT/` always shows the upcoming/active WOMBAT, and
- every year's site stays reachable at `numbats.github.io/WOMBAT/<YEAR>/`.

## How it works

This repo has two branches with different jobs:

- **`main`** -- documentation, the [event config](wombat-events.yml), and the
  GitHub Actions workflow that keeps `gh-pages` in sync. Nothing here is
  served as a website.
- **`gh-pages`** -- the published site. Each event is a git submodule at
  `/<YEAR>/`, pointing at that event repo's site branch. The active event's
  submodule is additionally mirrored up to the branch root by the sync
  workflow, so it's both `/` and `/<YEAR>/`.

[`wombat-events.yml`](wombat-events.yml) is the source of truth for which
repos/branches are included and which year is active:

```yaml
active: 2026

events:
  2026:
    repo: numbats/WOMBAT2026
    branch: gh-pages
  2025:
    repo: numbats/WOMBAT2025
    branch: gh-pages
  2024:
    repo: numbats/WOMBAT2024
    branch: main   # WOMBAT2024 publishes from main rather than gh-pages
```

### Keeping gh-pages in sync

[`.github/workflows/update-gh-pages.yml`](.github/workflows/update-gh-pages.yml)
does the syncing: it reconciles the `gh-pages` branch's submodules against
`wombat-events.yml` (adding/removing/repointing as needed), updates every
submodule to the latest commit on its tracked branch, mirrors the active
year to the site root, and pushes the result -- only if anything actually
changed. It runs on:

- **`repository_dispatch`** (`gh-pages-updated`) -- sent by an event repo
  right after it publishes, for a near-immediate update. See
  [`docs/source-repo-workflow.yml`](docs/source-repo-workflow.yml) for the
  workflow to add to an event repo, and the setup steps in its header
  (it needs a `WOMBAT_HUB_TOKEN` secret in that repo able to dispatch to
  this one -- not something this repo can set up on another repo's behalf).
- **a schedule** (every 6 hours) -- a fallback poll, so things stay eventually
  consistent even for a repo that isn't wired up to dispatch, or if a
  dispatch is missed.
- **`workflow_dispatch`** -- for a manual run (`gh workflow run update-gh-pages.yml`).
- **push to `main`** touching `wombat-events.yml` or the sync scripts -- so
  editing the config (e.g. bumping `active`) takes effect right away.

### Adding a new WOMBAT year

1. Add an entry for it under `events:` in `wombat-events.yml`, and update
   `active` once its site is ready to be the front page.
2. Merge to `main`. The workflow run this triggers adds the new submodule,
   drops the previous active year's root mirror, and republishes the new
   active year at root.
3. Optionally add the [notify workflow](docs/source-repo-workflow.yml) to
   the new event repo so it pushes updates to this hub immediately instead
   of waiting for the next scheduled poll.

## Local development

The scripts the workflow runs are plain Python (`pip install pyyaml`) and
can be run by hand against a second checkout of `gh-pages` (mirroring what
the workflow does with its `main`/`site` checkouts):

```sh
git worktree add ../WOMBAT-site gh-pages
cd ../WOMBAT-site
python ../WOMBAT/scripts/sync_config.py ../WOMBAT/wombat-events.yml
git submodule sync --recursive
git submodule update --init --remote --recursive
python ../WOMBAT/scripts/publish_root.py ../WOMBAT/wombat-events.yml
```
