import os
import unittest
from types import SimpleNamespace

from mkdocs_hooks.obsidian import (
    ENV_MEDIA_BASE_URL,
    OBSIDIAN_EMBED_RE,
    get_media_base_url,
    image_href,
    strip_about_author_section,
    strip_obsidian_tag_lines,
    transform_obsidian_embeds,
)


class TestObsidianEmbedRegex(unittest.TestCase):
    def test_plain_embed(self):
        m = OBSIDIAN_EMBED_RE.search("![[Securing_AI_Agents_Architecture.png]]")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Securing_AI_Agents_Architecture.png")

    def test_embed_with_width(self):
        m = OBSIDIAN_EMBED_RE.search("![[Pasted image 20261118111200.png|524]]")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Pasted image 20261118111200.png")


class TestTransformObsidianEmbeds(unittest.TestCase):
    def test_replaces_multiple_embeds(self):
        src = "posts/Entra Agent ID + Sidecar - A Practical Guide to Building Secure AI Agents.md"
        md = (
            "![[Securing_AI_Agents_Architecture.png]]\n\n"
            "![[Pasted image 20261102113718.png]]\n"
        )
        out = transform_obsidian_embeds(md, doc_src_uri=src)
        self.assertNotIn("![[", out)
        self.assertIn("../images/Securing_AI_Agents_Architecture.png", out)
        self.assertIn("../images/Pasted image 20261102113718.png", out)

    def test_width_suffix_stripped(self):
        out = transform_obsidian_embeds("![[foo.png|100]]", doc_src_uri="posts/foo.md")
        self.assertIn("../images/foo.png", out)
        self.assertNotIn("|100", out)

    def test_image_href_from_posts(self):
        href = image_href(
            "Securing_AI_Agents_Architecture.png",
            "posts/Entra Agent ID + Sidecar - A Practical Guide to Building Secure AI Agents.md",
        )
        self.assertEqual(href, "../images/Securing_AI_Agents_Architecture.png")

    def test_http_images_unchanged(self):
        md = "![alt](https://example.com/a.png)"
        self.assertEqual(transform_obsidian_embeds(md), md)

    def test_embed_strips_redundant_images_prefix(self):
        out = transform_obsidian_embeds(
            "![[images/Pasted image 20260407160447.png]]",
            doc_src_uri="posts/Implementing Agentic RAG on Azure From Hand-Coded Code to Ready-to-Use Solutions.md",
        )
        self.assertIn("../images/Pasted image 20260407160447.png", out)
        self.assertNotIn("images/images/", out)

    def test_embed_uses_azure_media_base_url(self):
        base = "https://example.blob.core.windows.net/media"
        out = transform_obsidian_embeds(
            "![[Pasted image 20260407160447.png]]",
            doc_src_uri="posts/foo.md",
            media_base_url=base,
        )
        self.assertIn("![](https://example.blob.core.windows.net/media/", out)
        self.assertIn("20260407160447.png", out)
        self.assertNotIn("%20%20", out)
        self.assertNotIn("../images/", out)

    def test_image_href_encodes_spaces_for_blob(self):
        href = image_href(
            "foo bar.png",
            "posts/x.md",
            media_base_url="https://acct.blob.core.windows.net/c",
        )
        self.assertEqual(href, "https://acct.blob.core.windows.net/c/foo%20bar.png")


class TestMediaBaseUrl(unittest.TestCase):
    def test_env_overrides_extra(self):
        config = SimpleNamespace(extra={"media_base_url": "https://from-yaml.example/c"})
        os.environ[ENV_MEDIA_BASE_URL] = "https://from-env.example/c"
        try:
            self.assertEqual(get_media_base_url(config), "https://from-env.example/c")
        finally:
            del os.environ[ENV_MEDIA_BASE_URL]

    def test_extra_when_env_unset(self):
        config = SimpleNamespace(extra={"media_base_url": "https://from-yaml.example/c/"})
        prev = os.environ.pop(ENV_MEDIA_BASE_URL, None)
        try:
            self.assertEqual(get_media_base_url(config), "https://from-yaml.example/c")
        finally:
            if prev is not None:
                os.environ[ENV_MEDIA_BASE_URL] = prev


class TestStripObsidianTagLines(unittest.TestCase):
    def test_removes_single_tag_line(self):
        md = "#mcp #oauth #apim #agent\n\n## Background\n"
        self.assertEqual(strip_obsidian_tag_lines(md), "## Background\n")

    def test_preserves_atx_headings(self):
        md = "## Background\n\n# Upload file\n"
        self.assertEqual(strip_obsidian_tag_lines(md), md)

    def test_preserves_spaced_heading(self):
        md = "# My Title\n\nBody\n"
        self.assertEqual(strip_obsidian_tag_lines(md), md)


class TestStripAboutAuthorSection(unittest.TestCase):
    def test_removes_section_and_preceding_rule(self):
        md = (
            "## Summary\n\nThe end.\n\n---\n\n"
            "## About the Author\n\nChris Bao\n"
        )
        self.assertEqual(strip_about_author_section(md), "## Summary\n\nThe end.\n")

    def test_case_insensitive(self):
        md = "## Body\n\n### About the author\n\nBio\n"
        self.assertEqual(strip_about_author_section(md), "## Body\n")

    def test_skips_when_absent(self):
        md = "## Summary\n\nTalks about authors in general.\n"
        self.assertEqual(strip_about_author_section(md), md)


if __name__ == "__main__":
    unittest.main()