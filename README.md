# SRE Observability Stack

Минимальный стенд наблюдаемости для измерения доступности сервиса в Kubernetes.

**Что делает:** периодически проверяет HTTP‑доступность целевого сервиса, экспортирует метрики в формате Prometheus, считает SLA на основе истории проб и (опционально) публикует SLA как ручную метрику в Sage Observability.

> Подходит для учебных стендов, тестовых кластеров и компактных демо по SRE/observability.

---

## Возможности

* Периодические HTTP‑пробы целевого сервиса
* Метрики проб: успех/ошибка/латентность
* Расчёт SLA по истории проб (скользящее окно)
* Экспорт SLA в `/metrics`
* Публикация SLA в Sage Observability (manual metric API)
* Структурированные JSON‑логи для PQL

---

## Архитектура

```
                ┌──────────────────────────┐
                │        OnCall service    │
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
                │     Sage Observability   │
                │     PQL logs & metrics   │
                └──────────────────────────┘
```

---

## Компоненты

### Prober (`prober/`)

Периодически выполняет HTTP GET запросы к конфигурируемой цели и экспортирует метрики:

* `probe_requests_total`
* `probe_success_total`
* `probe_failure_total`
* `probe_duration_seconds`

Логи событий пишутся в структурированном JSON (удобно для PQL).

### SLA Calculator (`sla/`)

Считывает исторические метрики проб, считает SLA на скользящем окне и:

* экспортирует `service_sla_percent` через `/metrics`;
* публикует SLA в Sage как manual metric (опционально):

  ```
  PUT https://sage.sre-ab.ru/sauron/api/Metric
  ```

### Kubernetes manifests (`manifests/`)

Манифесты развёртывания для:

* MySQL (backend для OnCall)
* OnCall service
* Prober
* SLA Calculator

Метрик‑эндпоинты размечены аннотациями для Prometheus‑scrape.

---

## Развёртывание

```bash
export KUBE_NS=st-your-namespace

# MySQL
kubectl apply -f manifests/mysql/secret.yaml      -n $KUBE_NS
kubectl apply -f manifests/mysql/statefulset.yaml -n $KUBE_NS
kubectl apply -f manifests/mysql/service.yaml     -n $KUBE_NS

# OnCall
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/config.yaml     | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/deployment.yaml | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/service.yaml    | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/ingress.yaml    | kubectl apply -f - -n $KUBE_NS

# Prober & SLA Calculator
kubectl apply -f manifests/prober/ -n $KUBE_NS
kubectl apply -f manifests/sla/    -n $KUBE_NS
```

---

## Проверка

### Метрики локально

```bash
kubectl exec -n $KUBE_NS deploy/prober -- curl -s localhost:9100/metrics
kubectl exec -n $KUBE_NS deploy/sla-calculator -- curl -s localhost:9101/metrics
```

### Логи проб в Sage (PQL)

```
pql {group="ab2_islamov", system="prober"}
```

### Ручная метрика SLA в Sage

```bash
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

---

## Демо

Скрипт `demo.sh` выводит:

* текущие метрики проб и SLA;
* последние события проб из Sage;
* последнюю SLA manual metric.

---

## Docker

Сборка:

```bash
docker build -t therad445/ab2-prober:<tag> prober/
docker build -t therad445/ab2-sla-calculator:<tag> sla/
```

Публикация:

```bash
docker push therad445/ab2-prober:<tag>
docker push therad445/ab2-sla-calculator:<tag>
```

---

## Идеи для расширения

* Алертинг при деградации SLA
* Дашборды Grafana через Sage datasource
* Несколько проберов для распределённых проверок
* SLO по латентности на гистограммах

---

## Лицензия

[MIT](LICENSE)
