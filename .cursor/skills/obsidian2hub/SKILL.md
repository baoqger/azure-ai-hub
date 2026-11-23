---
name: obsidian2hub
description: Copies a note from the local Obsidian vault into articles/posts/ with one blog category, copies images to images/, and leaves the vault markdown body unchanged. Use when the user gives an Obsidian note title and category, says obsidian2hub, or asks to import a vault note into azure-ai-hub.
---

# Obsidian → Azure AI Hub

Import one Obsidian note into this repository.

- **Body:** Same content as the vault file (any vault YAML front matter is stripped; the note body is not rewritten).
- **Blog front matter:** Added for MkDocs Material (`date`, `authors`, `title`, **one** `categories` entry).

## Required inputs

| Input | Rule |
|-------|------|
| **Note title** | Exact vault file base name (without `.md`) |
| **Category** | **Required.** Exactly **one** category string per article (e.g. `Security`, `Agents`) |

If the user omits a category, **ask for it** before importing.

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

2. **Confirm category** — use the category the user supplied; one category only.

3. **Write markdown**
   - Target: `articles/posts/<same-filename-as-vault>.md`
   - Strip leading YAML from the vault file if present; keep the body as in Obsidian.
   - Prepend MkDocs blog front matter:
     - `date`: vault note last-write date (`yyyy-MM-dd`), or keep existing `date` when re-importing the same post file
     - `authors`: `chris-bao` by default, or keep existing authors on re-import
     - `categories`: single list item — the user's category
     - `title`: vault file base name
   - Do not change the body text (no link or embed rewrites).

4. **Copy images**
   - Parse the **body** for embeds only:
     - Obsidian: `![[asset]]` and `![[asset|width]]`
     - Markdown: `![](path)` and `![alt](path)`
   - Resolve each asset under the vault (note dir → vault `images/` → vault-wide by file name).
   - Copy to `images/<original-filename>` (flat layout).
   - If a target already exists, compare hashes; skip when identical, otherwise ask the user before overwriting.

5. **Report**
   - Vault source path
   - Destination path, **category**
   - Images copied (and any missing assets)

## Preferred automation

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".cursor/skills/obsidian2hub/scripts/copy-note.ps1" -NoteTitle "<title>" -Category "<category>"
```

Optional parameters:

```powershell
-VaultRoot "C:\path\to\vault"
-RepoRoot "C:\develop\open-source\azure-ai-hub"
-DefaultAuthor "chris-bao"
```

## Manual fallback

If the script cannot run:

1. Locate the `.md` file per step 1.
2. Copy the body (without vault front matter) to `articles/posts/`.
3. Add the YAML front matter block with the user's **one** category.
4. Copy embed assets to `images/` per step 4.
5. Do not rewrite Obsidian image syntax in the body.

## Image link behavior

Imported notes may use Obsidian wiki syntax (e.g. `![[Pasted image ....png]]`). **Leave as-is** in the body. MkDocs hooks convert embeds at build time.

## Additional reference

Vault search order, regex, and conflicts: [reference.md](reference.md)