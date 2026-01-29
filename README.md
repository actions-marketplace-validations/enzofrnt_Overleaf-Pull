# Overleaf Pull

GitHub Action that downloads an Overleaf project (zip) and extracts it into a directory. Uses a small Docker image (uv + Python) and your Overleaf session cookie for authentication.

## Inputs

| Input       | Required | Description |
|------------|----------|-------------|
| `project_id` | Yes    | Overleaf project ID (from the project URL). |
| `cookie`     | Yes    | Session cookie value (`overleaf.sid`). Store as a secret. |
| `base_url`   | Yes    | Overleaf base URL, e.g. `https://overleaf.example.com` or `overleaf.example.com`. |
| `output_dir` | No     | Directory where to extract the project (default: `overleaf-project`). |

## Getting credentials

- **Project ID**: In Overleaf, open your project and check the URL: `https://…/project/<project_id>`.
- **Cookie**: Log in to Overleaf in your browser, open DevTools → Application (or Storage) → Cookies, and copy the value of `overleaf.sid`. It may be URL-encoded (e.g. `s%3A…`).
- **Base URL**: Your Overleaf instance URL, with or without `https://` (the action adds it if missing).

## Example: sync Overleaf to repo root

This workflow makes the repo root reflect the Overleaf project: on each run it pulls the project, replaces the root content (keeping `.github/` and `.git/`), then commits and pushes.

**Secrets:** `OVERLEAF_PROJECT_ID`, `OVERLEAF_COOKIE`, `OVERLEAF_HOST`

```yaml
name: Sync Overleaf Project to repo

on:
  workflow_dispatch:
  # Uncomment for automatic sync. Example: every 30 minutes.
  # Not recommended: frequent runs can cause merge conflicts if edits happen in both Overleaf and the repo; use workflow_dispatch if you don't handle conflicts.
  # schedule:
  #   - cron: "*/30 * * * *"

jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Pull Overleaf into temporary directory
        uses: enzofrnt/overleaf-pull@1.0.3
        with:
          project_id: ${{ secrets.OVERLEAF_PROJECT_ID }}
          cookie: ${{ secrets.OVERLEAF_COOKIE }}
          base_url: ${{ secrets.OVERLEAF_HOST }}
          output_dir: .overleaf-sync

      - name: Replace root with Overleaf project (keep .github and .git)
        run: |
          # Remove everything at root except .github, .git and the temp directory
          find . -maxdepth 1 ! -name '.' ! -name '..' ! -name '.github' ! -name '.git' ! -name '.overleaf-sync' -exec rm -rf {} +
          # Copy Overleaf content to root (including hidden files)
          cp -r .overleaf-sync/. .
          # Remove temp directory (created by container as root)
          sudo rm -rf .overleaf-sync

      - name: Commit and push if changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          if git diff --staged --quiet; then
            echo "No changes to commit."
          else
            git commit -m "chore: sync from Overleaf [skip ci]"
            git push
          fi
```

## Minimal example (extract to a folder)

```yaml
- uses: enzofrnt/overleaf-pull@1.0.3
  with:
    project_id: ${{ secrets.OVERLEAF_PROJECT_ID }}
    cookie: ${{ secrets.OVERLEAF_COOKIE }}
    base_url: ${{ secrets.OVERLEAF_HOST }}
    output_dir: my-overleaf-project
```

Add a checkout step before this if you need the repo contents. The project will be in `my-overleaf-project/` (or whatever `output_dir` you set).

## Local usage (CLI)

From the repo root, with Python 3 and `requests` installed:

```bash
pip install -r Overleaf-Pull/requirements.txt
python3 Overleaf-Pull/overleaf_pull.py "<project_id>" "<cookie>" "<base_url>" -o ./output
```

Cookie can be the raw value (e.g. `s%3A…`) or the full header `overleaf.sid=…`. `base_url` can omit `https://`.
