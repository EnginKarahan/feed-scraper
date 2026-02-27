"""Pydantic Models und Typen für den Feed-Scraper."""

from typing import Optional
from typing_extensions import TypedDict
from datetime import datetime
from pydantic import BaseModel, Field


class FeedCreate(BaseModel):
    """Schema für das Erstellen eines Feeds."""

    name: str = Field(..., description="Eindeutiger Name des Feeds")
    url: str = Field(..., description="URL der Webseite")
    css_selector: str = Field(
        default="", description="Optionaler CSS-Selektor für Artikel-Extraktion"
    )
    description: str = Field(default="", description="Beschreibung oder Kategorie")


class BulkFeedCreate(BaseModel):
    """Schema für Bulk-Import mehrerer Feeds."""

    feeds: list[FeedCreate] = Field(..., description="Liste von Feeds zum Importieren")


class Feed(TypedDict, total=False):
    """Feed-Datenstruktur (wie in JSON-DB gespeichert)."""

    name: str
    url: str
    css_selector: str
    description: str
    created: str
    last_update: Optional[str]
    last_status: Optional[str]
    last_error: Optional[str]
    article_count: int


class Article(TypedDict, total=False):
    """Artikel-Datenstruktur."""

    title: str
    url: str
    date_published: Optional[str]
    content: str


class DiscoveredFeed(TypedDict, total=False):
    """Entdeckter Feed bei Feed-Discovery."""

    url: str
    title: str
    type: str
    source: str


class FeedUpdateResult(TypedDict, total=False):
    """Ergebnis eines Feed-Updates."""

    name: str
    status: str
    article_count: Optional[int]
    error: Optional[str]


class ImportResult(TypedDict, total=False):
    """Ergebnis eines Import-Vorgangs."""

    name: str
    url: str
    reason: str


class BulkImportResponse(BaseModel):
    """Antwort für Bulk-Import."""

    status: str
    created: int
    errors: int
    skipped: int
    skipped_details: list[ImportResult]
    feeds: list[Feed]
    error_details: list[dict]


class OpmlImportResponse(BaseModel):
    """Antwort für OPML-Import."""

    status: str
    imported: int
    errors: int
    skipped: int
    skipped_details: list[ImportResult]
    error_details: list[dict]
