# Background

# Requirements

## Components

- Metrics (VictoriaMetrics)
- Logs (Grafana Loki)
- Profiling (Grafana Pyroscope)
- Tracing (Grafana Tempo)
- OTEL Collector (Grafana Alloy)
- 

sli and slos

dash board with example hands on walk through

profiling tracing

1hr 15min

google the art of SLO's

grafana get started -> tracaes, etc docker-compose examples

pin versions so things are consistent. 

if we need to chop - alerting sli slos skim it down good signals


just to preface this, we are in a bit of time crunch as we want to cover a lot of things in this session so if we dont get to any questions feel free to drop them in our observability channel: `#eng-ops-observability`


[https://grafana.com/docs/pyroscope/latest/get-started/ride-share-tutorial/](https://grafana.com/docs/pyroscope/latest/get-started/ride-share-tutorial/)[https://grafana.com/docs/tempo/next/docker-example/](https://grafana.com/docs/tempo/next/docker-example/)  
[https://github.com/grafana/tempo/tree/main/example/docker-compose](https://github.com/grafana/tempo/tree/main/example/docker-compose)

This might be useful https://github.com/grafana/intro-to-mltp

#  Breakdown

- Intro, services [5min]
- Setup / run local stack [5min]
	- Ensure folks have pulled images/local dependencies beforehand (`docker compose pull`) to make this seamless
- Concepts & workshopping (highlighting any key points below) [55min]
	- Metrics walkthrough
		- Querying basics and considerations
	- Metrics session
		- Build a dashboard
	- Logging walkthrough
	- Logging session
	- Profiling walkthrough
	- Profiling session
	- Traces walkthrough
	- Traces session
	- Alerting walkthrough
		- SLI, SLOs, golden signals, noise reduction
	- Alerting session
		- Common alert query example and applying noise reduction there
- Wrap up and closing remarks [5min]

# References

- https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos
- https://grafana.com/blog/2022/04/01/get-started-with-metrics-logs-and-traces-in-our-new-grafana-labs-asia-pacific-webinar-series/
- https://www.youtube.com/watch?v=fMkoJpSByV8