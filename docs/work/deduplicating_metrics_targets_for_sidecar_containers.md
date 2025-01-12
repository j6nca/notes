---
tags:
  - WIP
created: 2024-11-28
title: Deduplicating Metrics Targets For Sidecar Containers
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

The resulting block takes targets in and de-duplicates targets from the same pod, where the exposed annotation port number doesnt match the containers port.

```
// Drop sidecar pods from target list to prevent metric duplication.
// This works by checking the containers exposed ports with the port defined in the scrape annotation.

discovery.relabel "annotation_autodiscovery_pods_drop_sidecars" {
	targets = discovery.relabel.annotation_autodiscovery_pods.output
	
	rule {
		// List of labels whose values to select upon
		source_labels = ["__meta_kubernetes_pod_annotation_{{ include "escape_label" .Values.metrics.autoDiscover.annotations.metricsPortNumber }}"]
		
		// match label@value to regex
		regex = "(.+)"
		
		//write to temp label
		target_label = "__tmp_port_number"
	}
	
	rule {
		// only keep targets in which container port matches __tmp_port_number
		source_labels = ["__meta_kubernetes_pod_container_port_number"]
		action = "keepequal"
		target_label = "__tmp_port_number"
	}
	
	rule {
		action = "labeldrop"
		regex = "__tmp_port_number"
	}
}
```

In hindsight we actually see something similar applied in the k8s-monitoring chart, but only towards portName (not sure why portNumber is excluded here). Which indicates we were on the right track!

# References

- https://grafana.com/docs/alloy/latest/reference/components/discovery/discovery.relabel/
