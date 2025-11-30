import sys
import time
import signal
import logging
from datetime import datetime

import requests
from environs import Env
from prometheus_client import start_http_server, Gauge

env = Env()
env.read_env()

SAGE_METRIC_URL = "https://sage.sre-ab.ru/sauron/api/Metric"
SAGE_TOKEN = env("SAGE_TOKEN", None)
SAGE_LABELS = {
    "group": "ab2_islamov",
    "env": "prod",
    "system": "sla-app",
    "service": "oncall",
}


class Config(object):
    prometheus_api_url = env(
        "PROMETHEUS_API_URL",
        "http://prometheus-server.monitoring.svc.cluster.local:9090",
    )
    scrape_interval = env.int("SCRAPE_INTERVAL", 60)
    log_level = env.log_level("LOG_LEVEL", logging.INFO)
    metrics_port = env.int("METRICS_PORT", 9101)
    window = env("SLA_WINDOW", "1h")


SERVICE_SLA_PERCENT = Gauge(
    "service_sla_percent",
    "Calculated SLA for target service over window",
)


def setup_logging(config: Config) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log_level,
        format="%(asctime)s %(levelname)s:%(message)s",
    )


class PrometheusClient:
    def __init__(self, config: Config) -> None:
        self._url = config.prometheus_api_url

    def instant_query(self, query: str, ts: float) -> float | None:
        try:
            resp = requests.get(
                f"{self._url}/api/v1/query",
                params={"query": query, "time": ts},
                timeout=5,
            )
            data = resp.json()
        except Exception as err:
            logging.error("prometheus request error: %s", err)
            return None

        if data.get("status") != "success":
            logging.error("prometheus error response: %s", data)
            return None

        result = data.get("data", {}).get("result", [])
        if not result:
            return None

        # [timestamp, value]
        return float(result[0]["value"][1])


def push_sla_to_sage(sla_value: float) -> None:
    if not SAGE_TOKEN:
        return

    body = {
        "name": "service_sla_percent",
        "labels": SAGE_LABELS,
        "value": float(sla_value),
    }

    try:
        resp = requests.put(
            SAGE_METRIC_URL,
            headers={
                "Authorization": f"Bearer {SAGE_TOKEN}",
                "Content-Type": "application/json",
                "accept": "*/*",
            },
            json=body,
            timeout=3,
        )
        if resp.status_code != 200:
            logging.warning(
                "failed to push SLA metric to Sage: status=%s body=%s",
                resp.status_code,
                resp.text,
            )
    except Exception as exc:
        logging.warning("error while pushing SLA metric to Sage: %s", exc)


def main() -> None:
    config = Config()
    setup_logging(config)
    prom = PrometheusClient(config)

    logging.info(
        "Starting SLA exporter on port %d (window=%s)",
        config.metrics_port,
        config.window,
    )
    start_http_server(config.metrics_port)

    while True:
        now = datetime.utcnow().timestamp()

        q_success = f"increase(probe_success_total[{config.window}])"
        q_failure = f"increase(probe_failure_total[{config.window}])"

        success = prom.instant_query(q_success, now) or 0.0
        failure = prom.instant_query(q_failure, now) or 0.0
        total = success + failure

        if total <= 0:
            logging.info("no data for SLA window=%s", config.window)
        else:
            sla = success / total * 100.0
            SERVICE_SLA_PERCENT.set(sla)
            logging.info(
                "SLA window=%s success=%.1f failure=%.1f -> SLA=%.3f%%",
                config.window,
                success,
                failure,
                sla,
            )
            push_sla_to_sage(sla)

        time.sleep(config.scrape_interval)


def terminate(signum, frame):
    print("Terminating")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    main()
