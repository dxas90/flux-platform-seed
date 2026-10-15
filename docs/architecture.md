# Architecture decisions

This document explains the defaults in the seed and where to change them.

## Flux Operator owns Flux

Flux Operator installs and upgrades the Flux controllers from `FluxInstance/flux`. Do not combine this model with `flux bootstrap` or commit generated controller manifests. There should be one owner for the Flux controller Deployments.

The operator also creates the root `GitRepository/flux-system` and `Kustomization/flux-system` from `FluxInstance.spec.sync`. Child Kustomizations therefore reference `GitRepository/flux-system`.

## Controllers before configuration

Each cluster entrypoint creates two Flux Kustomizations:

1. `infra-controllers` reconciles namespaces, CRDs, sources, and HelmReleases.
2. `infra-configs` depends on `infra-controllers` and reconciles resources that require those controllers or CRDs.

Examples:

- Grafana Operator is in `controllers`; Grafana and GrafanaDatasource resources are in `configs`.
- cert-manager is in `controllers`; Issuers belong in environment `configs`.
- External Secrets Operator is in `controllers`; SecretStores and ExternalSecrets belong in environment `configs`.

This prevents CRD consumers from racing their controllers.

## One catalog, environment overlays

Every add-on has a reusable definition under:

```text
infrastructure/controllers/base/<addon>/
```

`infrastructure/controllers/base/kustomization.yaml` is the catalog switchboard. Add or remove an entry there to change the add-ons selected by all environments.

Environment overlays add a second generated values ConfigMap to each HelmRelease. Shared values stay in the base; cluster-specific changes stay under `controllers/<environment>/values/`.

## Enabled add-ons

The default selection provides a broad local platform:

- cert-manager
- External Secrets Operator
- metrics-server
- Reloader
- KEDA
- kube-prometheus-stack
- Grafana Operator
- Loki
- Fluent Bit
- Alloy
- Tempo
- ArgoCD
- Gateway API and Prometheus Operator CRDs

Optional catalog entries are commented out in the base Kustomization.

## Grafana is operator-managed

The Grafana bundled with kube-prometheus-stack is disabled. Grafana Operator installs the CRDs and controller; the `configs` layer creates the Grafana instance and Prometheus, Loki, and Tempo datasources.

This keeps dashboards and datasources declarative and avoids two Grafana installations.

## Fluent Bit and Alloy coexist without duplicate logs

Fluent Bit tails container logs from nodes and sends them to Loki. Alloy only collects pods explicitly labelled:

```yaml
logs.platform.example/collector: alloy
```

Fluent Bit excludes that label. This supports gradual migration or workload-specific Alloy pipelines without collecting the same pod twice.

## ArgoCD owns applications

Flux owns the platform resources in this repository. ArgoCD owns business workloads from a separate application-delivery repository.

This seed does not reconcile ArgoCD Application registrations and does not give application teams access to Flux resources. Platform owners create namespaces, AppProjects, repository credentials, identity, quotas, and network policy.

The default ArgoCD project is disabled so applications must use explicitly configured projects.

## Public Git by default

Checked-in FluxInstances use a public HTTPS placeholder and no pull Secret. Private repositories require an out-of-band credential before Flux can read the repository. That credential cannot depend on External Secrets reconciled from the same unavailable Git source.

## Source composition is opt-in

Git remains the root source because it is the simplest bootstrap path. `source-watcher` is installed so ArtifactGenerator and ExternalArtifact can be adopted later without changing the Flux distribution.

Examples are inactive. Enabling an ExternalArtifact consumer alongside the existing Git consumer can create duplicate ownership, so source migration must replace—not duplicate—the active consumer.

## Pruning and deletion

Layer Kustomizations use `deletionPolicy: Orphan`. Namespace and FluxInstance manifests disable pruning. These settings reduce damage from deleting a parent reconciliation object.

They do not prevent Helm uninstall when an actively pruned Kustomization removes a HelmRelease. Backups and explicit decommission procedures are still required.

## Production gaps

The seed intentionally leaves organization-specific choices unresolved:

- Object storage and high availability for Loki and Tempo
- Grafana authentication, SSO, and alert receivers
- DNS zones, certificate issuers, ingress classes, and cloud IAM
- StorageClasses, backups, retention, and resource sizing
- NetworkPolicies and admission policy
- Release promotion between staging and production

Resolve these in environment overlays and configuration resources before production use.
