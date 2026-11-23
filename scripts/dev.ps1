# Local dev server with live reload (livereload is on unless you pass -NoLiveReload).
param(
    [string] $DevAddr = "127.0.0.1:8000",
    [switch] $Open,
    [switch] $NoLiveReload,
    [switch] $Dirty
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Mkdocs = Join-Path $Root ".venv\Scripts\mkdocs.exe"
if (-not (Test-Path $Mkdocs)) {
    throw "Run 'python -m venv .venv' and 'pip install -r requirements.txt' first."
}

$args = @(
    "serve",
    "--dev-addr", $DevAddr,
    "--watch-theme"
)

if ($Open) { $args += "-o" }
if ($NoLiveReload) { $args += "--no-livereload" }
if ($Dirty) { $args += "--dirty" }

# watch paths in mkdocs.yml (images, mkdocs_hooks); repeat here if config changes are not picked up.
$args += "-w", (Join-Path $Root "images")
$args += "-w", (Join-Path $Root "mkdocs_hooks")

& $Mkdocs @args