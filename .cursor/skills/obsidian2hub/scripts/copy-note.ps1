param(
    [Parameter(Mandatory = $true)]
    [string] $NoteTitle,

    [string] $VaultRoot = "C:\Users\JBao6\Documents\obsidian-vault\OrgPro",

    [string] $RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
}

$articlesDir = Join-Path $RepoRoot "articles"
$imagesDir = Join-Path $RepoRoot "images"

if (-not (Test-Path -LiteralPath $VaultRoot)) {
    throw "Vault root not found: $VaultRoot"
}

New-Item -ItemType Directory -Force -Path $articlesDir, $imagesDir | Out-Null

$title = $NoteTitle.Trim()
if ($title.EndsWith(".md", [System.StringComparison]::OrdinalIgnoreCase)) {
    $title = $title.Substring(0, $title.Length - 3)
}

$mdFiles = Get-ChildItem -LiteralPath $VaultRoot -Recurse -Filter "*.md" -File |
    Where-Object { $_.FullName -notmatch '[\\/]\.obsidian[\\/]' }

$matches = @($mdFiles | Where-Object { $_.BaseName -ieq $title })

if ($matches.Count -eq 0) {
  $suggest = $mdFiles | Where-Object { $_.BaseName -like "*$title*" } | Select-Object -First 10
  $msg = "No note with base name '$title' under $VaultRoot."
  if ($suggest) {
    $msg += "`nSimilar: " + (($suggest | ForEach-Object { $_.FullName }) -join "`n")
  }
  throw $msg
}

if ($matches.Count -gt 1) {
  $list = ($matches | ForEach-Object { $_.FullName }) -join "`n"
  throw "Multiple notes match '$title'. Pick one:`n$list"
}

$note = $matches[0]
$destMd = Join-Path $articlesDir $note.Name
Copy-Item -LiteralPath $note.FullName -Destination $destMd -Force

$content = Get-Content -LiteralPath $note.FullName -Raw -Encoding UTF8

$assets = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

foreach ($m in [regex]::Matches($content, '!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]')) {
    [void]$assets.Add($m.Groups[1].Value.Trim())
}
foreach ($m in [regex]::Matches($content, '!\[[^\]]*\]\(([^)]+)\)')) {
    $p = $m.Groups[1].Value.Trim().Trim('"').Trim("'")
    if ($p -match '^(https?://|data:)') { continue }
    $p = $p.TrimStart('<').TrimEnd('>')
    [void]$assets.Add($p)
}

function Get-FileHashHex {
    param([string] $Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Resolve-VaultAsset {
    param([string] $Ref, [string] $NoteDir, [string] $Root)

    $leaf = [System.IO.Path]::GetFileName($Ref)
    if ([string]::IsNullOrWhiteSpace($leaf)) { return $null }

    $candidates = @()
    if ($Ref -match '[\\/]') {
        $candidates += Join-Path $NoteDir $Ref
    }
    $candidates += Join-Path (Join-Path $Root "images") $leaf
    $candidates += Join-Path $Root $leaf

    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c -PathType Leaf) { return (Resolve-Path -LiteralPath $c).Path }
    }

    $found = Get-ChildItem -LiteralPath $Root -Recurse -File -Filter $leaf -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '[\\/]\.obsidian[\\/]' } |
        Select-Object -First 1

    if ($found) { return $found.FullName }
    return $null
}

$noteDir = Split-Path -Parent $note.FullName
$copied = @()
$missing = @()

foreach ($ref in $assets) {
    $src = Resolve-VaultAsset -Ref $ref -NoteDir $noteDir -Root $VaultRoot
    if (-not $src) {
        $missing += $ref
        continue
    }

    $leaf = [System.IO.Path]::GetFileName($src)
    $dest = Join-Path $imagesDir $leaf

    if (Test-Path -LiteralPath $dest) {
        if ((Get-FileHashHex $src) -eq (Get-FileHashHex $dest)) {
            $copied += "[skip identical] $leaf"
            continue
        }
        throw "Image conflict: $dest exists with different content than $src"
    }

    Copy-Item -LiteralPath $src -Destination $dest
    $copied += $leaf
}

Write-Output "Note: $($note.FullName) -> $destMd"
$newCopies = @($copied | Where-Object { $_ -notlike '[skip identical]*' })
Write-Output "Images: $($newCopies.Count) new, $($copied.Count) total refs ($($copied -join ', '))"
if ($missing.Count -gt 0) {
    Write-Output "Missing assets: $($missing -join ', ')"
}