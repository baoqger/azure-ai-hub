"""MkDocs hooks: Obsidian embeds and repo-level images/."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import quote
from typing import Any

from mkdocs.utils import get_relative_url

ENV_MEDIA_BASE_URL = "AZURE_MEDIA_BASE_URL"

OBSIDIAN_EMBED_RE = re.compile(r"!\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
# Obsidian inline tags: one line of `#tag` tokens (no space after `#`), not ATX headings.
OBSIDIAN_TAG_LINE_RE = re.compile(r"^\s*(?:#[^\s#]+)(?:\s+#[^\s#]+)*\s*$")
ABOUT_AUTHOR_HEADING_RE = re.compile(
    r"^#{1,4}\s+About\s+(?:the\s+)?author\s*$",
    re.IGNORECASE | re.MULTILINE,
)

def _repo_root(config) -> Path:
    return Path(config.config_file_path).resolve().parent


def get_media_base_url(config: Any) -> str:
    """Blob/CDN base URL for article images. Env overrides mkdocs extra."""
    env = os.environ.get(ENV_MEDIA_BASE_URL, "").strip()
    if env:
        return env.rstrip("/")
    extra = getattr(config, "extra", None) or {}
    value = extra.get("media_base_url")
    if not value:
        return ""
    return str(value).strip().rstrip("/")


def normalize_image_asset_name(asset_name: str) -> str:
    """Strip optional leading `images/` from Obsidian embed paths."""
    name = asset_name.strip().replace("\\", "/")
    if name.lower().startswith("images/"):
        name = name[7:]
    return name


def image_href(
    asset_name: str,
    doc_src_uri: str,
    *,
    media_base_url: str = "",
) -> str:
    """Resolve Obsidian embed to a local relative URL or absolute blob/CDN URL."""
    name = normalize_image_asset_name(asset_name)
    if media_base_url:
        return f"{media_base_url}/{quote(name)}"
    image_url = f"images/{name}"
    return get_relative_url(image_url, doc_src_uri)


def transform_obsidian_embeds(
    markdown: str,
    doc_src_uri: str = "",
    *,
    media_base_url: str = "",
) -> str:
    """Convert Obsidian ![[file]] embeds to standard markdown images."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if media_base_url:
            href = image_href(name, doc_src_uri, media_base_url=media_base_url)
        elif doc_src_uri:
            href = image_href(name, doc_src_uri)
        else:
            href = f"images/{normalize_image_asset_name(name)}"
        return f"![]({href})"

    return OBSIDIAN_EMBED_RE.sub(repl, markdown)


def strip_obsidian_tag_lines(markdown: str) -> str:
    """Remove lines that contain only Obsidian `#tag` tokens."""

    kept: list[str] = []
    for line in markdown.splitlines():
        if OBSIDIAN_TAG_LINE_RE.match(line):
            continue
        kept.append(line)
    if not kept:
        return ""
    while kept and kept[0].strip() == "":
        kept.pop(0)
    result = "\n".join(kept)
    if markdown.endswith("\n"):
        result += "\n"
    return result


def strip_about_author_section(markdown: str) -> str:
    """Drop trailing 'About the Author' section and any horizontal rule above it."""

    match = ABOUT_AUTHOR_HEADING_RE.search(markdown)
    if not match:
        return markdown

    lines = markdown[: match.start()].splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and lines[-1].strip() == "---":
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return ""
    result = "\n".join(lines)
    if markdown.endswith("\n"):
        result += "\n"
    return result


def on_page_markdown(markdown, page, config, files):
    doc_src_uri = page.file.src_uri if page.file else ""
    media_base_url = get_media_base_url(config)
    markdown = strip_obsidian_tag_lines(markdown)
    markdown = strip_about_author_section(markdown)
    return transform_obsidian_embeds(
        markdown,
        doc_src_uri=doc_src_uri,
        media_base_url=media_base_url,
    )


def on_files(files, config):
    from mkdocs.structure.files import File, InclusionLevel

    if get_media_base_url(config):
        return files

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