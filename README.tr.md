# Feed Scraper

Web siteleri icin RSS feed ureticisi.

## Ozellikler

- Herhangi bir web sayfasinda otomatik makale tespiti
- FreshRSS ve diger okuyucularla uyumlu RSS export
- Feed kesfi - RSS feed'leri otomatik bulur veya web sitesinden olusturur
- Toplu import - ayni anda birden fazla URL ekle
- OPML import/export ve kopya kontrolu
- URL kopya kontrolu (normallestirilmis karsilastirma)
- Yedekleme ve geri yukleme
- Zamanlanmis guncellemeler (gunde 2 kez)
- Cok dilli arayuz (Almanca, Ingilizce, Turkce)

## Hizli Baslangic

### Yerel Gelistirme

```bash
git clone https://github.com/EnginKarahan/feed-scraper.git
cd feed-scraper

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

Acilir: http://localhost:5000

### Docker

```bash
docker build -t feed-scraper .
docker run -d -p 5000:5000 -v $(pwd)/data:/app/data feed-scraper
```

### Docker Compose

Mevcut docker-compose.yml dosyaniza ekleyin:

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

Guncelleme: `docker-compose pull && docker-compose up -d`

## API Uc Noktalari

| Metot | Endpoint | Aciklama |
|-------|----------|-----------|
| GET | / | WebUI |
| GET | /feed/{name}.xml | RSS feed |
| GET | /export/opml | FreshRSS icin OPML export |
| POST | /api/feeds | Feed olustur |
| POST | /api/feeds/bulk | Toplu olustur |
| POST | /api/feeds/{name}/refresh | Tek yenile |
| POST | /api/refresh-all | Tumerini yenile |
| DELETE | /api/feeds/{name} | Feed sil |
| GET | /api/discover?url= | Feed keşfet |
| POST | /api/preview | Onizleme |
| POST | /import/opml | OPML import et |
| GET | /api/backup | Yedek indir |
| POST | /api/restore | Yedek geri yukle |

## Yapilandirma

Ortam degiskenleri:

| Degisken | Varsayilan | Aciklama |
|----------|-----------|-----------|
| DATA_DIR | /app/data | Veri dizini |
| CONFIG_DIR | /app/config | Yapilandirma dizini |

Veriler saklanir:
- `data/db/feeds.json` - Feed yapilandirmasi
- `data/feeds/*.xml` - Uretilen RSS feedleri

## Dagitim

- Varsayilan port: 5000
- Zamanlama: 06:00 ve 18:00 (main.py'de degistirilebilir)
- Rate limiting: Yasaklanmamak icin saniyede 1 istek
- Tum feedler yerel JSON veritabaninda saklanir

## Lisans

MIT
