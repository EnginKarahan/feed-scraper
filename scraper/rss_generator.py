"""RSS-Generator: Erstellt RSS-Feeds aus Artikeln."""

import logging
import os
from typing import List, Dict, Optional

from feedgen.feed import FeedGenerator
from scraper.config import FEEDS_DIR

logger = logging.getLogger(__name__)


def generate_rss(feed: Dict, articles: List[Dict]) -> str:
    """Generiert eine RSS-Datei aus Artikeln.

    Args:
        feed: Feed-Dict mit name, url, description
        articles: Liste von Article-Dicts

    Returns:
        Pfad zur erstellten XML-Datei
    """
    if not articles:
        articles = [
            {
                "title": "Keine Artikel gefunden",
                "url": feed["url"],
                "date_published": None,
                "content": "Der Feed konnte keine Artikel von der Webseite extrahieren.",
            }
        ]

    fg = FeedGenerator()
    fg.title(feed["name"])
    fg.description(feed.get("description") or feed.get("url") or feed["name"])
    fg.link(href=feed["url"], rel="alternate")
    fg.link(href=f"/feed/{feed['name']}.xml", rel="self")
    fg.language("de")

    for article in articles[:30]:
        fe = fg.add_entry()
        fe.title(article.get("title") or "Ohne Titel")
        fe.link(href=article.get("url") or feed["url"])
        fe.description(article.get("content") or "")
        if article.get("date_published"):
            try:
                fe.pubDate(article["date_published"])
            except Exception:
                pass

    xml_file = os.path.join(FEEDS_DIR, f"{feed['name']}.xml")
    fg.rss_file(xml_file)
    return xml_file


def generate_rss_with_base_url(feed: Dict, articles: List[Dict], base_url: str) -> str:
    """Generiert eine RSS-Datei mit vollständiger Self-Link-URL.

    Args:
        feed: Feed-Dict mit name, url, description
        articles: Liste von Article-Dicts
        base_url: Basis-URL für den Self-Link (z.B. "http://localhost:5000")

    Returns:
        Pfad zur erstellten XML-Datei
    """
    if not articles:
        articles = [
            {
                "title": "Keine Artikel gefunden",
                "url": feed["url"],
                "date_published": None,
                "content": "Der Feed konnte keine Artikel von der Webseite extrahieren.",
            }
        ]

    fg = FeedGenerator()
    fg.title(feed["name"])
    fg.description(feed.get("description") or feed.get("url") or feed["name"])
    fg.link(href=feed["url"], rel="alternate")
    fg.link(href=f"{base_url}/feed/{feed['name']}.xml", rel="self")
    fg.language("de")

    for article in articles[:30]:
        fe = fg.add_entry()
        fe.title(article.get("title") or "Ohne Titel")
        fe.link(href=article.get("url") or feed["url"])
        fe.description(article.get("content") or "")
        if article.get("date_published"):
            try:
                fe.pubDate(article["date_published"])
            except Exception:
                pass

    xml_file = os.path.join(FEEDS_DIR, f"{feed['name']}.xml")
    fg.rss_file(xml_file)
    return xml_file


def get_rss_path(feed_name: str) -> str:
    """Gibt den Pfad zur RSS-Datei eines Feeds zurück.

    Args:
        feed_name: Name des Feeds

    Returns:
        Pfad zur XML-Datei
    """
    return os.path.join(FEEDS_DIR, f"{feed_name}.xml")


def rss_exists(feed_name: str) -> bool:
    """Prüft ob eine RSS-Datei existiert.

    Args:
        feed_name: Name des Feeds

    Returns:
        True wenn die Datei existiert
    """
    return os.path.exists(get_rss_path(feed_name))


def delete_rss(feed_name: str) -> bool:
    """Löscht die RSS-Datei eines Feeds.

    Args:
        feed_name: Name des Feeds

    Returns:
        True wenn gelöscht, False wenn nicht gefunden
    """
    path = get_rss_path(feed_name)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
