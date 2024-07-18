---
tags:
  - kubernetes
  - kustomize
  - WIP
---

# Metadata labeling

Recently I was tasked with implementing a metadata labeling standard across all of our kubernetes resources running in production. Now generally we exclusively only deploy helm charts spread across ArgoCD and Waypoint. Thinking about ways to implement this I came up with a few, re-usable ideas which would need to be introduced to every Helm chart we are installing.

## Policy management

Since we are setting a new standard with these metadata labels, it was important to introduce a new resource policy to enforce, to prevent and error out any new services deployed that don't adhere to the policy.

```

```


## Here's where Kustomize comes in

### Overcoming the hurdle with dynamic variables



## References

- 
