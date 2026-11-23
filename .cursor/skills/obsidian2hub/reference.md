# obsidian2hub reference

## Title → file mapping

| User input | Resolution |
|------------|------------|
| Exact note title | `*.md` whose base name equals the title (case-insensitive on Windows) |
| Title with `.md` suffix | Strip `.md`, then same as above |

## Image extraction regex

**Obsidian embeds** (capture group 1 = asset spec before optional `|`):

```regex
!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]
```

**Markdown images**:

```regex
!\[[^\]]*\]\(([^)]+)\)
```

For markdown paths, strip optional `<>` wrappers and ignore `http://` / `https://` URLs.

## Vault file resolution order

For each asset reference `name`:

1. If `name` is a relative path from the note, resolve from the note’s directory.
2. `Join-Path $VaultRoot "images" $leaf`
3. `Join-Path $VaultRoot $leaf`
4. `Get-ChildItem -Path $VaultRoot -Recurse -File -Filter $leaf` (exclude `.obsidian`), first match

`$leaf` is the file name portion of the reference (e.g. `Pasted image 20261118103207.png`).

## Conflicts

| Case | Action |
|------|--------|
| Duplicate image file name, same bytes | Skip copy |
| Duplicate image file name, different bytes | Stop and ask user |
| Note already in `articles/posts/` | Overwrite only if user asked to refresh; otherwise ask |

## Blog front matter (import)

Written by `copy-note.ps1` (not part of the vault body):

```yaml
---
date: yyyy-MM-dd
authors:
  - chris-bao
categories:
  - <single category from user>
title: <vault file base name>
---
```

- **One category only** — `categories` has exactly one list item.
- Re-import keeps existing `date` and `authors` when the post file already exists; **category** and **body** come from the current import (category from user, body from vault).

## Encoding

Post files are written UTF-8 without BOM. Image files use `Copy-Item`.