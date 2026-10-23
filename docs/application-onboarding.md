# Application onboarding

Applications are registered in this repository via a single catalog file. One pull request to one file onboards an app with its ArgoCD `AppProject`, stable `Application`, and (opt-in) preview `ApplicationSet`.

## Quick start — add your app

Edit [`charts/app-template/catalog.yaml`](../charts/app-template/catalog.yaml):

```yaml
apps:
  - name: my-service
    repo: https://github.com/my-org/my-service.git
    chart: k8s/chart
    registry: ghcr.io/my-org/my-service
```

Open a PR. ArgoCD syncs within seconds of merge.

See [`charts/app-template/README.md`](../charts/app-template/README.md) for the full field reference, preview environment setup (GitHub PRs and GitLab MRs), and annotated examples.

## What gets created

For every catalog entry ArgoCD creates:

| Resource | Scope |
| --- | --- |
| `AppProject/<name>` | Scopes the app's source repo and destination namespaces |
| `Application/<name>` | Deploys the stable branch to the `<name>` namespace |
| `ApplicationSet/<name>-preview` | *(opt-in)* One ephemeral Application per open PR/MR |

The platform `AppProject` (`platform`) is the only project that can manage these resources. No direct edits to the `argocd` namespace are needed.

## How it works

The `platform-apps` ArgoCD Application renders `charts/app-template` with `catalog.yaml` as its values file. Every merged catalog change immediately triggers a sync:

```text
Git push → ArgoCD detects change → renders charts/app-template + catalog.yaml
         → creates/updates AppProject + Application + ApplicationSet
```

The chart lives at `charts/app-template/`. `catalog.yaml` is co-located so ArgoCD can load it as a Helm values file without multi-source configuration.

## Preview environments

Preview environments are **opt-in**. To activate them, add a `preview` block to your catalog entry and label the PR/MR with **`preview`**.

```yaml
# GitHub PR previews
- name: my-service
  ...
  preview:
    github: {}            # owner/repo extracted from the repo URL

# GitLab MR previews (gitlab.com)
- name: my-service
  ...
  preview:
    gitlab:
      projectId: "12345678"

# Self-hosted GitLab
- name: my-service
  ...
  preview:
    gitlab:
      url: https://gitlab.mycompany.com
      projectId: "42"
```

Required secrets (one-time, platform admin):

```sh
# GitHub
kubectl -n argocd create secret generic github-token \
  --from-literal=token=<GITHUB_PAT>     # scopes: repo (read)

# GitLab
kubectl -n argocd create secret generic gitlab-token \
  --from-literal=token=<GITLAB_PAT>     # scopes: api, read_repository
```

## Namespace and RBAC model

- Each app gets a dedicated namespace (`<name>`) and an optional preview namespace (`<name>-preview`).
- The `AppProject` allows only the app's own source repository.
- Cluster-scoped resources are blocked by default (`clusterResourceWhitelist: []`).
- Allowed namespace-scoped kinds: ConfigMap, Secret, Service, ServiceAccount, PVC, Deployment, HPA, PDB, Ingress, NetworkPolicy, HTTPRoute.

To allow additional resource kinds, add `namespaceResourceWhitelist` entries to the Helm chart's `templates/project.yaml`.

## Advanced: manual AppProject / Application

For teams that need finer control than the catalog provides (custom RBAC, multi-source Applications, non-standard destinations), the manual pattern is still supported:

- `examples/onboarding/team-platform.yaml` — platform-side setup reference
- `examples/onboarding/application.yaml` — Application registration reference

Manual resources belong in `infrastructure/configs/<environment>/` so they are deployed by the `infra-configs` Flux Kustomization before any ArgoCD sync runs.

## Ownership boundary

Flux owns this repository and the ArgoCD controller. ArgoCD owns the objects rendered by `platform-apps`. Do not configure both controllers to reconcile the same workload resource.

Removing a catalog entry prunes the `Application` and its workloads (automated prune is on). Decommission applications deliberately, including persistent data and external resources.
