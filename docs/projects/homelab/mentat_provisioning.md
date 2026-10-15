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

Ubuntu Server 26.04 LTS is installed. The box is an **appliance**: it runs the llama.cpp and ComfyUI toolboxes and nothing else.

# Principles

1. **One repo is the source of truth.** A plain git repo holds the `/etc` payloads, the systemd units, the service config and the scripts. Nothing is configured by hand that could live there.
2. **Idempotent by construction, not by checking.** Build to a temp file, `cmp`, `install` only on difference. No `sed -i`, no appends. Every script is safe to run a hundred times.
3. **Derive, don't duplicate.** Any value appearing twice is a future inconsistency. `GPU_RESERVE_GIB` lives in `vars.sh`; both kernel knobs are computed from it.
4. **Expensive side effects are conditional.** `update-grub`, `sysctl --system`, `daemon-reload` and container recreation fire only when their input changed, so a converged `make` is silent and fast.
5. **Nothing on the host that a toolbox could carry.** No Python, no PyTorch, no compilers, no config-management tooling. ComfyUI's entire ROCm/PyTorch stack lives in its container.

> [!note] Earlier drafts of this page used chezmoi + mise. Both were dropped: chezmoi earns its keep managing `$HOME` across several machines with templating, and this is one appliance with no dotfiles; mise was pinning a single Go binary. `git` + `make` + `install(1)` cover the same ground with nothing extra on the host — Principle 5 applied to the automation itself.

# Repo layout

```
mentat/                              # git repo, cloned to ~/mentat
├── Makefile                         # the operational interface
├── vars.sh                          # every tunable, sourced by all scripts
├── etc/
│   └── sysctl.d/99-mentat.conf      # static payload
├── home/
│   ├── .config/llama/models.ini     # the model catalogue
│   └── .config/systemd/user/{llama-server,comfyui}.service
├── bin/
│   ├── lib.sh                       # install_if_changed helper
│   ├── bootstrap                    # packages, groups, model dirs (first run)
│   ├── install-system               # /etc + GRUB drop-in (generated)
│   ├── install-user                 # home files + daemon-reload
│   ├── toolboxes                    # create (idempotent)
│   ├── toolbox-postcreate           # per-toolbox first-run setup
│   ├── toolboxes-refresh            # pull + recreate changed
│   ├── models                       # fetch/list/remove GGUFs via the toolbox
│   └── verify                       # assert invariants
└── benchmarks/
    ├── baseline.json                # last-known-good tok/s, committed
    └── 2026-08-19-vulkan-radv.txt   # history, committed
```

No templating engine: the GRUB drop-in is the only file needing derived values, and a heredoc in `install-system` handles it. Everything else is static YAML/ini.

What deliberately stays **out** of git: BIOS settings (documented in [[strix_halo_ai_box|the plan]], Phase 0 — unautomatable), model weights (large, re-downloadable), and secrets. For a gated-model HF token, keep it in `~/.hf_token` (mode 0600, gitignored) rather than committed — the appliance has no secret-management story and doesn't need one for public GGUFs.

# vars.sh

The single source of tunables:

```bash
GPU_RESERVE_GIB=120        # both kernel knobs derive from this
SWAPPINESS=10
LLAMA_LISTEN=127.0.0.1:8080
COMFY_PORT=8188
MODELS_DIR=/srv/models     # one dir per repo; also LLAMA_CACHE for ad-hoc -hf
COMFY_MODELS_DIR=/srv/comfy-models
MODELS_MAX=2               # models the router may hold resident at once
ALWAYS_ON_MODEL=qwen38-27b # must match a models.ini section; verify asserts it stays awake

# name|image. The one list every script iterates: create, refresh, bench and
# verify all read this, so adding or retiring a backend is a one-line diff.
# Container names are deliberately decoupled from image tags — when the ROCm
# line moves again, the tag changes and `llama-rocm` keeps its name, so nothing
# downstream has to be renamed with it.
TOOLBOXES=(
  "llama-vulkan-radv|docker.io/kyuz0/amd-strix-halo-toolboxes:vulkan-radv"
  "llama-rocm|docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-10.0"
  "comfyui|docker.io/kyuz0/amd-strix-halo-comfyui:latest"
)
LLAMA_TB=llama-vulkan-radv  # the one that actually serves; see below
```

Upstream's stable set is `vulkan-radv` and `rocm-10.0`; everything else on that Docker Hub tag list (`rocm-7.14*`, `-performance`, `-pr26592`, `-rocmfpx`, `therock-nightly`) is experimental and rebuilt on someone's fork. `rocm-6.4.4` and `rocm-7.14` were the stable line when this page was first written — check the README's stable table, not the tag list, before bumping.

