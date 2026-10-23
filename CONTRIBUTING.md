# Maintainer guide

Use this checklist for changes to the platform seed.

## Before editing

1. Read `README.md`, `docs/architecture.md`, and the nearest component files.
2. Confirm whether the change belongs in `controllers` or `configs`.
3. Check ownership and dependencies before moving resources.
4. Preserve environment-specific overrides unless the change intentionally replaces them.

## Component conventions

A Helm-managed add-on normally contains:

```text
infrastructure/controllers/base/<addon>/
├── source.yaml
├── helmrelease.yaml
├── values.yaml
└── kustomization.yaml
```

Rules:

- Pin chart versions exactly.
- Keep non-trivial Helm values in `values.yaml`, not inline in HelmRelease.
- Keep source and HelmRelease in the release namespace.
- Require CPU and memory requests and limits for every rendered app, sidecar, and init container.
- Prefer documented chart resource values; use a narrowly targeted Helm post-renderer when the chart does not expose all containers.
- Treat checked-in resource values as starter examples and measure before production.
- Generate values ConfigMaps without name suffix hashes and label them for Flux watch reconciliation.
- Use literal YAML block scalars for post-renderer patches.
- Put controller CRs and other CRD consumers in `infrastructure/configs`, not beside the controller HelmRelease.
- Add environment override files for every catalog component.

## Definition of done

A change is complete when all applicable checks pass:

1. Every changed YAML file parses.
2. Every Kustomize root builds.
3. Flux paths and dependency graphs resolve.
4. Helm source/value references resolve.
5. Chart versions are pinned.
6. Every catalog chart renders for each environment.
7. Custom resources validate against the selected Flux/operator schemas.
8. No credentials, private keys, kubeconfigs, generated state, or local paths are committed.
9. Documentation explains new components, dependencies, and operational assumptions.
10. The final report lists the exact commands run and their actual results.

For changes to `charts/app-template/` or `catalog.yaml`, also run:

```sh
helm lint charts/app-template -f charts/app-template/catalog.yaml
helm template platform-apps charts/app-template -f charts/app-template/catalog.yaml > /dev/null
```

Run:

```sh
python scripts/check_text_files.py
python scripts/test_validate.py
python scripts/validate.py
python scripts/validate.py --helm
python scripts/validate_schemas.py --operator-version 0.61.0
```

Or with mise:

```sh
mise run validate
mise run validate/helm
mise run validate/schemas
```

## GitOps safety

- Do not use force push or rewrite shared history.
- Do not commit generated Flux controller manifests; Flux Operator owns them.
- Do not point Flux and ArgoCD at the same resource tree.
- Do not remove CRDs or stateful releases without reviewing existing custom resources and persistent data.
- Do not treat `deletionPolicy: Orphan` as a backup.
- Keep production changes reviewable and separately approved from staging.
