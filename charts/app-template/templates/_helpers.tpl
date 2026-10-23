{{/*
Extract the GitHub owner from a full HTTPS clone URL.
Input:  "https://github.com/dxas90/learn-go.git"
Output: "dxas90"
*/}}
{{- define "app-template.githubOwner" -}}
{{- $path := trimSuffix ".git" (trimPrefix "https://github.com/" .) -}}
{{- index (splitList "/" $path) 0 -}}
{{- end }}

{{/*
Extract the GitHub repository name from a full HTTPS clone URL.
Input:  "https://github.com/dxas90/learn-go.git"
Output: "learn-go"
*/}}
{{- define "app-template.githubRepo" -}}
{{- $path := trimSuffix ".git" (trimPrefix "https://github.com/" .) -}}
{{- index (splitList "/" $path) 1 -}}
{{- end }}

{{/*
Return a literal "{{" — used to embed ArgoCD go-template variables inside
Helm templates without triggering Helm's own template engine.
Usage: {{ include "lb" . }}.number{{ include "rb" . }}
*/}}
{{- define "lb" -}}{{- "{{" -}}{{- end }}
{{- define "rb" -}}{{- "}}" -}}{{- end }}
