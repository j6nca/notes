---
tags:
  - WIP
  - homelab
  - kubernetes
  - gitops
created: 2024-11-09
title: Secret Management on Kubernetes
---

This post focuses on setting up and managing secrets in a Kubernetes environment. Since I use 1Password, it outlines an approach using SOPS, 1Password Connect and external-secrets-operator, however much of this setup can be extended to other secret providers (Vault, Bitwarden, etc).

With the interest in keeping in line with GitOps, I want to also store some cluster configurations and boostrap secrets on Git. Using Mozilla's SOPS lets us achieve this. 

# Generating

You can create the secret and then copy the manifest to your repo (make sure you encrypt it with sops before you push!)

```
kubectl create secret generic op-credentials-test -n secret-ops --from-literal=1password-credentials.json="$(cat /path/to/1password-credentials.json | base64)"
```


# References

- 
