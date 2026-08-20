---
tags:
  - WIP
  - projects
  - homelab
  - ai
date: "2026-08-19"
title: mentat_provisioning
---

The concrete runbook for `mentat`. The *why* behind these choices lives in [[strix_halo_ai_box|Strix Halo AI box]] — this page is the implementation: every file that goes in git, and the commands that consume them.

Ubuntu Server 26.04 LTS is installed. Everything below assumes a fresh, otherwise-untouched host, and that the box is an **appliance**: it runs the llama.cpp and ComfyUI toolboxes and nothing else.

# Principles

1. **One repo is the source of truth.** The chezmoi dotfiles repo holds `$HOME`, the `/etc` payloads, the systemd units and the mise task definitions. Nothing is configured by hand that could live there.
2. **Idempotent by construction, not by checking.** Prefer whole-file replacement and `apt-get install` (already no-ops when converged) over `sed -i` and appends. Every script here is safe to run a hundred times.
3. **Derive, don't duplicate.** Any value appearing twice is a future inconsistency. The GTT reservation is one number in `.chezmoidata.yaml`; both kernel knobs are computed from it.
4. **Expensive side effects are conditional.** `update-grub`, `sysctl --system` and container recreation only fire when the input actually changed, so a no-op apply is silent and fast.
5. **Nothing on the host that a toolbox could carry.** No Python, no PyTorch, no compilers. This is the rule that keeps an appliance an appliance — ComfyUI's entire ROCm/PyTorch stack lives in its container.

# Repo layout

```
dotfiles/                                 # the chezmoi source repo — this is the artifact
├── .chezmoidata.yaml                     # host facts (the single GTT number lives here)
├── .chezmoiignore                        # keeps mentat-only files off my other machines
├── .chezmoiexternal.toml                 # upstream helper scripts, unvendored
├── .chezmoiscripts/
│   ├── run_onchange_before_10-mentat-packages.sh.tmpl
│   ├── run_onchange_before_20-mentat-kernel-cmdline.sh.tmpl
│   ├── run_onchange_before_30-mentat-sysctl.sh.tmpl
│   └── run_after_50-mentat-services.sh.tmpl
├── dot_config/
│   ├── llama-swap/config.yaml.tmpl       # model catalogue + TTLs
│   ├── mise/
│   │   ├── config.toml.tmpl              # llama-swap + operational tasks
│   │   ├── mise.lock                     # committed — makes tool versions reproducible
│   │   └── tasks/                        # global file tasks, runnable from any cwd
│   │       ├── bootstrap
│   │       ├── verify
│   │       ├── bench
│   │       └── toolbox/{create,refresh}
│   └── systemd/user/{llama-swap,comfyui}.service
├── mise.toml                             # repo-local: lint. Runs where I *edit*, not on mentat.
└── benchmarks/
    ├── baseline.json                     # last-known-good tok/s, committed
    └── 2026-08-19-vulkan-radv.txt        # history, committed
```

Two deliberate splits:

**mise config goes under `~/.config/mise/`**, not a `mise.toml` in the repo root — a project-local `mise.toml` only applies when cwd is inside that project, and `mise run verify` has to work from anywhere on this machine. `~/.config/mise/tasks/` is mise's global task directory, so tasks are always in scope.

**`shellcheck` and the `lint` task live in the repo-local `mise.toml`, not on `mentat`.** Linting happens where the scripts are edited (my laptop), which keeps the appliance free of tooling it doesn't need. Principle 5 applied to my own automation.

> [!warning] `mise.lock` is written by mise but managed by chezmoi, so the two will fight unless you round-trip it: `mise upgrade` → `chezmoi add ~/.config/mise/mise.lock` → commit. Forgetting the middle step means the next `chezmoi apply` silently reverts your upgrade.

What deliberately stays **out** of git: BIOS settings (documented in [[strix_halo_ai_box|the plan]], Phase 0 — unautomatable), model weights (large, re-downloadable), and secrets. For the HF token, pull from 1Password via chezmoi's template functions rather than committing it — same posture as [[projects/work/Secret Management on Kubernetes|Secret Management on Kubernetes]], minus the cluster machinery.

# First run

