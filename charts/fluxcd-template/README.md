# FluxCD Application Template

This Helm chart is the **single onboarding path** for registering applications to be deployed via the Flux controllers (HelmRelease + Kustomization). Add one entry to [catalog.yaml](./catalog.yaml) and open a pull request — you're done.

## Overview

This chart renders Flux-native resources and creates, for every entry:

| Resource | Purpose |
|---|---|
| `GitRepository` | Tracks the application repository for changes |
| `HelmRelease` | Stable Helm deployment of the application |
| `Kustomization` | Alternative: declarative Kustomize-based deployments |
| `ResourceSet` *(opt-in)* | Automatic preview environments per GitHub PR or GitLab MR using Flux operators |

---

## Quick Start

### 1. Add your app to `catalog.yaml`

```yaml
# charts/fluxcd-template/catalog.yaml
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
      github: {}  # Enable GitHub PR previews via Flux ResourceSets
```

### 3. Open a pull request

That's it. Flux will pick up the change within the reconciliation interval.

---

## Fields Reference

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | ✅ | — | App name. Lowercase letters, digits, hyphens. Becomes resource names. |
| `repo` | ✅ | — | Full HTTPS clone URL of the application repository, including `.git`. |
| `chart` | ✅ | — | Path to Helm chart or Kustomize base inside `repo` (e.g. `k8s/chart`). |
| `registry` | ✅ | — | Container image repository without tag (e.g. `ghcr.io/org/app`). |
| `namespace` | — | `flux-system` | Namespace where HelmRelease and Kustomization run. |
| `targetRevision` | — | `main` | Git branch/tag for stable deployment. |
| `interval` | — | `1m` | Reconciliation interval for HelmRelease and Kustomization. |
| `preview` | — | *(omit)* | Preview environment config via Flux ResourceSets. Omit to disable. |
| `preview.github` | — | — | GitHub PR preview config. Owner/repo extracted automatically. |
| `preview.gitlab` | — | — | GitLab MR preview config. Requires `projectId` and optional `url`. |
| `preview.namespace` | — | `flux-system` | Namespace where preview resources are created. |
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

---

## Prerequisites

1. **Flux Operator** installed (FluxInstance controls distribution)
2. **Git credentials** — Secrets in the Flux namespace (default: `flux-system`):
   - `github-credentials`: GitHub username + PAT (repo scope)
   - `gitlab-credentials`: GitLab username + PAT (api scope)

Create them with:

```bash
kubectl -n flux-system create secret generic github-credentials \
  --from-literal=username=<USERNAME> \
  --from-literal=password=<GITHUB_PAT>

kubectl -n flux-system create secret generic gitlab-credentials \
  --from-literal=username=<USERNAME> \
  --from-literal=password=<GITLAB_PAT>
```

---

## How It Works

### Stable Deployments

1. **Cluster entry** renders `fluxcd-template` with your catalog
2. Each app gets a `GitRepository` resource watching the application repo
3. A `HelmRelease` or `Kustomization` deploys the stable branch
4. Flux controllers reconcile every `interval` (default: 1 minute)

### Preview Environments (ResourceSets)

ResourceSets are Flux Operator constructs that automatically generate preview environments for pull/merge requests:

1. When a PR/MR is opened with a `preview` label, Flux detects it via Git webhooks
2. A new set of resources is instantiated from the ResourceSet template
3. The preview namespace/release name includes the PR/MR number and branch name
4. When the PR/MR closes, resources are automatically cleaned up

**Key advantage over ArgoCD ApplicationSet:** ResourceSet templates are simpler, Git-native, and work seamlessly with GitLab self-hosted.

---

## Sync Behavior

- **HelmRelease**: Reconciles every `interval` (default: 1m), with `retryInterval` (default: 1m)
- **Kustomization**: Same intervals, with automatic health checks for Deployments
- **Prune**: Enabled by default to remove orphaned resources
- **Wait**: Disabled by default (preview: customize per environment)

---

## Frequently Asked Questions

**Q: Should I use HelmRelease or Kustomization?**  
A: Use `HelmRelease` for Helm-packaged applications. Use `Kustomization` if you manage overlays with Kustomize. Both are included; choose based on your chart organization.

**Q: What's the difference between ResourceSet and ApplicationSet?**  
A: ResourceSet is native to Flux and Git-aware. It watches Git refs directly (e.g., `refs/merge-requests/*/head` for GitLab). ApplicationSet uses external API polling. ResourceSets are cleaner for self-hosted GitLab.

**Q: How do I customize preview behavior?**  
A: Edit `defaults.preview` in `values.yaml` to adjust intervals, timeouts, and labels. Per-app overrides are supported via preview fields.

**Q: Can preview namespaces use different configurations?**  
A: Yes, via Kustomize post-renderers and values substitution in the Kustomization template.

**Q: How do I rotate Git credentials?**  
A: Update the secrets in the flux-system namespace. Flux will re-authenticate on the next reconciliation.

---

## Monitoring and Debugging

Check ResourceSet status:

```bash
kubectl -n flux-system get resourcesets
kubectl -n flux-system describe resourceset <name>-preview
```

Check HelmRelease status:

```bash
kubectl -n flux-system get helmrelease
kubectl -n flux-system describe helmrelease <name>
flux get helmrelease -n flux-system
```

Check Kustomization status:

```bash
kubectl -n flux-system get kustomization
flux get kustomization -n flux-system
```

View reconciliation logs:

```bash
flux logs --follow --all-namespaces
```

---

## Related

- [Flux Operator Documentation](https://fluxcd.io/flux/)
- [ResourceSets for GitLab](https://fluxoperator.dev/docs/resourcesets/gitlab-merge-requests/)
- [HelmRelease API](https://fluxcd.io/flux/components/helm/api/)
- [Kustomization API](https://fluxcd.io/flux/components/kustomize/api/)
- [Flux Platform Seed Architecture](../../../README.md)
