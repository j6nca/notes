---
tags:
  - WIP
  - kubernetes
created: 2024-07-30
---

# Extensible ArgoCD Architecture

## Goals

- Modular support to enable different forms of scaling down the road
	- managing apps on new clusters
	- argo managing other instances of argo on other clusters
- Keep things DRY (don't repeat yourself)
- Per-cluster customizations isolated from shared configurations

## References

- 