**Why `vulkan-radv` serves and `rocm-10.0` only benches.** Upstream labels ROCm "recommended for performance" and Vulkan "most stable and compatible", which reads like an argument for ROCm — but the `rocm-10.0` image currently carries a *local patch* for [llama.cpp #25992](https://github.com/ggml-org/llama.cpp/issues/25992), stopping llama.cpp from selecting ROCm host buffers on integrated GPUs. A backend that needs a carried patch to not fail inference is not what an appliance should serve from. `llama-rocm` still gets created because it costs only disk and it is what makes `bin/bench` a comparison rather than a single number — the day Vulkan regresses, the A/B is already there. Flip `LLAMA_TB` if the numbers justify it.

# bin/lib.sh

The one abstraction the whole repo leans on. It returns non-zero when nothing changed, so callers can gate their side effects:

```bash
# install_if_changed <src> <dst> <mode> [--sudo]
# Returns 0 if the file was installed (changed), 1 if already current.
install_if_changed() {
  local src=$1 dst=$2 mode=$3 sudo_cmd=""
  [ "${4:-}" = "--sudo" ] && sudo_cmd="sudo"
  if $sudo_cmd cmp -s "$src" "$dst" 2>/dev/null; then
    echo "  unchanged: $dst"
    return 1
  fi
  $sudo_cmd install -D -m "$mode" "$src" "$dst"
  echo "  installed: $dst"
  return 0
}
```

# Makefile

```make
.PHONY: all bootstrap system user toolboxes refresh verify bench

all: system user toolboxes          ## converge the machine

bootstrap:  ; @bin/bootstrap
system:     ; @bin/install-system
user:       ; @bin/install-user
toolboxes:  ; @bin/toolboxes
refresh:    ; @bin/toolboxes-refresh
verify:     ; @bin/verify
```

# First run

Do **Storage layout** below first — `bootstrap` refuses to run until `/srv` is a real mountpoint.

```bash
git clone git@github.com:<me>/mentat.git ~/mentat && cd ~/mentat
make bootstrap       # packages, groups, model dirs
make system          # /etc + GRUB — prints REBOOT REQUIRED
sudo reboot

cd ~/mentat
make toolboxes
bin/models add <hf-repo> <filter>    # at least one model, see below
make user            # units + linger + enable
make verify
```

The reboot is mandatory: the GTT reservation is a boot parameter, and it also activates the new `render`/`video` group membership.

# Storage layout

The plan calls for model stores on a dedicated filesystem excluded from backups. That was never written down as a procedure, and the omission surfaced the first time a ~95 GiB download was attempted: `df` showed 35 GiB free and the fetch was impossible.

The cause was not a small disk. Ubuntu's installer creates a modest root LV and **leaves the rest of the physical volume unallocated** — on `mentat`, a 1.9 TB NVMe presented as a 100 GiB root filesystem with 1.76 TB idle in the volume group:

```
nvme0n1                    1.9T
└─nvme0n1p3                1.9T LVM2_member
  └─ubuntu--vg-ubuntu--lv  100G ext4  /      ← the installer's default

VG        VSize  VFree
ubuntu-vg 1.86t  1.76t                       ← unclaimed
```

This is not automated. Partitioning is a one-time, destructive-adjacent act on a machine whose whole storage story is "weights are re-downloadable", and a converge script that can resize filesystems is a converge script that can lose data. It belongs in the runbook, alongside the BIOS settings, as something done once by hand and recorded:

```bash
# 1. Root: 100 GiB is tight once podman image storage lives in $HOME.
#    Three toolboxes are ~20 GiB, and `make refresh` transiently doubles that.
sudo lvextend -L 200G /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv

# 2. A dedicated LV for both model stores.
sudo lvcreate -L 600G -n srv ubuntu-vg
sudo mkfs.ext4 -L srv /dev/ubuntu-vg/srv
```

`/etc/fstab`:

```
/dev/ubuntu-vg/srv  /srv  ext4  defaults,relatime,nofail  0 2
```

- **`relatime`, not `noatime`** — the instinct with very large files is `noatime`, and an earlier draft of this page said so. But with no `hf` CLI in the toolboxes (see Models), filesystem `atime` is the *only* record of when a model was last used, and `bin/models stale` depends on it. `relatime` writes at most one atime update per file per day: the cost is negligible against multi-GiB reads, and it keeps "which of these am I not using" answerable.
- **`nofail`** — deliberate on a headless box. Without it a missing LV drops boot into an emergency shell, which on a machine with no console and no display means *unreachable*. With it, the box boots, the router finds no models, and `verify` reports a failed mount over SSH. A loud failure you can log into beats a silent one you cannot.

**Allocate conservatively.** ext4 grows online with `lvextend` + `resize2fs`; shrinking requires an unmount and is genuinely risky. 600 GiB of the 1.76 TB covers ~95 GiB of LLM weights plus ComfyUI's video checkpoints with a lot of room, and the remaining ~1 TB stays in the VG as headroom to extend into. There is no advantage to claiming it now and a real cost to guessing wrong.

> [!warning] `/tmp` is `tmpfs` on this box — 62 GiB of it — and on a unified-memory machine **RAM is the GPU pool**. Any tool that stages a multi-GB download through `/tmp` consumes the memory the GTT reservation exists to protect, and it presents as inference OOM rather than a disk error. Same class of mistake as the zram warning in `bootstrap`. `bin/models` sidesteps it by having `curl` write straight to its destination with `-o`, so nothing is staged anywhere — but any tool that *does* stage (a Python HF client, an archive extraction, a `docker save`) needs `TMPDIR` pointed at real disk first.

# bin/bootstrap

```bash
#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/../vars.sh"

# apt-get install is idempotent, so re-running is a no-op.
# Note what is absent: no python, no rocm SDK, no compilers. Both workloads
# bring their own stack inside their toolbox.
REQUIRED=(podman crun distrobox mesa-vulkan-drivers vulkan-tools git curl jq make)
OPTIONAL=(rocm-smi radeontop)   # host monitoring is a convenience, not a dependency

sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${REQUIRED[@]}"
for pkg in "${OPTIONAL[@]}"; do
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$pkg" \
    || echo "note: optional package '$pkg' unavailable, skipping" >&2
done

# zram would compress model weights into RAM-backed swap: catastrophic here.
# Report rather than purge — silently removing a swap provider is not something
# a provisioning script should do unasked.
if dpkg-query -W -f='${Status}' zram-tools 2>/dev/null | grep -q 'ok installed'; then
  echo "WARNING: zram-tools installed. Remove it: sudo apt-get purge zram-tools" >&2
fi

# Additive and idempotent; takes effect at next login, which the reboot covers.
sudo usermod -aG render,video "$USER"

# ComfyUI's toolbox expects ~/comfy-models: symlink rather than duplicate.
sudo install -d -o "$USER" -g "$USER" -m 0755 "$MODELS_DIR" "$MODELS_DIR/hf" "$COMFY_MODELS_DIR"
ln -sfn "$COMFY_MODELS_DIR" "$HOME/comfy-models"
```

# bin/install-system

The highest-stakes script; the drop-in mechanism is what keeps it safe.

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. ./vars.sh
. ./bin/lib.sh

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# Ubuntu's grub-mkconfig sources /etc/default/grub.d/*.cfg after
# /etc/default/grub (Ubuntu ships 50-cloudimg-settings.cfg the same way), so we
# *append* via a drop-in rather than rewriting the main file. Idempotent by
# whole-file replacement, no sed, and a release upgrade that rewrites
# /etc/default/grub cannot silently drop our parameters.
#
# The two GTT knobs use different units and published guides routinely quote
# pairs that disagree. Both are computed here from one value:
#   ttm.pages_limit -> 4 KiB pages -> gib * 262144
#   amdgpu.gttsize  -> MiB         -> gib * 1024
cat >"$TMP/grub.cfg" <<EOF
# Managed by ~/mentat — edits here will be overwritten.
GRUB_CMDLINE_LINUX_DEFAULT="\$GRUB_CMDLINE_LINUX_DEFAULT amd_iommu=off amdgpu.gttsize=$((GPU_RESERVE_GIB*1024)) ttm.pages_limit=$((GPU_RESERVE_GIB*262144))"
EOF

if install_if_changed "$TMP/grub.cfg" /etc/default/grub.d/99-mentat-amdgpu.cfg 0644 --sudo; then
  sudo update-grub
  sudo touch /var/run/reboot-required
  echo ">>> ${GPU_RESERVE_GIB} GiB GTT — REBOOT REQUIRED"
fi

if install_if_changed etc/sysctl.d/99-mentat.conf /etc/sysctl.d/99-mentat.conf 0644 --sudo; then
  sudo sysctl --system >/dev/null
fi
```

The escaped `\$GRUB_CMDLINE_LINUX_DEFAULT` is deliberate: it must land in the file **literally** so GRUB expands it at `update-grub` time, while the `$(( ))` arithmetic is resolved when the script runs.

`etc/sysctl.d/99-mentat.conf`:

```
# Managed by ~/mentat — edits here will be overwritten.
# With 128 GB and a hard GTT ceiling, healthy operation should never swap. If it
# does, the GTT reservation is too aggressive.
vm.swappiness = 10
```

# bin/install-user

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. ./bin/lib.sh

CHANGED=0
install_if_changed home/.config/llama/models.ini \
  "$HOME/.config/llama/models.ini" 0644 && CHANGED=1
for unit in llama-server comfyui; do
  install_if_changed "home/.config/systemd/user/$unit.service" \
    "$HOME/.config/systemd/user/$unit.service" 0644 && CHANGED=1
done

# Headless box: without lingering, user units don't start until someone logs in.
# Presents as "the service didn't come back after reboot" and is easy to
# misdiagnose. Idempotent.
loginctl enable-linger "$USER"

if [ "$CHANGED" -eq 1 ]; then
  systemctl --user daemon-reload
  systemctl --user enable --now llama-server comfyui
  # models.ini is read at router startup, so a catalogue edit needs a restart —
  # but only the router: restarting ComfyUI would evict its models for nothing.
  systemctl --user restart llama-server
else
  systemctl --user enable --now llama-server comfyui
fi
```

# bin/toolboxes

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. ./vars.sh

# keep-groups is not a style choice. Under rootless podman a named --group-add
# (video/render) resolves against the *container's* /etc/group; the GID lands in
# the user namespace and never maps to the host's, granting no access to
# /dev/kfd. It fails as "the GPU isn't there", not as a permissions error.
#
# Upstream's own README uses `--group-add video --group-add render`, but its
# examples target Fedora toolbx, not rootless distrobox on Ubuntu. Confirm with
# `llama-cli --list-devices` on first create rather than trusting either.
#
# Every toolbox gets /dev/kfd: ComfyUI is ROCm-only, and it's harmless on the
# Vulkan box. One flag set, one less thing to get wrong.
# --volume /srv:/srv is not optional. distrobox bind-mounts $HOME, /tmp, /dev
# and the host root at /run/host — but NOT arbitrary top-level directories. With
# the model store on /srv the router lists models happily (it only reads
# models.ini) and every load then fails with "No such file or directory" against
# a path that plainly exists on the host. It also silently breaks ComfyUI, whose
# ~/comfy-models symlink points into /srv and dangles inside the container.
FLAGS="--device /dev/dri --device /dev/kfd --group-add keep-groups --security-opt seccomp=unconfined --volume /srv:/srv:rslave"

for entry in "${TOOLBOXES[@]}"; do
  IFS='|' read -r name image <<<"$entry"
  # podman container exists is exact and scriptable; parsing `distrobox list` is not.
  if podman container exists "$name"; then
    echo "  present: $name"
    continue
  fi
  echo "  creating: $name"
  distrobox create --yes --name "$name" --image "$image" --additional-flags "$FLAGS"
  bin/toolbox-postcreate "$name"
done
```

## bin/toolbox-postcreate

A freshly created toolbox is not yet usable. ComfyUI in particular writes its
`extra_model_paths.yaml` *inside* the container, and that file is what points it
at `~/comfy-models` instead of a path that dies with the container. Because
`toolboxes-refresh` destroys and recreates, this cannot be a one-time manual
step — it has to run on every create, which is why it's a script rather than a
line in the runbook:

```bash
#!/usr/bin/env bash
#   bin/toolbox-postcreate <name>
# Per-toolbox first-run setup. Called by bin/toolboxes on create only.
set -euo pipefail
NAME=${1:?usage: toolbox-postcreate <name>}

case "$NAME" in
  comfyui)
    # Links ComfyUI's model dirs to ~/comfy-models. Without it the next refresh
    # silently orphans every downloaded checkpoint — the models are still on
    # disk, but ComfyUI stops seeing them, which reads as a broken install.
    echo "  post-create: linking comfy model paths"
    distrobox enter -n comfyui -- /opt/set_extra_paths.sh
    ;;
  *)
    # llama toolboxes need nothing: llama-server is pointed at an absolute path
    # under $MODELS_DIR, which is a host path shared into every container.
    ;;
