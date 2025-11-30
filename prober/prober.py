import sys
import time
import signal
import logging
import json
import socket

import requests
from environs import Env
from prometheus_client import start_http_server, Counter, Gauge

env = Env()
env.read_env()


class Config(object):
    target_url = env("TARGET_URL")
    scrape_interval = env.int("SCRAPE_INTERVAL", 30)
    log_level = env.log_level("LOG_LEVEL", logging.INFO)
    metrics_port = env.int("METRICS_PORT", 9100)


PROBE_REQUESTS_TOTAL = Counter(
    "probe_requests_total", "Total count of probe runs"
)
PROBE_SUCCESS = Counter(
    "probe_success", "Total count of successful probe runs"
)
PROBE_FAILURE = Counter(
    "probe_failure", "Total count of failed probe runs"
)
PROBE_DURATION_SECONDS = Gauge(
    "probe_duration_seconds", "Duration of last probe run in seconds"
)


def setup_logging(config: Config) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log_level,
        format="%(asctime)s %(levelname)s:%message)s",
    )


class HttpProberClient:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.hostname = socket.gethostname()

    def probe(self) -> None:
        PROBE_REQUESTS_TOTAL.inc()
        start = time.perf_counter()
        ok = False
        status_code: int | None = None
        error: str | None = None

        try:
            resp = requests.get(self.config.target_url, timeout=5)
            status_code = resp.status_code
            ok = 200 <= resp.status_code < 300
        except Exception as err:
            logging.error("probe error: %s", err)
            error = str(err)

        duration = time.perf_counter() - start
        PROBE_DURATION_SECONDS.set(duration)

        if ok:
            PROBE_SUCCESS.inc()
            logging.info("probe success, duration=%.3fs", duration)
        else:
            PROBE_FAILURE.inc()
            logging.warning("probe failure, duration=%.3fs", duration)

        log_record = {
            "event": "probe_result",
            "target": self.config.target_url,
            "ok": ok,
            "status_code": status_code,
            "error": error,
            "duration_ms": round(duration * 1000, 3),
            "inst": self.hostname,
            "system": "prober",
            "env": "st",
        }
        print(json.dumps(log_record, ensure_ascii=False), flush=True)


def main() -> None:
    config = Config()
    setup_logging(config)

    logging.info("Starting prober exporter on port %d", config.metrics_port)
    start_http_server(config.metrics_port)
    client = HttpProberClient(config)

    while True:
        client.probe()
        time.sleep(config.scrape_interval)


def terminate(signum, frame):
    print("Terminating")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, terminate)
    main()
