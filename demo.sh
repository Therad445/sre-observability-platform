#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-st-ab2-islamov}"

echo "Namespace: $NAMESPACE"
echo

get_pod() {
  local label="$1"
  kubectl get pods -n "$NAMESPACE" -l "$label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true
}

echo "Checking prober..."
PROBER_POD="$(get_pod 'app=prober')"
if [[ -z "$PROBER_POD" ]]; then
  echo "  prober pod not found"
else
  echo "  prober pod: $PROBER_POD"
  kubectl exec -n "$NAMESPACE" "$PROBER_POD" -- \
    curl -sS http://127.0.0.1:9100/metrics \
    | grep -E 'probe_(requests|success|failure|duration)' \
    | head
fi
echo

echo "Checking SLA calculator..."
SLA_POD="$(get_pod 'app=sla-calculator')"
if [[ -z "$SLA_POD" ]]; then
  echo "  sla pod not found"
else
  echo "  sla pod: $SLA_POD"
  kubectl exec -n "$NAMESPACE" "$SLA_POD" -- \
    curl -sS http://127.0.0.1:9101/metrics \
    | grep -E 'service_sla_percent' || true
fi
echo

if [[ -z "${SAGE_TOKEN:-}" ]]; then
  echo "SAGE_TOKEN is not set, skip Sage API checks"
  exit 0
fi

echo "PQL (prober metrics aggregated by __name__)..."
curl -sS --request POST \
  --url https://sage.sre-ab.ru/mage/api/search \
  --header "Authorization: Bearer ${SAGE_TOKEN}" \
  --header 'Content-Type: application/json' \
  --header 'Source: prober' \
  --data "{
    \"query\": \"pql {group=\\\"ab2_islamov\\\", system=\\\"prober\\\"} | stats count by __name__\",
    \"size\": 1000,
    \"startTime\": \"2025-11-30T00:00:00Z\",
    \"endTime\":   \"2025-11-30T23:59:59Z\"
  }" | jq .
echo

echo "Manual metric service_sla_percent..."
curl -sS --request POST \
  --url https://sage.sre-ab.ru/sauron/api/Metric/search \
  --header "Authorization: Bearer ${SAGE_TOKEN}" \
  --header 'Content-Type: application/json' \
  --header 'accept: */*' \
  --data '{
    "name": "service_sla_percent",
    "labels": {
      "group":   "ab2_islamov",
      "env":     "prod",
      "system":  "sla-app",
      "service": "oncall"
    }
  }' | jq .
echo