esac
```

Model *weights* stay a deliberate manual step — `model_manager` inside the
ComfyUI toolbox is an interactive TUI that resolves workflow → checkpoint + LoRA
dependency chains, and hundreds of GB of downloads is not something a converge
script should start on my behalf. `bin/models` covers the GGUF side, where
the choice is a single repo and quant.

## bin/toolboxes-refresh

Pulls each image, compares the digest, and only destroys containers whose image
actually moved. Kept separate from `toolboxes` precisely because it destroys
things. Safe to do: toolboxes are stateless and `$HOME` is shared from the host,
so nothing of value lives inside one — as long as `toolbox-postcreate` runs on
the way back up.

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
. ./vars.sh

CHANGED=0
for entry in "${TOOLBOXES[@]}"; do
  IFS='|' read -r name image <<<"$entry"

  # The digest of the image the *container* was created from, versus the digest
  # of what the tag points at now. Comparing tags is useless here: these tags
  # are rebuilt in place whenever llama.cpp master moves.
  OLD=$(podman container inspect "$name" --format '{{.ImageDigest}}' 2>/dev/null || true)
  podman pull -q "$image" >/dev/null
  NEW=$(podman image inspect "$image" --format '{{.Digest}}')

  if [ "$OLD" = "$NEW" ]; then
    echo "  current: $name"
    continue
  fi
  echo "  moved:   $name"
  echo "           ${OLD:-<none>} -> $NEW"
  podman container exists "$name" && distrobox rm --force "$name"
  CHANGED=1
done

[ "$CHANGED" -eq 0 ] && { echo "all toolboxes current"; exit 0; }

bin/toolboxes   # recreates whatever was removed, and runs post-create

# Only restart if something was actually recreated: the router holds loaded
# models, and evicting 50 GiB of weights to no purpose is a slow no-op.
systemctl --user restart llama-server comfyui
echo ">>> toolboxes updated — re-run 'make verify' and 'bin/bench' before trusting the new images"
```

