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

{{- define "soma-apps.memorySecretName" -}}
{{- $name := (default (printf "%s-memory" .Release.Name) .Values.memory.secretName) -}}
{{- $name -}}
{{- end -}}

{{- define "soma-apps.jwtSecretName" -}}
{{- $name := (default (printf "%s-jwt" .Release.Name) .Values.jwt.secretName) -}}
{{- $name -}}
{{- end -}}

{{/* Standard pod security context mapping (only mapping body, not the key) */}}
{{- define "soma-apps.podSecurityContext" -}}
runAsNonRoot: {{ .Values.securityContext.pod.runAsNonRoot | default true }}
runAsUser: {{ .Values.securityContext.pod.runAsUser | default 10001 }}
runAsGroup: {{ .Values.securityContext.pod.runAsGroup | default 10001 }}
fsGroup: {{ .Values.securityContext.pod.fsGroup | default 10001 }}
seccompProfile:
  type: {{ .Values.securityContext.pod.seccompProfile | default "RuntimeDefault" }}
{{- end -}}

{{/* Standard container security context mapping (only mapping body, not the key) */}}
{{- define "soma-apps.containerSecurityContext" -}}
allowPrivilegeEscalation: {{ .Values.securityContext.container.allowPrivilegeEscalation | default false }}
readOnlyRootFilesystem: {{ .Values.securityContext.container.readOnlyRootFilesystem | default true }}
capabilities:
  drop:
{{- $drops := (default (list "ALL") .Values.securityContext.container.capabilities.drop) -}}
{{- range $i, $c := $drops }}
    - {{ $c | quote }}
{{- end }}
{{- end -}}
