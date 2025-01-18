---
tags:
  - WIP
  - learning
  - observability
  - grafana
  - irm
date: 2024-09-24
title: Oncall
---

# Oncall

Oncall is Grafana's incident response management (IRM) solution. It acts as an alternative to other on-call solutions such as PagerDuty and Splunk.

![Oncall component overview](https://grafana.com/static/img/docs/oncall/oncall-alert-workflow.png)

## Terminology

A list of common terms when referencing Grafana Oncall.

- Alert group: Set of related alerts grouped by common attributes and routed via escalation chains. Grouping reduces alert noise, reducing toil for IREs
- Escalation chain: Set of steps defining how alerts are directed to on-call schedules and users
- Routes: Configuration to route alerts to responders or channels
- On-call schedule: Calendar schedule to determine who is on-call at a given time
- Rotation: An on-call shift
- Shift: Period of time when a user/team is actively on-call
- Notification policy: Rules determining how alert notifications are propagated to the user
- Alert rules: 
- Integrations: Integrations are entry points for alerts. Each integration has a unique URL and routed accordingly


## References

- https://grafana.com/docs/oncall/latest/intro/