The bench reminder is the point of the last line. These tags are rebuilt on every llama.cpp master update, so `make refresh` is exactly the moment a silent throughput regression enters the machine — and the only thing that catches it is a number compared against `benchmarks/baseline.json`.

# Models

Nothing here works without at least one GGUF on disk, and the download happens **on the host**, not in a toolbox. That is the opposite of Principle 5's usual direction, so it needs justifying:

Both llama toolboxes are built `FROM fedora-minimal:44` with a runtime package list of `bash ca-certificates libatomic libstdc++ libgcc libibverbs vulkan-loader … radeontop procps-ng`. There is **no Python, no pip, and no `hf` CLI** in either. `llama-server -hf` does exist and is excellent — it resolves quants, follows split shards, and auto-discovers sibling MTP/mmproj/eagle3 drafts — but llama.cpp has no download-only flag, so it fetches and then *starts serving*, which is unusable from a provisioning script.

The host, by contrast, already has `curl` and `jq` from `bootstrap`, and `$MODELS_DIR` is a host path that every container sees. So the downloader stays on the host and stays boring:

```bash
#!/usr/bin/env bash
#   bin/models add   <hf-repo> [filter]   download; no filter lists the GGUFs
#   bin/models ls                         what's on disk, most-recently-used first
#   bin/models stale [days]               deletion candidates
#   bin/models rm    <file>               delete one
set -euo pipefail
cd "$(dirname "$0")/.."
. ./vars.sh

# Gated repos need a token; public GGUFs don't. Absent file = no header.
AUTH=()
[ -r "$HOME/.hf_token" ] && AUTH=(-H "Authorization: Bearer $(cat "$HOME/.hf_token")")

CMD=${1:?usage: models {add|ls|stale|rm} …}; shift
case "$CMD" in
add)
  REPO=${1:?usage: models add <hf-repo> [filter]}; FILTER=${2:-}
  FILES=$(curl -fsSL "${AUTH[@]}" "https://huggingface.co/api/models/${REPO}" \
          | jq -r '.siblings[].rfilename' | grep -i '\.gguf$' || true)
  [ -n "$FILES" ] || { echo "no GGUF files in ${REPO}" >&2; exit 1; }

  # No filter: list and stop. Cheaper than guessing a quant name wrong.
  [ -z "$FILTER" ] && { echo "$FILES"; echo; echo "re-run with a filter to download"; exit 0; }

  # Split models need every shard; llama.cpp is pointed at the first and finds
  # the rest.
  #
  # The filter is applied EXACTLY as given — an earlier version of this script
  # appended `|/mtp-` to pick up speculative-decoding drafts automatically, and
  # that matched all six variants in an MTP/ directory: 22.9 GiB against a
  # single 2.6 GiB file that was actually wanted. Draft heads are a deliberate
  # second `models add` with their own filter, not a freebie.
  DEST="${MODELS_DIR}/$(basename "$REPO")"
  echo "$FILES" | grep -iE -- "${FILTER}" | while read -r f; do
    out="${DEST}/${f}"
    [ -s "$out" ] && { echo "  have: $f"; continue; }
    echo "  fetching: $f"
    # An 87 GiB fetch spans hours and will hit a blip. Every flag here is a
    # scar: --create-dirs preserves the repo's subdirectory layout so quant
    # dirs stay distinguishable; -C - resumes rather than restarting;
    # --retry-all-errors covers HTTP failures and not just dropped sockets;
    # and --speed-limit turns a stalled-but-open connection into an error the
    # retry logic can act on, instead of a hang that looks like progress.
    # Without these, a failure mid-shard leaves a short file that loads fine
    # right up until it doesn't.
    curl -fL --progress-bar --create-dirs -C - "${AUTH[@]}" \
         --retry 10 --retry-delay 10 --retry-all-errors \
         --speed-limit 1048576 --speed-time 60 \
         -o "$out" "https://huggingface.co/${REPO}/resolve/main/${f}" \
      || { echo "  FAILED: $f" >&2; exit 1; }
  done

  # A truncated shard presents as a model-load crash, not a download error, so
  # the sizes are checked against the Hub rather than assumed.
  echo; echo "verifying:"
  curl -fsSL "${AUTH[@]}" "https://huggingface.co/api/models/${REPO}/tree/main?recursive=true" \
   | jq -r --arg f "$FILTER" '.[]|select(.path|test($f;"i"))|select(.path|test("gguf$"))|"\(.lfs.size // .size) \(.path)"' \
   | while read -r want path; do
       have=$(stat -c%s "${DEST}/${path}" 2>/dev/null || echo 0)
       [ "$have" = "$want" ] && echo "  ok   $path" \
                             || echo "  BAD  $path ($have of $want)"
     done
  echo; echo "models.ini paths:"; find "$DEST" -name '*.gguf' | sort
  ;;
# atime is why /srv is mounted relatime rather than noatime — see Storage layout.
ls)    find "$MODELS_DIR" -name '*.gguf' -printf '%A+  %10sB  %p\n' | sort -r ;;
stale) find "$MODELS_DIR" -name '*.gguf' -atime "+${1:-30}" -printf '%A+  %p\n' | sort ;;
rm)    rm -i -- "${1:?usage: models rm <file>}" ;;
*)     echo "unknown: $CMD" >&2; exit 1 ;;
esac
```

`bin/models add unsloth/Qwen3.8-27B-GGUF` lists what is in the repo; adding `UD-Q4_K_M` downloads it. Two-step by design — quant naming varies enough between publishers that guessing wastes a large download.

Run it under `tmux` for anything large. A multi-shard fetch outlives an SSH session, and losing the terminal kills the transfer at whatever byte it had reached — which the verification step will then report as a short file rather than a missing one.

`bin/models stale 30` answers "which experiments am I not actually using", which is the question that accumulates once you start cycling through models. It works off `atime`, so **`/srv` must be mounted `relatime`, not `noatime`** — see Storage layout.

> [!note] `llama-server -hf <repo>:<quant>` is still the better tool for *ad-hoc* use — trying one model with `--models-dir` and no config at all. It needs no path bookkeeping and pulls MTP siblings automatically. It just can't be scripted, because it serves rather than exits once the bytes land.

