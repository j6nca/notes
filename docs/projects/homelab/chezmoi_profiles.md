c---
tags:
  - projects
  - homelab
  - dotfiles
date: "2026-08-31"
title: chezmoi_profiles
---

How to run one dotfiles repo across a work laptop and personal machines, with shared config in one place and the divergent bits gated. chezmoi has no "profile" concept as such — what it has is **one source tree plus a per-machine config file that feeds template variables**, which covers the same ground with less machinery.

Source repo: `~/projects/dotfiles`, source dir `chezmoi/` (set by `.chezmoiroot`).

# Current state

```
dotfiles/
├── .chezmoiroot                     # contains "chezmoi" → source dir is chezmoi/
└── chezmoi/
    ├── .chezmoi.toml.tmpl           # rendered once per machine at `chezmoi init`
    ├── dot_zshrc
    ├── empty_dot_gitconfig
    ├── dot_pi/agent/{models.json.tmpl,settings.json}
    ├── dot_talos/private_config.tmpl
    └── private_dot_config/
        ├── cmux/private_cmux.json
        ├── fastfetch/{config.jsonc,logo.txt}
        ├── mise/config.toml
        ├── opencode/opencode.jsonc
        ├── starship.toml
        └── zed/private_settings.json
```

Templating is already in use, but only for secrets — `onepasswordRead` in `dot_talos/private_config.tmpl` and `dot_pi/agent/models.json.tmpl`. Nothing yet branches on *which machine this is*.

# The model

Four mechanisms, roughly in order of how much work they do:

1. **`.chezmoi.toml.tmpl`** — asks the question once, per machine, and records the answer.
2. **Template conditionals** — branch on the answer inside any `*.tmpl` file.
3. **`.chezmoiignore`** — drop whole files or directories on machines that shouldn't have them.
4. **`.chezmoidata` / `.chezmoitemplates`** — shared values and shared fragments, defined once.

## 1. The profile selector

`.chezmoi.toml.tmpl` is rendered exactly once per machine, at `chezmoi init`, and the result is written to `~/.config/chezmoi/chezmoi.toml`. That file — not the repo — is what makes a machine "work" or "personal".

```gotmpl
{{- $machine := promptChoiceOnce . "machine" "machine" (list "work" "personal") -}}
sourceDir = "~/projects/dotfiles/chezmoi"

[data]
    machine = {{ $machine | quote }}
```

`promptChoiceOnce` prompts only if `machine` isn't already set in the existing config, so re-running `chezmoi init` on a configured machine is silent. Every template below then reads `.machine`.

> [!note] The current `.chezmoi.toml.tmpl` sets `sourceDir` only — there is no `[data]` block, so `.machine` is undefined on a fresh machine. The live config on this laptop has `machine = "work"` in it, hand-added. Closing that gap is the first step.

## 2. Branching inside a file

Any file whose source name ends in `.tmpl` is run through Go's `text/template`:

```gotmpl
# dot_zshrc.tmpl
{{ if eq .machine "work" -}}
export AWS_PROFILE=stackadapt
alias k=kubectl
{{ else -}}
alias k='kubectl --context homelab'
{{ end -}}
```

Renaming `dot_zshrc` → `dot_zshrc.tmpl` is what opts a file in; there's no marker inside the file.

## 3. Excluding whole files

`.chezmoiignore` lists **target** paths (`.talos`, not `dot_talos`) and is itself a template, evaluated against the same data. This is the cleaner tool when a whole subtree is irrelevant to a profile:

```gotmpl
{{ if ne .machine "personal" }}
.talos
.config/cmux
{{ end }}

{{ if ne .machine "work" }}
.config/work-vpn
{{ end }}
```

Prefer this over an empty template output — an ignored file is never created, whereas a template that renders to nothing still leaves an empty file on disk.

## 4. Shared data and shared fragments

- `.chezmoidata.yaml` (or a `.chezmoidata/` directory of `.yaml`/`.toml`/`.json` files) holds static values available to every template on every machine. Good for things like a model catalogue or a host list that both profiles reference.
- `.chezmoitemplates/` holds named partials. A file in there is not installed anywhere; it's pulled in with `{{ template "name" . }}`. This is how you keep a shared block in exactly one place while two profile-specific files both use it.

