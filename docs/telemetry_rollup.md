# Rollup Telemetry Notes

## Prometheus Targets
- `network_overlay:8087/metrics`
- `voice_gateway:8088/metrics`
- Pack services expose `/metrics` on their assigned ports (8091-8096).

## Grafana Provisioning
Add the JSON dashboards from `telemetry/dashboards/` to the Grafana provisioning configuration to visualize overlay, voice, and blue team health.
