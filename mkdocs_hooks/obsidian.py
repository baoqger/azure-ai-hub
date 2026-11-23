"""MkDocs hooks: Obsidian embeds and repo-level images/."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

def _repo_root(config) -> Path:
    return Path(config.config_file_path).resolve().parent


def _to_site_image_path(asset_name: str) -> str:
    """Site-root image URL; encodes spaces and special characters."""
    # Preserve subpaths if present; encode each segment.
    parts = asset_name.replace("\\", "/").split("/")
    encoded = "/".join(quote(part, safe="") for part in parts)
    return f"/images/{encoded}"


def transform_obsidian_embeds(markdown: str) -> str:
    """Convert Obsidian ![[file]] embeds to standard markdown images."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        return f"![]({_to_site_image_path(name)})"

    return OBSIDIAN_EMBED_RE.sub(repl, markdown)


def on_page_markdown(markdown, page, config, files):
    return transform_obsidian_embeds(markdown)


def on_files(files, config):
    from mkdocs.structure.files import File, InclusionLevel

    root = _repo_root(config)
    images_dir = root / "images"
    if not images_dir.is_dir():
        return files

    for path in sorted(images_dir.iterdir()):
        if not path.is_file():
            continue
        rel = f"images/{path.name}"
        if files.get_file_from_path(rel) is not None:
            continue
        files.append(
            File(
                rel,
                str(root),
                config.site_dir,
                config.use_directory_urls,
                inclusion=InclusionLevel.INCLUDED,
            )
        )

    return files