---
tags:
  - WIP
  - grafana oncall
  - irm
date: 2025-01-22
title: Managing IRM As Code
---

> [!faq]- Disclaimer: 
> This isn't a guide, this post just outlines my approach at achieving a solution.

# Background

We use Grafana Oncall to manage our IRE rotations. In the case of DR and for convenience - we want to have the ability to manage and configure what we can in code - this allows us to formally review access changes before they are rolled out.

# Setting up your team

We are using terraform, setup with Grafana's providers to manage these resources. Currently in order to setup a new team with alerting/escalation chain we add the following files:

```
access/grafana/oncall
- team_teamA.tf
- integrations_teamA.tf
- escalation_teamA.tf
```

First create an empty schedule in Grafana oncall. We are leaving the management of schedules to be manual to allow for more flexibility in editting, however the option stands if you want to move that schedule into code ([overrides are still supported](https://registry.terraform.io/providers/grafana/grafana/latest/docs/resources/oncall_schedule#enable_web_overrides-1)). The schedule needs to be created first as we need to reference it for some of the resources we are about to create.

Next, populate the above files accordingly:

```hcl
# team_teamA.tf

# create team in grafana
resource "grafana_team" "teamA" {
provider = grafana.main
name = "teamA"
	members = [
		"firstname.lastname@company.com",
		...
	]
}

# oncall needs a separate data type to reference the team
data "grafana_oncall_team" "teamA" {
	name = "teamA"
	depends_on = [grafana_team.teamA]
}
```

```hcl
# integrations_teamA.tf

module "teamA" {
	source = "./modules/integration"
	name = "teamA"
	escalation_chain_id = grafana_oncall_escalation_chain.teamA.id
	oncall_team_id = data.grafana_oncall_team.teamA.id

	# add routes based on severity. ensure that oncall user has been invited to these channels otherwise messages won't go through.
	routes = [
		{
			routing_regex = "{{ \"alerts-sev-1\" in payload.commonLabels.slack_channel }}"
			slack_channel_name = "alerts-sev-1"
		},
		...
	]
}

```

```hcl
# escalation_teamA.tf

resource "grafana_oncall_escalation_chain" "teamA" {
	name = "teamA"
	team_id = data.grafana_oncall_team.teamA.id
}

# Schedule is not in github
data "grafana_oncall_schedule" "schedule_teamA" {
	name = "teamA"
}

// Notify users from on-call schedule
resource "grafana_oncall_escalation" "teamA_step_0" {
	escalation_chain_id = grafana_oncall_escalation_chain.teamA.id
	type = "notify_on_call_from_schedule"
	notify_on_call_from_schedule = data.grafana_oncall_schedule.schedule_teamA.id
	position = 0
}
```

# References

- 
