---
name: obsidian2hub
description: Copies a note from the local Obsidian vault into this repo unchanged (articles/posts/) and copies referenced image assets into images/. Use when the user gives an Obsidian note title, says obsidian2hub, or asks to import or sync a vault note into azure-ai-hub.
---

# Obsidian → Azure AI Hub

Import one Obsidian note into this repository. **Do not edit the markdown body** after copy—byte-identical to the vault file.

## Layout

| Destination | Path (repo root) |
|-------------|------------------|
| Markdown | `articles/posts/` |
| Images | `images/` |

## Default vault

Unless the user gives another path, search notes in:

`C:\Users\JBao6\Documents\obsidian-vault\OrgPro`

Override with an absolute vault root when the user specifies one.

## Workflow

1. **Resolve the note** from the title the user provided:
   - Match the note **file base name** (filename without `.md`) to the title.
   - On Windows, compare case-insensitively; require an exact base-name match (not substring).
   - Search recursively under the vault root (exclude `.obsidian`).
   - If **0** matches: list close base-name matches and ask the user.
   - If **>1** match: show full paths and ask which file to use.

2. **Copy markdown**
   - Target: `articles/posts/<same-filename-as-vault>.md`
   - Use raw file copy (preserve encoding and line endings). Do not reformat or rewrite.

3. **Copy images**
   - Parse the note for embeds only (do not modify the file):
     - Obsidian: `![[asset]]` and `![[asset|width]]`
     - Markdown: `![](path)` and `![alt](path)`
   - For each asset name/path, resolve the file under the vault:
     - Same directory as the note, then vault `images/`, then vault-wide search by **file name** (Obsidian often stores embeds by basename only).
   - Copy each resolved file to `images/<original-filename>` (flat layout).
   - If a target already exists, compare hashes; skip when identical, otherwise ask the user before overwriting.

4. **Report**
   - Vault source path
   - `articles/posts/` and `images/` paths written
   - List of images copied (and any referenced assets not found in the vault)

## Preferred automation

From the repository root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".cursor/skills/obsidian2hub/scripts/copy-note.ps1" -NoteTitle "<title>"
```

Optional parameters:

```powershell
-VaultRoot "C:\path\to\vault"
-RepoRoot "C:\develop\open-source\azure-ai-hub"
```

The script copies markdown without changes and copies images; it does not rewrite links in the note.

## Manual fallback

If the script cannot run:

1. Locate the `.md` file per step 1.
2. `Copy-Item` the note to `articles/posts/`.
3. Extract embeds with regex; `Copy-Item` each resolved image to `images/`.
4. Never run find-replace on the markdown for this task.

## Image link behavior

Imported notes may still use Obsidian wiki syntax (e.g. `![[Pasted image ....png]]`). **Leave as-is** per project rule. Publishing tooling in this repo is responsible for resolving those references if needed.

## Additional reference

Vault-specific search order and regex details: [reference.md](reference.md)