---
tags:
  - kubernetes
  - kustomize
  - WIP
---

# Metadata labeling

Recently I was tasked with implementing a metadata labeling standard across all of our kubernetes resources running in production. Currently we exclusively only deploy helm charts spread across ArgoCD and Waypoint. Thinking about ways to implement this I came up with a few, re-usable ideas which would need to be introduced to every Helm chart we are installing.

## Policy management

First I'll dive into how we will enforce labeling going forward. Since we are setting a new standard with these metadata labels, it was important to introduce a new resource policy, to prevent and error out any new services deployed that don't adhere to the policy. I'll deploy this in `audit` mode initially, and then eventually flip the switch to `enforce` once we are confident everything we expect to abide to the policy is following it.

```

```

## Why not just manage common labels in helm?

The problem on relying on helm to define these standardized labels, is that it would be impossible to achieve consistency amongst all the third party helm charts we use. Different chart maintainers may have different ways of organizing and defining their helm charts.



## Here's where Kustomize comes in

### Overcoming the hurdle with dynamic variables



## References

- 
