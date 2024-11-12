---
tags:
  - WIP
  - helm
  - kubernetes
  - automation
created: 2024-11-11
title: Automating Helm Dependency Versioning
---

# Background

As we deploy more and more services to kubernetes, there is additional effort required to maintain charts and services to ensure regular cadence of upgrades to get the latest changes for new features and security updates. Currently this process is largely manual with no automated direct channel for new versions.

# Automating

Here is where renovate/renovatebot comes in. Renovate is an OSS alternative to dependabot with support for helm charts (not yet available with dependabot) and allows us to configure a powerful yet flexible automation for continuously upgrading our helm chart dependencies.

## Considerations

With automatic upgrade PR in place, there is still a few things to consider:

- Our current rollout setup is loosely as follows:
	- dev/testing clusters -> main or testing branches
	- staging cluster -> stable
	- production cluster -> production

The cadence for syncing between main and stable and is stable and production is currently not regulated (there is a scheduled workflow that routinely runs this but the team can trigger this whenever needed as well). Based on the way we've set up the services to pull from the charts in the repository, as these branch syncs run, the new dependency versions are promoted to the next branch. This doesn't necessarily impact or change any of our current processes but it is important to keep in mind that these changes will be included as the main branch gets promoted gradually to production.



# References

- https://docs.renovatebot.com/modules/manager/helmv3/
- https://docs.renovatebot.com/modules/manager/helm-values/
- https://docs.renovatebot.com/getting-started/installing-onboarding/
- https://docs.renovatebot.com/key-concepts/presets/
- https://docs.renovatebot.com/key-concepts/dashboard/
