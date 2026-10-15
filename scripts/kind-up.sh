#!/usr/bin/env bash
# Create a disposable kind cluster, install Flux Operator, and apply the kind FluxInstance.
set -euo pipefail

cluster="${KIND_CLUSTER_NAME:-seed}"
context="kind-${cluster}"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

for command in docker kind kubectl helm; do
  command -v "$command" >/dev/null || { printf '%s is required\n' "$command" >&2; exit 1; }
done
docker info >/dev/null 2>&1 || { printf 'Docker daemon is not running\n' >&2; exit 1; }

if ! kind get clusters | grep -qx "$cluster"; then
  kind create cluster --name "$cluster" --config "$root/kind-config.yaml"
fi

helm upgrade --install flux-operator \
  oci://ghcr.io/controlplaneio-fluxcd/charts/flux-operator \
  --kube-context "$context" \
  --namespace flux-system \
  --create-namespace \
  --version 0.61.0 \
  --wait \
  --timeout 5m

CONFIRM_BOOTSTRAP="$context" "$root/scripts/bootstrap.sh" kind "$context"

kubectl --context "$context" -n flux-system get fluxinstance,gitrepository,kustomization
