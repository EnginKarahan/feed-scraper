"""Feed-Scraper: FastAPI-Anwendung.

RSS feed generator für Webseiten ohne nativen RSS-Support.
"""

import logging
import os
import schedule
import time
from typing import List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import scraper
from scraper.config import FEEDS_DIR
from scraper.models import FeedCreate, BulkFeedCreate
from scraper.opml_parser import generate_opml

# Logging
logger = logging.getLogger(__name__)

# FastAPI-App
app = FastAPI(
    title="Feed Scraper", description="RSS Feed Generator für beliebige Webseiten"
)

# Statische Dateien
app.mount(
    "/templates",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "templates")),
    name="templates",
)

# Templates
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


# ==================== ROUTES ====================


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Zeigt die Startseite mit allen Feeds."""
    feeds = scraper.load_feeds()
    return templates.TemplateResponse(
        "index.html", {"request": request, "feeds": feeds}
    )


@app.get("/feed/{feed_name}.xml")
async def get_feed(feed_name: str):
    """Liefert den RSS-Feed für einen bestimmten Feed."""
    xml_file = os.path.join(FEEDS_DIR, f"{feed_name}.xml")
    if not os.path.exists(xml_file):
        raise HTTPException(status_code=404, detail="Feed nicht gefunden")
    with open(xml_file, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="application/xml")


# ==================== OPML ====================


@app.get("/export/opml")
async def export_opml(request: Request):
    """Exportiert alle Feeds als OPML für FreshRSS."""
    feeds = scraper.load_feeds()

    # Basis-URL ermitteln
    base_url = request.headers.get("X-Base-Url")
    if not base_url:
        base_url = str(request.base_url).rstrip("/")

    if not base_url or base_url == "/":
        forward_host = request.headers.get("X-Forwarded-Host")
        if forward_host:
            scheme = request.headers.get("X-Forwarded-Proto", "http")
            base_url = f"{scheme}://{forward_host}"
        else:
            base_url = "http://localhost:5000"

    opml_content = generate_opml(feeds, base_url)

    return Response(
        content=opml_content,
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=feeds.opml"},
    )


@app.post("/import/opml")
async def import_opml(request: Request):
    """Importiert Feeds aus einer OPML-Datei."""
    content = await request.body()
    logger.info(f"OPML Import: received {len(content)} bytes")

    if not content:
        return {"status": "error", "error": "No content received"}

    try:
        existing_feeds = scraper.load_feeds()
        existing_urls = {
            scraper.normalize_url(f.get("url", "")) for f in existing_feeds
        }

        parsed_feeds = scraper.parse_opml(content)
        logger.info(f"OPML Import: parsed {len(parsed_feeds)} feeds")

        if not parsed_feeds:
            return {"status": "error", "error": "No feeds found in OPML"}

        results = []
        errors = []
        skipped = []

        for feed in parsed_feeds:
            normalized_url = scraper.normalize_url(feed.get("url", ""))

            if normalized_url in existing_urls:
                skipped.append(
                    {
                        "name": feed["name"],
                        "url": feed["url"],
                        "reason": "URL existiert bereits",
                    }
                )
                continue

            if normalized_url in [
                scraper.normalize_url(r.get("url", "")) for r in results
            ]:
                skipped.append(
                    {
                        "name": feed["name"],
                        "url": feed["url"],
                        "reason": "Doppelte URL in OPML",
                    }
                )
                continue

            try:
                result = scraper.add_feed(
                    name=feed["name"],
                    url=feed["url"],
                    css_selector=feed.get("css_selector", ""),
                    description=feed.get("description", ""),
                    normalize_func=scraper.normalize_url,
                )
                results.append(result)
                existing_urls.add(normalized_url)
            except ValueError as e:
                errors.append({"name": feed["name"], "error": str(e)})
            except Exception as e:
                errors.append({"name": feed["name"], "error": str(e)})

        return {
            "status": "completed",
            "imported": len(results),
            "errors": len(errors),
            "skipped": len(skipped),
            "skipped_details": skipped[:10],
            "error_details": errors[:10],
        }
    except Exception as e:
        logger.error(f"OPML Import Error: {e}")
        return {"status": "error", "error": str(e)}


# ==================== BACKUP ====================


@app.get("/api/backup")
async def create_backup():
    """Erstellt ein Backup der Feed-Konfiguration."""
    import json

    feeds = scraper.load_feeds()
    content = json.dumps(
        {"feeds": feeds, "backup_date": scraper.get_current_datetime()},
        indent=2,
        ensure_ascii=False,
    )

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=feed-scraper-backup.json"
        },
    )


@app.post("/api/restore")
async def restore_backup(request: Request):
    """Stellt ein Backup wieder her."""
    import json

    content = await request.body()
    try:
        data = json.loads(content)
        feeds = data.get("feeds", [])
        scraper.save_feeds(feeds)
        return {
            "status": "success",
            "restored": len(feeds),
            "message": f"{len(feeds)} Feeds wiederhergestellt",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Restore Error: {str(e)}")


# ==================== FEEDS CRUD ====================


@app.post("/api/feeds", status_code=201)
async def create_feed(feed: FeedCreate):
    """Erstellt einen neuen Feed."""
    try:
        result = scraper.add_feed(
            name=feed.name,
            url=feed.url,
            css_selector=feed.css_selector or "",
            description=feed.description or "",
            normalize_func=scraper.normalize_url,
        )
        return {"status": "success", "feed": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/feeds")
async def list_feeds():
    """Listet alle Feeds auf."""
    return scraper.load_feeds()


@app.put("/api/feeds/{feed_name}")
async def update_feed(feed_name: str, feed: FeedCreate):
    """Aktualisiert einen Feed."""
    try:
        result = scraper.update_feed_data(
            name=feed_name,
            new_name=feed.name,
            url=feed.url,
            css_selector=feed.css_selector or "",
            description=feed.description or "",
        )
        return {"status": "success", "feed": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/feeds/{feed_name}")
async def delete_feed(feed_name: str):
    """Löscht einen Feed."""
    if scraper.delete_feed(feed_name):
        return {"status": "success", "message": f"Feed '{feed_name}' gelöscht"}
    raise HTTPException(status_code=404, detail="Feed nicht gefunden")


# ==================== BULK OPERATIONS ====================


@app.post("/api/feeds/bulk")
async def create_bulk_feeds(bulk: BulkFeedCreate):
    """Erstellt mehrere Feeds auf einmal."""
    existing_feeds = scraper.load_feeds()
    existing_urls = {scraper.normalize_url(f.get("url", "")) for f in existing_feeds}

    results = []
    errors = []
    skipped = []

    for feed in bulk.feeds:
        normalized_url = scraper.normalize_url(feed.url)

        if normalized_url in existing_urls:
            skipped.append(
                {"name": feed.name, "url": feed.url, "reason": "URL existiert bereits"}
            )
            continue

        if normalized_url in [scraper.normalize_url(r.get("url", "")) for r in results]:
            skipped.append(
                {
                    "name": feed.name,
                    "url": feed.url,
                    "reason": "Doppelte URL in Eingabe",
                }
            )
            continue

        try:
            result = scraper.add_feed(
                name=feed.name,
                url=feed.url,
                css_selector=feed.css_selector or "",
                description=feed.description or "",
                normalize_func=scraper.normalize_url,
            )
            results.append(result)
            existing_urls.add(normalized_url)
        except ValueError as e:
            errors.append({"name": feed.name, "error": str(e)})
        except Exception as e:
            errors.append({"name": feed.name, "error": str(e)})

    return {
        "status": "completed",
        "created": len(results),
        "errors": len(errors),
        "skipped": len(skipped),
        "skipped_details": skipped[:10],
        "feeds": results,
        "error_details": errors,
    }


@app.post("/api/feeds/bulk/refresh")
async def bulk_refresh(feed_names: List[str]):
    """Aktualisiert mehrere Feeds."""
    results = []
    for name in feed_names:
        try:
            result = scraper.update_feed(name)
            results.append(
                {
                    "name": name,
                    "status": "success",
                    "articles": result.get("article_count", 0),
                }
            )
        except Exception as e:
            results.append({"name": name, "status": "error", "error": str(e)})
    return {"status": "success", "results": results}


@app.post("/api/feeds/bulk/delete")
async def bulk_delete(feed_names: List[str]):
    """Löscht mehrere Feeds."""
    deleted = []
    errors = []
    for name in feed_names:
        if scraper.delete_feed(name):
            deleted.append(name)
        else:
            errors.append(name)
    return {"status": "success", "deleted": deleted, "errors": errors}


# ==================== REFRESH ====================


@app.post("/api/feeds/{feed_name}/refresh")
async def refresh_feed(feed_name: str):
    """Aktualisiert einen einzelnen Feed."""
    try:
        result = scraper.update_feed(feed_name)
        return {"status": "success", "feed": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/refresh-all")
async def refresh_all():
    """Aktualisiert alle Feeds."""
    results = scraper.update_all_feeds()
    return {"status": "success", "results": results}


# ==================== DISCOVERY & PREVIEW ====================


@app.get("/api/discover")
async def discover_feeds(url: str):
    """Entdeckt RSS-Feeds auf einer Webseite."""
    try:
        feeds = scraper.discover_rss_feeds(url)
        return {"status": "success", "url": url, "feeds": feeds}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/preview")
async def preview_feed(feed: FeedCreate):
    """Zeigt eine Vorschau der extrahierten Artikel."""
    try:
        articles = scraper.fetch_articles(feed.url, feed.css_selector or "")
        return {
            "status": "success",
            "url": feed.url,
            "css_selector": feed.css_selector,
            "article_count": len(articles),
            "articles": articles[:10],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ==================== STATUS ====================


@app.get("/api/status")
async def status():
    """Gibt den Status aller Feeds zurück."""
    feeds = scraper.load_feeds()
    success = sum(1 for f in feeds if f.get("last_status") == "success")
    error = sum(1 for f in feeds if f.get("last_status") == "error")
    return {
        "total": len(feeds),
        "success": success,
        "error": error,
        "last_update": max(
            (f.get("last_update") for f in feeds if f.get("last_update")), default=None
        ),
    }


# ==================== SCHEDULER ====================


def run_scheduler():
    """Hintergrund-Scheduler für automatische Updates."""
    schedule.every().day.at("06:00").do(lambda: scraper.update_all_feeds())
    schedule.every().day.at("18:00").do(lambda: scraper.update_all_feeds())

    logger.info("Scheduler gestartet: Updates um 06:00 und 18:00")

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ != "uvicorn":
    import threading

    threading.Thread(target=run_scheduler, daemon=True).start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
