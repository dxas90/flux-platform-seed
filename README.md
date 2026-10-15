# Flux platform seed

A reusable starting point for running Kubernetes platform add-ons with Flux Operator, FluxCD, Kustomize, and Helm.

This repository owns cluster infrastructure and the ArgoCD controller. Application registrations and workload manifests belong in separate repositories.

## What is included

Enabled by default:

- cert-manager
- External Secrets Operator
- metrics-server
- Reloader
- KEDA
- kube-prometheus-stack, with its bundled Grafana disabled
- Grafana Operator and a Grafana instance
- Loki, Fluent Bit, Alloy, and Tempo
- ArgoCD
- Gateway API and Prometheus Operator CRDs

Available but disabled in `infrastructure/controllers/base/kustomization.yaml`:

- external-dns
- Kyverno
- node-feature-discovery
- CloudNativePG
- Dragonfly Operator

## Architecture

```text
flux-operator
└── FluxInstance/flux
    ├── Flux controllers
    └── GitRepository/flux-system + Kustomization/flux-system
        ├── infra-controllers  → namespaces, CRDs, Helm repositories and releases
        └── infra-configs      → resources that require those controllers/CRDs
```

The operator creates and owns the Flux controllers. `FluxInstance` configures the distribution and points Flux at one cluster directory in this repository. The cluster entrypoint creates two ordered Flux Kustomizations:

1. `infra-controllers` installs controllers and platform services.
2. `infra-configs` waits for the controllers, then creates resources such as the Grafana instance and datasources.

ArgoCD Applications are deliberately outside this repository.

## Repository layout

```text
clusters/
  kind/                         # Local test cluster
  staging/                      # Staging cluster entrypoint
  prod/                         # Production cluster entrypoint
infrastructure/
  controllers/
    base/                       # Add-on catalog
    kind/                       # Local overrides
    staging/                    # Staging overrides
    prod/                       # Production overrides
  configs/
    base/                       # CRD consumers and platform configuration
    kind/
    staging/
    prod/
examples/
  onboarding/                   # Namespace/AppProject/Application examples
  sources/                      # Bucket, OCI, ArtifactGenerator examples
scripts/
  bootstrap.sh                  # Apply a configured FluxInstance
  create_pull_secret.py         # Optional SSH credentials for private Git
  validate.py                   # Kustomize and chart checks
  validate_schemas.py           # CRD schema checks
  test_validate.py              # Regression tests
```

## Prerequisites

- Kubernetes cluster and a kubeconfig context
- Helm
- kubectl
- Kustomize
- Flux CLI
- Python 3 with dependencies from `requirements-dev.txt`
- A default StorageClass for stateful add-ons

The tested tool versions are in `mise.toml`.

## 1. Create your repository

Fork this repository or create a new repository from it. Replace the placeholder source URL in every FluxInstance:

```yaml
spec:
  sync:
    url: https://github.com/YOUR_ORG/flux-platform-seed.git
```

Configure the target branch and keep each cluster's path aligned with its directory:

| Cluster | `spec.sync.path` |
|---|---|
| kind | `clusters/kind` |
| staging | `clusters/staging` |
| prod | `clusters/prod` |

