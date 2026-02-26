FROM python:3.11-slim

LABEL maintainer="feed-scraper"
LABEL description="RSS Feed Generator for websites without RSS"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/feeds /app/data/db /app/data/logs /app/config

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV CONFIG_DIR=/app/config

CMD ["python", "main.py"]
