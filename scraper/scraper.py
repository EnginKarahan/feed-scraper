"""Web-Scraper: Article-Extraktion und Feed-Discovery."""

import re
import logging
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_articles(url: str, css_selector: str = "") -> List[Dict]:
    """Ruft eine Webseite ab und extrahiert Artikel mit mehreren Strategien.

    Args:
        url: URL der Webseite
        css_selector: Optionaler CSS-Selektor für Artikel

    Returns:
        Liste von Article-Dicts
    """
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
        except Exception:
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
    """Extrahiert Titel, Link, Datum und Inhalt aus einem Element.

    Args:
        element: BeautifulSoup-Element
        base_url: Basis-URL für relative Links

    Returns:
        Article-Dict oder None
    """
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


def discover_rss_feeds(url: str) -> List[Dict]:
    """Entdeckt RSS/Atom-Feeds auf einer Webseite.

    Args:
        url: URL der Webseite

    Returns:
        Liste von DiscoveredFeed-Dicts
    """
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
        feeds.append(
            {
                "url": url,
                "title": domain,
                "type": "scrape",
                "source": "fallback",
            }
        )

    return feeds[:10]


def parse_error_message(e: Exception) -> str:
    """Wandelt eine Exception in eine benutzerfreundliche Fehlermeldung um.

    Args:
        e: Exception-Objekt

    Returns:
        Benutzerfreundliche Fehlermeldung
    """
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
