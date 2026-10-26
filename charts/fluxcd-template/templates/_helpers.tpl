{{/*
fluxcd-template helpers — Flux-native edition (no ArgoCD).

All templates receive the top-level $ (root) context.  Per-app templates
receive (list $ $app) so helper functions can reference both global Values
and per-app overrides.

Naming conventions
  Namespace:            <app.name>
  GitRepository:        <app.name>              (in .Values.controlNamespace)
  HelmRelease:          <app.name>              (in .Values.controlNamespace)
  SA:                   app-<app.name>          (in .Values.controlNamespace)
  Role:                 app-<app.name>          (in <app.name> namespace)
  RoleBinding:          app-<app.name>          (in <app.name> namespace)
  Preview provider:     <app.name>-mr-provider  (in .Values.previewNamespace)
  ResourceSet:          <app.name>-preview      (in .Values.previewNamespace)
  Preview SA:           preview-<app.name>      (in .Values.controlNamespace)
  Preview RoleBinding:  preview-<app.name>      (in <app.name> namespace)

Security model (enforced by generated RBAC — documented in README):
  - Flux HelmRelease and GitRepository always live in controlNamespace.
  - Helm storage always lives in controlNamespace (storageNamespace).
  - The app namespace SA has a Role in the APP namespace only (no cluster-wide
    or controlNamespace grants) with a restricted resource list (no RBAC types).
  - Preview namespaces have Pod Security restricted + default-deny NetworkPolicy.
  - Clone credentials and preview tokens are never projected into app pods.
  - ResourceSet SA (preview-<app>) is in controlNamespace; it binds a Role in
    the app namespace only; the preview namespace has no way to mutate the SA.
  - Namespace RBAC isolation is explicitly documented as insufficient for truly
    untrusted workloads; previews require trusted MRs (deploy/flux-preview opt-in).
*/}}

{{/*
Return the effective targetRevision for an app.
Usage: include "fluxcd-template.targetRevision" (list $ $app)
*/}}
{{- define "fluxcd-template.targetRevision" -}}
{{- $app := index . 1 -}}
{{- $vals := (index . 0).Values -}}
{{- default $vals.defaults.targetRevision $app.targetRevision -}}
{{- end }}

{{/*
Return the effective sync interval.
Usage: include "fluxcd-template.interval" (list $ $app)
*/}}
{{- define "fluxcd-template.interval" -}}
{{- $app := index . 1 -}}
{{- $vals := (index . 0).Values -}}
{{- default $vals.defaults.interval $app.interval -}}
{{- end }}

{{/*
Return "true" (non-empty) if preview is enabled for an app.
Requires .preview.gitlab to be set — GitHub previews not supported via
ResourceSetInputProvider (provider type GitLabMergeRequest only).
Opt-out: set preview.enabled: false.
Usage: include "fluxcd-template.previewEnabled" (list $ $app)
*/}}
{{- define "fluxcd-template.previewEnabled" -}}
{{- $app := index . 1 -}}
{{- if and $app.preview (ne (($app.preview).enabled | toString) "false") (hasKey (default dict $app.preview) "gitlab") -}}
true
{{- end -}}
{{- end }}

{{/*
Return the GitLab project HTTPS URL without trailing .git (used for API calls).
Usage: include "fluxcd-template.gitlabProjectURL" (list $ $app)
*/}}
{{- define "fluxcd-template.gitlabProjectURL" -}}
{{- $app := index . 1 -}}
{{- trimSuffix ".git" $app.repo -}}
{{- end }}

{{/*
Return a literal "<<" — used to embed Flux Operator template delimiters inside
Helm templates without triggering Helm's own template engine.
Usage: {{ include "lo" . }} inputs.id {{ include "ro" . }}
*/}}
{{- define "fluxcd-template.lo" -}}{{- "<<" -}}{{- end }}
{{- define "fluxcd-template.ro" -}}{{- ">>" -}}{{- end }}