The only commands typed by hand, ever:

```bash
sudo apt-get update && sudo apt-get install -y git curl
sh -c "$(curl -fsLS get.chezmoi.io)" -- -b ~/.local/bin   # upstream installer, not apt — templates need a current version
curl https://mise.run | sh

~/.local/bin/chezmoi init --apply git@github.com:<me>/dotfiles.git
```

That single `init --apply` runs the whole `/etc` layer. Then:

```bash
sudo reboot                    # required: the GTT reservation is a boot parameter
mise run bootstrap             # groups, model stores, llama-swap, toolboxes
mise run verify                # confirm the machine is what the repo says it is
```

Group membership (`render`, `video`) only takes effect on a new login, so the reboot covers it — running `verify` before rebooting will legitimately fail the GPU checks.

# Host facts

`.chezmoidata.yaml` — the only place a tunable number appears:

```yaml
mentat:
  # GTT reservation for the iGPU, in GiB. Both kernel knobs derive from this.
  # 120 on a 128 GB headless appliance: 8 GiB for OS, podman, journald and page
  # cache while streaming multi-GB safetensors off disk.
  gpu_reserve_gib: 120
  swappiness: 10
  llama_listen: "127.0.0.1:8080"
  comfy_listen_port: 8188
  models_dir: /srv/models          # GGUFs for llama.cpp
  comfy_models_dir: /srv/comfy-models
```

`.chezmoiignore` keeps this machine's files off the laptop:

```
{{ if ne .chezmoi.hostname "mentat" }}
.config/llama-swap
.config/systemd/user/llama-swap.service
.config/systemd/user/comfyui.service
{{ end }}
```

# The `/etc` layer

chezmoi owns `$HOME`, so system files are installed by `run_onchange_before_` scripts that `sudo` their payload into place. Two things make this work cleanly:

- The payload is **inline in the script** rather than in a separate `.chezmoitemplates` file. Changing a value changes the rendered script, which is exactly what makes chezmoi re-run it — no `sha256sum` indirection needed.
- Every script is wrapped in a hostname guard, so `chezmoi apply` on the laptop skips them entirely.

## Packages

`.chezmoiscripts/run_onchange_before_10-mentat-packages.sh.tmpl`

```bash
{{ if eq .chezmoi.hostname "mentat" -}}
#!/usr/bin/env bash
set -euo pipefail

# apt-get install is idempotent, so this whole script is a no-op once converged.
# The list lives inline: editing it changes this script, which is what triggers
# chezmoi to re-run it.
#
# Note what is absent: no python, no rocm SDK, no compilers. Both workloads
# bring their own stack inside their toolbox.
REQUIRED=(
  podman crun distrobox        # crun is load-bearing — see the toolbox section
  mesa-vulkan-drivers vulkan-tools
  git curl jq
)

# Host-side GPU monitoring is a convenience; the authoritative rocm-smi lives
# inside the toolboxes. Don't let a missing universe package fail the apply.
OPTIONAL=( rocm-smi radeontop )

sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${REQUIRED[@]}"

for pkg in "${OPTIONAL[@]}"; do
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$pkg" \
    || echo "note: optional package '$pkg' unavailable, skipping" >&2
done

# zram would compress model weights into RAM-backed swap: catastrophic here.
# Report rather than purge — silently removing a swap provider is not something
# a dotfile apply should do on my behalf.
if dpkg-query -W -f='${Status}' zram-tools 2>/dev/null | grep -q 'ok installed'; then
  echo "WARNING: zram-tools installed. Remove it: sudo apt-get purge zram-tools" >&2
fi
{{ end -}}
```

## Kernel command line

`.chezmoiscripts/run_onchange_before_20-mentat-kernel-cmdline.sh.tmpl`

The highest-stakes file on the machine; the drop-in mechanism is what keeps it safe:

