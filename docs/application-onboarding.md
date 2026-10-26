# Application onboarding

This repository provides two independent Helm charts. Choose exactly one chart for each application so ArgoCD and Flux do not reconcile the same workload.

## ArgoCD applications

ArgoCD is disabled by default. Enable it for the target cluster first — see [architecture docs](architecture.md#argocd-is-opt-in) for the three-location opt-in. Once running, register an application in `charts/argocd-template/catalog.yaml`:

```yaml
apps:
  - name: example-api
    repo: https://git.example.invalid/org/example-api.git
    chart: deploy/chart
    registry: registry.example.invalid/org/example-api
    preview:
      github: {}
```

The ArgoCD platform Application renders `charts/argocd-template`. Each entry produces an `AppProject` and stable `Application`; the optional preview block produces an `ApplicationSet` using the configured Git provider generator.

## Flux applications

Register an application in `charts/fluxcd-template/catalog.yaml`:

```yaml
apps:
  - name: example-api
    repo: https://git.example.invalid/org/example-api.git
    chart: deploy/chart
    registry: registry.example.invalid/org/example-api
```

The `fluxcd-application-catalog` HelmRelease renders `charts/fluxcd-template` from the cluster's Flux GitRepository. Each entry produces a hardened namespace, NetworkPolicies, scoped workload RBAC, GitRepository, and HelmRelease.

## Flux GitLab merge-request previews

Flux previews use the Flux Operator ResourceSet API described in the [GitLab merge-request guide](https://fluxoperator.dev/docs/resourcesets/gitlab-merge-requests/). This chart supports GitLab MRs only because the provider is `GitLabMergeRequest`:

```yaml
apps:
  - name: example-api
    repo: https://git.example.invalid/org/example-api.git
    chart: deploy/chart
    registry: registry.example.invalid/org/example-api
    preview:
      gitlab: {}
      domain: preview.example.invalid
```

The chart generates:

- `ResourceSetInputProvider` in `flux-previews`, polling the GitLab project for the `deploy/flux-preview` label.
- `ResourceSet` in `flux-previews`, with one generated namespace, pinned GitRepository, and HelmRelease per matching MR.
- Preview RBAC and Pod Security labels.
- A separate clone credential reference from the read-only GitLab API credential.

The generated GitRepository is pinned to the MR commit SHA, preventing branch movement during a preview. ResourceSet garbage collection removes generated resources when an MR no longer matches the provider. A Flux `Receiver` can be added separately for lower event latency; polling remains the safe default.

GitHub preview generation is not implemented by this Flux chart. Use the ArgoCD chart for GitHub PR ApplicationSet previews, or add a separately reviewed Flux provider integration.

## Credentials and trust boundary

Create these secrets outside Helm values:

- API credential in `flux-previews`, with `username` and read-only `password`, for MR discovery.
- Git clone credential in `flux-system`, with read-only repository access, for generated GitRepositories.

### Preview namespace layout

Each MR gets its own namespace (`<app>-<mr-id>`). The per-MR `HelmRelease` and its Helm release storage (`storageNamespace`) both live in that namespace. The `GitRepository` lives in `flux-system` so it can reference the clone credential Secret there via `secretRef`.

This layout avoids the following RBAC error, which occurs when `storageNamespace` is set to `flux-system` but the preview ServiceAccount only has access to the per-MR namespace:

```
Could not determine release state: failed to retrieve last release from storage:
secrets is forbidden: User "system:serviceaccount:flux-system:helm-preview-<app>"
cannot list resource "secrets" in API group "" in the namespace "flux-system"
```

The root cause: Helm stores its release state as `Secret` objects in `storageNamespace`. The `helm-preview-<app>` ServiceAccount is scoped to the per-MR namespace via a `Role` + `RoleBinding` — it has no access to `flux-system` Secrets. Moving `storageNamespace` to the per-MR namespace resolves it.

MR previews execute chart and workload content from the MR. Enable them only for trusted repositories and review the generated RBAC and admission policies before allowing external contributors.

## Validation

```sh
helm unittest charts/argocd-template charts/fluxcd-template
helm template argocd-template charts/argocd-template -f charts/argocd-template/catalog.yaml
helm template fluxcd-template charts/fluxcd-template -f charts/fluxcd-template/values.yaml -f charts/fluxcd-template/catalog.yaml
python scripts/validate.py
python scripts/validate_schemas.py --operator-version 0.61.0
```

See the chart READMEs for complete field references and controller-specific options.
