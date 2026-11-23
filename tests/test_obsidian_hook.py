import re
import unittest

from mkdocs_hooks.obsidian import OBSIDIAN_EMBED_RE, image_href, transform_obsidian_embeds


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


if __name__ == "__main__":
    unittest.main()