```bash
{{ if eq .chezmoi.hostname "mentat" -}}
#!/usr/bin/env bash
set -euo pipefail

# Ubuntu's grub-mkconfig sources /etc/default/grub.d/*.cfg after
# /etc/default/grub (Ubuntu ships 50-cloudimg-settings.cfg the same way), so we
# *append* via a drop-in rather than rewriting the main file. Consequences:
# idempotent by whole-file replacement, no sed, and a release upgrade that
# rewrites /etc/default/grub can't silently drop our parameters.
#
# The two GTT knobs use different units, and published guides routinely quote
# pairs that disagree with each other. Both are computed from one value:
#   ttm.pages_limit -> 4 KiB pages -> gib * 262144
#   amdgpu.gttsize  -> MiB         -> gib * 1024

DROPIN=/etc/default/grub.d/99-mentat-amdgpu.cfg
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<'EOF'
# Managed by chezmoi — edits here will be overwritten.
GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT amd_iommu=off amdgpu.gttsize={{ mul .mentat.gpu_reserve_gib 1024 }} ttm.pages_limit={{ mul .mentat.gpu_reserve_gib 262144 }}"
EOF

# update-grub is slow and touches the boot path: only run it on a real change.
if sudo cmp -s "$TMP" "$DROPIN"; then
  echo "kernel cmdline already current ({{ .mentat.gpu_reserve_gib }} GiB GTT)"
else
  sudo install -D -m 0644 -o root -g root "$TMP" "$DROPIN"
  sudo update-grub
  sudo touch /var/run/reboot-required
  echo "kernel cmdline updated -> {{ .mentat.gpu_reserve_gib }} GiB GTT — REBOOT REQUIRED"
fi
{{ end -}}
```

`mul` is a sprig function, available in chezmoi templates by default. The single-quoted heredoc is deliberate: `$GRUB_CMDLINE_LINUX_DEFAULT` must land in the file **literally** so GRUB expands it at `update-grub` time, while `{{ mul … }}` is already resolved by chezmoi before the script runs.

## Sysctl

`.chezmoiscripts/run_onchange_before_30-mentat-sysctl.sh.tmpl`

```bash
{{ if eq .chezmoi.hostname "mentat" -}}
#!/usr/bin/env bash
set -euo pipefail

# With 128 GB and a hard GTT ceiling, healthy operation should never swap. This
# makes swap a pressure-relief valve rather than a routine destination; if it
# ever gets used, the GTT reservation is too aggressive.
CONF=/etc/sysctl.d/99-mentat.conf
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT

cat >"$TMP" <<'EOF'
# Managed by chezmoi — edits here will be overwritten.
vm.swappiness = {{ .mentat.swappiness }}
EOF

if sudo cmp -s "$TMP" "$CONF"; then
  echo "sysctl already current"
else
  sudo install -D -m 0644 -o root -g root "$TMP" "$CONF"
  sudo sysctl --system >/dev/null
  echo "sysctl applied"
fi
{{ end -}}
```

## Services

`.chezmoiscripts/run_after_50-mentat-services.sh.tmpl` — note the bare `run_` prefix, so it executes on **every** apply. `daemon-reload` is cheap and needs to happen whenever a unit file changes; making it conditional would be more code than it saves.

```bash
{{ if eq .chezmoi.hostname "mentat" -}}
#!/usr/bin/env bash
set -euo pipefail

# Headless box: without lingering, user units don't start until someone logs in.
# This presents as "the service didn't come back after reboot" and is easy to
# misdiagnose. Idempotent.
loginctl enable-linger "{{ .chezmoi.username }}"

systemctl --user daemon-reload
systemctl --user enable --now llama-swap.service comfyui.service
{{ end -}}
```

# Tools & tasks

mise's job shrank with the dev-box role, but didn't vanish: it pins `llama-swap` and it is the **operational interface** — every routine action here is a `mise run`.

`dot_config/mise/config.toml.tmpl`:

```toml
[tools]
# The only binary that belongs on the host. Everything else lives in a toolbox.
"ubi:mostlygeek/llama-swap" = "latest"

[env]
HF_HOME = "{{ .mentat.models_dir }}/hf"

[settings]
# "latest" above is a *policy*; mise.lock is the reproducible fact. Commit the
# lockfile so a rebuild resolves to identical versions, and let `mise upgrade`
# bump it deliberately as a reviewable diff.
lockfile = true

# --- short operational tasks inline; anything longer is a file task ---
[tasks.serve]
description = "Restart both inference services"
run = "systemctl --user restart llama-swap comfyui && systemctl --user --no-pager status llama-swap comfyui"

[tasks.logs]
description = "Follow logs from both services"
run = "journalctl --user -u llama-swap -u comfyui -f"

[tasks.status]
description = "What's resident in the memory pool right now"
run = """
rocm-smi --showmeminfo all
systemctl --user is-active llama-swap comfyui
curl -fsS http://{{ .mentat.llama_listen }}/running 2>/dev/null || true
"""
```

