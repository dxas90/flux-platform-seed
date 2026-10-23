# App Template Chart

This Helm chart is the **single onboarding path** for registering applications on this platform. Add one entry to [catalog.yaml](./catalog.yaml) and open a PR — you're done.

ArgoCD renders the chart and creates, for every entry:

| Resource | Purpose |
|---|---|
| `AppProject` | Scopes the app's source repo + namespaces |
| `Application` | Deploys the stable branch (`targetRevision`) |
| `ApplicationSet` *(opt-in)* | Deploys a preview environment per GitHub PR or GitLab MR |

---

## Quick start

### 1. Add your app to `catalog.yaml`

```yaml
# charts/app-template/catalog.yaml
apps:
  - name: my-service                                  # lowercase, hyphens OK
    repo: https://github.com/my-org/my-service.git   # full HTTPS clone URL
    chart: k8s/chart                                  # path to Helm chart in repo
    registry: ghcr.io/my-org/my-service               # image repo without tag
```

### 2. Open a pull request

That's it. ArgoCD will pick up the change within seconds of merge.

---

## Fields reference

| Field | Required | Default | Description |
|---|---|---|---|
| `name` | ✅ | — | App name. Lowercase letters, digits, hyphens. Becomes the AppProject name and the stable namespace. |
| `repo` | ✅ | — | Full HTTPS clone URL of the application repository, including `.git`. |
| `chart` | ✅ | — | Path to the Helm chart directory inside `repo` (e.g. `k8s/chart`). |
| `registry` | ✅ | — | Container image repository without tag (e.g. `ghcr.io/org/app`). Passed as `image.repository` to the chart. |
| `targetRevision` | — | `main` | Git ref for the stable Application. Override when your default branch isn't `main`. |
| `extraHelmParameters` | — | `[]` | Additional `name`/`value` pairs forwarded to the stable Application. |
| `preview` | — | *(omit)* | Preview environment config. **Omit this block entirely to skip ApplicationSet generation.** |

### `preview` sub-fields

| Field | Description |
|---|---|
| `preview.enabled` | Set `false` to temporarily disable previews without removing the block. |
| `preview.namespace` | Override the preview namespace name (default: `<name>-preview`). |
| `preview.github` | Opt-in to GitHub PR previews. Set to `{}` — owner and repo are extracted from the `repo` URL automatically. |
| `preview.gitlab.projectId` | *(string)* Numeric project ID from GitLab **Settings → General**. Required for GitLab previews. |
| `preview.gitlab.url` | Base URL of a self-hosted GitLab instance (e.g. `https://gitlab.example.com`). Omit for `gitlab.com`. |

---

## Preview environments

Preview environments are **opt-in**. You activate them by adding a `preview` block to your catalog entry.

### GitHub PR previews

```yaml
- name: my-service
  repo: https://github.com/my-org/my-service.git
  chart: k8s/chart
  registry: ghcr.io/my-org/my-service
  preview:
    github: {}    # owner + repo extracted from the URL above
```

**How it works:**

1. Add the label **`preview`** to a GitHub PR.
2. ArgoCD detects the label and deploys a preview Application named `my-service-preview-<pr-number>-<branch-slug>`.
3. When the PR is closed or the label is removed, ArgoCD deletes the preview Application and all its resources.

**Required secret** (one-time, platform admin):

```shell
kubectl -n argocd create secret generic github-token \
  --from-literal=token=<GITHUB_PAT>
# Required scopes: repo (read)
```

### GitLab.com MR previews

```yaml
- name: my-service
  repo: https://gitlab.com/my-group/my-service.git
  chart: k8s/chart
  registry: registry.gitlab.com/my-group/my-service
  preview:
    gitlab:
      projectId: "12345678"   # Settings → General → Project ID
```

### Self-hosted GitLab MR previews

```yaml
- name: my-service
  repo: https://gitlab.mycompany.com/team/my-service.git
  chart: k8s/chart
  registry: registry.mycompany.com/team/my-service
  preview:
    gitlab:
      url: https://gitlab.mycompany.com   # omit for gitlab.com
      projectId: "42"
```

**Required secret** (one-time, platform admin):

```shell
kubectl -n argocd create secret generic gitlab-token \
  --from-literal=token=<GITLAB_PAT>
# Required scopes: api, read_repository
```

### Disabling previews temporarily

Once a `preview` block exists you can disable it without removing config:

```yaml
preview:
  enabled: false   # set back to true (or remove the line) to re-enable
  github: {}
```

---

## Examples

### Minimum (no previews)

```yaml
- name: my-app
  repo: https://github.com/my-org/my-app.git
  chart: k8s/chart
  registry: ghcr.io/my-org/my-app
```

### With extra Helm parameters

```yaml
- name: my-app
  repo: https://github.com/my-org/my-app.git
  chart: k8s/chart
  registry: ghcr.io/my-org/my-app
  extraHelmParameters:
    - name: env.variables.APP_ENV
      value: production
    - name: replicaCount
      value: "2"
```

### Pin to a specific branch

```yaml
- name: my-app
  repo: https://github.com/my-org/my-app.git
  chart: k8s/chart
  registry: ghcr.io/my-org/my-app
  targetRevision: release/1.2
```

---

## How ArgoCD renders this chart

The `platform-apps` ArgoCD Application points at this chart:

```yaml
# infrastructure/configs/base/platform-apps.yaml
source:
  repoURL: https://github.com/dxas90/flux-platform-seed.git
  targetRevision: main
  path: charts/app-template
  helm:
    valueFiles:
      - catalog.yaml
```

`catalog.yaml` lives inside the chart directory so ArgoCD can load it as a values file without multi-source configuration. Every merge to `main` triggers an ArgoCD sync within seconds.

---

## Chart structure

```
charts/app-template/
├── Chart.yaml                # Helm chart metadata
├── values.yaml               # Platform defaults (tokens, syncOptions, etc.)
├── values.schema.json        # JSON schema — validates catalog entries
├── catalog.yaml              # ← THE ONE FILE teams edit
├── README.md                 # This file
└── templates/
    ├── _helpers.tpl          # GitHub URL parser + template-escape helpers
    ├── project.yaml          # AppProject per app
    ├── application.yaml      # Stable Application per app
    └── applicationset.yaml   # Preview ApplicationSet per app (opt-in)
```
