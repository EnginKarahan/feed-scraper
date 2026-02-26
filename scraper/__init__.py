import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from tenacity import retry, stop_after_attempt, wait_exponential
import time

from scraper.config import DB_FILE, FEEDS_DIR, LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
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
    name: str, url: str, css_selector: str = "", description: str = ""
) -> Dict:
    """Fügt einen neuen Feed hinzu."""
    feeds = load_feeds()

    for feed in feeds:
        if feed["name"] == name:
            raise ValueError(f"Feed '{name}' existiert bereits")

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
    """Löscht einen Feed."""
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
    new_name: str = None,
    url: str = None,
    css_selector: str = "",
    description: str = "",
) -> Dict:
    """Aktualisiert die Daten eines Feeds."""
    feeds = load_feeds()
    feed = next((f for f in feeds if f["name"] == name), None)

    if not feed:
        raise ValueError(f"Feed '{name}' nicht gefunden")

    if new_name and new_name != name:
        for f in feeds:
            if f["name"] == new_name:
                raise ValueError(f"Feed '{new_name}' existiert bereits")
        feed["name"] = new_name
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


def parse_error_message(e: Exception) -> str:
    """Wandelt eine Exception in eine benutzerfreundliche Fehlermeldung um."""
    error_str = str(e)

    # RetryError entpacken
    if "RetryError" in error_str:
        if "ConnectionError" in error_str:
            return "Seite nicht erreichbar (Verbindung fehlgeschlagen)"
        elif "SSLError" in error_str:
            return "SSL-Zertifikatsfehler"
        elif "HTTPError" in error_str:
            if "404" in error_str:
                return "Nicht gefunden (404)"
            elif "401" in error_str or "403" in error_str:
                return "Zugriff verweigert (401/403)"
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                return "Serverfehler"
            else:
                return "HTTP-Fehler"
        elif "Timeout" in error_str or "timed out" in error_str.lower():
            return "Zeitüberschreitung"
        elif "MissingSchema" in error_str:
            return "Ungültige URL (fehlendes https://)"
        else:
            return "Verbindungsfehler"

    if "ConnectionError" in error_str:
        return "Seite nicht erreichbar"
    if "SSLError" in error_str or "SSL" in error_str:
        return "SSL-Zertifikatsfehler"
    if "HTTPError" in error_str:
        if "404" in error_str:
            return "Nicht gefunden (404)"
        return "HTTP-Fehler"
    if "Timeout" in error_str or "timed out" in error_str.lower():
        return "Zeitüberschreitung"
    if "MissingSchema" in error_str:
        return "Ungültige URL"

    return error_str[:100]


def update_feed(name: str) -> Dict:
    """Aktualisiert einen einzelnen Feed."""
    feeds = load_feeds()
    feed = next((f for f in feeds if f["name"] == name), None)

    if not feed:
        raise ValueError(f"Feed '{name}' nicht gefunden")

    try:
        articles = fetch_articles(feed["url"], feed.get("css_selector", ""))
        feed["last_update"] = datetime.now().isoformat()
        feed["last_status"] = "success"
        feed["article_count"] = len(articles)

        generate_rss(feed, articles)
        logger.info(f"Feed aktualisiert: {name} ({len(articles)} Artikel)")

    except Exception as e:
        feed["last_update"] = datetime.now().isoformat()
        feed["last_status"] = "error"
        feed["last_error"] = parse_error_message(e)
        logger.error(f"Feed fehlerhaft: {name} - {parse_error_message(e)}")

    save_feeds(feeds)
    return feed


