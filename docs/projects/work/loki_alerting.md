---
tags:
  - WIP
  - work
  - observability
  - alerting
date: "2025-08-25"
title: Loki Alerting
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background

Figuring out how to manage alerts for loki - similarly to how we are managing promalerts as-code. Previously we could've used Grafana Alerting, but it is less intuitive and relies on specifying a not-so reader-friendly code block with a lot of overhead via terraform, and also further diversifying our alerting pool which we should keep simple.

Loki has a `ruler` component that can evaluate Prometheus-compatible alert or record rules.

# Requirements

There is a support for this feature going as far back as `v2.0.x`.

# Work Breakdown

- Deploy `ruler` component, responsible for evaluating alert rules
- Setup `ruler` component to pull alerts config from code i.e (`alerts` repo)
	- A good initial test rule we can add for measuring query duration (from the docs)
	  ```
	  sum by (org_id) (rate({job="loki-prod/query-frontend"} |= "metrics.go" | logfmt | duration > 10s [1m])
	  ```
	  - There is also terraform supported for these rules too, which is a leaner than the Grafana Alerting equivalent, however we wont need it if we can just sync the config files
- Setup CI for alerts changes to trigger sync/re-deploy
	- We can use `lokitool/cortextool` here to lint and even diff/sync these rules if needed

# References

- [Loki Documentation](https://grafana.com/docs/loki/latest/alert/)
