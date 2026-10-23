# Required Secrets — network-stats

Two secrets are required in the **argocd** namespace before this directory
can function. They carry the same PAT value but are different Kubernetes
Secret objects with different key names (ArgoCD ApplicationSet and
argocd-notifications read from separate locations).

## Secret 1 — ApplicationSet PR generator

Used by applicationset.yaml to call the GitLab API and discover open MRs.
The Secret MUST carry the label `argocd.argoproj.io/secret-type=scm-creds`
or the ApplicationSet controller rejects it with:
"secret is not a valid SCM creds secret: secret must have label argocd.argoproj.io/secret-type=scm-creds"

    kubectl -n argocd create secret generic gitlab-token \
      --from-literal=token=<YOUR_GITLAB_PAT>
    kubectl -n argocd label secret gitlab-token \
      argocd.argoproj.io/secret-type=scm-creds

Required GitLab PAT scopes: api, read_repository

## Secret 2 — argocd-notifications (commit statuses)

Used by argocd-notifications-cm (argocd-notifications.yaml) to post
commit statuses back to GitLab MRs. The key name MUST be "gitlab-token"
(matches the $gitlab-token reference in service.gitlab).

    kubectl -n argocd create secret generic argocd-notifications-secret \
      --from-literal=gitlab-token=<YOUR_GITLAB_PAT>

Required GitLab PAT scopes: api (write access to post commit statuses)

## GitLab Webhook (ApplicationSet polling acceleration)

Register in the network-stats GitLab project under Settings > Webhooks:
  URL:    https://<argocd-server>/api/webhook
  Events: Merge request events

Without this, the ApplicationSet polls every 10 minutes (requeueAfterSeconds: 600).

## Confirmed values

GitLab project ID: 30270366  (already set in applicationset.yaml)
GitLab project URL: https://gitlab.com/dxas90/network-stats
