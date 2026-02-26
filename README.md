# Feed Scraper

RSS feed generator for websites without native RSS support.

## Features

- Automatic article detection on any webpage
- RSS export compatible with FreshRSS and other readers
- Feed discovery - finds RSS feeds automatically or creates from website
- Bulk import - add multiple URLs at once
- OPML import/export with duplicate detection
- URL duplicate checking (normalized comparison)
- Backup and restore
- Scheduled updates (2x daily)
- Multi-language UI (German, English, Turkish)

## Quick Start

### Local Development

```bash
git clone https://github.com/EnginKarahan/feed-scraper.git
cd feed-scraper

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Open: http://localhost:5000

### Docker

```bash
docker build -t feed-scraper .
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data feed-scraper
```

### Docker Compose

Add to your existing docker-compose.yml:

```yaml
services:
  feed-scraper:
    image: enginkarahan/feed-scraper:latest
    ports:
      - "5000:5000"
    volumes:
      - ./feed-scraper-data:/app/data
    restart: unless-stopped
```

Update: `docker-compose pull && docker-compose up -d`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | WebUI |
| GET | /feed/{name}.xml | RSS feed |
| GET | /export/opml | OPML export for FreshRSS |
| POST | /api/feeds | Create feed |
| POST | /api/feeds/bulk | Bulk create |
| POST | /api/feeds/{name}/refresh | Refresh single |
| POST | /api/refresh-all | Refresh all |
| DELETE | /api/feeds/{name} | Delete feed |
| GET | /api/discover?url= | Discover feeds |
| POST | /api/preview | Preview articles |
| POST | /import/opml | Import OPML |
| GET | /api/backup | Download backup |
| POST | /api/restore | Restore backup |

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| DATA_DIR | /app/data | Data directory |
| CONFIG_DIR | /app/config | Config directory |

Data is stored in:
- `data/db/feeds.json` - Feed configuration
- `data/feeds/*.xml` - Generated RSS feeds

## Deployment Notes

- Default port: 5000
- Scheduler runs at 06:00 and 18:00 (configurable in main.py)
- Rate limiting: 1 request per second to avoid bans
- All feeds stored in local JSON database

## License

MIT
