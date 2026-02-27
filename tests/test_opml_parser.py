"""Tests für OPML-Parser."""

import pytest

from scraper.opml_parser import parse_opml, escape_xml, generate_opml


class TestOPMLParser:
    """Tests für OPML-Parsing."""

    def test_parse_opml_basic(self):
        """Test: Einfaches OPML wird korrekt geparst."""
        opml_content = b"""<?xml version="1.0"?>
<opml version="2.0">
  <body>
    <outline text="Test Feed" htmlUrl="https://example.com" xmlUrl="https://example.com/feed.xml"/>
  </body>
</opml>"""

        feeds = parse_opml(opml_content)

        assert len(feeds) == 1
        assert feeds[0]["name"] == "test-feed"
        assert feeds[0]["url"] == "https://example.com"

    def test_parse_opml_multiple(self):
        """Test: Mehrere Feeds werden geparst."""
        opml_content = b"""<?xml version="1.0"?>
<opml version="2.0">
  <body>
    <outline text="Feed 1" htmlUrl="https://site1.com" xmlUrl="https://site1.com/feed.xml"/>
    <outline text="Feed 2" htmlUrl="https://site2.com" xmlUrl="https://site2.com/feed.xml"/>
  </body>
</opml>"""

        feeds = parse_opml(opml_content)

        assert len(feeds) == 2

    def test_parse_opml_empty(self):
        """Test: Leere OPML gibt leere Liste."""
        opml_content = b"""<?xml version="1.0"?>
<opml version="2.0">
  <body>
  </body>
</opml>"""

        feeds = parse_opml(opml_content)

        assert feeds == []


class TestEscapeXML:
    """Tests für XML-Escaping."""

    def test_escape_ampersand(self):
        """Test: & wird zu &amp;."""
        result = escape_xml("A & B")
        assert "&amp;" in result

    def test_escape_less_than(self):
        """Test: < wird zu &lt;."""
        result = escape_xml("A < B")
        assert "&lt;" in result

    def test_escape_greater_than(self):
        """Test: > wird zu &gt;."""
        result = escape_xml("A > B")
        assert "&gt;" in result

    def test_escape_empty(self):
        """Test: Leerer String gibt leeren String."""
        result = escape_xml("")
        assert result == ""


class TestGenerateOPML:
    """Tests für OPML-Generierung."""

    def test_generate_opml_basic(self):
        """Test: Einfaches OPML wird generiert."""
        feeds = [{"name": "test", "url": "https://example.com", "description": "Test"}]

        opml = generate_opml(feeds, "http://localhost:5000")

        assert '<?xml version="1.0"' in opml
        assert '<opml version="2.0">' in opml
        assert "test" in opml
        assert "http://localhost:5000/feed/test.xml" in opml

    def test_generate_opml_categories(self):
        """Test: Kategorien werden gruppiert."""
        feeds = [
            {"name": "feed1", "url": "https://a.com", "description": "Kat1"},
            {"name": "feed2", "url": "https://b.com", "description": "Kat1"},
            {"name": "feed3", "url": "https://c.com", "description": "Kat2"},
        ]

        opml = generate_opml(feeds, "http://localhost:5000")

        assert "Kat1" in opml
        assert "Kat2" in opml