`dot_config/mise/tasks/bootstrap` — the fresh-install path, and the only task needing `sudo`. Everything is idempotent, so it doubles as a repair task:

```bash
#!/usr/bin/env bash
#MISE description="Fresh-install path: groups, model stores, tools, toolboxes"
set -euo pipefail

# usermod -aG is additive and idempotent. It only takes effect at next login,
# which is why first-run order is: chezmoi apply -> reboot -> bootstrap.
# (Lingering is handled by chezmoi's run_after_50 script, not here.)
sudo usermod -aG render,video "$USER"

# Two model stores, both owned by me: toolboxes run unprivileged and share $HOME.
# ComfyUI's toolbox expects ~/comfy-models, so symlink rather than duplicate.
sudo install -d -o "$USER" -g "$USER" -m 0755 /srv/models /srv/models/hf /srv/comfy-models
ln -sfn /srv/comfy-models "$HOME/comfy-models"

mise install          # resolve from mise.lock, not whatever is newest today
mise run toolbox:create

echo
echo "bootstrap complete. Next: mise run verify"
```

# Toolboxes

`dot_config/mise/tasks/toolbox/create` — the subdirectory gives it the `toolbox:create` name automatically:

```bash
#!/usr/bin/env bash
#MISE description="Create the gfx1151 toolboxes (idempotent, skips existing)"
set -euo pipefail

# name|image
TOOLBOXES=(
  "llama-vulkan-radv|docker.io/kyuz0/amd-strix-halo-toolboxes:vulkan-radv"
  "llama-rocm|docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-7.14"
  "comfyui|docker.io/kyuz0/amd-strix-halo-comfyui:latest"
)

# keep-groups is not a style choice. Under rootless podman a named --group-add
# (video/render) resolves against the *container's* /etc/group; the GID lands in
# the user namespace and never maps to the host's, granting no access to
# /dev/kfd. It fails as "the GPU isn't there", not as a permissions error.
#
# Every toolbox here gets /dev/kfd: ComfyUI is ROCm-only, and the vulkan llama
# box is harmless to grant it. One flag set, one less thing to get wrong.
FLAGS="--device /dev/dri --device /dev/kfd --group-add keep-groups --security-opt seccomp=unconfined"

for entry in "${TOOLBOXES[@]}"; do
  IFS='|' read -r name image <<<"$entry"
  # podman container exists is exact and scriptable; parsing `distrobox list` is not.
  if podman container exists "$name"; then
    echo "==> $name already present"
  else
    echo "==> creating $name"
    distrobox create --yes --name "$name" --image "$image" --additional-flags "$FLAGS"
  fi
done
```

`dot_config/mise/tasks/toolbox/refresh` — pulling a newer image does **not** move a running container onto it, so adopting an update means recreate. Safe, because toolboxes are stateless: `$HOME` is shared from the host, so nothing of value lives inside one. Kept as a separate task precisely because it destroys containers and `create` shouldn't.

```bash
#!/usr/bin/env bash
#MISE description="Pull latest images and recreate changed toolboxes"
set -euo pipefail

IMAGES=(
  "llama-vulkan-radv|docker.io/kyuz0/amd-strix-halo-toolboxes:vulkan-radv"
  "llama-rocm|docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-7.14"
  "comfyui|docker.io/kyuz0/amd-strix-halo-comfyui:latest"
)

for entry in "${IMAGES[@]}"; do
  IFS='|' read -r name image <<<"$entry"
  before=$(podman image inspect "$image" --format '{{.Id}}' 2>/dev/null || echo none)
  podman pull "$image"
  after=$(podman image inspect "$image" --format '{{.Id}}')
  if [ "$before" = "$after" ]; then
    echo "==> $name: image unchanged, leaving container alone"
  else
    echo "==> $name: new image, recreating"
    distrobox rm --force "$name" || true
  fi
done

mise run toolbox:create
systemctl --user restart llama-swap comfyui
```

