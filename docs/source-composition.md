# Flux sources and artifact composition

The default platform sync uses a GitRepository. Flux supports other source types, and `source-watcher` adds ArtifactGenerator and ExternalArtifact support.

## Source types

| Resource | Typical use |
|---|---|
| GitRepository | Version-controlled platform manifests; default root source |
| HelmRepository | HTTP Helm repositories referenced by HelmRelease charts |
| OCIRepository | OCI Helm charts or immutable manifest bundles |
| Bucket | Manifests or configuration stored in S3-compatible object storage |
| ArtifactGenerator | Compose several source artifacts or split one artifact into smaller outputs |
| ExternalArtifact | Artifact produced by ArtifactGenerator or another compatible controller |
| ImageRepository / ImagePolicy / ImageUpdateAutomation | Optional image discovery and Git updates; additional Flux controllers are required |
| Provider / Alert / Receiver | Reconciliation notifications and incoming webhook automation |

Sources publish artifacts. They do not apply Kubernetes resources. Kustomization and HelmRelease consume artifacts and reconcile cluster objects.

## Included examples

The files under `examples/sources/` are inactive templates:

- `bucket.yaml` shows an AWS S3-compatible Bucket source.
- `oci.yaml` shows an OCI source.
- `artifact-generator.yaml` copies the infrastructure tree from the root Git source into a generated ExternalArtifact.
- `external-artifact-consumer.yaml` shows a suspended Kustomization that consumes that generated artifact.

All placeholders must be replaced before use.

## ArtifactGenerator ownership

ArtifactGenerator creates and updates ExternalArtifact objects. Do not handcraft an ExternalArtifact status, URL, digest, or revision.

The artifact copy rules must include every relative Kustomize base and component needed by the selected overlay. A valid schema does not guarantee that the generated artifact contains a buildable directory tree.

## Safe adoption

1. Identify why Git alone is insufficient: independent revisions, composition, decomposition, or immutable OCI releases.
2. Create and validate the new source without changing the active consumer.
3. Reconcile the ArtifactGenerator and inspect the generated ExternalArtifact revision and contents.
4. Build the selected path from the generated artifact.
5. Switch the existing consumer to the new source.
6. Remove the old consumer after verifying ownership and health.

Do not run Git and ExternalArtifact Kustomizations against the same resources. That creates competing ownership.

## Root sync

Flux Operator can generate root sync objects for GitRepository, OCIRepository, or Bucket sources. Child Kustomizations must reference the generated source kind and name. Changing only `FluxInstance.spec.sync.kind` while leaving child `sourceRef` values unchanged will break reconciliation.

ArtifactGenerator and ExternalArtifact are not root sync kinds in this seed. Keep the generator and its inputs reachable from the root source.

## Authentication

Source credentials must exist before the source can reconcile. Bootstrap credentials cannot be supplied by External Secrets reconciled from that same unavailable source.

Use workload identity where supported. Otherwise create narrowly scoped Kubernetes Secrets out-of-band and reference them from the source.

## Validation

`validate_schemas.py` checks the examples against the CRDs exported by the selected Flux distribution and operator chart. It does not connect to a real bucket or registry and does not exercise a live artifact pipeline.

## References

- [Flux source-controller](https://fluxcd.io/flux/components/source/)
- [ArtifactGenerator API](https://fluxcd.io/flux/components/source/artifactgenerators/)
- [source-watcher](https://github.com/fluxcd/source-watcher/tree/main/docs)
- [Flux Operator sync configuration](https://github.com/controlplaneio-fluxcd/flux-operator/blob/main/docs/guides/instance/instance-sync.md)
