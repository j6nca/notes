# Setting up Kestra for GitOps

Kestra has various options that allow us to keep workloads in sync via git version management. This provides us with flexibility on how we want to keep changes in Kestra synced and up-to-date.

- [git.PushFlows](https://kestra.io/plugins/plugin-git/io.kestra.plugin.git.PushFlows)
- [git.SyncFlows](https://kestra.io/plugins/plugin-git/io.kestra.plugin.git.syncflows)
- [GitHub Actions]()

![Kestra sync strategy summary](https://kestra.io/docs/developer-guide/git/git.png)

## Bootstrapping

## Change Management

Since we are using the open-source offering of Kestra, only basic auth is supported. Because of this limitation, everyone with access to the UI effectively has the same amount of permissions. This can cause a lot of potential issues, which we hope adopting a gitops approach will help mitigate.

- Limit permissions from UI access to regulate changes better and enforce them through git
- Workflow changes gated via git PR merges
- 