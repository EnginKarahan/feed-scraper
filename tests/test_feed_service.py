"""Tests für Feed-Service."""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# Test-Setup: Config mocken bevor wir importieren
with (
    patch("scraper.config.DB_FILE", "/tmp/test_feeds.json"),
    patch("scraper.config.FEEDS_DIR", "/tmp/test_feeds"),
    patch("scraper.config.LOG_FILE", "/tmp/test.log"),
):
    from scraper import feed_service


@pytest.fixture
def temp_db():
    """Temporäre Datenbank für Tests."""
    test_db = "/tmp/test_feeds.json"
    test_feeds_dir = "/tmp/test_feeds"

    os.makedirs(test_feeds_dir, exist_ok=True)

    # Leere Datenbank erstellen
    with open(test_db, "w") as f:
        json.dump({"feeds": [], "updated": "2024-01-01"}, f)

    yield test_db

    # Aufräumen
    if os.path.exists(test_db):
        os.remove(test_db)


class TestFeedService:
    """Tests für Feed-CRUD-Operationen."""

    def test_load_feeds_empty(self, temp_db):
        """Test: Leere Feed-Liste wird korrekt geladen."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feeds = feed_service.load_feeds()
            assert feeds == []

    def test_add_feed(self, temp_db):
        """Test: Feed wird korrekt hinzugefügt."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed = feed_service.add_feed(
                name="test-feed",
                url="https://example.com",
                css_selector=".article",
                description="Test",
            )

            assert feed["name"] == "test-feed"
            assert feed["url"] == "https://example.com"
            assert feed["css_selector"] == ".article"
            assert feed["description"] == "Test"
            assert "created" in feed

    def test_add_duplicate_name_raises(self, temp_db):
        """Test: Doppelter Name wirft ValueError."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed_service.add_feed("test", "https://example.com")

            with pytest.raises(ValueError, match="existiert bereits"):
                feed_service.add_feed("test", "https://other.com")

    def test_delete_feed(self, temp_db):
        """Test: Feed wird korrekt gelöscht."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed_service.add_feed("to-delete", "https://example.com")
            result = feed_service.delete_feed("to-delete")

            assert result is True

            feeds = feed_service.load_feeds()
            assert len(feeds) == 0

    def test_delete_nonexistent_feed(self, temp_db):
        """Test: Löschen nicht-existierenden Feeds gibt False."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            result = feed_service.delete_feed("nonexistent")
            assert result is False

    def test_update_feed_data(self, temp_db):
        """Test: Feed wird korrekt aktualisiert."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed_service.add_feed("test", "https://example.com")

            updated = feed_service.update_feed_data(
                name="test", url="https://new-url.com", description="Neue Beschreibung"
            )

            assert updated["url"] == "https://new-url.com"
            assert updated["description"] == "Neue Beschreibung"

    def test_get_feed_by_name(self, temp_db):
        """Test: Feed wird nach Name gefunden."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed_service.add_feed("find-me", "https://example.com")

            feed = feed_service.get_feed_by_name("find-me")
            assert feed is not None
            assert feed["name"] == "find-me"

    def test_get_feed_by_name_not_found(self, temp_db):
        """Test: Nicht existenter Feed gibt None zurück."""
        with patch("scraper.feed_service.DB_FILE", temp_db):
            feed = feed_service.get_feed_by_name("nonexistent")
            assert feed is None


class TestURLNormalization:
    """Tests für URL-Normalisierung (extern)."""

    def test_normalize_url_https(self):
        """Test: HTTPS URLs werden normalisiert."""
        from scraper import normalize_url

        result = normalize_url("https://Example.com/")
        assert result == "https://example.com/"

    def test_normalize_url_www(self):
        """Test: www. wird entfernt."""
        from scraper import normalize_url

        result = normalize_url("https://www.example.com/page")
        assert result == "https://example.com/page"

    def test_normalize_url_trailing_slash(self):
        """Test: Trailing Slash wird normalisiert."""
        from scraper import normalize_url

        result = normalize_url("https://example.com/page/")
        assert result == "https://example.com/page"

    def test_normalize_url_empty(self):
        """Test: Leere URL gibt leeren String."""
        from scraper import normalize_url

        result = normalize_url("")
        assert result == ""
