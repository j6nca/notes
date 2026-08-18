---
tags:
  - WIP
  - projects
  - homelab
  - kubernetes
date: "2026-07-03"
title: k8s_cluster
---

# Requirements

- Secret Management
- Observability
- Disaster Recovery
	- Volume Snapshotting

- Media Server
- AI Workspace
- Personal Projects
- Other Self-hosted Projects

# Background

# Networking

Cluster-internal networking. The physical/home side of the network lives in [[networking|home networking]].

## CNI

## Ingress

## Load Balancing

Bare metal has no cloud load balancer to fall back on, so this has to be solved in-cluster.

## DNS

## Certificates

# Storage

Persistent volumes for the self-hosted workloads, including the volume snapshotting called out under Requirements.

## CSI Driver

## Storage Classes

## Volume Snapshots

## Backup & Restore

# Secrets Management

Written up in depth already in [[projects/work/Secret Management on Kubernetes|Secret Management on Kubernetes]] — SOPS + age, 1Password Connect and external-secrets-operator, bootstrapped through Flux. This section should stay a summary and link out rather than restate it.

## Approach

## Bootstrapping

## Rotation

# GitOps

## Tooling

Flux is already carrying the secrets bootstrap, so the useful thing to record here is *why* Flux over Argo CD. Related notes: [[notes/kubernetes/fluxcd|FluxCD]], [[notes/kubernetes/argocd|Argo CD]].

## Repository Layout

## Reconciliation & Drift

## Bootstrapping

# Generalizing chart deployments with `generic`

Premise: most of the self-hosted workloads here are the same shape — a Deployment, a Service, an Ingress, a PVC and some config — so one parameterized chart can serve all of them instead of maintaining a bespoke chart per app.

## Motivation

## Chart Interface

The values schema is the real API. Templating patterns worth reusing are in [[notes/kubernetes/helm_scratch_sheet|Helm scratch sheet]].

## Templates

## Per-app Overrides

## When to Break Out

Where a workload earns its own chart instead of bending `generic` to fit.

# Media

# References

- [Bare metal Kubernetes: Talos on Hetzner](https://datavirke.dk/posts/bare-metal-kubernetes-part-1-talos-on-hetzner/)