> [!warning] `gguf-vram-estimator.py` ships in both llama toolboxes at `/usr/local/bin/`, and **neither image has an interpreter to run it with**. An earlier draft of this page called it via `bin/models fit`; that command could never have worked. Either run it from the ComfyUI toolbox (which does carry Python) against the shared `/srv` path, or skip it — loading the model and watching `rocm-smi --showmeminfo all` is the measurement that actually matters.

## Choosing models for this hardware

Strix Halo's ceiling is **memory bandwidth** (~256 GB/s), not compute — far below a discrete GPU. The practical consequence:

**Prefer MoE over dense.** A mixture-of-experts model with few active parameters per token reads far less memory per token than a dense model of the same total size, so it runs dramatically faster here. A dense 70B is bandwidth-starved on this box; a much larger MoE with ~10B active can outrun it. This is the single most important model-selection rule for gfx1151.

Sizing against the 120 GiB pool, leaving room for ComfyUI:

| Tier | Model | Quant | Size | Topology |
|---|---|---|---|---|
| Always resident | `unsloth/Qwen3.8-27B-GGUF` | `UD-Q4_K_M` | 15.3 GiB | **dense** 27B |
| Sleep-evicted | `unsloth/Qwen3.8-Flash-Next-GGUF` | `UD-IQ4_XS` | 87.3 GiB (3 shards) | 512 experts, 10 active |

Both are the current generation (August 2026). Deliberately *not* chosen:

- **`Qwen3-Coder-Next`** — the obvious pick by name, and stale by lineage. Released 2026-01-30 on the `Qwen3Next` architecture from September 2025, so two generations behind. There is no coder-tuned model on the 3.8 line; coder-specific and current-generation are mutually exclusive at the moment, and current wins.
- **`gpt-oss-120b`** — fine model, but two heavies cannot both fit (see the warning below), and this pairing keeps one tokenizer and one prompt format.

## The dense trap, and why it's accepted here

`Qwen3.8-27B` has no `num_experts` in its config: it is **dense**. Every token reads all 15.3 GiB, so ~256 GB/s of bandwidth puts a hard ceiling near **16 tok/s** before any inefficiency. It is simultaneously the newest model in the family and the worst bandwidth profile on this hardware — a direct contradiction of the MoE rule above, taken knowingly because it is small enough to stay resident and current enough to be worth keeping.

The mitigation is **MTP**. Both models carry `mtp_num_hidden_layers: 1`, and Unsloth ships standalone draft GGUFs (`MTP/mtp-Qwen3.8-27B-Q4_0.gguf`, 1.3 GiB) for llama.cpp's speculative decoding. Whether that closes the gap is a measurement, not an assumption — see Open items.

> [!tip] If the 27B's latency disappoints, the swap is **`unsloth/Qwen3.6-35B-A3B-GGUF`** at `UD-Q4_K_M` (20.6 GiB) or `UD-IQ4_XS` (16.5 GiB): 256 experts with 8 active, so ~3B active instead of 27B dense — several times faster for 5 GiB more. Four months older (2026-04-15) but the same hybrid attention, same 256k context, same MTP. For a model whose whole job is answering fast, the MoE is probably the better trade; recency is the only argument for the dense one.

## Context is cheap on this generation

`full_attention_interval: 4` — only one layer in four keeps a growing KV cache, the rest are linear attention with constant state. At 256k context KV costs a fraction of a classic transformer, so **weights dominate the budget and context is nearly free**. This inverts the old advice: earlier drafts of this page warned that 128k context could cost more than the weights, which was true of `Qwen3Moe` and is not true here. Set generous `ctx-size` values.

> [!warning] `--models-max` caps the model *count*, not the *footprint*. Two heavies at 76 GiB each would both be admitted and then exhaust the pool. With one small and one heavy this is safe; the moment a second heavy is added to `models.ini` the cap stops being a guard. This is the concrete cost of dropping llama-swap, whose group policy could express "at most one heavy" — see the note in Serving config.

> [!note] The first shard of these split repos is genuinely tiny — 10,946,624 bytes, an index rather than weights. An earlier draft of this page recorded that the HF API "does not report a size" for it; the API reports it correctly and the fault was rounding 10.4 MiB to `0 GiB` at GiB precision. Real totals: `UD-IQ3_XXS` 76.3 GiB, `UD-IQ4_XS` 87.3 GiB, `UD-Q4_K_XL` 96.7 GiB.

# Serving config

Earlier drafts put **llama-swap** in front of `llama-server`. That is no longer necessary: `llama-server` launched with *no model* is itself a router, forwarding each request to the right instance. It covers everything llama-swap was here for — on-demand loading, idle eviction, per-model context and sampling, a concurrent-model cap, HF downloads, Prometheus metrics.

Dropping it removes a host binary, a version pin, an install script and a `make` target. The serving layer now has **nothing on the host at all** — the router runs inside the same toolbox as the models it loads, so Principle 5 holds for inference the way it already did for ComfyUI.

> [!note] What llama-swap still does better, should this ever matter: it fronts *any* OpenAI-compatible server (vLLM, whisper.cpp, stable-diffusion.cpp), and it can route different models to different backends — model A to the Vulkan toolbox, model B to ROCm — because each model's launch command is arbitrary. Router mode is one process in one container, so it is llama.cpp-only and single-backend. Neither limitation binds here.

## home/.config/llama/models.ini

`[*]` applies to every model, which is where the two mandatory gfx1151 flags go — the same reason they lived in the llama-swap macro. Forgetting `flash-attn` or leaving `mmap` on doesn't degrade gracefully on this hardware; it crashes or crawls.

```ini
version = 1

[*]
flash-attn = on
load-mode = none            ; was `mmap = off`; --no-mmap is deprecated
n-gpu-layers = 999
cache-type-k = q8_0
cache-type-v = q8_0
jinja = true

; ── always-on tier ────────────────────────────────────────────
; Dense 27B: ~16 tok/s bandwidth ceiling, so the draft model is doing
; real work here rather than being a nicety. Never sleeps.
[qwen38-27b]
model = /srv/models/Qwen3.8-27B-GGUF/Qwen3.8-27B-UD-Q4_K_M.gguf
spec-draft-model = /srv/models/Qwen3.8-27B-GGUF/MTP/mtp-Qwen3.8-27B-Q4_0.gguf
ctx-size = 65536
sleep-idle-seconds = -1

; ── heavy tier ────────────────────────────────────────────────
; 10 of 512 experts active, so the per-token bandwidth cost is small
; despite ~76 GiB of weights. Sleeps after 5 min — short, because this
; one is holding most of the pool and ComfyUI wants it back.
; Point at shard 1; llama.cpp finds the rest.
[qwen38-flash-next]
model = /srv/models/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
ctx-size = 131072
sleep-idle-seconds = 300
```

