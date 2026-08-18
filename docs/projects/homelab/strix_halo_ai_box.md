---
tags:
  - WIP
  - projects
  - homelab
  - ai
  - rocm
date: "2026-08-14"
title: strix_halo_ai_box
---

> [!faq]- Disclaimer:
> Same caveat as [[ai_workspace|AI workspace]] — the gfx1151 software stack (ROCm, llama.cpp, vLLM) moves week to week. Treat every version number below as a snapshot, not a pin. The point of codifying this in mise/chezmoi is so churn is cheap.

# Goal

Turn the Strix Halo box into an **AI-first development machine**: the thing I SSH into (or sit at) to do real work, where local inference is a first-class local service rather than a science project. Two jobs, deliberately kept separate:

1. **Inference host** — serves models over an OpenAI-compatible endpoint to everything else on the network, including workloads in the [[k8s_cluster|Kubernetes cluster]].
2. **Dev box** — my normal shell, editor, language runtimes and agent harnesses, provisioned identically to my other machines.

Non-goal: making this a cluster node. See [Relationship to the k8s cluster](#relationship-to-the-k8s-cluster).

# Hardware

**BosGame M5** — AMD Ryzen AI Max+ 395 (Zen 5) with an integrated Radeon 8060S (RDNA 3.5, **gfx1151**) and an XDNA 2 NPU, on a **unified memory** architecture: CPU and iGPU share one LPDDR5X pool at ~256 GB/s theoretical. Listed under Compute — AI in [[hardware|homelab hardware]]; the only node there that isn't part of the [[k8s_cluster|Kubernetes cluster]].

The unified memory pool is the whole reason this machine is interesting and also the source of nearly every configuration gotcha below. There is no discrete VRAM to allocate; there's one pool, and the job is convincing the kernel to let the GPU address most of it.

> [!todo] Confirm the final RAM/storage config — the GTT math in Phase 2 assumes 128 GB, and every number in that table rescales if it isn't.

# Design decisions

Three choices that shape everything else:

**Containers are the GPU runtime boundary.** Every guide worth reading says the same thing: *do not install packaged ROCm SDKs from the Arch repos or the AUR* for gfx1151 — they lag too far behind for this GPU. The alternative to hand-rolling TheRock nightlies into `/opt/rocm7.x` is to let someone else do it: [`kyuz0/amd-strix-halo-toolboxes`](https://github.com/kyuz0/amd-strix-halo-toolboxes) publishes containers with matched ROCm/Vulkan + llama.cpp builds for gfx1151, rebuilt against llama.cpp master. The host stays clean (kernel + `amdgpu` + podman), and swapping backends is `distrobox create`, not a reinstall. This is the main reason to prefer the toolboxes over a native build.

**Vulkan first, ROCm when measured.** RADV needs no extra host setup and is competitive with (sometimes better than) ROCm for token generation at normal context lengths on gfx1151. ROCm's win is prompt processing on long inputs. Start on Vulkan, keep both toolboxes, benchmark before committing.

**The host is disposable, the config is not.** Everything below should be reachable from a fresh CachyOS install by `chezmoi init` + one `mise run` — including the root-owned `/etc` bits. See [Automation](#automation--replicability).

# Phase 0 — Firmware & BIOS

Do this first; it's the part no amount of config management can automate.

- **UMA Frame Buffer Size → 512 MB** (minimum). Counterintuitive but correct: the BIOS carveout is GPU-*exclusive* and wasted. Setting it low forces the iGPU to source memory from GTT instead, which is the large, dynamically shared pool.
  - Path: `Advanced → AMD CBS → NBIO Common Options → GFX Configuration`
- **IOMMU → Disabled** — worth ~6–7% memory bandwidth (~234 vs ~221 GB/s reported) and a similar prompt-processing gain. Only do this if I don't need VFIO passthrough or hardware-isolated VMs on this box. Given it's not a cluster node, that's fine. Revisit if that changes.
  - Path: `Advanced → AMD CBS → NBIO Common Options → IOMMU`
- Update BIOS/EC to latest before benchmarking anything. Early Strix Halo firmware had memory-clock and power-limit bugs.
- Record the final BIOS revision and settings in this doc — this is the one piece of state that lives outside git.

# Phase 1 — Base OS

CachyOS, mainline `linux-cachyos` (**not** `-lts`). Kernel floor matters more than usual here:

| Constraint | Why |
|---|---|
| Kernel ≥ 6.18.9 | Older kernels (incl. 6.18.4) have a gfx1151 stability bug |
| Avoid `linux-firmware-20251125` | Breaks ROCm on Strix Halo — crashes/instability |
| Kernel ≥ 6.14 | `amd-xdna` driver, if I ever want the NPU |

Pin firmware away from the known-bad version in `/etc/pacman.conf` `IgnorePkg` only as a temporary measure, and leave a dated comment — a stale ignore on `linux-firmware` is a footgun six months from now.

Host packages, deliberately minimal:

```
podman distrobox              # the GPU runtime boundary
rocm-smi-lib                  # host-side monitoring only, not the SDK
vulkan-radv mesa              # RADV for the Vulkan backend
```

Add my user to `video` and `render`. Verify `/dev/dri` and `/dev/kfd` exist and are group-accessible before touching containers.

## Headless or not?

Leaning **headless + Tailscale**, driven from the laptop, with a desktop session available but not the primary interface. Keeps the memory pool for models instead of a compositor. Decide before Phase 2 — it changes the GTT headroom math.

# Phase 2 — Memory topology

The highest-leverage configuration on this machine. Three interacting knobs.

## GTT sizing

GTT is how much of the shared pool the iGPU may address. Two ways to set it; use one, not both:

```
# module option — /etc/modprobe.d/amdgpu_llm_optimized.conf
options ttm pages_limit=29360128
```

```
# or boot params, alongside the IOMMU disable
amd_iommu=off amdgpu.gttsize=126976 ttm.pages_limit=32505856
```

The arithmetic, because the units differ and every guide quotes a different total:

- `ttm.pages_limit` is in **4 KiB pages** → `pages = GiB × 262144`
- `amdgpu.gttsize` is in **MiB** → `MiB = GiB × 1024`

So on 128 GB:

| Reserve for GPU | `ttm.pages_limit` | `amdgpu.gttsize` | OS headroom |
|---|---|---|---|
| 112 GiB | 29360128 | 114688 | ~16 GiB |
| 124 GiB | 32505856 | 126976 | ~4 GiB |

Start at **112 GiB**. The 124 GiB figure comes from Fedora appliance-style setups; 4 GiB of headroom on a machine that's also my dev box (browser, LSPs, containers, builds) invites the OOM killer. Tighten later if measurements justify it.

After editing modprobe config: `sudo mkinitcpio -P`.

## ZRAM

CachyOS ships aggressive ZRAM defaults that fight the GTT setup — under memory pressure the kernel will happily compress model weights into swap, which is catastrophic for throughput. Shrink it and de-prioritise it:

```
# /usr/lib/systemd/zram-generator.conf.d/10-zram-override.conf
[zram0]
compression-algorithm = zstd lz4 (type=huge)
zram-size = ram / 8
swap-priority = 100
fs-type = swap
```

## Swappiness

CachyOS's udev rule sets a high `vm.swappiness` when ZRAM comes up. Copy it to `/etc/udev/rules.d/99-zram.rules` (higher precedence) and drop swappiness to `10`, so swap is a pressure-relief valve rather than a routine destination.

> [!warning] CachyOS overwrites files it manages during updates. Anything in `/usr/lib` is system-owned — prefer the `/etc` equivalent where one exists, and treat the `/usr/lib` drop-in above as needing a post-update `chezmoi apply` to survive. The verification task in Phase 6 exists to catch exactly this drift.

## Verify

```bash
rocm-smi --showmeminfo all      # GTT heap should report ~112 GiB
vulkaninfo | grep -i heap
```

# Phase 3 — Inference runtime

## llama.cpp toolboxes

The toolboxes are Fedora-based and documented for Fedora's `toolbox`; on Arch/CachyOS use `distrobox` over `podman`. Variants:

| Tag | Notes |
|---|---|
| `vulkan-radv` | Most compatible. **Start here.** |
| `vulkan-amdvlk` | Fastest Vulkan, but a 2 GiB buffer limit — rules out big single tensors |
| `rocm-7.14` | Current ROCm line (Fedora 44 base) |
| `rocm-6.4.4` | Older, occasionally more stable |

```bash
distrobox create -n llama-vulkan-radv \
  --image docker.io/kyuz0/amd-strix-halo-toolboxes:vulkan-radv \
  --additional-flags "--device /dev/dri --group-add video --security-opt seccomp=unconfined"

distrobox create -n llama-rocm \
  --image docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-7.14 \
  --additional-flags "--device /dev/dri --device /dev/kfd --group-add video --group-add render --security-opt seccomp=unconfined"
```

Two flags are **required** on gfx1151 or llama.cpp crashes — `-fa 1` (flash attention) and `--no-mmap`:

```bash
llama-server -m <model> -c 8192 -ngl 999 -fa 1 --no-mmap
llama-cli --list-devices     # confirm the iGPU is actually visible
```

`--no-mmap` is not a tuning preference here — with unified memory, mmap'd weights and GTT interact badly. Bake both into every launch config so I can't forget.

The repo also ships `gguf-vram-estimator.py` (context-aware footprint estimates — useful for deciding what actually fits) and `refresh-toolboxes.sh`.

## vLLM (later)

[`kyuz0/amd-strix-halo-vllm-toolboxes`](https://github.com/kyuz0/amd-strix-halo-vllm-toolboxes) — `kyuz0/vllm-therock-gfx1151:latest`, Ubuntu 24.04 + ROCm 7.14 + stable vLLM, with a `start-vllm` TUI that handles launch flags. Worth it for continuous batching and serving AWQ 4-bit models; overkill for single-user interactive work. **Phase 3b at the earliest** — get llama.cpp solid first.

## Model storage

Models on a dedicated dataset/subvolume, `HF_HOME` pointed at it, excluded from backups (re-downloadable). Toolboxes share `$HOME`, so one cache serves every backend — worth getting right early to avoid three copies of a 70 GB model.

# Phase 4 — Serving layer

The dev box shouldn't care which backend is running. Target: one stable endpoint on the tailnet.

- **Model routing** — `llama-swap` in front of `llama-server` to load/unload models on demand by name. Without it, switching models means restarting things by hand, which kills the "AI-first" premise.
- **Lifecycle** — user-level systemd units generated by `distrobox generate-entrypoint`, so the stack survives reboots. Not root services; keep it in the user session.
- **Exposure** — bind to the tailnet interface only, never `0.0.0.0`. If a firewall rule opening a port ever feels necessary, that's the signal I've mis-scoped the interface binding.
- **Consumers** — editor/agent config, MCP servers ([[ai_workspace|AI workspace]]), and cluster workloads all point at the one endpoint.

# Phase 5 — Dev box layer

The part that makes it a *development* machine and not an appliance:

- **mise** — language runtimes and CLI tools, per-project and global.
- **chezmoi** — shell, editor, git, agent harness configs, shared with my other machines.
- Agent harnesses configured against both hosted models and the local endpoint, so I can switch by env var.
- Container tooling for actual project work — note this competes with the model pool for memory. Budget for it in the Phase 2 headroom.

# Automation & replicability

The interesting design problem: **chezmoi owns `$HOME`, but the highest-value config on this machine lives in `/etc`, `/usr/lib` and the BIOS.** Split by layer:

| Layer | Owner | Mechanism |
|---|---|---|
| BIOS/firmware | Me, manually | Documented in Phase 0. Unavoidable. |
| `/etc`, `/usr/lib` (GTT, zram, udev) | chezmoi → sudo scripts | `run_onchange_before_` scripts |
| Toolbox containers | mise tasks | Idempotent create/refresh |
| systemd user units | chezmoi | Plain files under `~/.config/systemd/user/` |
| `$HOME` dotfiles | chezmoi | Normal chezmoi |
| Runtimes & CLI tools | mise | `mise.toml` |

## chezmoi

Keep the system files as `.chezmoitemplates/` content and install them from `.chezmoiscripts/run_onchange_before_*.sh.tmpl`. The trick that makes it correct: embed a hash of the template in a comment so chezmoi reruns the script when — and only when — the content changes.

```
# .chezmoiscripts/run_onchange_before_10-amdgpu-memory.sh.tmpl
# template hash: {{ include ".chezmoitemplates/etc/modprobe.d/amdgpu_llm_optimized.conf" | sha256sum }}
```

Gate all of it on the host so my laptop never tries to set GTT parameters:

```
{{ if eq .chezmoi.hostname "<strix-host>" }}
```

Put the GiB→pages arithmetic in `.chezmoidata.yaml` as a single `gpu_reserve_gib` value and template both `ttm.pages_limit` and `amdgpu.gttsize` from it. One number to change, no chance of the two knobs disagreeing — which is a genuinely easy mistake to make by hand.

Also worth having: a `.chezmoiexternal.toml` entry for the toolbox repo's helper scripts, so `gguf-vram-estimator.py` and `refresh-toolboxes.sh` come along without vendoring them.

The `/etc` scripts need `sudo`, so this is an interactive `chezmoi apply`, not something to run from a cron job.

## mise

A `mise.toml` in the dotfiles repo with tasks as the operational interface:

| Task | Does |
|---|---|
| `bootstrap` | Host packages, groups, podman — the fresh-install path |
| `toolbox:create` | Create/refresh all toolbox containers idempotently |
| `serve` | Start/reload the llama-swap + llama-server units |
| `bench` | Run `llama-bench` across backends, write results to a dated file |
| `verify` | Assert the invariants below and exit non-zero on drift |

`verify` is the one that earns its keep. Post-kernel-update or post-CachyOS-update, it answers "is this machine still configured the way I think it is?" without me remembering five commands.

## Acceptance checks

`mise run verify` should assert:

- Kernel ≥ 6.18.9; `linux-firmware` is not the known-bad build
- GTT heap ≈ configured `gpu_reserve_gib` (`rocm-smi --showmeminfo all`)
- `vm.swappiness == 10`; ZRAM size ≈ RAM/8
- `amd_iommu=off` present in `/proc/cmdline`
- `llama-cli --list-devices` inside each toolbox reports the iGPU, not CPU-only
- The endpoint answers a trivial completion over the tailnet
- Recorded `llama-bench` tok/s within tolerance of the last-known-good baseline

That last one is the real regression detector. Everything can look healthy while inference has silently fallen back to CPU — a throughput baseline catches what boolean checks can't.

# Relationship to the k8s cluster

**Recommendation: keep this node out of the cluster.** Scheduling against a unified memory pool means the GPU "device" and node memory are the same resource, which the standard AMD device plugin doesn't model — I'd be fighting the scheduler to protect the model's memory. Meanwhile all the benefit (cluster workloads using local inference) is available by just exposing an endpoint.

Revisit if I ever add a second Strix Halo box and want scheduled multi-node inference — the toolbox repo ships `run_distributed_llama.py` for SSH-based multi-node, which would be the cheaper experiment first.

# Open questions

- Headless vs desktop session (Phase 1) — gates the GTT headroom number.
- Is 112 GiB right, or does my actual dev workload push it to 104?
- Does ROCm's long-context prompt-processing advantage matter for how I actually work, or is `vulkan-radv` sufficient permanently?
- NPU (`amd-xdna`) — currently a curiosity, not a workload. Anything real to do with it?
- Does the vLLM toolbox belong here at all, given single-user usage?

# Media

# References

- [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes) — llama.cpp toolboxes for gfx1151 ([benchmarks](https://kyuz0.github.io/amd-strix-halo-toolboxes/))
- [kyuz0/amd-strix-halo-vllm-toolboxes](https://github.com/kyuz0/amd-strix-halo-vllm-toolboxes) — vLLM on gfx1151
- [Configuring CachyOS for LLMs on Strix Halo](https://brian.th3rogers.com/posts/strixhalo-cachyos/) — the closest match to this setup
- [Building a LLM server based on CachyOS and AMD Ryzen AI Max 395](https://codepitbull.medium.com/building-a-llm-server-based-on-cachyos-and-amd-ryzen-ai-max-395-strix-halo-1a2260337a8e) — zram/swappiness specifics
- [Framework-strix-halo-llm-setup](https://github.com/Gygeek/Framework-strix-halo-llm-setup) — BIOS and kernel config
- [Pushing AMD Strix Halo to 120GB Unified VRAM under Linux](https://zyphersystems.com/blog/strix-halo-setup.html)
