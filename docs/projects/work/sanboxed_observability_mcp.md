---
tags:
  - WIP
  - work
  - observability
  - mcp
date: "2026-05-02"
title: Sanboxed Observability MCP
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background

With the rising usage and adoption of AI tooling we wanted to enable users the ability to flexibly create queries/dashboards and troubleshoot leveraging data from our observability stack. 

Initially we had just opened an avenue to do this by creating a service account for Grafana MCP (read-only) and generating individual tokens for users to setup their local environments. This approach didn't really scale for us, as it bogged down our support requests and didn't provide any additional value.

# Considerations

There were two main considerations we had with rolling out Grafana MCP. The first and foremost, we currently manage dashboards via clickops largely for the convenience of various teams creating their own visualisations. Ideally we could run something like Grafana MCP with write permissions to let folks seamlessly edit and create new dashboards, but conversely, this means that MCP could also accidentally delete resources, which creates a problem for us. While we do backup the Grafana database regularly, it is not ideal to have to go and restore these backups whenever MCP decides to hallucinate and delete something. We are slowly moving to a more provisioned state for Grafana, which could let us quickly recover but even then, it would require the cooperation of teams to leverage managing these dashboards in code.

Additionally, our main Grafana instance is configured for various datasources. We wanted to limit mcp access to only a certain scope of datasources (Prometheus, AlertManager, Loki, Pyroscope and Tempo). The fine tuning here requires something such as RBAC, which the OSS offerring of Grafana does not support. That means, whatever API token is generated would theoretically have access to read any datasources.



# Implementation

With the above considerations in mind, this is how we ended up implementing Grafana MCP, with a few quirks here and there.

We ended up spinning a sandboxed environment, containing a Grafana server and MCP server. The Grafana server was only accessible via the MCP server which is then exposed to end users. For the sake of simplicity, we opted to create this Grafana server as provisioned, and entirely stateless using anonymous viewer mode (BEWARE, it is highly not recommended to expose your grafana instance to the internet with anonymous viewer mode, as savvy users may be able to query your datasources via API calls).

The standalone Grafana MCP server contains several tools for working with metrics, dashboards, logs, profiles etc. However, Tempo has it's own MCP tooling built-in to it's cluster which Grafana MCP does not have, so we must run Tempo MCP and proxy these tools over to Grafana MCP.

# References

- 
