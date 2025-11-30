# **SRE Observability Stack**

Minimal observability environment for measuring service availability in Kubernetes.
Includes HTTP probing, metrics export, SLA calculation, and integration with Sage Observability.

## Overview

This project implements a compact availability monitoring pipeline:

* periodic HTTP probing of a target service;
* export of probe metrics (`probe_success`, `probe_failure`, latency);
* SLA calculation based on historical probe data;
* publishing SLA as a manual metric to Sage;
* exposing all metrics via `/metrics` (Prometheus format).

The stack is suitable for test clusters, training stands, or lightweight observability demos.

## Architecture

```
                ┌──────────────────────────┐
                │       OnCall service     │
                │   HTTP endpoint to probe │
                └───────────────┬──────────┘
                                │
                                ▼
                   ┌──────────────────────┐
                   │        Prober        │
                   │  probe_success       │
                   │  probe_failure       │
                   │  probe_duration      │
                   └───────────┬──────────┘
                               │
                     Prometheus scrape
                               │
                               ▼
                   ┌──────────────────────┐
                   │    SLA Calculator    │
                   │ increase(probe_*)    │
                   │ SLA = ok/(all) * 100 │
                   │ export to Sage       │
                   └───────────┬──────────┘
                               │
                        Manual metric API
                               │
                               ▼
                ┌──────────────────────────┐
                │      Sage Observability  │
                │   PQL logs & metrics     │
                └──────────────────────────┘
```

## Components

### Prober (`prober/`)

Periodically performs HTTP GET requests to the configured target service and exports metrics:

* `probe_requests_total`
* `probe_success_total`
* `probe_failure_total`
* `probe_duration_seconds`

Log events are emitted as structured JSON suitable for PQL queries.

### SLA Calculator (`sla/`)

Consumes historical probe metrics, calculates SLA over a sliding window, and:

* exposes `service_sla_percent` via `/metrics`;
* publishes the SLA value into Sage as a manual metric:

  ```
  PUT https://sage.sre-ab.ru/sauron/api/Metric
  ```

### Kubernetes manifests (`manifests/`)

Provides deployments and services for:

* MySQL (backend for OnCall)
* OnCall service
* Prober
* SLA Calculator

All metric endpoints are annotated for Prometheus-based scraping.

## Deployment

```
export KUBE_NS=st-your-namespace

# MySQL
kubectl apply -f manifests/mysql/secret.yaml      -n $KUBE_NS
kubectl apply -f manifests/mysql/statefulset.yaml -n $KUBE_NS
kubectl apply -f manifests/mysql/service.yaml     -n $KUBE_NS

# OnCall
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/config.yaml    | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/deployment.yaml| kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/service.yaml   | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/ingress.yaml   | kubectl apply -f - -n $KUBE_NS

# Prober & SLA Calculator
kubectl apply -f manifests/prober/ -n $KUBE_NS
kubectl apply -f manifests/sla/    -n $KUBE_NS
```

## Verification

### Local metrics

```
kubectl exec -n $KUBE_NS deploy/prober -- curl -s localhost:9100/metrics
kubectl exec -n $KUBE_NS deploy/sla-calculator -- curl -s localhost:9101/metrics
```

### Probe logs in Sage (PQL)

```
pql {group="ab2_islamov", system="prober"}
```

### Manual SLA metric in Sage

```
curl -X POST \
  https://sage.sre-ab.ru/sauron/api/Metric/search \
  -H "Authorization: Bearer $SAGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "service_sla_percent",
        "labels": {
          "group": "ab2_islamov",
          "env": "prod",
          "system": "sla-app",
          "service": "oncall"
        }
      }'
```

## Demo Script

`demo.sh` prints:

* current probe & SLA metrics;
* recent probe events from Sage;
* latest SLA manual metric.

## Docker

Build:

```
docker build -t therad445/ab2-prober:<tag> prober/
docker build -t therad445/ab2-sla-calculator:<tag> sla/
```

Publish:

```
docker push therad445/ab2-prober:<tag>
docker push therad445/ab2-sla-calculator:<tag>
```

## Extensions

The stack can be extended with:

* alerting on SLA degradation;
* Grafana dashboards through the Sage datasource;
* multiple probers for distributed availability checks;
* histogram-based latency SLOs.

## License

[MIT](LICENSE)
