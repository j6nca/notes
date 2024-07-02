# Prometheus

## PromQL

Data types:

- Scalar i.e `20`
- Instant Vector i.e `20@1719512652`
- Range Vector `[20@1719512652, 20@1719512653, 20@1719512654]`

The 4 golden metrics:

- Traffic (Rate)
- Error Rate
- Latency (Duration)
- Saturation

Records - build reusable queries with cached results.

Histogram metrics counts observations in buckets, an exposes multiple timeseries:

- `<base_metric_name>_buckets`: cumulative counter for observation buckets
- `<base_metric_name>_count`: total sum of all observed values
- `<base_metric_name>_sum`: count of events that have been observed

Notice this includes RED - best for reporting on symptoms and user satisfaction.


## References

- https://www.youtube.com/watch?v=FLT0d8fyhK4
- https://prometheus.io/docs/prometheus/latest/querying/basics/
- https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/
- https://prometheus.io/docs/concepts/metric_types/#histogram