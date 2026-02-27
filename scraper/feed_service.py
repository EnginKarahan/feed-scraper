"""Feed-Service: CRUD-Operationen für Feeds."""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from scraper.config import DB_FILE, FEEDS_DIR

logger = logging.getLogger(__name__)


def load_feeds() -> List[Dict]:
    """Lädt alle Feeds aus der JSON-DB."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("feeds", [])
    return []


def save_feeds(feeds: List[Dict]) -> None:
    """Speichert alle Feeds in die JSON-DB."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"feeds": feeds, "updated": datetime.now().isoformat()},
            f,
            indent=2,
            ensure_ascii=False,
        )


def add_feed(
    name: str,
    url: str,
    css_selector: str = "",
    description: str = "",
    normalize_func=None,
) -> Dict:
    """Fügt einen neuen Feed hinzu.

    Args:
        name: Eindeutiger Name des Feeds
        url: URL der Webseite
        css_selector: Optionaler CSS-Selektor
        description: Beschreibung/Kategorie
        normalize_func: Funktion zur URL-Normalisierung (für Duplikatsprüfung)

    Returns:
        Das erstellte Feed-Dict

    Raises:
        ValueError: Wenn Feed-Name oder URL bereits existiert
    """
    feeds = load_feeds()

    # Name-Duplikatsprüfung
    for feed in feeds:
        if feed["name"] == name:
            raise ValueError(f"Feed '{name}' existiert bereits")

    # URL-Duplikatsprüfung
    if normalize_func:
        normalized_url = normalize_func(url)
        for feed in feeds:
            existing_normalized = normalize_func(feed.get("url", ""))
            if existing_normalized == normalized_url:
                raise ValueError(
                    f"URL '{url}' existiert bereits als Feed '{feed['name']}'"
                )

    feed = {
        "name": name,
        "url": url,
        "css_selector": css_selector,
        "description": description,
        "created": datetime.now().isoformat(),
        "last_update": None,
        "last_status": None,
        "article_count": 0,
    }
    feeds.append(feed)
    save_feeds(feeds)
    logger.info(f"Feed hinzugefügt: {name}")
    return feed


def delete_feed(name: str) -> bool:
    """Löscht einen Feed und seine RSS-Datei.

    Args:
        name: Name des zu löschenden Feeds

    Returns:
        True wenn gelöscht, False wenn nicht gefunden
    """
    feeds = load_feeds()
    feeds = [f for f in feeds if f["name"] != name]
    if len(feeds) == len(load_feeds()):
        return False
    save_feeds(feeds)

    xml_file = os.path.join(FEEDS_DIR, f"{name}.xml")
    if os.path.exists(xml_file):
        os.remove(xml_file)

    logger.info(f"Feed gelöscht: {name}")
    return True


def update_feed_data(
    name: str,
    new_name: Optional[str] = None,
    url: Optional[str] = None,
    css_selector: str = "",
    description: str = "",
) -> Dict:
    """Aktualisiert die Daten eines Feeds.

    Args:
        name: Aktueller Name des Feeds
        new_name: Neuer Name (optional)
        url: Neue URL (optional)
        css_selector: Neuer CSS-Selektor
        description: Neue Beschreibung

    Returns:
        Das aktualisierte Feed-Dict

    Raises:
        ValueError: Wenn Feed nicht gefunden oder neuer Name bereits vergeben
    """
    feeds = load_feeds()
    feed = next((f for f in feeds if f["name"] == name), None)

    if not feed:
        raise ValueError(f"Feed '{name}' nicht gefunden")

    if new_name and new_name != name:
        # Prüfen ob neuer Name bereits existiert
        for f in feeds:
            if f["name"] == new_name:
                raise ValueError(f"Feed '{new_name}' existiert bereits")

        feed["name"] = new_name
        # RSS-Datei umbenennen
        old_xml = os.path.join(FEEDS_DIR, f"{name}.xml")
        new_xml = os.path.join(FEEDS_DIR, f"{new_name}.xml")
        if os.path.exists(old_xml):
            os.rename(old_xml, new_xml)

    if url:
        feed["url"] = url
    if css_selector is not None:
        feed["css_selector"] = css_selector
    if description is not None:
        feed["description"] = description

    save_feeds(feeds)
    logger.info(f"Feed aktualisiert: {name}")
    return feed


def get_feed_by_name(name: str) -> Optional[Dict]:
    """Holt einen Feed anhand seines Namens.

    Args:
        name: Name des Feeds

    Returns:
        Feed-Dict oder None wenn nicht gefunden
    """
    feeds = load_feeds()
    return next((f for f in feeds if f["name"] == name), None)


def update_feed_status(
    name: str,
    status: str,
    article_count: int = 0,
    error: Optional[str] = None,
) -> Dict:
    """Aktualisiert den Status eines Feeds.

    Args:
        name: Name des Feeds
        status: "success" oder "error"
        article_count: Anzahl der Artikel
        error: Optionale Fehlermeldung

    Returns:
        Das aktualisierte Feed-Dict
    """
    feeds = load_feeds()
    feed = next((f for f in feeds if f["name"] == name), None)

    if not feed:
        raise ValueError(f"Feed '{name}' nicht gefunden")

    feed["last_update"] = datetime.now().isoformat()
    feed["last_status"] = status
    feed["article_count"] = article_count

    if error:
        feed["last_error"] = error
    elif "last_error" in feed:
        del feed["last_error"]

    save_feeds(feeds)
    return feed
