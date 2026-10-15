---
tags:
  - WIP
  - kubernetes
  - aws
date: 2024-07-22
title: Zero-downtime deployments behind AWS ALB Controller
---

This post dives into the initial setup for k8s releases as well as finally solving a long-present issue that has been present when rolling out changes.

## The setup

Our  setup involved the AWS ALB ingress controller which managed and provision respective loadbalancer resources based on events in k8s, and exposing our services to the world by creating said ingresses. The ingress controller would then update target routes as pods get cycled in and out. Sounds like a plan right?

```mermaid
flowchart LR
    client["Client"] --> alb["AWS ALB"]
    alb --> tg["Target group"]
    tg --> podA["Pod"] & podB["Pod"]
    ingress["Ingress"] -.->|"watched by"| ctrl["AWS Load Balancer Controller"]
    endpoints["Pod endpoints"] -.->|"watched by"| ctrl
    ctrl -->|"provisions"| alb
    ctrl -->|"registers / deregisters targets"| tg
```

## The problem

Even though we expected release rollouts to be zero-downtime, when performing releases we noticed that if we hit the services at the right time, there was a few second window where we would see `502 Bad Gateway`!

![Ruh-roh raggy!](https://res.cloudinary.com/drwjkxxud/image/upload/v1722577813/giphy_1_dow8oh.gif)

Pod shutdown and target deregistration happen independently, so the ALB can keep routing to a pod that has already stopped serving:

```mermaid
sequenceDiagram
    participant C as Client
    participant ALB as AWS ALB
    participant LBC as ALB Controller
    participant K as Kubernetes
    participant Old as Old pod
    participant New as New pod

    K->>New: Start new pod
    New-->>K: Ready
    LBC->>ALB: Register new pod target
    K->>Old: SIGTERM
    Old->>Old: Stops accepting connections
    K->>LBC: Old pod endpoint removed
    rect rgba(255, 80, 80, 0.15)
        Note over C,Old: Old target still registered in the ALB
        C->>ALB: Request
        ALB->>Old: Forward to old target
        Old--xALB: Connection refused
        ALB-->>C: 502 Bad Gateway
    end
    LBC->>ALB: Deregister old pod target
```

## The solution



## References

- 
