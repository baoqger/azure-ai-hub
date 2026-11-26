"""Apply post-body cleanups from mkdocs_hooks/obsidian to articles/posts/*.md."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mkdocs_hooks.obsidian import strip_about_author_section, strip_obsidian_tag_lines


def clean_post_body(body: str) -> str:
    body = strip_obsidian_tag_lines(body)
    return strip_about_author_section(body)


def main() -> int:
    posts = ROOT / "articles" / "posts"
    changed = 0
    for path in sorted(posts.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        if not raw.startswith("---"):
            continue
        end = raw.find("---", 3)
        if end < 0:
            continue
        front = raw[: end + 3]
        body = raw[end + 3 :].lstrip("\n")
        new_body = clean_post_body(body)
        if new_body != body:
            path.write_text(front + "\n" + new_body, encoding="utf-8", newline="\n")
            changed += 1
    print(f"Updated {changed} posts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())