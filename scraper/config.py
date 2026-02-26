from datetime import datetime
import os

# Lokale Pfade als Standard (für Entwicklung)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
FEEDS_DIR = os.path.join(DATA_DIR, "feeds")
DB_FILE = os.path.join(DATA_DIR, "db", "feeds.json")
LOG_FILE = os.path.join(DATA_DIR, "logs", "scraper.log")

os.makedirs(FEEDS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