> [!note] These task files are managed by chezmoi as plain (non-`.tmpl`) files, so `{{.Id}}` is written literally. Keeping `tasks/` un-templated avoids a whole class of Go-template escaping bug — the podman `--format` syntax collides with chezmoi's delimiters.

# Serving

## llama.cpp

`llama-swap` is a single Go binary that proxies an OpenAI-compatible endpoint and spawns backends on demand, so it runs on the **host** and shells into the toolbox per model.

`dot_config/llama-swap/config.yaml.tmpl`:

```yaml
# Managed by chezmoi.
healthCheckTimeout: 300
models:
  "qwen3-30b":
    # ttl is what makes coexistence with ComfyUI work: an idle model is evicted
    # and the memory pool returns to the GPU, instead of squatting on ~20 GiB
    # while a video render tries to allocate.
    ttl: 600
    # -fa 1 and --no-mmap are mandatory on gfx1151 or llama.cpp crashes.
    # ${PORT} is substituted by llama-swap.
    cmd: >
      distrobox enter --name llama-vulkan-radv --
      llama-server --host 127.0.0.1 --port ${PORT}
      -m {{ .mentat.models_dir }}/qwen3-30b-a3b-q6_k.gguf
      -c 32768 -ngl 999 -fa 1 --no-mmap
  "qwen3-30b-rocm":
    ttl: 600
    cmd: >
      distrobox enter --name llama-rocm --
      llama-server --host 127.0.0.1 --port ${PORT}
      -m {{ .mentat.models_dir }}/qwen3-30b-a3b-q6_k.gguf
      -c 32768 -ngl 999 -fa 1 --no-mmap
```

Defining the same model against both backends is the cheap way to A/B Vulkan vs ROCm — switch by model name in the client, no restarts.

`dot_config/systemd/user/llama-swap.service`:

```ini
[Unit]
Description=llama-swap (gfx1151 LLM router)
After=network-online.target

[Service]
ExecStart=%h/.local/share/mise/shims/llama-swap --config %h/.config/llama-swap/config.yaml --listen {{ .mentat.llama_listen }}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

## ComfyUI

`dot_config/systemd/user/comfyui.service`:

```ini
[Unit]
Description=ComfyUI (gfx1151, ROCm)
After=network-online.target

[Service]
# start_comfy_ui is a shell ALIAS inside the toolbox. Bash does not expand
# aliases in non-interactive shells, so neither `distrobox enter -- start_comfy_ui`
# nor `bash -lc 'start_comfy_ui'` will work here. Resolve it once:
#     distrobox enter --name comfyui -- bash -ic 'type start_comfy_ui'
# and put the real script path below. A unit that fails this way looks like a
# broken container rather than a missing alias, so it is worth pinning down.
ExecStart=/usr/bin/distrobox enter --name comfyui -- <resolved /opt script> \
    --listen 127.0.0.1 --port {{ .mentat.comfy_listen_port }} \
    --bf16-vae --disable-mmap --cache-none
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

`--disable-mmap` is the same unified-memory lesson as llama.cpp's `--no-mmap`. `--cache-none` is what keeps ComfyUI from holding models between runs, which is half of the coexistence story — the other half is llama-swap's `ttl` above.

## Exposure

Both bound to loopback and published by Tailscale rather than by binding a wider interface:

```bash
tailscale serve --bg --https=443 http://127.0.0.1:8080          # LLM endpoint
tailscale serve --bg --https=8188 http://127.0.0.1:8188         # ComfyUI
```

TLS, no firewall rules, no hardcoded tailnet IP to drift, and `0.0.0.0` never enters the picture. `tailscale serve` config persists across reboots.

# Verification

`dot_config/mise/tasks/verify` — the task that earns its keep. On an LTS with unattended upgrades enabled, post-reboot is exactly when the machine will have changed underneath me.

