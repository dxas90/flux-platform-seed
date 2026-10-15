#!/usr/bin/env bash
# flux-operator must already be installed. Applies only the chosen FluxInstance.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  printf 'Usage: %s <kind|staging|prod> <kube-context>\n' "$0" >&2
  exit 2
fi
cluster=$1 context=$2
case "$cluster" in kind|staging|prod) ;; *) printf 'Unsupported cluster\n' >&2; exit 2 ;; esac
if [[ ${CONFIRM_BOOTSTRAP:-} != "$context" ]]; then
  printf 'Set CONFIRM_BOOTSTRAP to the exact kube-context to apply the FluxInstance. This activates platform reconciliation.\n' >&2
  exit 2
fi
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
instance="$root/clusters/$cluster/flux-system/flux-instance.yaml"
# Fail before contacting a cluster if essential configuration is still a template.
python3 - "$instance" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
if 'REPLACE_ME' in text:
    sys.exit('Configure the real Git URL in flux-instance.yaml first')
PY
kubectl --context="$context" wait --for=condition=Established crd/fluxinstances.fluxcd.controlplane.io --timeout=60s
kubectl --context="$context" -n flux-system rollout status deployment/flux-operator --timeout=120s
kubectl --context="$context" apply --server-side --field-manager=platform-bootstrap -f "$instance"
# Ownership of the FluxInstance's desired state transfers to Git after initial sync.
kubectl --context="$context" -n flux-system wait fluxinstance/flux --for=condition=Ready --timeout=300s
