# Platform-side application onboarding

Application delivery is intentionally split across repositories:

| Repository | Owner | Contents |
|---|---|---|
| Platform repository | Platform team | ArgoCD, namespaces, AppProjects, repository access, identity, quotas, policy |
| Application-delivery repository | Application teams | ArgoCD Application registrations |
| Workload repository | Application team | Deployments, Services, configuration, charts or Kustomize overlays |

This repository is the platform repository.

## Platform setup for a team

Before accepting an Application registration, create and review:

1. A dedicated namespace with the required Pod Security labels.
2. An AppProject with exact source repositories and destination namespaces.
3. ArgoCD repository credentials delivered through an approved secret mechanism.
4. Workload identity and any ExternalSecrets required by the application.
5. ResourceQuota, LimitRange, NetworkPolicy, and admission rules appropriate for the environment.

Start from `examples/onboarding/team-platform.yaml`, then move the customized resources into the relevant environment under `infrastructure/configs/<environment>/`.

## AppProject rules

Avoid the default project. A team project should:

- Allow only approved source repositories.
- Allow only the team's destination namespace.
- Deny cluster-scoped resources unless explicitly required.
- Allow only the namespace-scoped resource kinds the team needs.

The example is intentionally restrictive and may need additional workload resource kinds.

## Application registration

Application registrations do not belong in this repository. Keep them in a separate application-delivery repository. The example at `examples/onboarding/application.yaml` shows the expected contract:

- `metadata.namespace: argocd`
- A non-default, platform-managed project
- An approved repository URL and target revision
- The team's existing destination namespace
- `FailOnSharedResource=true`
- No cascading deletion finalizer by default

## Ownership boundary

Flux owns this platform repository and the ArgoCD controller. ArgoCD owns objects rendered by Applications. Do not configure both controllers to reconcile the same workload resource.

Removing an Application object without a cascading finalizer leaves its workloads behind. Decommission applications deliberately, including persistent data and external resources.

## Security boundary

AppProject restrictions are necessary but not sufficient for hostile multi-tenancy. Repository approval, ArgoCD RBAC, admission policy, workload identity, network policy, and secret access must enforce the same team boundary.
