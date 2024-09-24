---
tags:
  - WIP
  - learning
  - observability
  - grafana
  - irm
created: 2024-09-24
title: Oncall
---

# Oncall

Oncall is Grafana's incident response management (IRM) solution. It acts as an alternative to Prometheus' [AlertManager](../prometheus/alertmanager).

## Terminology

- Alert group: Set of related alerts grouped by a common attribute
- Escalation chain: Set of steps defining how alerts are directed to on-call schedules and users
- Routes: Configuration to route alerts to responders or channels
- On-call schedule: Calendar schedule to determine who is on-call at a given time
- Rotation: An on-call shift
- Shift: Period of time when a user/team is actively on-call
- Notification policy: Rules determining how alert notifications are propagated to the user
- Alert rules: 
- Integrations:


## Media

## References

- https://grafana.com/docs/oncall/latest/intro/