# Machine facts you get for free

Not everything needs a prompt. chezmoi populates `.chezmoi.*` on every run:

| Variable | Example |
| --- | --- |
| `.chezmoi.hostname` | short hostname |
| `.chezmoi.fqdnHostname` | fully-qualified |
| `.chezmoi.os` | `darwin`, `linux` |
| `.chezmoi.arch` | `arm64`, `amd64` |
| `.chezmoi.username` | login user |

If work machines are reliably identifiable by hostname or username, deriving the profile beats prompting for it:

```gotmpl
{{- $machine := "personal" -}}
{{- if eq .chezmoi.username "jonathan.ng" }}{{ $machine = "work" }}{{ end -}}
```

Prompting is the better default though — it survives a hostname change and it's explicit.

# What's actually profile-specific in this repo

Four things worth gating:

- **`empty_dot_gitconfig`** hardcodes `me@j6n.ca` and signs every commit with `~/.ssh/id_ed25519.pub`. On a work machine both are wrong. Two options: template the `[user]` block on `.machine`, or — better — leave the global identity personal and add a git-native override, which keeps the split working even outside chezmoi:

  ```
  [includeIf "gitdir:~/work/"]
    path = ~/.gitconfig-work
  ```

- **`dot_talos/private_config.tmpl`** reads from `op://Personal/...`. The homelab Talos cluster has no business on a work laptop — `.chezmoiignore` it off `work`.
- **`dot_pi/agent/models.json.tmpl`** points at `litellm.j6n.internal`, reachable only on the home network. Either gate it or give `work` a different `baseUrl`.
- **`private_dot_config/cmux`, `mise`, `zed`** — likely shared, but worth confirming rather than assuming.

Secrets reinforce the split: `onepasswordRead` calls against a `Personal` vault will simply fail on a machine signed into a different 1Password account, so those files want ignoring rather than templating.

# Bootstrapping a new machine

```sh
chezmoi init --apply git@github.com:<user>/dotfiles.git
```

`--apply` runs `chezmoi apply` immediately after cloning. The prompt from `.chezmoi.toml.tmpl` fires first, so the profile is chosen before anything is written. To skip the prompt in an unattended run:

```sh
chezmoi init --apply --promptChoice machine=work git@github.com:<user>/dotfiles.git
```

> [!warning] `--promptChoice` keys on the **prompt string** — the third argument to `promptChoiceOnce` — not the data path. The template above uses `"machine"` for both, so `--promptChoice machine=work` matches. Had the prompt been `"machine type"`, the flag would need `--promptChoice "machine type=work"`, and a mismatched key silently falls back to the first choice rather than erroring.

To change a machine's profile later, edit `~/.config/chezmoi/chezmoi.toml` directly — `promptChoiceOnce` returns the existing value without prompting whenever the key is already present in the config data.

# Gotchas

- **Stale `sourceDir`.** The live `~/.config/chezmoi/chezmoi.toml` on this laptop points at `~/projects/dotfiles/home`, which is an empty leftover directory from a rename. `chezmoi source-path` resolves there, so chezmoi is currently operating against nothing. The config file wins over `.chezmoiroot`; fix the config.
- **`.chezmoiignore` paths are target paths**, relative to `$HOME`, and use the destination name — `.config/cmux`, not `private_dot_config/cmux`.
- **`.tmpl` is opt-in per file.** A conditional in a file not named `*.tmpl` is written to disk verbatim.
- **`chezmoi diff` before `chezmoi apply`**, always, after touching a template — a broken conditional silently produces a wrong file rather than an error.
- **`chezmoi execute-template`** renders a string against the current machine's data without touching disk; useful for checking a conditional in isolation:

  ```sh
  chezmoi execute-template '{{ .machine }} / {{ .chezmoi.hostname }}'
  ```

# References

- [chezmoi user guide — machine-to-machine differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/)
- [chezmoi reference — target types and attributes](https://www.chezmoi.io/reference/target-types/)
- [[mentat_provisioning|mentat provisioning]] — the counter-example: a single appliance where chezmoi was dropped in favour of `git` + `make`
