---
tags:
  - WIP
created: 2024-10-31
title: Enabling metrics for VPC CNI
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

## Background

Looking into why the `cni-metrics-helper` chart was having issues pulling metrics from the cni pods:  

```
metrics/metrics.go:399","msg":"grabMetricsFromTarget: Failed to grab CNI endpoint: the server is currently unable to handle the request (get pods aws-node-2jfgx:61678)"}
```

Looks like the metrics helper is hardcoded to extract metrics from port `61678` whereas the cni pods expose their metrics at `61680` 🫠
```
aws-eks-nodeagent {"level":"info","ts":"2024-10-28T21:00:25.036Z","caller":"metrics/metrics.go:23","msg":"Serving metrics on ","port":61680}
```

## References

- https://aws.github.io/aws-eks-best-practices/networking/ip-optimization-strategies/
- https://github.com/aws/amazon-vpc-cni-k8s/tree/master/charts/cni-metrics-helper