```bash
#!/usr/bin/env bash
#MISE description="Assert mentat's invariants; non-zero exit on drift"
set -uo pipefail   # deliberately not -e: collect every failure, don't stop at the first

FAIL=0
ok()  { printf '  \033[32mok  \033[0m %s\n' "$1"; }
bad() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

EXPECT_GIB=120

echo "kernel & firmware"
KVER=$(uname -r); KVER=${KVER%%-*}
ver_ge "$KVER" 6.18.9 && ok "kernel $KVER >= 6.18.9" || bad "kernel $KVER below the gfx1151 floor"
dpkg-query -W -f='${Version}' linux-firmware 2>/dev/null | grep -q '20251125' \
  && bad "linux-firmware 20251125 installed — known to break ROCm on Strix Halo" \
  || ok "linux-firmware not the known-bad build"

echo "kernel cmdline"
grep -q 'amd_iommu=off' /proc/cmdline && ok "iommu off" || bad "amd_iommu=off missing"
GTT_MIB=$(grep -oP 'amdgpu\.gttsize=\K[0-9]+' /proc/cmdline || true)
PAGES=$(grep -oP 'ttm\.pages_limit=\K[0-9]+' /proc/cmdline || true)
if [ -n "$GTT_MIB" ] && [ -n "$PAGES" ]; then
  # 1 MiB = 256 x 4 KiB pages. Catches the copy-paste-from-a-blog-post bug.
  [ "$((GTT_MIB * 256))" -eq "$PAGES" ] \
    && ok "gttsize and pages_limit agree ($((GTT_MIB / 1024)) GiB)" \
    || bad "gttsize=${GTT_MIB}MiB disagrees with pages_limit=${PAGES} pages"
  [ "$((GTT_MIB / 1024))" -eq "$EXPECT_GIB" ] && ok "reservation is ${EXPECT_GIB} GiB" \
    || bad "reservation is $((GTT_MIB / 1024)) GiB, expected ${EXPECT_GIB}"
else
  bad "GTT parameters absent from /proc/cmdline"
fi

echo "memory behaviour"
[ "$(cat /proc/sys/vm/swappiness)" -eq 10 ] && ok "swappiness 10" || bad "swappiness $(cat /proc/sys/vm/swappiness)"
dpkg-query -W -f='${Status}' zram-tools 2>/dev/null | grep -q 'ok installed' \
  && bad "zram-tools installed" || ok "no zram"
SWAP_USED=$(awk '/^SwapTotal/{t=$2} /^SwapFree/{f=$2} END{print t-f}' /proc/meminfo)
[ "$SWAP_USED" -lt 65536 ] && ok "swap essentially unused" \
  || bad "swap in use (${SWAP_USED} kB) — GTT reservation may be too aggressive"

echo "appliance hygiene"
# Principle 5: if these ever appear, something was installed by hand and the
# repo is no longer the source of truth.
for unwanted in python3-torch rocm-hip-sdk build-essential; do
  dpkg-query -W -f='${Status}' "$unwanted" 2>/dev/null | grep -q 'ok installed' \
    && bad "$unwanted installed on the host — belongs in a toolbox" \
    || ok "$unwanted absent"
done

echo "gpu access"
command -v crun >/dev/null && ok "crun present (keep-groups works)" || bad "crun missing — rootless GPU access will silently fail"
for tb in llama-vulkan-radv llama-rocm comfyui; do
  podman container exists "$tb" || { bad "$tb does not exist"; continue; }
  ok "$tb exists"
done
distrobox enter --name llama-vulkan-radv -- llama-cli --list-devices 2>/dev/null | grep -qiE 'rocm|vulkan' \
  && ok "llama toolbox sees the iGPU" || bad "llama toolbox reports no GPU — CPU fallback"
distrobox enter --name comfyui -- python -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null \
  && ok "comfyui torch sees the GPU" || bad "comfyui torch has no GPU"

echo "services"
loginctl show-user "$USER" -p Linger --value | grep -q yes && ok "linger enabled" || bad "linger disabled — units won't start on boot"
for svc in llama-swap comfyui; do
  systemctl --user is-active --quiet "$svc" && ok "$svc active" || bad "$svc not active"
done
curl -fsS --max-time 5 http://127.0.0.1:8080/v1/models >/dev/null && ok "LLM endpoint answers" || bad "LLM endpoint not responding"
curl -fsS --max-time 10 http://127.0.0.1:8188/ >/dev/null && ok "ComfyUI answers" || bad "ComfyUI not responding"

echo
[ "$FAIL" -eq 0 ] && echo "mentat is converged." || echo "drift detected."
exit "$FAIL"
```

