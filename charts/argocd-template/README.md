# ArgoCD Application Template

This Helm chart is the **single onboarding path** for registering applications to be deployed via the ArgoCD controller. Add one entry to [catalog.yaml](./catalog.yaml) and open a pull request — you're done.

## Overview

ArgoCD renders this chart and creates, for every entry:

| Resource | Purpose |
|---|---|
| `AppProject` | Scopes the app's source repo and authorized deployment namespaces |
| `Application` | Stable deployment of the application from the specified Git branch |
| `ApplicationSet` *(opt-in)* | Automatic preview environments per GitHub PR or GitLab MR |

---

## Quick Start

### 1. Add your app to `catalog.yaml`

```yaml
# charts/argocd-template/catalog.yaml
apps:
  - name: my-service                                  # lowercase, hyphens OK
    repo: https://github.com/org/my-service.git      # full HTTPS clone URL
    chart: k8s/chart                                  # path to Helm chart in repo
    registry: ghcr.io/org/my-service                 # image repo without tag
```

### 2. Optionally enable preview environments

```yaml
apps:
  - name: my-service
    repo: https://github.com/org/my-service.git
    chart: k8s/chart
    registry: ghcr.io/org/my-service
    preview:
      github: {}  # Enable GitHub PR previews
```

### 3. Open a pull request

That's it. ArgoCD will pick up the change within seconds of merge.

---

## Fields Reference

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | ✅ | — | App name. Lowercase letters, digits, hyphens. Becomes the AppProject name and stable deployment namespace. |
| `repo` | ✅ | — | Full HTTPS clone URL of the application repository, including `.git`. |
| `chart` | ✅ | — | Path to the Helm chart directory inside `repo` (e.g. `k8s/chart`). |
| `registry` | ✅ | — | Container image repository without tag (e.g. `ghcr.io/org/app`). Passed as `image.repository` to the chart. |
| `targetRevision` | — | `main` | Git ref for stable deployment. Override when your default branch isn't `main`. |
| `extraHelmParameters` | — | `[]` | Additional Helm parameters forwarded to the stable Application. |
| `preview` | — | *(omit)* | Preview environment config. Omit to disable previews. |
| `preview.github` | — | — | GitHub PR preview config. Owner/repo extracted automatically. |
| `preview.gitlab` | — | — | GitLab MR preview config. Requires `projectId` and optional `url` for self-hosted. |
| `preview.namespace` | — | `<name>-preview` | Override the preview namespace. |
| `preview.enabled` | — | `true` | Set `false` to temporarily disable previews without removing the block. |

---

## Examples

### Minimal app (stable only, no previews)

```yaml
apps:
  - name: web-app
    repo: https://github.com/org/web-app.git
    chart: k8s
    registry: ghcr.io/org/web-app
```

### App with GitHub PR previews

```yaml
apps:
  - name: api
    repo: https://github.com/org/api.git
    chart: helm
    registry: ghcr.io/org/api
    targetRevision: develop
    preview:
      github: {}
```

### App with GitLab MR previews (self-hosted)

```yaml
apps:
  - name: backend
    repo: https://gitlab.internal.example/org/backend.git
    chart: k8s/helm
    registry: registry.internal.example/org/backend
    preview:
      gitlab:
        projectId: 123
        url: https://gitlab.internal.example
```

### App with custom Helm parameters

```yaml
apps:
  - name: worker
    repo: https://github.com/org/worker.git
    chart: charts/worker
    registry: ghcr.io/org/worker
    extraHelmParameters:
      - name: env
        value: production
      - name: replicas
        value: "3"
    preview:
      github: {}
      namespace: worker-staging
```

---

## Prerequisites

1. **ArgoCD** installed and running in the `argocd` namespace.
2. **Git credentials** — Secrets in the `argocd` namespace:
   - `github-token`: GitHub PAT with `repo` scope
   - `gitlab-token`: GitLab PAT with `api` scope

Create them with:

```bash
kubectl -n argocd create secret generic github-token \
  --from-literal=token=<GITHUB_PAT>

kubectl -n argocd create secret generic gitlab-token \
  --from-literal=token=<GITLAB_PAT>
```

---

## How It Works

1. **Cluster entry** renders `argocd-template` with your catalog
2. Each app receives an `AppProject` authorizing its repository and namespaces
3. An `Application` is created for stable deployments (e.g., from `main` branch)
4. (Optional) An `ApplicationSet` generator watches GitHub/GitLab for PRs/MRs
5. Preview ApplicationSets auto-create temporary environments per PR/MR, cleaned up when the PR closes

---

## Sync Behavior

All Applications use:
- **Automated sync** with `prune: true` and `selfHeal: true`
- **Server-side apply** for CRD-safe deployments
- **Namespace auto-creation** via `CreateNamespace=true`
- **CRD schema validation** override for stability

Customize defaults in `values.yaml` under `defaults.syncOptions`.

---

## Frequently Asked Questions

**Q: Can I use different Helm charts for stable and preview?**  
A: Not with this template—stable and preview deploy the same chart. Use `extraHelmParameters` to pass different values.

**Q: What if my Git repository isn't on GitHub or GitLab.com?**  
A: GitLab preview supports self-hosted via `preview.gitlab.url`. GitHub only works with github.com; self-hosted GitHub Enterprise is not supported by ApplicationSet generators.

**Q: How do I disable previews for a single app?**  
A: Set `preview.enabled: false` in that app's entry.

**Q: Can preview namespaces use different configurations?**  
A: Yes, via `extraHelmParameters` and conditional logic in your Helm chart.

---

## Related

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [ApplicationSet](https://argo-cd.readthedocs.io/en/latest/features/application-set/)
- [Flux Platform Seed Architecture](../../../README.md)
