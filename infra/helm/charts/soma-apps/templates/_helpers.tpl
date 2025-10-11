{{- define "soma-apps.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "soma-apps.fullname" -}}
{{- printf "%s" .Release.Name -}}
{{- end -}}

{{- define "soma-apps.componentName" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- printf "%s-%s" $root.Release.Name $component -}}
{{- end -}}

{{- define "soma-apps.labels" -}}
app.kubernetes.io/name: {{ include "soma-apps.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- end -}}
