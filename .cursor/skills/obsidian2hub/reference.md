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
| Note already in `articles/` | Overwrite only if user asked to refresh; otherwise ask |

## Encoding

Read/write as UTF-8 without BOM when using .NET APIs; `Copy-Item` is preferred for the markdown file to preserve original bytes.