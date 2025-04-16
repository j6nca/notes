---
tags:
  - WIP
  - grafana
date: "2025-03-27"
title: grafana_alerting
---

# Background

We are looking to rollout Grafana Alerting usage to enhance our existing alerting ecosystem.

This provides us with the ability to create alerts based off other datasources such as logging and traces, along with tying alert rules and dashboard queries when computing expensive queries.

# Setup

## Testing

You can preview and test alert expressions and configuration with the built-in alert editor. This also provides a nifty editor to preview alert evaluation behaviour.

### Alert Organization

Alert rules are defined under Grafana Folders and alert rule groups. In terraform the minimum resource definition is the alert rule group (`grafana_rule_group`) which contains a set of alert rules.

idea: Organize alerts by `Folder (Grafana team) > Alert rule group (service) > Alert rule 

```
- TeamA
	- TeamA/ServiceA
		- TeamA/ServiceA/AlertA
	- TeamA/ServiceB
		- TeamA/ServiceB/AlertA
- TeamB
	- TeamB/ServiceA
		- TeamB/ServiceA/AlertA
```

This also promotes leaning into Grafana Folders as a means of managing team resources (dashboards, alerts). There is also additional support for labelling these alerts which we may consume downstream for our Oncall insights solution.

Alert rule groups allow us to group relevant alert rules together under one notification. This is handy to reduce noise for on-call engineers.

## Recording rules

Recording rules allow you to pre-compute frequently used or expensive queries and reference them as a new time-series metric. This allows us to reuse queries across alert rules and dashboards.

## CICD

Grafana provides a terraform provider, which we will use here

# Future

The latest version of Grafana 11.6 announces alert rule version management. Not sure how this will play with terraform-managed rules, but since the CI process allows us to control and manage alert rule changes - I don't see much changing in regards to how we will manage these alerts.

# References

- https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-recording-rules/
- https://registry.terraform.io/providers/grafana/grafana/latest/docs/resources/rule_group
