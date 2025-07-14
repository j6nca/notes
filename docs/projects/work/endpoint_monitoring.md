---
tags:
  - WIP
date: "2025-05-05"
title: endpoint_monitoring
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background

We are running gatus to monitor our endpoint health.

# Organizing Alerts

Gatus exposes prometheus metrics (`/metrics`) that we can consume for alerting.

Since we are monitoring various endpoints owned by various teams, we need a way to properly route alerts to their respective audiences, as our team will not be the ones addressing these alerts.

Gatus comes out of the box with a feature for grouping endpoints together, and is also exposed as a label alongside its metrics. By organizing these endpoints grouped by their owner team, we are then able to simply reference the `group` label here and route accordingly via prometheus receivers.

An example of this setup is as follows:

```
groups:
	- name: gatus
		labels:
			# If metric supplied has a 'group' label use that value for routing, otherwise route to default team
			owner_team: '{{if .Labels.group}}{{ .Labels.group }}{{else}}team.default{{end}}'
		rules:
			- alert: EndpointDown
				expr: sum(increase(gatus_results_total{success="false"}[5m])) by (name, group) >= 3
				for: 1m
				labels:
					severity: 'sev-1'
				annotations:
					title: "{{ $labels.name }} endpoint is down"
```

# Multi-region monitoring

The high latencies from monitoring endpoints in other regions from a central gatus make some of the metrics and value that gatus provides less consistent/usable. To address this, we should look to deploy additional instances of gatus across various regions. Endpoint configs should then be split amongst these regional deployments such that there is no overlaps (to avoid confusion). This addresses the latency issues and allows us to continue extracting appropriate endpoint monitoring information from all endpoints.

## Automating Endpoint Discovery

Use consul discovery

status.stackadapt.dev
status.stackadapt.com

look into consul templating

# References

- 
