# Azure AI Hub

Static site for Azure AI guides and articles, built with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

Published at [https://baoqger.github.io/azure-ai-hub/](https://baoqger.github.io/azure-ai-hub/) when GitHub Pages is enabled for this repository.

## Repository layout

| Path | Purpose |
|------|---------|
| [`articles/`](articles/) | MkDocs `docs_dir`: home page, blog index, and post sources |
| [`articles/posts/`](articles/posts/) | Blog posts (imported from Obsidian) |
| [`images/`](images/) | Images referenced by posts |
| [`mkdocs_hooks/`](mkdocs_hooks/) | Build-time Obsidian `![[...]]` transform and image bundling |
| [`.cursor/skills/obsidian2hub/`](.cursor/skills/obsidian2hub/) | Import notes from Obsidian into `articles/posts/` + `images/` |

## Local development

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\mkdocs serve
```

Open the URL shown in the terminal (default `http://127.0.0.1:8000/`).

Production build:

```powershell
.\.venv\Scripts\mkdocs build --strict
```

Output is written to [`site/`](site/) (gitignored).

Run hook unit tests:

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## Obsidian import vs. site build

1. **Import** (`obsidian2hub`): Copies vault markdown **unchanged** (including `![[image.png]]`) into `articles/posts/` and assets into `images/`.
2. **Build** (`mkdocs build`): The [`mkdocs_hooks/obsidian.py`](mkdocs_hooks/obsidian.py) hook converts Obsidian embeds to site-root image URLs and copies `images/` into the static output. Source files in git are not modified.

### Blog metadata for new posts

After importing a post, add YAML front matter at the top of the file in `articles/posts/` (not in Obsidian unless you want it round-tripped):

```yaml
---
date: 2026-11-08
authors:
  - chris-bao
categories:
  - Azure
title: Your post title
---
```

Author identifiers must exist in [`articles/blog/.authors.yml`](articles/blog/.authors.yml).

## CI and deployment

The [`.github/workflows/docs.yml`](.github/workflows/docs.yml) workflow:

- On pull requests: install deps, run tests, `mkdocs build --strict`, upload `site/` as an artifact.
- On push to `main`: build and deploy to the `gh-pages` branch via GitHub Actions.

Enable **GitHub Pages** for this repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Python version

Use **Python 3.10+** (3.12 recommended; matches CI).