> [!tip] Run this through `shellcheck` (`mise run lint`, from the dotfiles repo on my laptop) before trusting it. `verify` failing for the wrong reason is worse than not having it, and this is exactly the kind of quoting-heavy bash where a typo hides for months.

## Throughput baseline

Boolean checks can all pass while inference has silently fallen back to CPU, so the real regression detector is a number. `mise run bench` writes a dated `llama-bench` run into `benchmarks/`, and both the results and `baseline.json` get committed — a git-tracked performance history across kernel and image upgrades, which makes a regression a diff rather than a vague feeling.

```bash
#!/usr/bin/env bash
#MISE description="Benchmark each llama backend; write a dated, committable result"
set -euo pipefail

MODEL="${1:?usage: mise run bench <model.gguf>}"
STAMP=$(date +%F)
mkdir -p benchmarks

for tb in llama-vulkan-radv llama-rocm; do
  podman container exists "$tb" || continue
  echo "==> $tb"
  distrobox enter --name "$tb" -- \
    llama-bench -m "$MODEL" -fa 1 --no-mmap -ngl 999 \
    | tee "benchmarks/${STAMP}-${tb}.txt"
done
```

Compare against `baseline.json` and fail outside tolerance — worth wiring into `verify` once there are a few runs to set a sane tolerance from. Guessing a threshold before having the data would just produce false alarms. ComfyUI needs an equivalent (wall-clock on a fixed workflow at a fixed seed), which is a separate task to write.

# Operational cheatsheet

| Intent | Command |
|---|---|
| Converge the machine | `chezmoi apply` |
| Preview what would change | `chezmoi diff` |
| Change the GTT reservation | edit `gpu_reserve_gib`, `chezmoi apply`, reboot |
| Restart both services | `mise run serve` |
| Tail logs | `mise run logs` |
| See what's holding memory | `mise run status` |
| Adopt newer toolbox images | `mise run toolbox:refresh` |
| Add an LLM | edit `config.yaml.tmpl`, `chezmoi apply`, `mise run serve` |
| Add a ComfyUI model | drop it in `/srv/comfy-models` — no config change |
| Bump `llama-swap` | `mise upgrade` → `chezmoi add ~/.config/mise/mise.lock` → commit |
| Record performance | `mise run bench <model>` |
| Confirm nothing drifted / after any reboot | `mise run verify` |

# Open items

- Resolve the real `start_comfy_ui` target so `comfyui.service` can be finalised — currently a placeholder in the unit.
- Concurrency policy between the two workloads: whether `ttl` + `--cache-none` is enough in practice, or heavy jobs need serialising. Measure before adding machinery.
- Wire the `bench` → `baseline.json` tolerance check into `verify` once there's history to calibrate against, and write the ComfyUI equivalent.
- Wire `mise run lint` into a pre-commit hook in the dotfiles repo.
- Decide whether `verify` should run automatically post-boot via a systemd unit that reports failures, rather than relying on me remembering.
- Secrets: confirm the 1Password template path for the HF token before any gated model pulls.

# References

- [chezmoi: scripts](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/) — `run_`, `run_once_`, `run_onchange_` semantics
- [mise: file tasks](https://mise.jdx.dev/tasks/file-tasks.html) — task-directory layout and `#MISE` metadata
- [Debian `grub-mkconfig`](https://sources.debian.org/src/grub2/sid/util/grub-mkconfig.in/) — confirms `/etc/default/grub.d/*.cfg` is sourced after the main file
- [How to Run AMD GPU Containers with Podman](https://oneuptime.com/blog/post/2026-03-18-run-amd-gpu-containers-podman/view) — the rootless `keep-groups` trap
- [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes) and [ComfyUI toolboxes](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes) — images, tags and upstream helper scripts
