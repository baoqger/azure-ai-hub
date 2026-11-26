param(
    [Parameter(Mandatory = $true)]
    [string] $NoteTitle,

    [Parameter(Mandatory = $true)]
    [string] $Category,

    [string] $VaultRoot = "C:\Users\JBao6\Documents\obsidian-vault\OrgPro",

    [string] $RepoRoot = "",

    [string] $DefaultAuthor = "chris-bao"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir "..\..\..\..")).Path
}

$articlesDir = Join-Path (Join-Path $RepoRoot "articles") "posts"
$imagesDir = Join-Path $RepoRoot "images"

if (-not (Test-Path -LiteralPath $VaultRoot)) {
    throw "Vault root not found: $VaultRoot"
}

$category = $Category.Trim()
if ([string]::IsNullOrWhiteSpace($category)) {
    throw "Category is required (one category per article)."
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

function Get-NoteBodyWithoutFrontMatter {
    param([string] $Path)

    $raw = [System.IO.File]::ReadAllText($Path)
    if ($raw.Length -ge 1 -and [int][char]$raw[0] -eq 0xFEFF) {
        $raw = $raw.Substring(1)
    }

    if ($raw -match '^(?s)\s*---\r?\n.*?\r?\n---\r?\n?') {
        return $raw.Substring($Matches[0].Length)
    }
    return $raw
}

function Get-ExistingPostMeta {
    param([string] $Path)

    $result = @{
        date = $null
        authors = @()
    }

    if (-not (Test-Path -LiteralPath $Path)) { return $result }

    $raw = [System.IO.File]::ReadAllText($Path)
    if ($raw -notmatch '^(?s)\s*---\r?\n(.*?)\r?\n---') { return $result }

    $yaml = $Matches[1]
    if ($yaml -match '(?m)^date:\s*(.+)\s*$') {
        $result.date = $Matches[1].Trim().Trim("`'""").Trim()
    }

    $inAuthors = $false
    foreach ($line in ($yaml -split '\r?\n')) {
        if ($line -match '^authors:\s*$') {
            $inAuthors = $true
            continue
        }
        if ($inAuthors) {
            if ($line -match '^\s+-\s+(.+)\s*$') {
                $result.authors += $Matches[1].Trim().Trim("`'""").Trim()
                continue
            }
            if ($line -match '^[^\s#]') { $inAuthors = $false }
        }
    }

    return $result
}

function Remove-ObsidianTagLines {
    param([string] $Body)

    if ([string]::IsNullOrEmpty($Body)) { return $Body }

    $pattern = '^\s*(?:#[^\s#]+)(?:\s+#[^\s#]+)*\s*$'
    $lines = $Body -split '\r?\n'
    $kept = foreach ($line in $lines) {
        if ($line -match $pattern) { continue }
        $line
    }
    while ($kept.Count -gt 0 -and [string]::IsNullOrWhiteSpace($kept[0])) {
        $kept = $kept[1..($kept.Count - 1)]
    }
    $joined = $kept -join "`n"
    if ($Body.EndsWith("`n")) { return $joined + "`n" }
    return $joined
}

function Remove-AboutAuthorSection {
    param([string] $Body)

    if ([string]::IsNullOrEmpty($Body)) { return $Body }

    $pattern = '(?im)^#{1,4}\s+About\s+(?:the\s+)?author\s*$'
    $match = [regex]::Match($Body, $pattern)
    if (-not $match.Success) { return $Body }

    $lines = $Body.Substring(0, $match.Index) -split '\r?\n'
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[-1])) {
        $lines = $lines[0..($lines.Count - 2)]
    }
    while ($lines.Count -gt 0 -and $lines[-1].Trim() -eq '---') {
        $lines = $lines[0..($lines.Count - 2)]
    }
    while ($lines.Count -gt 0 -and [string]::IsNullOrWhiteSpace($lines[-1])) {
        $lines = $lines[0..($lines.Count - 2)]
    }
    $joined = ($lines -join "`n").TrimEnd()
    if ($Body.EndsWith("`n")) { return $joined + "`n" }
    return $joined
}

function Build-PostMarkdown {
    param(
        [string] $Body,
        [string] $PostTitle,
        [string] $CategoryName,
        [string] $Date,
        [string[]] $Authors
    )

    $authorLines = ($Authors | ForEach-Object { "  - $_" }) -join "`n"
    $front = @"
---
date: $Date
authors:
$authorLines
categories:
  - $CategoryName
title: $PostTitle
---
"@.TrimEnd()

    if ($Body.Length -gt 0 -and $Body[0] -ne "`n" -and $Body[0] -ne "`r") {
        $front += "`n"
    }
    return $front + $Body
}

$note = $matches[0]
$destMd = Join-Path $articlesDir $note.Name
$body = Get-NoteBodyWithoutFrontMatter -Path $note.FullName
$body = Remove-ObsidianTagLines $body
$body = Remove-AboutAuthorSection $body

$existing = Get-ExistingPostMeta -Path $destMd
$postDate = $existing.date
if (-not $postDate) {
    $postDate = $note.LastWriteTime.ToString("yyyy-MM-dd")
}
$authors = @($existing.authors)
if ($authors.Count -eq 0) {
    $authors = @($DefaultAuthor)
}

$postTitle = $note.BaseName
$merged = Build-PostMarkdown -Body $body -PostTitle $postTitle -CategoryName $category `
    -Date $postDate -Authors $authors

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($destMd, $merged, $utf8NoBom)

$content = $body

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
Write-Output "Category: $category"
$newCopies = @($copied | Where-Object { $_ -notlike '[skip identical]*' })
Write-Output "Images: $($newCopies.Count) new, $($copied.Count) total refs ($($copied -join ', '))"
if ($missing.Count -gt 0) {
    Write-Output "Missing assets: $($missing -join ', ')"
}