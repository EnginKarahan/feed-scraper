"""OPML-Parser: Parst OPML-Dateien und extrahiert Feeds."""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def parse_opml(content: bytes) -> List[Dict]:
    """Parst eine OPML-Datei und extrahiert Feeds.

    Args:
        content: Bytes-Inhalt der OPML-Datei

    Returns:
        Liste von Feed-Dicts mit name, url, css_selector, description

    Raises:
        Exception: Bei Parsing-Fehlern
    """
    feeds = []

    try:
        content_str = content.decode("utf-8", errors="ignore")

        # Find all outline elements with xmlUrl attribute
        pattern = r'<outline[^>]*\sxmlUrl="([^"]+)"[^>]*/?>'
        matches = re.findall(pattern, content_str)

        logger.info(f"OPML: Found {len(matches)} outline elements with xmlUrl")

        for xml_url in matches:
            # Get the full outline tag
            full_pattern = (
                rf'<outline([^>]*(?:\sxmlUrl="{re.escape(xml_url)}")[^>]*/?>)'
            )
            full_match = re.search(full_pattern, content_str)

            if full_match:
                attrs = full_match.group(1)

                # Extract text attribute
                text_match = re.search(r'text="([^"]*)"', attrs)
                name = text_match.group(1) if text_match else "Unnamed"

                # Extract htmlUrl
                html_match = re.search(r'htmlUrl="([^"]*)"', attrs)
                html_url = html_match.group(1) if html_match else ""

                # Clean name
                name = name.lower().replace(" ", "-").replace("/", "-")
                name = "".join(c for c in name if c.isalnum() or c in "-_")

                feeds.append(
                    {
                        "name": name[:50],
                        "url": html_url or xml_url,
                        "css_selector": "",
                        "description": "Importiert aus OPML",
                    }
                )

        logger.info(f"OPML Import: {len(feeds)} Feeds gefunden")

    except Exception as e:
        logger.error(f"OPML Parse Fehler: {e}")
        raise

    return feeds


def escape_xml(text: str) -> str:
    """Escapt XML-Sonderzeichen.

    Args:
        text: Zu escapender Text

    Returns:
        Text mit escapten XML-Zeichen
    """
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_opml(feeds: List[Dict], base_url: str) -> str:
    """Generiert OPML aus einer Feed-Liste.

    Args:
        feeds: Liste von Feed-Dicts
        base_url: Basis-URL für die RSS-Links

    Returns:
        OPML-XML als String
    """
    from datetime import datetime

    opml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        "  <head>",
        "    <title>Feed Scraper Exports</title>",
        f"    <dateCreated>{datetime.now().isoformat()}</dateCreated>",
        "  </head>",
        "  <body>",
    ]

    # Gruppiere nach Kategorie/description
    categories = {}
    for feed in feeds:
        cat = feed.get("description", "Unkategorisiert") or "Unkategorisiert"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(feed)

    for category, cat_feeds in categories.items():
        opml.append(f'    <outline text="{escape_xml(category)}">')
        for feed in cat_feeds:
            feed_url = f"{base_url}/feed/{feed['name']}.xml"
            opml.append(
                f'      <outline text="{escape_xml(feed["name"])}" '
                f'htmlUrl="{feed["url"]}" type="rss" xmlUrl="{feed_url}"/>'
            )
        opml.append("    </outline>")

    opml.extend(["  </body>", "</opml>"])

    return "\n".join(opml)
