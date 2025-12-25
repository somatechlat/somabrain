{{- define "milvus.fullname" -}}
{{- printf "%s-%s" .Release.Name "milvus" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "milvus.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "-" }}
app.kubernetes.io/name: {{ include "milvus.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "milvus.selectorLabels" -}}
app.kubernetes.io/name: {{ include "milvus.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}