## Coexistence in practice

`UD-IQ4_XS` was chosen deliberately over `UD-IQ3_XXS` — better quality, and disk is not the constraint at 600 GiB. The consequence is worth stating as a number rather than as "tight":

| State | Resident | Pool free |
|---|---|---|
| Both LLMs loaded | 15.3 + 87.3 GiB | **~17 GiB** |
| Flash-Next asleep | 15.3 GiB | **~105 GiB** |

17 GiB does not run the workflows in the plan. Upstream's HunyuanVideo preset alone is configured for 32 GB, and Qwen Image at FP8 wants roughly 20 GB before the VAE and text encoder. So with both models resident, ComfyUI is not merely constrained — it will OOM on anything documented.

This is not a flaw to fix; it is the correct shape for a single-user box. It does mean **`sleep-idle-seconds = 300` on Flash-Next is load-bearing, not an optimisation**: it is the entire mechanism by which image and video work becomes possible. The pinned 27B costs only 15.3 GiB and leaves ~105 GiB once the heavy model sleeps, which covers every documented workflow, so pinning it stays worthwhile.

The practical habit: before a render, take the pool back rather than waiting out the timer.

```bash
curl -X POST localhost:8080/models/unload        # all models
rocm-smi --showmeminfo all                       # confirm before starting ComfyUI
```

## MTP: not available here, and why

Unsloth ships MTP draft heads for Flash-Next that upstream measures at **1.67×** (83 → 139 tok/s, greedy, single stream). They cannot be used on this box, and the reason is worth recording so the 23 GiB of heads don't get re-downloaded:

