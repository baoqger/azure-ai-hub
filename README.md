# Azure AI Hub

Static site for Azure AI guides and articles, built with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

Published via [Azure Static Web Apps](https://learn.microsoft.com/azure/static-web-apps/) (see CI workflow). Set [`site_url`](mkdocs.yml) to your SWA hostname (e.g. `https://<app-name>.azurestaticapps.net/`).

## Repository layout

| Path | Purpose |
|------|---------|
| [`articles/`](articles/) | MkDocs `docs_dir`: home page, blog index, and post sources |
| [`articles/posts/`](articles/posts/) | Blog posts (imported from Obsidian) |
| [`images/`](images/) | Images referenced by posts |
| [`mkdocs_hooks/`](mkdocs_hooks/) | Build-time Obsidian `![[...]]` transform and image bundling |
| [`api/`](api/) | Minimal SWA managed API (`GET /api/health`); enables portal Application Insights for the Functions backend |
| [`staticwebapp.config.json`](staticwebapp.config.json) | SWA platform settings (`apiRuntime`); copied into `site/` at deploy |
| [`.cursor/skills/obsidian2hub/`](.cursor/skills/obsidian2hub/) | Import notes from Obsidian into `articles/posts/` + `images/` |

## Local development

One-time setup:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

**Hot reload** (auto browser refresh on save, incremental rebuilds):

```powershell
.\scripts\dev.ps1 -Open -Dirty
```

Open `http://127.0.0.1:8000/` if the browser did not open automatically.

Equivalent without the helper script:

```powershell
.\.venv\Scripts\mkdocs serve -o --dirty --watch-theme -w images -w mkdocs_hooks
```

### Live reload (hot reload)

`mkdocs serve` **rebuilds and refreshes the browser automatically** when watched files change (livereload). You do **not** need a separate file watcher unless you turned livereload off.

| What | Watched by default |
|------|-------------------|
| Posts, `articles/index.md`, `articles/blog/` | Yes (`docs_dir: articles`) |
| [`images/`](images/) | Yes — [`watch`](mkdocs.yml) + [`scripts/dev.ps1`](scripts/dev.ps1) |
| [`mkdocs_hooks/`](mkdocs_hooks/) | Yes — same |
| [`mkdocs.yml`](mkdocs.yml) | Yes |

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

A single workflow builds and deploys the site:

[`.github/workflows/azure-static-web-apps-polite-pond-0d22a6d0f.yml`](.github/workflows/azure-static-web-apps-polite-pond-0d22a6d0f.yml)

| Trigger | What runs |
|---------|-----------|
| **Push to `main`** | `pip install` → unit tests → `mkdocs build --strict` → deploy `site/` to Azure Static Web Apps |
| **Pull request** | Same build; SWA creates a **staging** preview; closing the PR runs the close job |

The deploy step uses `skip_app_build: true` and uploads the pre-built `site/` folder (MkDocs output).

**Requirements in GitHub:** secret `AZURE_STATIC_WEB_APPS_API_TOKEN_POLITE_POND_0D22A6D0F` (injected when the SWA resource is linked to this repo).

**Azure portal:** Static Web App → **Configuration** → set `site_url` in [`mkdocs.yml`](mkdocs.yml) to match **Overview → URL** (or your custom domain).

## Page views (Application Insights)

Production builds embed the [Application Insights JavaScript SDK](https://learn.microsoft.com/azure/azure-monitor/app/javascript-sdk) loader. It records **page views** per URL; new posts do not require analytics changes.

| Scope | Behavior |
|-------|----------|
| **Production** (`main` deploy) | CI sets `APPLICATIONINSIGHTS_CONNECTION_STRING` during `mkdocs build`; telemetry runs only on the host from `site_url` in `mkdocs.yml`. |
| **Local `mkdocs serve` / PR builds** | No connection string in the build → no telemetry script (or empty stub). |

**GitHub (production):** **Settings → Secrets and variables → Actions** → `APPLICATIONINSIGHTS_CONNECTION_STRING` (from Application Insights → **Overview** → connection string).

Verify in Azure: Application Insights → **Usage** → page views, or **Live metrics** after visiting the deployed site.

This is **client-side RUM**, separate from SWA server-side monitoring.

### Link SWA to Application Insights (API)

After the minimal [`api/`](api/) app is deployed (`api_location: api` in CI):

1. Azure portal → your **Static Web App** → **Application Insights** → **Yes** → select the same App Insights resource you created → **Save**.
2. Smoke test: `https://<your-swa-host>/api/health` should return `{"status":"ok","service":"azure-ai-hub"}`.

That portal toggle reports **API/server** telemetry (requests, failures, traces). **Blog page views** still come from the JavaScript loader above.

Local API (optional): install [Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local) and Node 20+, then run `npm install` in `api/` and `func start` from `api/`, or use the [Static Web Apps CLI](https://learn.microsoft.com/azure/static-web-apps/static-web-apps-cli) with `--api-location api`.

## Python version

Use **Python 3.10+** (3.12 recommended; matches CI).