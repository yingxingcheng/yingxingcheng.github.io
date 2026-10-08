"""Regression tests for safe, repeatable bilingual page generation."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from generate_html import _is_web_url, _publications, _software, generate_html

ROOT = Path(__file__).resolve().parents[1]


class ParsedHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class PublicationRenderingTests(unittest.TestCase):
    def setUp(self):
        self.publication = {
            "authors": "A. Author & B. Author",
            "title": "A paper",
            "journal": "A journal",
            "volume": "1",
            "pages": "1\u201310",
            "year": "2026",
            "link": "https://doi.org/10.1234/example",
        }

    def render(self, **changes):
        return _publications({"title": "Publications", "items": [{**self.publication, **changes}]})

    def test_metadata_is_escaped_in_every_citation_field(self):
        payload = '<img src="x" onerror="alert(1)"><script>alert(2)</script>&'
        for field in ("authors", "title", "journal", "volume", "pages", "year"):
            with self.subTest(field=field):
                html = self.render(**{field: payload})
                self.assertIn("&lt;img", html)
                self.assertIn("&lt;script&gt;", html)
                self.assertNotIn("<img", html)
                self.assertNotIn("<script", html)
                self.assertFalse(
                    any(
                        attr.startswith("on")
                        for _, attrs in ParsedHTML(html).elements
                        for attr in attrs
                    )
                )

    def test_unsafe_links_are_plain_text(self):
        for link in (
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "//example.com/paper",
            "/paper",
            'https://example.com/" onclick="alert(1)',
            "https://example.com/\\evil",
            "java\nscript:alert(1)",
            "https://[broken",
        ):
            with self.subTest(link=link):
                self.assertFalse(_is_web_url(link))
                self.assertNotIn(
                    "a", [tag for tag, _ in ParsedHTML(self.render(link=link)).elements]
                )

    def test_web_link_text_and_attribute_are_escaped(self):
        link = 'https://example.com/paper?a=1&b="quoted"'
        html = self.render(link=link)
        anchors = [attrs for tag, attrs in ParsedHTML(html).elements if tag == "a"]
        self.assertEqual(anchors, [{"href": link}])
        self.assertIn("&amp;b=&quot;quoted&quot;", html)

    def test_curated_math_is_preserved(self):
        title = r"HfO\(_2\) and \(\overline{1}11\)"
        html = self.render(title=title)
        self.assertIn(title, html)
        self.assertNotIn("tex2jax_ignore", html)

    def test_imported_math_is_not_interpreted_as_commands(self):
        html = self.render(title=r"\(\href{javascript:alert(1)}{click}\)", source="crossref")
        paragraphs = [attrs for tag, attrs in ParsedHTML(html).elements if tag == "p"]
        self.assertEqual(paragraphs, [{"class": "tex2jax_ignore"}])

    def test_numeric_metadata_is_supported(self):
        self.assertIn("(2026)", self.render(year=2026, volume=1))


class SoftwareRenderingTests(unittest.TestCase):
    def render(self, **changes):
        item = {"title": "Package", "description": r"An <em>ab-initio</em> \(\omega\) model."}
        return _software({"title": "Software", "items": [{**item, **changes}]})

    def test_private_repository_availability_replaces_link(self):
        html = self.render(availability="Private repository", link="https://example.com/private")
        self.assertIn('<span class="availability">Private repository</span>', html)
        self.assertNotIn("<a", html)
        self.assertNotIn("https://example.com/private", html)

    def test_optional_link_does_not_require_placeholder(self):
        self.assertNotIn("<a", self.render())
        self.assertIn(
            '<a href="https://example.com/public">More</a>',
            self.render(link="https://example.com/public"),
        )

    def test_curated_software_markup_is_preserved(self):
        html = self.render(availability="<private>")
        self.assertIn(r"<em>ab-initio</em> \(\omega\)", html)
        self.assertIn("&lt;private&gt;", html)


class PageGenerationTests(unittest.TestCase):
    def test_import_has_no_file_io_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", "import generate_html"],
                cwd=directory,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_generated_pages_match_content_and_navigation(self):
        content = json.loads((ROOT / "content.json").read_text(encoding="utf-8"))
        for language, filename, alternate in (
            ("en", "index.html", "index-zh.html"),
            ("zh", "index-zh.html", "index.html"),
        ):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / filename
                generate_html(content[language], target)
                html = target.read_text(encoding="utf-8")
                self.assertEqual(html, (ROOT / filename).read_text(encoding="utf-8"))
                elements = ParsedHTML(html).elements
                links = [attrs["href"] for tag, attrs in elements if tag == "a"]
                ids = {attrs["id"] for _, attrs in elements if "id" in attrs}
                self.assertEqual(len([link for link in links if link.startswith("#")]), 7)
                self.assertTrue(all(link[1:] in ids for link in links if link.startswith("#")))
                self.assertIn(alternate, links)
                self.assertNotIn("https://github.com/yingxingcheng/LRC-CD", links)


if __name__ == "__main__":
    unittest.main()
