"""Scraper-Paket: Feed-Management, RSS-Generierung, Web-Scraping und OPML-Parsing.

Dieses Modul bündelt alle Funktionen für den Feed-Scraper:
- feed_service: CRUD-Operationen für Feeds
- rss_generator: RSS-Feed-Erstellung
- scraper: Web-Scraping und Article-Extraktion
- opml_parser: OPML-Import/Export
- utils: Hilfsfunktionen (URL-Normalisierung, etc.)
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Importiere alle Module
from scraper import feed_service
from scraper import rss_generator
from scraper import scraper as scraper_module
from scraper import opml_parser

# Importiere für einfachen Zugriff
load_feeds = feed_service.load_feeds
save_feeds = feed_service.save_feeds
add_feed = feed_service.add_feed
delete_feed = feed_service.delete_feed
update_feed_data = feed_service.update_feed_data

# RSS-Generator
generate_rss = rss_generator.generate_rss

# Scraper
fetch_articles = scraper_module.fetch_articles
extract_article = scraper_module.extract_article
discover_rss_feeds = scraper_module.discover_rss_feeds
parse_error_message = scraper_module.parse_error_message

# OPML
parse_opml = opml_parser.parse_opml
escape_xml = opml_parser.escape_xml
generate_opml = opml_parser.generate_opml


def normalize_url(url: str) -> str:
    """Normalisiert eine URL für den Vergleich.

    Entfernt www., normalisiert Trailing-Slash, etc.

    Args:
        url: Zu normalisierende URL

    Returns:
        Normalisierte URL
    """
    if not url:
        return ""

    url = url.strip()
    parsed = urlparse(url)

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/") or "/"
    query = parsed.query

    normalized = f"{scheme}://{netloc}{path}"
    if query:
        normalized += f"?{query}"

    return normalized


def get_current_datetime() -> str:
    """Gibt das aktuelle Datum als ISO-String zurück."""
    return datetime.now().isoformat()


def update_feed(name: str) -> Dict:
    """Aktualisiert einen einzelnen Feed.

    Args:
        name: Name des zu aktualisierenden Feeds

    Returns:
        Aktualisiertes Feed-Dict

    Raises:
        ValueError: Wenn Feed nicht gefunden
    """
    feeds = load_feeds()
    feed = next((f for f in feeds if f["name"] == name), None)

    if not feed:
        raise ValueError(f"Feed '{name}' nicht gefunden")

    try:
        articles = fetch_articles(feed["url"], feed.get("css_selector", ""))

        # Nutze feed_service für Status-Update
        feed_service.update_feed_status(
            name=name,
            status="success",
            article_count=len(articles),
        )

        generate_rss(feed, articles)
        logger.info(f"Feed aktualisiert: {name} ({len(articles)} Artikel)")

    except Exception as e:
        feed_service.update_feed_status(
            name=name,
            status="error",
            article_count=0,
            error=parse_error_message(e),
        )
        logger.error(f"Feed fehlerhaft: {name} - {parse_error_message(e)}")

    return feed_service.get_feed_by_name(name)


def update_all_feeds() -> List[Dict]:
    """Aktualisiert alle Feeds.

    Returns:
        Liste von Ergebnis-Dicts
    """
    feeds = load_feeds()
    results = []

    for feed in feeds:
        try:
            result = update_feed(feed["name"])
            results.append(result)
        except Exception as e:
            logger.error(f"Fehler beim Update von {feed['name']}: {e}")
            results.append({"name": feed["name"], "status": "error", "error": str(e)})

        time.sleep(1)

    return results


# Import time hier, um zirkulären Import zu vermeiden
import time
