---
tags:
  - WIP
date: "2025-02-20"
title: Enabling Local Terraform Plans
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background


That should be it right? Just supply roles with the plan capabilities to read from the state bucket! 

Wrong.

Here's the catch. Terraform plan, while seemingly a no-op that should be impact-less when run, actually does write and lock state. This is because behind the scenes, terraform does a state refresh, to consolidate state with potential resource changes.

# References

- 
