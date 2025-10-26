# Alertmanager Playbooks

This guide helps you run incident response without dashboards. It covers alert routing, silencing, escalation, and a few ready‑to‑use Prometheus alert rules for SomaBrain.

## Routing and Receivers

A minimal `alertmanager.yml` snippet to route alerts by severity and service:

```
route:
  group_by: ['alertname', 'service', 'tenant']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 2h
  receiver: oncall-default
  routes:
    - matchers: [severity="critical"]
      receiver: oncall-critical
      continue: true
    - matchers: [service="somabrain"]
      receiver: oncall-somabrain

receivers:
  - name: oncall-default
    webhook_configs:
      - url: http://alert-webhook.local/ingest
  - name: oncall-critical
    pagerduty_configs:
      - routing_key: ${PAGERDUTY_ROUTING_KEY}
  - name: oncall-somabrain
    email_configs:
      - to: ops@soma.local
```

## Silences

Use silences to mute noisy or scheduled maintenance windows without editing rules:

- Mute by tenant during a load test: matchers `service="somabrain"`, `tenant="loadtest"`.
- Mute a single alert: `alertname="SomabrainErrorRateHigh"`.
- Time‑bound silences are safer than removing rules.

## Inhibition

Prevent lower‑severity alerts from firing when a higher‑severity root alert is active:

```
inhibit_rules:
  - source_matchers: [severity="critical"]
    target_matchers: [severity="warning"]
    equal: ["alertname", "service", "tenant"]
```

## Notification Templates

Include context such as tenant, endpoint, and sample labels:

```
templates:
  - '/etc/alertmanager/templates/*.tmpl'
```

Example template fields commonly used:
- `{{ .CommonLabels.tenant }}`
- `{{ .CommonLabels.service }}`
- `{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}`

## Prometheus Alert Rules (Examples)

Store alerts in your Prometheus rule files (referenced by Prometheus config).

- API high error rate (per‑tenant):
```
- alert: SomabrainErrorRateHigh
  expr: sum by (tenant) (rate(somabrain_http_requests_total{status=~"5.."}[5m]))
        /
        sum by (tenant) (rate(somabrain_http_requests_total[5m])) > 0.05
  for: 10m
  labels:
    severity: warning
    service: somabrain
  annotations:
    summary: "High 5xx error rate for tenant {{ $labels.tenant }}"
    runbook_url: "https://github.com/somatechlat/somabrain/blob/main/docs/monitoring/alertmanager-playbooks.md#api-high-error-rate"
```

- Memory journal backlog growing:
```
- alert: SomabrainJournalBacklogGrowing
  expr: rate(somabrain_ltm_store_queued_total[5m]) > 0.5
  for: 15m
  labels:
    severity: warning
    service: somabrain
  annotations:
    summary: "Journal backlog is growing"
    action: "Check memory backend availability and queue consumers"
```

- Learning rate anomalous:
```
- alert: SomabrainLearningRateAnomalous
  expr: avg_over_time(somabrain_effective_learning_rate[30m]) < 0.01 or avg_over_time(somabrain_effective_learning_rate[30m]) > 0.9
  for: 30m
  labels:
    severity: info
    service: somabrain
  annotations:
    summary: "Effective learning rate outside expected band"
    action: "Verify neuromodulators and recent feedback volume"
```

## Ops Checklist

- Triage annotations and labels first (tenant, endpoint, service)
- Confirm upstream dependencies (Redis, Kafka, Postgres, memory backend)
- Check service health endpoints `/health` or `/healthz`
- Use PromQL to validate: error rates, queue growth, latency percentiles
- Silence only what you have positively triaged

## See Also

- Prometheus configuration: `docs/technical-manual/monitoring.md`
- PromQL cheat sheet (same doc)
- OTel/Tracing integration: `docs/technical-manual/observability.md`
