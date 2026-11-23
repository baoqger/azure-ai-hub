"""MkDocs hooks: Obsidian embeds and repo-level images/."""

from __future__ import annotations

import re
from pathlib import Path

from mkdocs.utils import get_relative_url

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

def _repo_root(config) -> Path:
    return Path(config.config_file_path).resolve().parent


def image_href(asset_name: str, doc_src_uri: str) -> str:
    """Link from a doc file to a repo-level image (see on_files)."""
    name = asset_name.strip().replace("\\", "/")
    image_url = f"images/{name}"
    return get_relative_url(image_url, doc_src_uri)


def transform_obsidian_embeds(markdown: str, doc_src_uri: str = "") -> str:
    """Convert Obsidian ![[file]] embeds to standard markdown images."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if doc_src_uri:
            href = image_href(name, doc_src_uri)
        else:
            href = f"images/{name.replace(chr(92), '/')}"
        return f"![]({href})"

    return OBSIDIAN_EMBED_RE.sub(repl, markdown)


def on_page_markdown(markdown, page, config, files):
    doc_src_uri = page.file.src_uri if page.file else ""
    return transform_obsidian_embeds(markdown, doc_src_uri=doc_src_uri)


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