The checked-in examples use a public HTTPS repository. For a private repository, add `spec.sync.pullSecret` and create the Secret before applying the FluxInstance. See [Private Git authentication](#private-git-authentication).

## 2. Install Flux Operator

Flux Operator is intentionally not installed by this repository. Install it once per cluster:

```sh
helm install flux-operator \
  oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --namespace flux-system \
  --create-namespace \
  --version 0.61.0 \
  --wait
```

Confirm that the operator and CRD are ready:

```sh
kubectl -n flux-system rollout status deployment/flux-operator
kubectl wait --for=condition=Established \
  crd/fluxinstances.fluxcd.controlplane.io --timeout=60s
```

## 3. Review the add-on catalog

Edit `infrastructure/controllers/base/kustomization.yaml` before first deployment. Comment an enabled resource to disable it, or uncomment a catalog entry to enable it for every environment.

Environment-specific Helm values live under:

```text
infrastructure/controllers/<environment>/values/<addon>.yaml
```

Shared values live under:

```text
infrastructure/controllers/base/<addon>/values.yaml
```

Helm merges chart defaults, shared values, then environment values. Helm replaces lists rather than appending them.

Review at least:

- Storage sizes, StorageClasses, retention, replicas, requests, and limits
- Ingress, DNS, certificate issuers, and cloud IAM
- Grafana authentication and alert receivers
- Loki/Tempo storage and production high availability
- Whether your cluster already provides metrics-server or other add-ons

The defaults are suitable for local evaluation, not production capacity planning.

## 4. Validate locally

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/test_validate.py
.venv/bin/python scripts/validate.py
.venv/bin/python scripts/validate.py --helm
.venv/bin/python scripts/validate_schemas.py --operator-version 0.61.0
```

The checks cover:

- YAML parsing and duplicate keys
- Kustomize builds for every base and environment
- Flux dependency graphs and paths
- Helm source/value references and pinned chart versions
- Rendering every catalog chart for each environment
- FluxInstance, ArtifactGenerator, ExternalArtifact, and Bucket schemas

These checks do not replace API-server admission or live smoke tests.

## 5. Apply the FluxInstance

Applying a FluxInstance starts reconciliation immediately. Verify the context and configuration first.

Use the guarded script for any configured cluster:

```sh
CONFIRM_BOOTSTRAP=my-context \
  bash scripts/bootstrap.sh staging my-context
```

For kind:

```sh
CONFIRM_BOOTSTRAP=kind-seed \
  bash scripts/bootstrap.sh kind kind-seed
```

The script:

1. Rejects placeholder configuration.
2. Verifies the FluxInstance CRD and operator Deployment.
3. Applies only the selected FluxInstance.
4. Waits for the FluxInstance to become Ready.

The script supports `kind`, `staging`, and `prod`.

## Local kind test

The repository includes a small kind configuration and lifecycle scripts:

```sh
bash scripts/kind-up.sh
# inspect Flux and workloads
bash scripts/kind-down.sh
```

`kind-up.sh` creates `kind-seed`, installs Flux Operator, applies the kind FluxInstance, and prints the Flux reconciliation objects. Update the kind FluxInstance repository URL before running it from a fork.

## Verify reconciliation

```sh
kubectl -n flux-system get fluxinstance
flux get sources all --all-namespaces
flux get kustomizations --namespace=flux-system
flux get helmreleases --all-namespaces
```

Expected order:

```text
flux-system → infra-controllers → infra-configs
```

A Ready FluxInstance proves the operator reconciled the Flux distribution and root sync. Verify the child Kustomizations and HelmReleases separately.

## Private Git authentication

For SSH authentication, add this to the FluxInstance:

```yaml
spec:
  sync:
    pullSecret: flux-system
```

Create the Secret before applying the FluxInstance:

```sh
python3 scripts/create_pull_secret.py \
  ~/.ssh/git-deploy-key \
  my-kube-context \
  github.com
```

The script creates an Opaque Secret with the `identity` and `known_hosts` keys expected by Flux source-controller. Never commit the private key or generated Secret.

## Application delivery boundary

This repository installs ArgoCD and may define platform-owned AppProjects and namespaces. Keep ArgoCD Application registrations and business workloads in a separate repository.

The onboarding examples demonstrate the contract only:

- `examples/onboarding/team-platform.yaml` is a platform-owner example.
- `examples/onboarding/application.yaml` is an application-repository example.

See [Application onboarding](docs/application-onboarding.md).

## Source composition

The default root source is Git. `source-watcher` is enabled so the platform can also use ArtifactGenerator and ExternalArtifact when composition or decomposition is useful.

The inactive examples under `examples/sources/` cover:

- S3-compatible Bucket sources
- OCI repositories
- ArtifactGenerator
- ExternalArtifact consumers

See [Flux sources and artifact composition](docs/source-composition.md).

## Removal and rollback

Flux Kustomizations use `deletionPolicy: Orphan`. Namespaces and FluxInstance resources also disable pruning. This reduces accidental teardown when a parent object disappears, but it is not a backup policy.

Removing a HelmRelease from an actively reconciled and pruned path can uninstall that release. Review CRD ownership, persistent data, and backups before removing or downgrading add-ons.

Rollback by reverting the Git change and watching Flux and Helm status. Do not delete the FluxInstance to pause reconciliation; deletion may remove operator-managed Flux controllers.

## Security notes

- No credentials belong in this repository.
- Use workload identity or an external secret manager for cloud access.
- Restrict ArgoCD projects, repositories, destinations, and cluster-scoped resources.
- Review NetworkPolicies for your CNI and API-server topology.
- Loki and Tempo require authentication or network isolation in shared clusters.
- Treat application logs and traces as potentially sensitive data.

## Development checks

This repository requires LF line endings and a final newline in every tracked text file. `.editorconfig`, `.gitattributes`, pre-commit hooks, and `scripts/check_text_files.py` enforce that policy.

Install hooks once:

```sh
pre-commit install
```

Run all fast checks:

```sh
mise run validate
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full maintainer checklist.

## Further reading

- [Flux repository structure](https://fluxcd.io/flux/guides/repository-structure/)
- [Flux Kustomize/Helm example](https://github.com/fluxcd/flux2-kustomize-helm-example)
- [Flux multi-tenancy example](https://github.com/fluxcd/flux2-multi-tenancy)
- [Flux Operator documentation](https://fluxoperator.dev/docs/)
- [Maintainer guide](CONTRIBUTING.md)
- [Architecture decisions](docs/architecture.md)
