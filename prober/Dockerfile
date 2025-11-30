FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY prober.py .

ENV TARGET_URL=http://oncall:8080/health \
    SCRAPE_INTERVAL=30 \
    LOG_LEVEL=INFO \
    METRICS_PORT=9100

CMD ["python", "prober.py"]