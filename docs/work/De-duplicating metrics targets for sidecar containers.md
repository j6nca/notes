---
tags:
  - WIP
created: 2024-11-28
title: Deduplicating metrics targets for sidecar containers
---

# Background

After rolling out Grafana Alloy to collect metrics across our kubernetes infrastructure, we observed duplication of metrics coming from containers running additional sidecars (i.e for vault secret injection). This was deduced when we checked alloy UI and it displayed each container from the same pod as a scrape target. This resulting in metric duplication seen when querying the metrics via Grafana.

```
// Targets registered under `discovery.relabel.annotation_autodiscovery_pods`
targets: [
...
{
  __address__ = "my-node-ip",
  __meta_kubernetes_namespace = "my-namespace",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_logs_enabled = "true",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_path = "/metrics",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_portNumber = "3500", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scheme = "http", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scrapeInterval = "30s",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_scrape = "true",
  __meta_kubernetes_pod_container_name = "my-service"
},
{
  __address__ = "my-node-ip",
  __meta_kubernetes_namespace = "my-namespace",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_logs_enabled = "true",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_path = "/metrics",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_portNumber = "3500", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scheme = "http", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scrapeInterval = "30s",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_scrape = "true",
  __meta_kubernetes_pod_container_name = "vault-agent"
},
{
  __address__ = "my-node-ip",
  __meta_kubernetes_namespace = "my-namespace",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_logs_enabled = "true",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_path = "/metrics",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_portNumber = "3500", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scheme = "http", 
  __meta_kubernetes_pod_annotation_k8s_grafana_com_metrics_scrapeInterval = "30s",
  __meta_kubernetes_pod_annotation_k8s_grafana_com_scrape = "true",
  __meta_kubernetes_pod_container_name = "vault-agent-init"
}
...
]
```

# Dialing in some labels

Looking at the target list there are a few interesting labels that we might be able to filter out based on. We could potentially exclude the vault containers based on name (probably the simplest approach, adding any other potential sidecar containers we may see). Additionally if we want a broader exclude we could attempt to create an exclusion based on port definition (if the container isnt exposing a port for metrics collection then it probably doesnt need to be registered as a target).

Ideally we could look at combining this check to see if the port exposed is equal to the annotation port.

# Understanding the Discovery.relabel alloy component


# References

- https://grafana.com/docs/alloy/latest/reference/components/discovery/discovery.relabel/