def update_all_feeds() -> List[Dict]:
    """Aktualisiert alle Feeds."""
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


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_articles(url: str, css_selector: str = "") -> List[Dict]:
    """Ruft eine Webseite ab und extrahiert Artikel mit mehreren Strategien."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "lxml")
    articles = []

    # Strategie 1: Benutzerdefinierter Selektor
    if css_selector and css_selector.strip():
        elements = soup.select(css_selector)
        for elem in elements[:50]:
            article = extract_article(elem, url)
            if article and article.get("title"):
                articles.append(article)
        if articles:
            logger.info(
                f"Artikel gefunden mit benutzerdefiniertem Selektor: {css_selector}"
            )
            return articles

    # Strategie 2: Suche nach Links mit Datum (time-Element)
    all_times = soup.find_all("time")
    for time_elem in all_times[:50]:
        parent = time_elem.parent
        if parent and parent.name == "a":
            href = parent.get("href", "")
            title = parent.get_text(strip=True)
        else:
            link = time_elem.find_next("a", href=True)
            if link:
                href = link.get("href", "")
                title = link.get_text(strip=True)
            else:
                continue

        if href and title and len(title) > 10:
            if not href.startswith("http"):
                href = url.rstrip("/") + href

            date = time_elem.get("datetime") or time_elem.get_text(strip=True)

            articles.append(
                {
                    "title": title[:200],
                    "url": href,
                    "date_published": date,
                    "content": title,
                }
            )

    if articles:
        logger.info(f"Artikel gefunden via time-Element: {len(articles)}")
        return articles[:50]

    # Strategie 3: Alle Links mit Datum-Attributen
    links_with_dates = soup.find_all("a", href=True, datetime=True)
    for link in links_with_dates[:50]:
        title = link.get_text(strip=True)
        href = link.get("href", "")

        if href and title and len(title) > 10:
            if not href.startswith("http"):
                href = url.rstrip("/") + href

            articles.append(
                {
                    "title": title[:200],
                    "url": href,
                    "date_published": link.get("datetime"),
                    "content": title,
                }
            )

    if articles:
        logger.info(f"Artikel gefunden via datetime-Attribut: {len(articles)}")
        return articles[:50]

    # Strategie 4: Article/Post/News Listen
    selectors = [
        ".article-list-item",
        ".blog-item",
        ".news-item",
        ".post-item",
        ".entry-item",
        "article",
        ".entry",
        ".post",
    ]

    for selector in selectors:
        try:
            elements = soup.select(selector)
            for elem in elements[:50]:
                article = extract_article(elem, url)
                if article and article.get("title"):
                    articles.append(article)
            if articles:
                logger.info(f"Artikel gefunden mit Selektor: {selector}")
                return articles
        except:
            continue

    # Strategie 5: Alle relevanten Links (letzter Fallback)
    all_links = soup.find_all("a", href=True)
    seen = set()

    for link in all_links[:300]:
        href = link.get("href", "")
        title = link.get_text(strip=True)

        if not href or not title or len(title) < 15:
            continue

        # Nur interne Links
        if href.startswith("/"):
            href = url.rstrip("/") + href
        elif not href.startswith(url):
            continue

        if href in seen:
            continue
        seen.add(href)

        articles.append(
            {
                "title": title[:200],
                "url": href,
                "date_published": None,
                "content": title,
            }
        )

    if articles:
        logger.info(f"Artikel gefunden via Link-Scan: {len(articles)}")

    return articles[:50]


def extract_article(element, base_url: str) -> Optional[Dict]:
    """Extrahiert Titel, Link, Datum und Inhalt aus einem Element."""
    try:
        title_elem = (
            element.find(["h1", "h2", "h3", "h4"]) or element.select_one("a") or element
        )
        title = title_elem.get_text(strip=True) if title_elem else ""

        if not title or len(title) < 5:
            return None

        link_elem = element.find("a", href=True) or element
        href = link_elem.get("href", "")
        if href and not href.startswith("http"):
            href = urljoin(base_url, href)

        date_elem = element.find("time")
        date_published = None
        if date_elem:
            date_published = date_elem.get("datetime") or date_elem.get_text(strip=True)

        content = (
            element.get_text(strip=True)[:500] if element.get_text(strip=True) else ""
        )

        return {
            "title": title,
            "url": href,
            "date_published": date_published,
            "content": content,
        }
    except Exception:
        return None


def generate_rss(feed: Dict, articles: List[Dict]) -> str:
    """Generiert eine RSS-Datei."""
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
            except:
                pass

    xml_file = os.path.join(FEEDS_DIR, f"{feed['name']}.xml")
    fg.rss_file(xml_file)
    return xml_file


# ========== Hilfsfunktionen ==========
def get_current_datetime() -> str:
    """Gibt das aktuelle Datum als ISO-String zurück."""
    return datetime.now().isoformat()


def escape_xml(text: str) -> str:
    """Escapt XML-Sonderzeichen."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ========== PHASE 4: Feed-Discovery ==========
def discover_rss_feeds(url: str) -> List[Dict]:
    """Entdeckt RSS/Atom-Feeds auf einer Webseite."""
    import re
    from urllib.parse import urlparse

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # Add https:// if no scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    feeds = []
    parsed = urlparse(url)
    base_url = url.rstrip("/")
    domain = parsed.netloc.replace("www.", "")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, "lxml")

        # Suche nach RSS/Atom-Links im <head>
        for link in soup.find_all(
            "link", type=["application/rss+xml", "application/atom+xml"]
        ):
            href = link.get("href", "")
            title = link.get("title", "RSS Feed")

            if href:
                if not href.startswith("http"):
                    href = base_url + href
                feeds.append(
                    {"url": href, "title": title, "type": "rss", "source": "head"}
                )

        # Suche nach typischen Feed-URLs auf der Seite
        feed_patterns = [
            r"/feed/?",
            r"/rss/?",
            r"/atom/?",
            r"/\.rss$",
            r"/feed\.xml",
            r"/rss\.xml",
            r"/atom\.xml",
            r"/feed/rss",
            r"/news/rss",
            r"/blog/feed",
        ]

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            for pattern in feed_patterns:
                if re.search(pattern, str(href), re.IGNORECASE):
                    if not href.startswith("http"):
                        href = base_url + href
                    if href not in [f["url"] for f in feeds]:
                        feeds.append(
                            {
                                "url": href,
                                "title": link.get_text(strip=True) or "RSS Feed",
                                "type": "rss",
                                "source": "link",
                            }
                        )
                    break

        # Wenn keine Feeds gefunden, als Fallback die Original-URL hinzufügen
        if not feeds:
            feeds.append(
                {
                    "url": url,
                    "title": domain,
                    "type": "scrape",
                    "source": "fallback",
                }
            )

    except Exception as e:
        logger.error(f"Feed-Discovery Fehler für {url}: {e}")
        # Bei Fehler auch die Original-URL als Fallback
        feeds.append(
            {
                "url": url,
                "title": domain,
                "type": "scrape",
                "source": "fallback",
            }
        )

    return feeds[:10]


# ========== PHASE 6: OPML-Import ==========
def parse_opml(content: bytes) -> List[Dict]:
    """Parst eine OPML-Datei und extrahiert Feeds."""
    import re

    feeds = []

    try:
        content_str = content.decode("utf-8", errors="ignore")

        # Find all outline elements with xmlUrl attribute (including self-closing tags)
        # Pattern matches both: <outline ... xmlUrl="..."/> and <outline ... xmlUrl="...">
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
