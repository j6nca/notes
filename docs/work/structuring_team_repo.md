---
tags:
  - WIP
date: 2025-01-13
title: Structuring Team Repo
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my thought process and resulting approach.

# Background

This post outlines decisions and goals made to create a modular and easy to extend team monorepo.

# Considerations

There were a lot of things to consider when designing this repo structure and honestly, nothing is final, if there are improvements or new tooling we want to adopt hopefully it is setup in a way to easily incorporate these changes.

We also have to be wary that certain decisions may lock us into certain workflows/patterns in the long run and want to make sure that decisions made line up with the goals of the team and are flexible, easy to understand and easy to work with

Goals:

- simple
- extends to multiple aws accounts and/or environments
- extends to multiple aws regions
- main representative of production / source of truth
- componentization
- releases/deployments are tracked in code as well as "live state"

Additional features:
- support for gatus scraping out-of-the-box
- expose and export metrics

## Componentization

It was important that each `component` encapsulated everything needed for that component to be running within its own state file. This made it so if we ever wanted to remove something, it was a matter of running `terraform destroy` to cleanup the component in its entirety.

## Additional Features

Most of these were a matter of bundling additional security groups and/or other resources to facilitate the ability for parts of the observability stack to collect metrics on services.

# Exploration

## WYSIWYG

After jotting out some of the big ideas we wanted for this repo, it was time to start building it out and testing what ideas are possible and what drawbacks we may expect to see come forward with different approaches. There were two primary trains of thought that were identified each with their own advantages and disadvantages.

1. An approach leveraging modularization of terraform code
	1. There was also an idea to version modules using git refs but a good point was raised where multiple terraform modules within one git repo along with code that consumes it doesn't really work and presents a chicken vs egg situation when trying to pull said versioned modules. 
2. Another approach was more focused on keeping environments in-line with each other, using `.tfvars` files to layer environmental changes. 
	1. The benefit of this is also its drawback - that is flexibility within the environment. If additional resources needed to be deployed to staging - this would add a layer of complexity to this approach.
	2. Additionally, there was no solid way to manage backend using this approach as variables are not permitted in the backend block and having to introduce a parameter to set the correct state everytime terraform is run against it can be cumbersome in addition to error-prone (I've done something similar in the past working with [[building_ephemeral_environments]] and it was a painpoint then, the only consolidation being those were with ephemeral environments where a mistake could just be wiped and recreated, I would definitely not want to introduce this pattern into a staging -> production scenario.

Both approaches had the benefit of keeping things DRY. Both also contradict our goal of keeping main a representation of live state in production. 

In the end, we settled on a simple, WYSIWYG approach for the structure. Landing on a commonly used structure following a `account/env > region > component` pattern for organizing terraform configuration.

```
terraform
- production
	- us-east-1
		- gatus
	- eu-central-1
- staging
```

However, WYSIWYG had the downside of not really scaling if our responsibilities gradually grew over time. We decided to go back to the drawing board. After some more bouncing of ideas - we landed on something promising. Deciding to incorporate modularization (to address the issue mentioned above) as well as a release branching strategy, allowing us to capture the state of an environment as a version and managing changes in production by promoting said versions. Versioning like this, allows us to have both states of staging and production in code which is a huge plus.

```
terraform
- modules
	- ecs-cluster
	- ecs-service
	...
- production
	- us-east-1
		- gatus
		...
	- eu-central-1
	...
- staging
```

## Release branching

```
|  x (release-n): -> production
| /
x (main): staging
|
|  x (release-1): -> previously production
| /
x
```

## Ignore: just some rough work

```
|  x release branch: 
| /
x hotfix   x release-v2.1.1
|        /
|      x release-v2.1.0
|     /
x ---
```

# References

- 
