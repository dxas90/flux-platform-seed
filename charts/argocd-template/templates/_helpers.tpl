{{/*
Extract the GitHub owner from a full HTTPS clone URL.
Input:  "https://github.com/org/app.git"
Output: "org"
*/}}
{{- define "argocd-template.githubOwner" -}}
{{- $path := trimSuffix ".git" (trimPrefix "https://github.com/" .) -}}
{{- index (splitList "/" $path) 0 -}}
{{- end }}

{{/*
Extract the GitHub repository name from a full HTTPS clone URL.
Input:  "https://github.com/org/app.git"
Output: "app"
*/}}
{{- define "argocd-template.githubRepo" -}}
{{- $path := trimSuffix ".git" (trimPrefix "https://github.com/" .) -}}
{{- index (splitList "/" $path) 1 -}}
{{- end }}

{{/*
Return a literal "{{" — used to embed ArgoCD go-template variables inside
Helm templates without triggering Helm's own template engine.
Usage: {{ include "argocd-template.lb" . }}.number{{ include "argocd-template.rb" . }}
*/}}
{{- define "argocd-template.lb" -}}{{- "{{" -}}{{- end }}
{{- define "argocd-template.rb" -}}{{- "}}" -}}{{- end }}
