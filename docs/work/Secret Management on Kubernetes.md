---
tags:
  - WIP
  - homelab
  - kubernetes
  - gitops
date: 2024-11-09
title: Secret Management on Kubernetes
---

# Background

This post focuses on setting up and managing secrets in a Kubernetes environment. Since I use 1Password, it outlines an approach using SOPS, 1Password Connect and external-secrets-operator, however much of this setup can be extended to other secret providers (Vault, Bitwarden, etc).

This article goes over my process for bootstrapping a kubernetes cluster for secrets management using SOPS.

# Configuring FluxCD with sops-age

First I generate a sops key to use for encryption.

```
age-keygen -o age.agekey

cat age.agekey |
kubectl create secret generic sops-age \
--namespace=flux-system \
--from-file=age.agekey=/dev/stdin
```

You can create the secret and then copy the manifest to your repo (make sure you encrypt it with sops before you push!)

```
kubectl create secret generic op-credentials-test -n secret-ops --from-literal=1password-credentials.json="$(cat /path/to/1password-credentials.json | base64)"
```

Now that we've deployed Connect, we will deploy external-secrets to setup and handle secret retrieval. For simplicity's sake, we will use a single ClusterSecretStore to handle retrieving secrets across the cluster.




# References

- 
