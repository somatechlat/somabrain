{{- define "somabrain.fullname" -}}
{{- printf "%s-%s" .Release.Name "somabrain" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "somabrain.labels" -}}
app.kubernetes.io/name: {{ include "somabrain.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}