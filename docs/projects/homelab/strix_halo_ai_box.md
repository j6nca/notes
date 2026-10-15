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
> Same caveat as [[ai stack|AI workspace]] — the gfx1151 software stack (ROCm, llama.cpp, ComfyUI/PyTorch) moves week to week. Treat every version number below as a snapshot, not a pin. The point of codifying this in a git repo is so churn is cheap.

# Goal

`mentat` is a **headless inference appliance**. Not a dev box: nothing is developed on it, and no toolchain lives on it beyond what serves a model. It runs exactly two workloads, both as containerised toolboxes:

1. **llama.cpp** — LLM serving over an OpenAI-compatible endpoint, several models available at once, consumed by my editor, agent harnesses, MCP servers ([[ai stack|AI workspace]]) and workloads in the [[k8s_cluster|Kubernetes cluster]].
2. **ComfyUI** — image and video generation (Flux, Qwen Image, Wan 2.2, HunyuanVideo).

Everything else is in service of those two sharing one memory pool without stepping on each other. Non-goal: joining the cluster — see [Relationship to the k8s cluster](#relationship-to-the-k8s-cluster).

# Hardware

**BosGame M5**, hostname **`mentat`** — AMD Ryzen AI Max+ 395 (Zen 5) with an integrated Radeon 8060S (RDNA 3.5, **gfx1151**) and an XDNA 2 NPU, 128 GB on a **unified memory** architecture: CPU and iGPU share one LPDDR5X pool at ~256 GB/s theoretical. Listed under Compute — AI in [[hardware|homelab hardware]]; the only node there that isn't part of the [[k8s_cluster|Kubernetes cluster]].

The unified memory pool is the whole reason this machine is interesting and also the source of nearly every configuration gotcha below. There is no discrete VRAM to allocate; there's one pool, and the job is convincing the kernel to let the GPU address most of it — then dividing it between workloads.

# Design decisions

**Ubuntu Server 26.04 LTS, headless, appliance-only.** No display stack, no language runtimes, no editors. Every GiB and every watt goes to inference. The LTS kernel also solves the problem that made a rolling distro attractive in the first place; see Phase 1.

**Containers are the GPU runtime boundary.** Distro-packaged ROCm lags badly for gfx1151 — AMD's own matrix only lists ROCm 6.4.4 for the AI Max+ 395, while the useful llama.cpp and PyTorch builds track 7.x. Rather than hand-rolling TheRock nightlies into `/opt`, [kyuz0](https://github.com/kyuz0) publishes matched toolboxes for [llama.cpp](https://github.com/kyuz0/amd-strix-halo-toolboxes) and [ComfyUI](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes) on gfx1151. The host stays minimal (kernel + `amdgpu` + podman), and swapping backends is `distrobox create`, not a reinstall.

This decision does most of the work of the appliance framing: **ComfyUI's entire Python/PyTorch/ROCm stack lives inside its container**, so the host never grows a Python environment. That's the single biggest reason not to install a dev toolchain here — the workloads bring their own.

**Vulkan first for LLMs, ROCm when measured.** RADV needs no extra host setup and is competitive with (sometimes better than) ROCm for token generation at normal context lengths. ROCm's win is prompt processing on long inputs. ComfyUI has no such choice: it's ROCm-only.

## llama.cpp router mode, not vLLM

Worth recording properly, because vLLM's reputation as *the* serving engine makes this look like the wrong call:

| | llama.cpp router mode | vLLM |
|---|---|---|
| Single-stream on gfx1151 | ~48–80 tok/s | ~20 tok/s |
| Models per process | many, load-on-demand | one |
| Idle memory | model + KV unloaded on idle | KV cache pre-allocated, held |
| New-release quants | GGUF, hours | AWQ/GPTQ, weeks or never |

vLLM's headline 162–181 tok/s on this hardware is *aggregate* throughput at 64 concurrent sequences; its own benchmark output warns that isn't single-request speed. For one user, it's a ~3× latency regression.

The architectural mismatch matters more than the benchmark. vLLM's parallelism is **request** parallelism against one model. My requirement is the other axis — *many models, one user* — and running several in vLLM means several processes, each statically pre-allocating a `gpu_memory_utilization` slice, hand-tuned to sum under 1.0, with no eviction. That directly breaks the ComfyUI coexistence this design depends on (Phase 4).

**Revisit if** this ever serves a team, or an agent swarm starts fanning out many parallel requests. Even then the move is adding vLLM as a *third* toolbox for one pinned model, not routing the general endpoint through it. Intermediate option first: `llama-server --parallel N` gives shared-KV batching on a single model without leaving llama.cpp.

**The host is disposable, the config is not.** Everything below should be reachable from a fresh Ubuntu Server install by `git clone` + `make`. See [Automation](#automation--replicability).

# Phase 0 — Firmware & BIOS

Do this first; it's the part no amount of config management can automate.

- **UMA Frame Buffer Size → 512 MB** (or the vendor minimum, sometimes 2 GB). Counterintuitive but correct: the BIOS carveout is GPU-*exclusive* and wasted. Setting it low forces the iGPU to source memory from GTT instead, which is the large, dynamically shared pool.
  - Path: `Advanced → AMD CBS → NBIO Common Options → GFX Configuration`
- **IOMMU → Disabled** — worth ~6–7% memory bandwidth (~234 vs ~221 GB/s reported) and a similar prompt-processing gain. Headless with no VFIO passthrough makes this free.
  - Path: `Advanced → AMD CBS → NBIO Common Options → IOMMU`
- Update BIOS/EC to latest before benchmarking anything. Early Strix Halo firmware had memory-clock and power-limit bugs.
- Record the final BIOS revision and settings here — the one piece of state that lives outside git.

# Phase 1 — Base OS

**Ubuntu Server 26.04 LTS.** The kernel floor is the thing to get right, and 26.04 clears it without any work:

| Constraint | Status on 26.04 LTS |
|---|---|
| Kernel ≥ 6.18.9 (older, incl. 6.18.4, has a gfx1151 stability bug) | ✅ ships **Linux 7.0** GA |
| Kernel ≥ 6.14 for `amd-xdna` (NPU) | ✅ |
| Avoid `linux-firmware-20251125` — breaks ROCm on Strix Halo | Check installed version; `apt-mark hold` if needed |

No chasing mainline, no kernel pinning gymnastics, five years of support. The tradeoff is the inverse risk — an **unattended kernel upgrade regressing gfx1151**. Policy: leave `unattended-upgrades` on for security (it's network-reachable), run `make verify` after every reboot, and rely on the throughput baseline to catch a silent regression. Hold `linux-image-*`/`linux-firmware` only in response to an actual known-bad version, with a dated comment — a stale indefinite hold is a worse footgun.

Host packages, deliberately minimal — note what's *absent*:

```
podman crun distrobox          # the GPU runtime boundary — crun is not optional, see Phase 3
mesa-vulkan-drivers            # RADV for llama.cpp's Vulkan backend (works fine headless)
rocm-smi                       # host-side monitoring only, NOT the ROCm SDK
```

No Python, no PyTorch, no ROCm SDK, no compilers, no editors. If something needs those, it belongs in a toolbox.

## Headless appliance

- **More memory for models.** No display stack means the OS headroom in Phase 2 can be tighter than a workstation would allow.
- **Both workloads are web UIs / APIs**, so there's nothing to sit in front of anyway. Administration is SSH.
- **Networking via Netplan**, with Tailscale for reachability. Services bind loopback and are published to the tailnet.
- **systemd *user* units need lingering** — `loginctl enable-linger` — or the stack won't start until I log in. Easy to forget on a headless box; presents as a mysterious post-reboot failure.
- RADV is still required. Vulkan compute works headless; it does not need a display server.

# Phase 2 — Memory topology

The highest-leverage configuration on this machine.

## GTT sizing

GTT is how much of the shared pool the iGPU may address. On Ubuntu, set it via a **`grub.d` drop-in** rather than editing `/etc/default/grub` in place. Ubuntu's `grub-mkconfig` sources `/etc/default/grub.d/*.cfg` after the main file (Ubuntu ships `50-cloudimg-settings.cfg` by exactly this route), so appending is a whole-file write with no `sed`, and a release upgrade that rewrites `/etc/default/grub` can't silently drop the parameters:

```sh
# /etc/default/grub.d/99-mentat-amdgpu.cfg
GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT amd_iommu=off amdgpu.gttsize=122880 ttm.pages_limit=31457280"
```

Then `sudo update-grub` and reboot.

The arithmetic, because the units differ and published guides routinely contradict each other:

- `ttm.pages_limit` is in **4 KiB pages** → `pages = GiB × 262144`
- `amdgpu.gttsize` is in **MiB** → `MiB = GiB × 1024`

| Reserve for GPU | `ttm.pages_limit` | `amdgpu.gttsize` | OS headroom |
|---|---|---|---|
| 112 GiB | 29360128 | 114688 | 16 GiB |
| 116 GiB | 30408704 | 118784 | 12 GiB |
| **120 GiB** | **31457280** | **122880** | **8 GiB** |
| 124 GiB | 32505856 | 126976 | 4 GiB |

**120 GiB.** Dropping the dev-box role is worth a straight 4 GiB over the 116 GiB a machine running builds and LSPs would want. The remaining 8 GiB covers the OS, podman, journald and page cache for streaming multi-GB safetensors off disk. Upstream's ComfyUI toolbox suggests 124 GiB; that's a Fedora single-purpose appliance and leaves 4 GiB, which is thin for a box running two services and reading very large files.

> [!warning] One widely-circulated guide pairs `amdgpu.gttsize=131072` (128 GiB) with `ttm.pages_limit=31457280` (120 GiB) — the two knobs disagree by 8 GiB. This is why the repo derives both from a single `GPU_RESERVE_GIB` instead of copying pairs out of blog posts.

## Swap

Ubuntu Server has **no zram by default**, which removes a whole class of problem. Two things to get right:

- **Do not install `zram-tools`.** Compressing model weights into RAM-backed swap is the worst possible outcome for throughput.
- Keep the installer's swapfile as an OOM pressure valve, but set `vm.swappiness=10`. With 128 GB and a hard GTT ceiling, healthy operation should never touch it — if it does, the GTT reserve is too aggressive.

## Verify

```bash
rocm-smi --showmeminfo all      # GTT heap should report ~120 GiB
vulkaninfo --summary | grep -i heap
```

# Phase 3 — The two toolboxes

## The rootless podman group trap

Read this before copying any `create` command. Under **rootless** podman, `--group-add video` / `--group-add render` are resolved against the *container's* `/etc/group`; the resulting GID lives inside the user namespace and never maps to the host's — so it grants **no access to `/dev/kfd`**. Both upstream READMEs use named groups because Fedora's `toolbox` handles this differently.

The fix is `--group-add keep-groups`, which is crun's `keep_original_groups` and passes the real host supplementary groups through. That is why `crun` is in the Phase 1 package list — with the default runtime this silently fails, and it presents as *"the GPU isn't there"*, not as a permissions error. This applies to **both** toolboxes.

ROCm needs **both** `/dev/kfd` and `/dev/dri`.

## llama.cpp

Upstream maintains a small **stable** set and a long experimental tail. Only the stable two are worth running here:

| Tag | Status | Notes |
|---|---|---|
| `vulkan-radv` | stable | "Most stable and compatible." **This is what serves.** |
| `rocm-10.0` | stable | Fedora 44, AMD's supported gfx1151 package set. Labelled the performance pick — but currently ships a local patch for [llama.cpp #25992](https://github.com/ggml-org/llama.cpp/issues/25992) to stop it selecting ROCm host buffers on an iGPU. Kept for benchmarking, not serving. |
| `vulkan-amdvlk` | — | Fastest Vulkan, but a 2 GiB buffer limit — rules out big single tensors |
| `rocm-7.14`, `-performance`, `-rocmfpx`, `therock-nightly` | experimental | Forks and nightlies. `rocm-7.14` and `rocm-6.4.4` *were* the stable line; they've since been demoted |

The tag churn is the lesson: read the README's stable table, not the Docker Hub tag list, and expect the answer to have moved. Both stable images are rebuilt automatically whenever llama.cpp master updates, so the tag you pinned is not the image you pulled last month — which is why `make refresh` compares digests and why a throughput baseline exists at all.

Two flags are **required** on gfx1151 or llama.cpp crashes — `-fa 1` (flash attention) and `--no-mmap`. With unified memory, mmap'd weights and GTT interact badly. Bake both into every launch config.

The repo also ships `gguf-vram-estimator.py` — context-aware footprint estimates, which is how to check whether a new release fits *alongside* what's already resident.

## ComfyUI

Image `docker.io/kyuz0/amd-strix-halo-comfyui:latest` — a full ROCm 7 environment with PyTorch, ComfyUI and helper scripts in `/opt`. ROCm-only; there's no Vulkan alternative here.

- Launch inside the toolbox via `start_comfy_ui`, which defaults to `--bf16-vae --disable-mmap --cache-none`.
- `--disable-mmap` is the same lesson as llama.cpp's `--no-mmap`, for the same unified-memory reason. `--cache-none` matters for coexistence — see Phase 4.
- Models live in `~/comfy-models`, wired into the container by `/opt/set_extra_paths.sh`. Workflows at `/opt/comfy-workflows`.
- Validated workflows: Qwen Image / Qwen Image Edit, Wan 2.2 (with 4-step Lightning LoRA), HunyuanVideo 1.5, MiniMax-H3.
- Default port 8188.

> [!warning] `start_comfy_ui` is a shell **alias**, so it won't resolve in a non-interactive `distrobox enter -- …` used by a systemd unit. Resolve it to the real script in `/opt` — a unit failing this way looks like a broken container rather than a missing alias.

## Model storage

Two stores, both on a dedicated filesystem and both excluded from backups (re-downloadable): GGUFs for llama.cpp and `~/comfy-models` for ComfyUI. Toolboxes share `$HOME`, so one copy of each serves everything.

# Phase 4 — Coexistence

Three things want the same 120 GiB: a large LLM, a small always-on LLM, and ComfyUI. Everything is evictable, which is what makes this tractable — but with the current generation of models the honest framing is **two of the three at a time**, not all three. The heavy model is simply too large for a comfortable three-way split, and that is a property of where open models have gone, not a flaw in the design.

## Multiple LLMs at once

`llama-server` started with **no model** is itself a router: it holds a catalogue, loads on demand, forwards each request by the `model` field, and unloads on idle. An earlier draft of this page put **llama-swap** in front of it for exactly these features; llama.cpp has since absorbed them, so the extra process no longer earns its place. Two knobs express the "one large, one small" shape:

- `--models-max N` — how many may be resident at once.
- `sleep-idle-seconds`, per model in `models.ini` — `-1` for the always-on tier, a timeout for the heavy one.

The difference from llama-swap is worth being honest about: llama-swap had a *declarative policy* (`persistent: true` guarantees the small model survives any load), whereas sleeping is a per-model *timeout* with no cross-model guarantee. The shapes coincide here because only two tiers exist and `--models-max 2` admits both. If this ever grows to several heavy models competing for one slot, that equivalence breaks and llama-swap's group solver becomes the right tool again.

Keep llama-swap in mind for two other cases it still owns: fronting non-llama.cpp servers (vLLM, whisper.cpp, stable-diffusion.cpp), and routing different models to different *backends* — Vulkan for one, ROCm for another — which router mode cannot do because it is a single process in a single container.

## Against ComfyUI

Both sides release memory when idle, which is what makes co-residency cheap even though co-*execution* isn't:

- `sleep-idle-seconds` on the heavy model — after the timeout llama.cpp unloads **the model and its KV cache**, which on unified memory is what actually returns GTT to the pool. Keep this short (5 min): the heavy model is holding most of the pool, and ComfyUI wants it back.
- `sleep-idle-seconds = -1` on the small model; it's meant to stay.
- ComfyUI's `--cache-none` avoids holding models between runs.
- **`--models-max` caps count, not footprint.** Two heavies would both be admitted and then exhaust the pool. Safe with one small and one heavy; not a guard beyond that. This is the one thing llama-swap's group policy expressed that router mode cannot.

Budget with the models actually chosen (both August 2026, the current generation):

| | Weights | Left of 120 GiB |
|---|---|---|
| `Qwen3.8-27B` UD-Q4_K_M — always resident | 15.3 GiB | 104.7 |
| `Qwen3.8-Flash-Next` UD-IQ3_XXS — sleeps at 5 min | ~76 GiB | **~28 GiB** |

~28 GiB is enough for ComfyUI image workflows and not enough for video. Choosing Flash-Next's quant *is* choosing the coexistence story:

| Flash-Next quant | Size | Consequence |
|---|---|---|
| `UD-Q2_K_XL` / `UD-IQ3_XXS` | 73–76 GiB | coexists with ComfyUI image work |
| `UD-Q3_K_XL` / `UD-IQ4_XS` | 84–87 GiB | tight; ComfyUI effectively excluded |
| `UD-Q4_K_XL` | ~104 GiB | sole occupant |

Low-bit quantization degrades a 512-expert MoE more than a dense model, so this is a quality decision, not just a size one. Test on real prompts rather than picking by arithmetic.

**KV is no longer the thing to fear.** This generation sets `full_attention_interval: 4` — three linear-attention layers with constant state for every one full-attention layer — so a 256k context costs a fraction of what it would on a classic transformer. Weights dominate; context is nearly free. Earlier drafts of this page warned the opposite, which was true of `Qwen3Moe` and no longer applies.

## Serving

- **`llama-server` in router mode**, routing by model name, `--models-max` for concurrency, per-model idle sleep for eviction. Runs *inside* the toolbox — nothing on the host at all.
- **ComfyUI** on 8188, inside its toolbox.
- **Lifecycle** — user-level systemd units plus `loginctl enable-linger` so both survive reboot on a box nobody logs into.
- **Exposure** — bind loopback, publish to the tailnet with `tailscale serve`. Never `0.0.0.0`; if a firewall rule opening a port feels necessary, the interface binding is wrong.
- **Metrics** — `/metrics?model=<id>` for Prometheus, which plugs into [[observability|the observability stack]].

# Automation & replicability

The interesting design problem: **the highest-value config lives in `/etc` and the BIOS, not in a dotfile.** Split by layer:

| Layer | Owner | Mechanism |
|---|---|---|
| BIOS/firmware | Me, manually | Documented in Phase 0. Unavoidable. |
| `/etc` (GRUB cmdline, sysctl) | repo + `make` | Generate → `cmp` → `install`, side effects on change only |
| Toolbox containers | repo + `make` | Idempotent create/refresh |
| systemd user units + linger | repo + `make` | Files copied to `~/.config/systemd/user/` |
| Service config (models, workflows) | repo | Plain INI, no templating needed |
| Model weights | not in git | `bin/models add` → shared HF cache on `/srv` |

An earlier draft of this used chezmoi and mise. Both were dropped: chezmoi's value is managing `$HOME` across *several* machines with templating, and this is one appliance with no dotfiles to speak of; mise was pinning exactly one Go binary and acting as a task runner. A git repo, a `Makefile` and `install(1)` cover the same ground with nothing extra installed — which is Principle 5 (nothing on the host a toolbox could carry) applied to the automation itself.

Ubuntu's `/etc` is unmanaged between releases, so this layer is simpler than on a rolling distro — files stay put and don't get reverted on update. The one thing to watch is a release upgrade rewriting `/etc/default/grub`, which the drop-in above already defends against.

Two rules worth stating once:

- **Derive, don't duplicate.** The GiB→pages/MiB arithmetic is computed from a single `GPU_RESERVE_GIB` in `vars.sh`. One number to change, no chance of the two knobs disagreeing.
- **`verify` is the load-bearing target.** On an LTS with unattended upgrades enabled, post-reboot is exactly when the machine will have changed underneath me. Boolean checks aren't enough on their own: everything can look healthy while inference has silently fallen back to CPU, so a recorded `llama-bench` baseline is the real regression detector.

> [!info] The implementation — every file, script and command — is in [[mentat_provisioning|Provisioning mentat]]. This section stays a statement of intent so the two don't drift.

# Relationship to the k8s cluster

**Recommendation: keep this node out of the cluster.** Scheduling against a unified memory pool means the GPU "device" and node memory are the same resource, which the standard AMD device plugin doesn't model — I'd be fighting the scheduler to protect the model's memory. The capacity table in [[hardware|homelab hardware]] makes the mismatch concrete: this one box holds more RAM than all seven cluster nodes combined, so a scheduler would see one node it could never fill and seven it could. Meanwhile all the benefit (cluster workloads using local inference) is available by just exposing an endpoint.

Revisit if I ever add a second Strix Halo box and want scheduled multi-node inference — the toolbox repo ships `run_distributed_llama.py` for SSH-based multi-node, which would be the cheaper experiment first.

# Open questions

- Is 120 GiB right for an appliance, or does 124 work now that nothing else runs here?
- Does the `persistent` + `ttl` split hold up under real use, or does ComfyUI still get starved when a big model is warm?
- Does ROCm's long-context prompt-processing advantage matter for how I actually use the LLM, or is `vulkan-radv` sufficient permanently?
- IOMMU off — confirm the bandwidth gain on *this* board rather than trusting a reported figure.
- Is `start_comfy_ui` a wrapper around something directly callable from a systemd unit?
- NPU (`amd-xdna`) — currently a curiosity, not a workload.

# Media

# References

- [kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes) — llama.cpp toolboxes for gfx1151 ([benchmarks](https://kyuz0.github.io/amd-strix-halo-toolboxes/))
- [kyuz0/amd-strix-halo-comfyui-toolboxes](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes) — ComfyUI/ROCm toolbox ([benchmarks](https://kyuz0.github.io/amd-strix-halo-comfyui-toolboxes/))
- [Strix Halo AI Toolboxes](https://strix-halo-toolboxes.com/) — index of the whole toolbox family
- [llama-server router mode](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#router-mode) — `--models-preset`, `--models-max`, and [sleep on idle](https://github.com/ggml-org/llama.cpp/pull/18228)
- [llama-swap: groups and swapping policies](https://deepwiki.com/mostlygeek/llama-swap/3.4-groups-and-swapping-policies) — `swap` / `exclusive` / `persistent` semantics; no longer used here, but the reference if several heavy models ever compete for one slot
- [AMD Strix Halo (gfx1151) vLLM benchmarks](https://kyuz0.github.io/amd-strix-halo-vllm-toolboxes/) and [known-good llama.cpp stack](https://github.com/ggml-org/llama.cpp/discussions/20856) — the numbers behind the engine decision
- [Ubuntu 26.04 LTS release notes](https://documentation.ubuntu.com/release-notes/26.04/summary-for-lts-users/) — kernel 7.0 GA
- [How to Run AMD GPU Containers with Podman](https://oneuptime.com/blog/post/2026-03-18-run-amd-gpu-containers-podman/view) — the rootless `keep-groups` trap
- [ROCm issue #5665](https://github.com/ROCm/ROCm/issues/5665) / [#5750](https://github.com/ROCm/ROCm/issues/5750) — known gfx1151 GPU hang and idle-clock bugs. #5665 is specifically AI workloads *plus* video encoding, which is close to running both toolboxes at once
- CachyOS-specific writeups whose *memory math* still transfers: [Brian Rogers](https://brian.th3rogers.com/posts/strixhalo-cachyos/), [Jochen Mader](https://codepitbull.medium.com/building-a-llm-server-based-on-cachyos-and-amd-ryzen-ai-max-395-strix-halo-1a2260337a8e)
