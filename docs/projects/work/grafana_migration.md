---
tags:
  - WIP
  - observability
  - work
date: "2025-07-07"
title: grafana_migration
---

# Background

Previously our Grafana setup hinged on and ec2 instance with a local sqlite db as persistent storage. In an effort to improve our reliability and availability of Grafana, we needed to change this.

# Process

We've broken the work out into a few migration phases:

- Migrate off sqlite db to postgres for a sharable storage backend
- Move Grafana to a scalable workload orchestration (ECS)
	- Lower TTL for associated records for more responsive switches when a Grafana task has to be cycled out (ECS Service Discovery defaults to 10s which we can match)
- Configure high availability (along with unified alerting)
	- To de-duplicate alert propagation (Grafana evaluates alert rules on each instance) we will need to properly configure peering for multiple instances dynamically.

## Migrating backend to Postgres

Grafana was backed with a local sqlite db which was restricting our ability to scale the application. For a more reliable experience for users, 

## Migrating Grafana to ECS

### Upgrading to Grafana v12

While Grafana does have support for rolling updates, since this was a major version with known breaking changes, and we havent enabled anything yet - I figured it would be smoother to upgrade at this point and then enable HA.

Some notable changes for us in the new version:

- Git Sync support (Experimental)
- Dashboard schema changes (Experimental)
- Drilldown

See the full breakdown of changes [here](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-0/).

## Enabling High Availability


# References

- 
