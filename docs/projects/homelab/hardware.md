Below is a list of hardware used in my current home lab set up.

| Components                  | Qty | Cost (CAD) |
|-----------------------------|-----|------------|
| Rack     | | |
| 18U open frame rack         | 1   | 287.87     |
| 12 outlet PDU               | 1   | 52.69      |
| 1U rack shelf               | 1   | 49.71      |
| RGB lightstrip              | 1   | 22.59      |
| Compute — Kubernetes     | | |
| Beelink Mini S12 (Intel N100) | 3 | 288.38 ea |
| GMKtec (Intel N100)         | 2   |            |
| BosGame E2 (Ryzen 5 3550H)  | 2   |            |
| Compute — AI     | | |
| BosGame M5 (Ryzen AI Max+ 395) | 1 |          |
| Networking     | | |
| 24 port gigabit switch      | 1   | 101.69     |
| Modular 24-port patch panel | 1   | 28.24      |
| Cat6 keystone               | 25  | 31.63      |
| Total Cost (WIP)            |     | 1439.56*   |
| Upcoming | | |
| POE Switch | | |
| Rack mountable UPS | | |
| Rack mountable PC cases | | |

\* Partial. Assumes all three Beelinks were the 288.38 unit price; the GMKtec, BosGame E2 and BosGame M5 costs still need filling in.

The seven N100/3550H nodes form the [[k8s_cluster|Kubernetes cluster]]. The BosGame M5 is standalone — it hosts local inference rather than joining the cluster, for the reasons in [[strix_halo_ai_box|Strix Halo AI box]].

# Compute capacity

| Node | Host | Qty | CPU | Cores/node | Threads/node | Cores | Threads | RAM/node | RAM |
|---|---|---|---|---|---|---|---|---|---|
| Beelink Mini S12 | | 3 | Intel N100 | 4 | 4 | 12 | 12 | 16 GB | 48 GB |
| GMKtec | | 2 | Intel N100 | 4 | 4 | 8 | 8 | 8 GB | 16 GB |
| BosGame E2 | | 2 | Ryzen 5 3550H | 4 | 8 | 8 | 16 | 16 GB | 32 GB |
| **Kubernetes total** | | **7** | | | | **28** | **36** | | **96 GB** |
| BosGame M5 | `mentat` | 1 | Ryzen AI Max+ 395 | 16 | 32 | 16 | 32 | 128 GB | 128 GB |
| **AI total** | | **1** | | | | **16** | **32** | | **128 GB** |
| **Homelab total** | | **8** | | | | **44** | **68** | | **224 GB** |

Two things fall out of this:

**The AI node outweighs the entire cluster.** One machine holds 128 GB against the cluster's combined 96 GB, plus 36% of the lab's cores and nearly half its threads. That asymmetry is the justification for keeping it out of the cluster — a scheduler would see one node it could never fill and seven it could, and the unified memory pool it needs isn't schedulable anyway.

**The N100s are SMT-less.** All four cores are efficiency cores with no hyperthreading, so the cluster's 28 cores yield only 36 threads — the extra 8 come entirely from the two 3550H nodes. Worth remembering when setting CPU requests: there's less thread headroom than the core count suggests.

**The two GMKtec nodes are the memory floor** at 8 GB each. On a 7-node cluster that's where memory-hungry pods will get evicted first; probably worth either upgrading those SODIMMs or tainting them for lightweight workloads.

> [!todo] Cluster hostnames still unassigned. `mentat` opens a Dune naming theme if I want one for the seven cluster nodes — plenty of material for control-plane vs worker roles.

![Server rack](../../diagrams/homelab_hardware.drawio)

![[../../diagrams/homelab_hardware.drawio]]