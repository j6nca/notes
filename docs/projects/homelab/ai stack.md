---
tags:
  - WIP
date: "2026-06-18"
title: ai_workspace
---

> [!faq]- Disclaimer: 
> This setup is prone to frequent iteration given the speed at which this industry and tooling are constantly changing as of recent.

# Background

# Components

The broad picture of this workspace is composed of the following:

- LLM
- MCP Servers
- Agents/Harnesses



## LLMs

## MCP Servers

## Agents/Harnesses

## Workflows

```mermaid
flowchart LR
	Work 
	--> Overwatch 
	--> Agents
	-->|"Human Approval"| Review
	Review -->|"Feedback"| Agents
	Review --> Work
```


aaaaa

```mermaid
flowchart TD
    need["Something I want pi to do differently"] --> wiring{"Just wiring existing<br/>things together?"}
    wiring -->|"yes"| settings["Settings<br/>settings.json"]
    wiring -->|"no"| sayNo{"Needs to intercept,<br/>block, or render?"}
    sayNo -->|"yes"| ext["Extension<br/>extensions/*.ts"]
    sayNo -->|"no"| judgement{"Needs judgement<br/>+ reference docs?"}
    judgement -->|"yes"| skill["Skill<br/>SKILL.md dir"]
    judgement -->|"no"| retyped{"Retyped the same<br/>paragraph 3×?"}
    retyped -->|"yes"| tmpl["Prompt template<br/>prompts/*.md"]
    retyped -->|"no"| wait["Not yet: note it<br/>for the Stage 2 backlog"]
```

# References

- 
