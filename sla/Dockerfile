FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sla_calculator.py .

ENV PROBER_METRICS_URL=http://prober:9100/metrics \
    SCRAPE_INTERVAL=60 \
    LOG_LEVEL=INFO \
    METRICS_PORT=9101 \
    SLA_WINDOW=1h

CMD ["python", "sla_calculator.py"]
