# GitLab PAT secret — create out-of-band before deploying.
#
# Using flux-operator CLI:
#   echo $GITLAB_TOKEN | flux-operator -n network-stats-preview \
#     create secret basic-auth gitlab-token-readonly \
#     --username=flux \
#     --password-stdin
#
# Or manually:
#   kubectl -n network-stats-preview create secret generic gitlab-token-readonly \
#     --from-literal=username=flux \
#     --from-literal=password=<YOUR_GITLAB_PAT>
#
# Required GitLab PAT scopes: read_api, read_repository
#
# This file is intentionally NOT committed — it is documented here
# so operators know what secret is expected at runtime.
# The secret name is referenced by:
#   - apps/network-stats-preview/input-provider-mr.yaml
#   - apps/network-stats-preview/input-provider-env.yaml
#   - apps/network-stats-preview/resourceset-mr.yaml
#   - apps/network-stats-preview/resourceset-env.yaml
