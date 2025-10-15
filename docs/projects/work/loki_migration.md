---
tags:
  - WIP
date: "2025-10-09"
title: loki_migration
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background

We are looking to migrate Loki along with our other observability components to ECS

# Components

![Loki components](https://grafana.com/docs/loki/latest/get-started/loki_architecture_components.svg)

# Deployment Strategies

Loki has a few options for deployment. Namely:

- monolithic
	- ![monolithic](https://grafana.com/docs/loki/latest/get-started/monolithic-mode.png)
- simple scalable (aka SSD)
	- ![simple scalable](https://grafana.com/docs/loki/latest/get-started/scalable-monolithic-mode.png)
- microservices
	- ![microservices](https://grafana.com/docs/loki/latest/get-started/microservices-mode.png)

# Current setup

Currently we have Loki deployed in a `simple-scalable` strategy, with read components running on-demand via nomad, and write deployed via ec2.

We see about a 0.5TB volume of logs daily which is within the recommend range for SSD deployment (good room to grow up to a few TB/day before the value of microservices shines).

For simplicity of the migration - it may also help us along with this migration to keep the same deployment strategy and based on the volume it seems there is no urgent need to change this for now.

# Migration

For the migration, the plan is the follows, starting with the simplest to cutover pieces:

1. Read components
2. Write components
3. Backend components

# References

- [Loki deployment modes](https://grafana.com/docs/loki/latest/get-started/deployment-modes/)
- [Loki components](https://grafana.com/docs/loki/latest/get-started/components/)
- [Auto-scaling Loki querier](https://grafana.com/docs/loki/latest/operations/autoscaling_queriers/)