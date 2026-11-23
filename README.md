# Azure AI Hub

Static site for Azure AI guides and articles, built with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

Published at [https://baoqger.github.io/home/](https://baoqger.github.io/home/) when GitHub Pages is enabled for this repository.

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
.\scripts\dev.ps1 -Open
```

Or without the helper script:

```powershell
.\.venv\Scripts\mkdocs serve
```

Open the URL shown in the terminal (default `http://127.0.0.1:8000/`).

### Live reload (hot reload)

`mkdocs serve` **rebuilds and refreshes the browser automatically** when watched files change (livereload). You do **not** need a separate file watcher unless you turned livereload off.

| What | Watched by default |
|------|-------------------|
| Posts, `articles/index.md`, `articles/blog/` | Yes (`docs_dir: articles`) |
| [`images/`](images/) | Yes — [`watch`](mkdocs.yml) + [`scripts/dev.ps1`](scripts/dev.ps1) |
| [`mkdocs_hooks/`](mkdocs_hooks/) | Yes — same |
| [`mkdocs.yml`](mkdocs.yml) | Yes |

**Recommended dev command** (opens browser, faster incremental rebuilds):

```powershell
.\scripts\dev.ps1 -Open -Dirty
```

| Flag | Effect |
|------|--------|
| `-Open` | Open the site in your browser after the first build |
| `-Dirty` | Only rebuild changed pages (faster while editing one post) |
| `-NoLiveReload` | Rebuild on save but **no** auto browser refresh |
| `-DevAddr "0.0.0.0:8000"` | Listen on all interfaces (e.g. test from another device) |

After running `obsidian2hub`, saving a post under `articles/posts/` or an image under `images/` should trigger a reload within a second or two. If the tab does not refresh, hard-refresh once and confirm you did not pass `-NoLiveReload`.

Disable the Material EOL banner in the terminal (optional):

```powershell
$env:NO_MKDOCS_2_WARNING = "1"
.\scripts\dev.ps1 -Open -Dirty
```

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

1. **Import** (`obsidian2hub`): Copies the vault **body** unchanged (including `![[image.png]]`) into `articles/posts/`, adds blog YAML (including **one category** you provide), and copies assets into `images/`.
2. **Build** (`mkdocs build`): The [`mkdocs_hooks/obsidian.py`](mkdocs_hooks/obsidian.py) hook converts Obsidian embeds at build time and bundles `images/`.

Example import:

```powershell
.\.cursor\skills\obsidian2hub\scripts\copy-note.ps1 -NoteTitle "My Note Title" -Category "Security"
```

Author identifiers in front matter must exist in [`articles/blog/.authors.yml`](articles/blog/.authors.yml) (default `chris-bao`).

## CI and deployment

The [`.github/workflows/docs.yml`](.github/workflows/docs.yml) workflow:

- On pull requests: install deps, run tests, `mkdocs build --strict`, upload `site/` as an artifact.
- On push to `main`: build and deploy to the `gh-pages` branch via GitHub Actions.

Enable **GitHub Pages** for this repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

## Python version

Use **Python 3.10+** (3.12 recommended; matches CI).