`vulkan-radv` builds from `ggml-org/llama.cpp` master. Mainline accepts `--spec-type draft-mtp` as a *flag*, but the MTP graph for the `qwen4exp` architecture — plus the cross-model tensor borrowing the `shared-` heads need — lives in [PR #28243](https://github.com/ggml-org/llama.cpp/pull/28243), still open. A stock build therefore accepts the flag and silently speculates nothing.

Getting it would mean serving from a fork (`unslothai/llama.cpp`) or the `rocm-10.0-qwen-3.8-flash-next` toolbox upstream publishes for exactly this. Both contradict the appliance's "serve from the stable image" rule for a 1.67× that arrives in mainline eventually anyway. **Revisit when #28243 merges** — at that point the flags are `-md <path> --spec-type draft-mtp --spec-draft-n-max 2`, with `-md` mandatory because sidecar auto-discovery does not search the `MTP/` subfolder.

Two things to remember then: a `shared-` head logs a scary `borrow_shared_tensor` error at startup and then works (the memory fit measures it before the main model exists), and MTP is a net **loss** at concurrency 8 (~0.85×) — it trades idle capacity for latency, which is the right trade for one user and the wrong one for a shared endpoint.

The 27B's draft head is a different architecture (`qwen35`) and may well work on mainline; it is 1.28 GiB, so the cost of testing is negligible. That is the only `spec-draft-model` line worth keeping until #28243 lands.

`spec-draft-model` is the INI spelling of `--spec-draft-model` / `-md`. Upstream's example file uses long flag names without the leading dashes, and the router passes unreserved arguments through to each instance — but this specific key is inferred from that pattern rather than documented, so confirm it loads before trusting it. If it is rejected, the fallback is `--spec-draft-hf` on the router command line, which applies globally and is worse.

`--models-max 2` caps residency at two. Sleep is the eviction mechanism: it unloads the model **and its KV cache**, which on unified memory is what actually returns GTT to the pool — the ComfyUI coexistence story from the plan's Phase 4, now a per-model number instead of a group policy.

> [!note] **Per-model sleep is structural, confirmed on the box.** The worry was that `sleep-idle-seconds` might only be a router-wide flag, which would make the always-on tier impossible and bring llama-swap back. It isn't: the router **spawns a separate `llama-server` process per model**, on its own port, with that model's INI keys as its argument list —
> ```
> srv load: spawning server instance with name=qwen38-27b on port 40889
> srv load:   --sleep-idle-seconds -1  --ctx-size 65536  --alias qwen38-27b …
> ```
> One model's settings cannot leak into another's because they are different processes. This also explains why `hf-repo` is router-reserved while everything else passes through.

## home/.config/systemd/user/llama-server.service

```ini
[Unit]
Description=llama-server router (gfx1151)
After=network-online.target

[Service]
# LLAMA_CACHE is what makes `bin/models add` and the router agree on one
# location. Set it here, not in the shell profile: the unit must not depend
# on an interactive environment it will never have.
Environment=LLAMA_CACHE=/srv/models
ExecStart=/usr/bin/distrobox enter --name llama-vulkan-radv -- \
    llama-server --models-preset %h/.config/llama/models.ini \
    --host 127.0.0.1 --port 8080 --models-max 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

No `-m`: passing a model is what puts `llama-server` in single-model mode and silently disables routing.

`home/.config/systemd/user/comfyui.service`:

```ini
[Unit]
Description=ComfyUI (gfx1151, ROCm)
After=network-online.target

[Service]
# start_comfy_ui is a shell ALIAS inside the toolbox, and bash does not expand
# aliases non-interactively — so neither `distrobox enter -- start_comfy_ui` nor
# `bash -lc '…'` works here. Resolve it once:
#     distrobox enter -n comfyui -- bash -ic 'type start_comfy_ui'
# and use the real script path.
#
# Upstream documents that the alias already applies --bf16-vae, --disable-mmap
# and --cache-none, so those are NOT repeated here — all three are load-bearing
# (see the plan, Phase 4) and passing them twice risks arg-parse surprises.
# Only the bind address is ours to set.
ExecStart=/usr/bin/distrobox enter --name comfyui -- <resolved /opt script> \
    --listen 127.0.0.1 --port 8188
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

`--disable-mmap` is the same unified-memory lesson as llama.cpp's `--no-mmap`. `--cache-none` keeps ComfyUI from holding models between runs, which is half the coexistence story — the other half is `ttl` above.

## Exposure

```bash
tailscale serve --bg --https=443  http://127.0.0.1:8080     # LLM endpoint
tailscale serve --bg --https=8188 http://127.0.0.1:8188     # ComfyUI
```

TLS, no firewall rules, no tailnet IP to drift, and `0.0.0.0` never enters the picture. Config persists across reboots.

Serving 8080 also publishes `llama-server`'s built-in web UI, so model switching and a test playground are reachable from any device on the tailnet — the same convenience llama-swap's `/ui` would have provided, without the extra process. Note that `--host 127.0.0.1` in the unit is what keeps this tailnet-only; `tailscale serve` is doing the exposure, and the bind address must never be widened to match.

# bin/verify

The script that earns its keep. On an LTS with unattended upgrades enabled, post-reboot is exactly when the machine will have changed underneath me.

```bash
#!/usr/bin/env bash
set -uo pipefail   # deliberately not -e: collect every failure, don't stop at the first
cd "$(dirname "$0")/.."
. ./vars.sh

FAIL=0
ok()  { printf '  \033[32mok  \033[0m %s\n' "$1"; }
bad() { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

echo "kernel & firmware"
KVER=$(uname -r); KVER=${KVER%%-*}
ver_ge "$KVER" 6.18.9 && ok "kernel $KVER >= 6.18.9" || bad "kernel $KVER below the gfx1151 floor"
dpkg-query -W -f='${Version}' linux-firmware 2>/dev/null | grep -q '20251125' \
  && bad "linux-firmware 20251125 — known to break ROCm on Strix Halo" \
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
  [ "$((GTT_MIB / 1024))" -eq "$GPU_RESERVE_GIB" ] && ok "reservation is ${GPU_RESERVE_GIB} GiB" \
    || bad "reservation is $((GTT_MIB / 1024)) GiB, vars.sh says ${GPU_RESERVE_GIB}"
else
  bad "GTT parameters absent from /proc/cmdline"
fi

echo "memory behaviour"
[ "$(cat /proc/sys/vm/swappiness)" -eq "$SWAPPINESS" ] && ok "swappiness $SWAPPINESS" || bad "swappiness $(cat /proc/sys/vm/swappiness)"
dpkg-query -W -f='${Status}' zram-tools 2>/dev/null | grep -q 'ok installed' \
  && bad "zram-tools installed" || ok "no zram"
SWAP_USED=$(awk '/^SwapTotal/{t=$2} /^SwapFree/{f=$2} END{print t-f}' /proc/meminfo)
[ "$SWAP_USED" -lt 65536 ] && ok "swap essentially unused" \
  || bad "swap in use (${SWAP_USED} kB) — GTT reservation may be too aggressive"

echo "appliance hygiene"
# Principle 5: if these appear, something was installed by hand and the repo is
# no longer the source of truth.
for unwanted in python3-torch rocm-hip-sdk build-essential; do
  dpkg-query -W -f='${Status}' "$unwanted" 2>/dev/null | grep -q 'ok installed' \
    && bad "$unwanted on the host — belongs in a toolbox" || ok "$unwanted absent"
done

echo "gpu access"
command -v crun >/dev/null && ok "crun present (keep-groups works)" || bad "crun missing — rootless GPU access will silently fail"
for entry in "${TOOLBOXES[@]}"; do
  tb=${entry%%|*}
  podman container exists "$tb" && ok "$tb exists" || bad "$tb missing"
done
distrobox enter -n "$LLAMA_TB" -- llama-cli --list-devices 2>/dev/null | grep -qiE 'rocm|vulkan' \
  && ok "$LLAMA_TB sees the iGPU" || bad "$LLAMA_TB reports no GPU — CPU fallback"
distrobox enter -n comfyui -- python -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null \
  && ok "comfyui torch sees the GPU" || bad "comfyui torch has no GPU"
# The post-create step is easy to lose across a refresh, and losing it doesn't
# break anything until the next time ComfyUI looks for a checkpoint.
# NB: confirm the real path on the box — `distrobox enter -n comfyui --
# cat /opt/set_extra_paths.sh` shows where it writes. Placeholder below.
distrobox enter -n comfyui -- test -f /opt/ComfyUI/extra_model_paths.yaml 2>/dev/null \
  && ok "comfy model paths linked" || bad "extra_model_paths.yaml absent — run bin/toolbox-postcreate comfyui"

echo "storage"
mountpoint -q /srv && ok "/srv mounted" || bad "/srv not mounted — models invisible to the router"
SRV_FREE=$(df -BG --output=avail /srv 2>/dev/null | tail -1 | tr -dc '0-9')
[ "${SRV_FREE:-0}" -ge 50 ] && ok "/srv has ${SRV_FREE}G free" || bad "/srv low on space (${SRV_FREE:-?}G)"
# relatime, deliberately: bin/models stale reads atime. noatime would break it.
findmnt -no OPTIONS /srv | grep -q relatime && ok "/srv relatime" || bad "/srv not relatime — bin/models stale won't work"

echo "models"
# -hf writes HF cache layout, so there are no flat *.gguf to glob for. Ask the
# router what it can actually serve instead — which is the thing that matters.
MODEL_IDS=$(curl -fsS --max-time 5 "http://${LLAMA_LISTEN}/v1/models" 2>/dev/null | jq -r '.data[].id' || true)
[ -n "$MODEL_IDS" ] && ok "router lists $(echo "$MODEL_IDS" | wc -l | tr -d ' ') model(s)" \
  || bad "router lists no models — check ${MODELS_DIR} and models.ini"

echo "services"
loginctl show-user "$USER" -p Linger --value | grep -q yes && ok "linger enabled" || bad "linger disabled — units won't start on boot"
for svc in llama-server comfyui; do
  systemctl --user is-active --quiet "$svc" && ok "$svc active" || bad "$svc not active"
done
curl -fsS --max-time 5 "http://${LLAMA_LISTEN}/v1/models" >/dev/null && ok "LLM endpoint answers" || bad "LLM endpoint not responding"
# The always-on tier is a policy, not a fact: assert it rather than assume it.
# If this fails, sleep-idle-seconds is not being honoured per model.
curl -fsS --max-time 5 "http://${LLAMA_LISTEN}/props?model=${ALWAYS_ON_MODEL}" 2>/dev/null \
  | jq -e '.is_sleeping == false' >/dev/null \
  && ok "${ALWAYS_ON_MODEL} resident" || bad "${ALWAYS_ON_MODEL} asleep — always-on tier not holding"
curl -fsS --max-time 10 "http://127.0.0.1:${COMFY_PORT}/" >/dev/null && ok "ComfyUI answers" || bad "ComfyUI not responding"

echo
[ "$FAIL" -eq 0 ] && echo "mentat is converged." || echo "drift detected."
exit "$FAIL"
```

> [!tip] Run `shellcheck bin/*` before trusting these. `verify` failing for the wrong reason is worse than not having it, and this is exactly the kind of quoting-heavy bash where a typo hides for months. Worth a pre-commit hook.

## Throughput baseline

Boolean checks can all pass while inference has silently fallen back to CPU, so the real regression detector is a number. `bin/bench` runs `llama-bench` per backend and writes a dated file into `benchmarks/`; both the results and `baseline.json` get committed, giving a git-tracked performance history across kernel and image upgrades — a regression becomes a diff rather than a vague feeling.

```bash
#!/usr/bin/env bash
set -euo pipefail
. "$(dirname "$0")/../vars.sh"
MODEL="${1:?usage: bin/bench <model.gguf>}"
STAMP=$(date +%F)
mkdir -p benchmarks
for entry in "${TOOLBOXES[@]}"; do
  tb=${entry%%|*}
  [ "$tb" = comfyui ] && continue      # different workload, different script
  podman container exists "$tb" || continue
  echo "==> $tb"
  distrobox enter -n "$tb" -- llama-bench -m "$MODEL" -fa 1 --no-mmap -ngl 999 \
    | tee "benchmarks/${STAMP}-${tb}.txt"
done
```

Wiring a tolerance check into `verify` is worth doing once there are a few runs to calibrate from — guessing a threshold beforehand just produces false alarms. ComfyUI needs an equivalent (wall-clock on a fixed workflow and seed), which is a separate script to write.

# Operational cheatsheet

| Intent | Command |
|---|---|
| Converge the machine | `make` |
| Change the GTT reservation | edit `vars.sh`, `make system`, reboot |
| Restart both services | `systemctl --user restart llama-server comfyui` |
| Tail logs | `journalctl --user -u llama-server -u comfyui -f` |
| What's loaded, what's asleep | `curl -s localhost:8080/v1/models \| jq '.data[].id'` |
| Is the always-on tier still up | `curl -s 'localhost:8080/props?model=<id>' \| jq .is_sleeping` |
| See pool usage | `rocm-smi --showmeminfo all` |
| Free the pool now | `curl -X POST localhost:8080/models/unload` |
| List a repo's quants | `bin/models add <repo>` |
| Download one | `bin/models add <repo> <filter>` |
| What's on disk | `bin/models ls` |
| What I haven't used lately | `bin/models stale 30` |
| Delete a model | `bin/models rm <file>` |
| Pin context/sampling for a model | edit `home/.config/llama/models.ini`, `make user` |
| Adopt newer toolbox images | `make refresh` |
| Record performance | `bin/bench <model>` |
| After any reboot | `make verify` |
| Grow the model store | `sudo lvextend -L +200G /dev/ubuntu-vg/srv && sudo resize2fs /dev/ubuntu-vg/srv` |

Adding a model needs no config edit — the router serves anything in the cache. `models.ini` is only for pinning per-model context, sampling and sleep behaviour.

# Open items

- Resolve the real `start_comfy_ui` target so `comfyui.service` can be finalised — currently a placeholder. `distrobox enter -n comfyui -- bash -ic 'type start_comfy_ui'`.
- Confirm where `/opt/set_extra_paths.sh` writes its config, so `verify`'s check points at the real file rather than a guessed `/opt/ComfyUI/extra_model_paths.yaml`.
- Verify `--group-add keep-groups` actually beats upstream's `--group-add video --group-add render` under rootless distrobox on Ubuntu. `llama-cli --list-devices` inside the toolbox is the test; the reasoning says keep-groups, but upstream's Fedora examples say otherwise and only the box settles it.
- Wire the `bench` → `baseline.json` tolerance check into `verify` once there's history, and write the ComfyUI equivalent.
- Re-check the stable tag set at each `make refresh`: upstream demoted `rocm-7.14` to experimental and promoted `rocm-10.0` between drafts of this page, and the README's stable table is the only reliable signal — the Docker Hub tag list is mostly experimental builds.
- **Measure the dense 27B with and without MTP.** If speculative decoding doesn't lift it well clear of its ~16 tok/s ceiling, replace the always-on tier with `Qwen3.6-35B-A3B` (MoE, ~3B active) and accept a four-month-older model in exchange for latency.
- **Confirm `spec-draft-model` is a valid `models.ini` key**, and that a draft model is even wanted per-model rather than router-wide.
- **Revisit Flash-Next's quant if ComfyUI coexistence starts to matter.** Currently `UD-IQ4_XS` (87.3 GiB), which with the 27B resident leaves only ~17 GiB — enough to run ComfyUI but not to do anything substantial with it. `UD-IQ3_XXS` (76.3 GiB) buys ~28 GiB instead. Disk is not the constraint at 600 GiB, so both can live on disk and be selected per request; memory is. Low-bit quantization hits a 512-expert MoE harder than a dense model, so decide on real prompts rather than arithmetic.
- **Test whether the 27B's `qwen35` MTP head works on mainline.** 1.28 GiB, and the only speculative-decoding option available until #28243 merges.
- Decide what to do about `gguf-vram-estimator.py`: copy it to `/srv` and run it from the ComfyUI toolbox's Python, or drop the idea and rely on `rocm-smi` during a real load.
- `shellcheck` pre-commit hook.
- Decide whether `verify` should run post-boot via a systemd unit that reports failures, rather than relying on me remembering.

# References

- [llama-server router mode](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#router-mode) — `--models-preset`, `--models-max`, `/models/unload`, and [sleep on idle](https://github.com/ggml-org/llama.cpp/pull/18228) (PR #18228), which unloads model *and* KV cache
- [`models.ini` example](https://github.com/kyuz0/amd-strix-halo-toolboxes/blob/main/docs/models.ini.example) — upstream's preset file, tuned for this hardware
- [Hugging Face model API](https://huggingface.co/docs/hub/api) — the `/api/models/<repo>` endpoint `bin/models add` uses to list files
- [llama-swap](https://github.com/mostlygeek/llama-swap) — no longer used here; still the answer for fronting non-llama.cpp servers or several backends at once
- [Debian `grub-mkconfig`](https://sources.debian.org/src/grub2/sid/util/grub-mkconfig.in/) — confirms `/etc/default/grub.d/*.cfg` is sourced after the main file
- [How to Run AMD GPU Containers with Podman](https://oneuptime.com/blog/post/2026-03-18-run-amd-gpu-containers-podman/view) — the rootless `keep-groups` trap
- [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes) and [ComfyUI toolboxes](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes) — images, tags, upstream helper scripts
