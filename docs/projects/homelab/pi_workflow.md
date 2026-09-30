---
tags:
  - WIP
  - projects
  - homelab
  - ai
  - dotfiles
date: "2026-09-01"
title: pi_workflow
---

> [!faq]- Disclaimer:
> Same caveat as [[ai_workspace|AI workspace]] — harnesses are churning fast. This page is a running outline of *decisions and reasoning*, not a finished runbook. Expect it to be wrong in six months.

The Agents/Harnesses slot in [[ai_workspace|AI workspace]], filled in. `pi` is the harness; this page is why, and what a deliberately-built workflow on top of it looks like.

Upstream: [pi.dev](https://pi.dev) / `earendil-works/pi-mono`, TypeScript, MIT. Installed via mise (`github:badlogic/pi-mono`). Config lives in `dotfiles` at `chezmoi/dot_pi/agent/`.

# Why pi

Evaluated against [jcode](https://github.com/1jehuang/jcode) (Rust, server + thin clients, embedding-backed memory graph, swarm, self-modifying source). Chose pi.

The deciding axis was **ideology, not features**. pi is a substrate: an agent loop, seven built-in tools (`read` `write` `edit` `bash` `grep` `find` `ls`), a documented TypeScript extension API, and nothing else. jcode is a product — memory, swarm, side panels, browser, all in the binary — and its answer to customization is "tell the agent to rewrite its own Rust and hot-reload". That's a poor fit for machine config that should be boring and reproducible.

What pi **deliberately omits**: MCP, subagents, permission prompts, plan mode, todos, background bash, sandbox. This is the point, not a gap. Reference implementations for most of them ship in `examples/extensions/`, so each one is a conscious opt-in whose context and behaviour cost you can see.

> [!note] What would change the answer: running **many concurrent sessions in one repo**. jcode's server/thin-client model is ~261 MB at 10 sessions vs pi's ~833 MB, and its swarm conflict-notification (server tells agent B when agent A edits a file B has read) has no pi equivalent. Migration is cheap and one-way — jcode resumes pi/Claude Code/Codex sessions, not the reverse.

Two caveats on jcode's published benchmarks, both visible in its own README: at **one** session jcode's default config uses *more* RAM than pi (167 MB vs 144 MB) — the famous 27.8 MB baseline requires disabling the embeddings that power its headline memory feature. And it benchmarks pi 0.62.0 against a current 0.84.x.

# Current state

Everything, as of today:

```json
{
  "theme": "dark",
  "packages": ["npm:pi-provider-litellm"],
  "defaultProvider": "litellm",
  "defaultModel": "deepseek-v4-flash"
}
```

Plus `models.json.tmpl`, which points at `litellm.j6n.internal` with the key pulled via `onepasswordRead`, and serves `deepseek-v4-flash` / `MiniMax-M3`.

Session count: **1**. So there is no workflow yet — there's an install.

The notable gap: `~/projects/skills` is a real, harness-agnostic skills repo (`org-defaults`, `pr-commit-conventions`, `rubric-justification`, `rubric-justification-review`, plus a template) and pi cannot currently see any of it. Its README says to *copy* skill directories into each agent environment. pi doesn't need that — the `skills` settings array points at a directory and discovers `SKILL.md` recursively, in place.

# The model

Four customization surfaces, ordered by effort and by how much they can hurt:

| Surface | Lives in | Cost | Use when |
| --- | --- | --- | --- |
| **Settings** | `settings.json` | minutes | wiring existing things together |
| **Prompt templates** | `prompts/*.md` | ~zero | you've retyped the same paragraph 3× |
| **Skills** | any `SKILL.md` dir | low | the task needs decisions + reference material |
| **Extensions** | `extensions/*.ts` | real | you need to *intercept, block, or render* something |

The routing rule: retyped text → template. Needs judgement and docs → skill. Needs to say *no* → extension.

## Settings worth setting

- `skills: ["~/projects/skills/skills"]` — connects the existing repo. Single source of truth across pi and Claude Code.
- `enabledModels` — Ctrl+P cycling between the two litellm models.
- `steeringMode` / `followUpMode` — `"all"` vs `"one-at-a-time"` for queued messages. Taste; try both.
- `defaultProjectTrust` — matters *before* scripting pi, because `-p` / `--mode json` / `--mode rpc` never prompt and silently fall back to this.
- `defaultTools` — the nuclear option for context discipline; can start a session with a subset of built-ins.

`~/.pi/agent/AGENTS.md` is the highest-leverage file in the setup and does not exist yet. Global instructions, loaded every project. Keep it short.

## Extensions: the event bus is the API

The ~30 lifecycle events are the real surface. The ones that matter:

- `tool_call` — return `{ block: true, reason }`. This is the primitive behind every guardrail.
- `tool_result` — rewrite what the model sees.
- `before_provider_request` — inspect exactly what goes over the wire. Useful for debugging the litellm gateway.
- `session_before_compact` — own compaction instead of accepting the default.

Adoption order, cheapest and least risky first — all copied from `examples/extensions/` in the installed package, and each testable with `pi -e ./thing.ts` before committing to it:

1. `status-line.ts` / `custom-footer.ts` — read-only, zero risk, teaches the API.
2. `protected-paths.ts` + `confirm-destructive.ts` — first interceptor. Aim at the real hazards here: `chezmoi apply`, `talosctl`, `kubectl` against the cluster, `flux`.
3. `git-checkpoint.ts` / `dirty-repo-guard.ts` — cheap undo.
4. `todo.ts` / `plan-mode/` — only if actually missed.
5. `subagent/` — last. Changes cost and context behaviour the most.

# Where things live

The structural decision, and the one worth getting right first.

**Extensions do not belong in chezmoi.** They're TypeScript with a `package.json` and `node_modules`; a dotfile manager is the wrong tool. Instead, mirror what `~/projects/skills` already does:

- **`~/projects/pi-workspace`** — a git repo holding `extensions/`, `prompts/`, `themes/`, with a `pi` manifest in `package.json`. Installed with `pi install git:github.com/<user>/pi-workspace@v1`, which runs `npm install` and pins to a ref.
- **chezmoi manages only `settings.json`**, which names that package.

Payoff: versioned, pinned, testable in CI, shareable, and reproducible on a new machine from one settings line. Same shape as the rest of the dotfiles.

> [!note] Open question — whether this is a new repo or a `pi/` directory inside the existing `skills` repo. Arguments for merging: one place for all agent-facing assets, skills and prompts are neighbours anyway. Against: `skills` is deliberately harness-neutral and org-shared (CODEOWNERS, branch protection), and pi extensions are neither.

## Machine profiles

`litellm.j6n.internal` is only reachable on the home network, so the pi config is one of the things [[chezmoi_profiles|chezmoi profiles]] has to gate — either `.chezmoiignore` it off the work machine or give that profile a different `baseUrl`. The `onepasswordRead` against a `Personal` vault fails there regardless.

> [!warning] The selector in `.chezmoi.toml.tmpl` now offers **`stackadapt`** / `personal`, but [[chezmoi_profiles|chezmoi profiles]] documents `work` / `personal`. Any `{{ if eq .machine "work" }}` written from that page will silently never match. Reconcile before gating anything.

# Plan

- [ ] **Stage 0 — config** (~15 min). `skills` → the existing repo. `enabledModels`. `defaultProjectTrust`. First-draft `AGENTS.md`.
- [ ] **Stage 1 — prompt templates** (~30 min). `/review`, `/pr` (against `pr-commit-conventions`), `/rubric` (`$1` = level), `/wr`.
- [ ] **Stage 2 — use it for two weeks and write nothing.** Keep a list of every "it should have stopped me" and "I keep retyping this". That list is the real backlog, and it will be shorter and different than the one written today.
- [ ] **Stage 3 — `pi-workspace` repo**, seeded from whatever Stage 2 produced.
- [ ] **Stage 4 — per-project `.pi/`** for the repos that need different guardrails (`homelab-cluster`, `k8s-lab`, `dotfiles`).

# Open questions

- Does the memory-graph idea from jcode matter enough to rebuild a thin version as a pi extension, or is `/compact` + `/tree` + good `AGENTS.md` genuinely sufficient? *Suspect the latter, but that's untested.*
- Is there value pointing pi at `mentat` directly ([[mentat_provisioning|mentat provisioning]]) instead of through litellm, or is the gateway worth the hop for routing and key management?
- Local model viability: are `deepseek-v4-flash` / `MiniMax-M3` good enough to drive extension authoring, or does that work want a frontier model?
- MCP is absent by design. Does anything in [[ai_workspace|AI workspace]] actually need it, or is a custom pi tool the better answer each time?

# Gotchas

- **Models don't reliably auto-load skills.** Only names and descriptions live in the system prompt; the model has to choose to `read` the `SKILL.md`. Force with `/skill:name`, or write descriptions with hard trigger words — `org-defaults` naming its own trigger phrase is the right pattern.
- **A permission-gate extension is UX, not security.** pi has no sandbox and extensions run with full user permissions. Unattended or untrusted work needs a container — see `docs/containerization.md` and the `gondolin/` example.
- **Project trust gates config loading, not tool calls.** It stops a repo from silently changing settings before approval. It does nothing about prompt injection from repo content.
- **Paths in `~/.pi/agent/settings.json` resolve relative to `~/.pi/agent`.** Use `~`-prefixed or absolute paths.
- **`peerDependencies` with `"*"`** for `@earendil-works/*` and `typebox` when packaging. Don't bundle them.
- **Install with `--ignore-scripts`** — pi doesn't need lifecycle scripts for a normal npm install.

# References

- [pi docs](https://pi.dev) — and the copy shipped in the installed package, which is the version-accurate one
- `examples/extensions/` and `examples/sdk/` in the installed package — the actual starting point for anything non-trivial
- [Agent Skills specification](https://agentskills.io/specification) — pi implements it, leniently
- [[ai_workspace|AI workspace]] — the umbrella this page sits under
- [[chezmoi_profiles|chezmoi profiles]] — how the config gets gated per machine
- [[mentat_provisioning|mentat provisioning]] — where the local models actually run
