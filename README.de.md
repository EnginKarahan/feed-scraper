# Feed Scraper

RSS-Feed-Generator fuer Webseiten ohne nativen RSS-Support.

## Funktionen

- Automatische Artikel-Erkennung auf beliebigen Webseiten
- RSS-Export kompatibel mit FreshRSS und anderen Readern
- Feed-Discovery - findet RSS-Feeds automatisch oder erstellt welche von Webseiten
- Bulk-Import - mehrere URLs gleichzeitig hinzufuegen
- OPML Import/Export mit Duplikatsuche
- URL-Duplikatsuche (normalisierter Vergleich)
- Backup und Restore
- Geplante Aktualisierungen (2x taeglich)
- Mehrsprachige Oberflaeche (Deutsch, Englisch, Tuerkisch)

## Schnellstart

### Lokale Entwicklung

```bash
git clone https://github.com/EnginKarahan/feed-scraper.git
cd feed-scraper

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Oeffnen: http://localhost:5000

### Docker (GHCR - Empfohlen)

```bash
# Von GitHub Container Registry ziehen
docker pull ghcr.io/enginkarahan/feed-scraper:latest

# Starten
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data ghcr.io/enginkarahan/feed-scraper:latest
```

### Docker (Selbst bauen)

```bash
docker build -t feed-scraper .
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data feed-scraper
```

### Docker Compose

Zur bestehenden docker-compose.yml hinzufuegen:

```yaml
services:
  feed-scraper:
    image: ghcr.io/enginkarahan/feed-scraper:latest
    ports:
      - "5000:5000"
    volumes:
      - ./feed-scraper-data:/app/data
    restart: unless-stopped
```

Aktualisieren: `docker compose pull && docker compose up -d`

## Projektstruktur

```
feed-scraper/
├── main.py                    # FastAPI-Anwendung
├── scraper/
│   ├── __init__.py          # Paket-Exports & Kompatibilitaet
│   ├── config.py            # Konfiguration
│   ├── models.py            # Pydantic Models & Typen
│   ├── feed_service.py      # Feed CRUD-Operationen
│   ├── rss_generator.py     # RSS-Feed-Erstellung
│   ├── scraper.py           # Web-Scraping & Artikel-Extraktion
│   └── opml_parser.py       # OPML Import/Export
├── tests/                   # Test-Suite
└── templates/               # HTML-Templates
```

## API Endpunkte

| Methode | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | / | WebUI |
| GET | /feed/{name}.xml | RSS-Feed |
| GET | /export/opml | OPML-Export fuer FreshRSS |
| POST | /api/feeds | Feed erstellen |
| POST | /api/feeds/bulk | Mehrere erstellen |
| POST | /api/feeds/{name}/refresh | Einzelner aktualisieren |
| POST | /api/refresh-all | Alle aktualisieren |
| DELETE | /api/feeds/{name} | Feed loeschen |
| GET | /api/discover?url= | Feeds entdecken |
| POST | /api/preview | Vorschau |
| POST | /import/opml | OPML importieren |
| GET | /api/backup | Backup herunterladen |
| POST | /api/restore | Backup wiederherstellen |

## Konfiguration

Umgebungsvariablen:

| Variable | Standard | Beschreibung |
|----------|---------|--------------|
| DATA_DIR | /app/data | Datenverzeichnis |
| CONFIG_DIR | /app/config | Konfigurationsverzeichnis |

Daten werden gespeichert in:
- `data/db/feeds.json` - Feed-Konfiguration
- `data/feeds/*.xml` - Generierte RSS-Feeds

## Entwicklung

### Tests ausfuehren

```bash
pip install pytest
pytest tests/
```

## Deployment

- Standard-Port: 5000
- Zeitplan: 06:00 und 18:00 Uhr (aenderbar in main.py)
- Rate Limiting: 1 Request pro Sekunde um Sperren zu vermeiden
- Alle Feeds werden in lokaler JSON-Datenbank gespeichert

## Lizenz

MIT
