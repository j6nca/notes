---
tags:
  - WIP
created: 2024-08-08
title: Observability Stack on K8s
---


Our observability stack currently runs on a series of EC2 nodes. In an effort to improve scalability and management of the various components for Grafana we are moving to deploy this via Kubernetes

## Stateful vs Stateless

One prominent question that I wanted to visit was the idea of managing Grafana resources statefully vs stateless. While I do prefer the stateless strategy here (managing alerts, dashboards other resources in code versus using storage, and because everything is in code we only need to worry about storage for our metrics/logging data), I believe the goal for this stack down the road is to enable teams to set their own alerting and dashboards. With that, it would make more sense for teams to interact with the UI to make these changes.

## Planning work

- Set up a testing environment for deploying and testing changes quick
- Deploy our stack on k8s (no data involved)
  - Grafana OnCall
	  - ![oncall architecture](https://raw.githubusercontent.com/grafana/oncall/dev/docs/img/architecture_diagram.png)
  - Grafana Alerting
  - Grafana Server
  - VictoriaMetrics Operator
  - Loki
  - Mimir
- Migrate less-involved services to k8s first
  - Deploy and configure chart for k8s
  - Test data storage, backups and restore from backups
  - Migration from Prometheus alerts to Grafana alerts
  
  - Additional services to integrate in the future
    - Synthetic testing w/ K6
    - 

## References

- 
