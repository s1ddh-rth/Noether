{{/*
Chart name / fullname / labels — standard Helm idiom.
*/}}
{{- define "noether.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "noether.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s" .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "noether.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels applied to every object. */}}
{{- define "noether.labels" -}}
helm.sh/chart: {{ include "noether.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: noether
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}

{{/*
Per-component selector labels. Usage:
  {{- include "noether.selectorLabels" (dict "ctx" . "component" "inference") }}
*/}}
{{- define "noether.selectorLabels" -}}
app.kubernetes.io/name: {{ include "noether.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Full set of labels for a component (common + selector). */}}
{{- define "noether.componentLabels" -}}
{{ include "noether.labels" .ctx }}
{{ include "noether.selectorLabels" (dict "ctx" .ctx "component" .component) }}
{{- end -}}

{{/* Stable per-component object name: <release>-<component>. */}}
{{- define "noether.componentName" -}}
{{- printf "%s-%s" (include "noether.fullname" .ctx) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Resolve an image ref through the global mirror prefix. */}}
{{- define "noether.image" -}}
{{- printf "%s%s" .ctx.Values.global.imageRegistry .ref -}}
{{- end -}}

{{/* App-service image: <repo>-<svc>:<tag|appVersion>, mirror-prefixed. */}}
{{- define "noether.appImage" -}}
{{- $tag := .ctx.Values.image.tag | default .ctx.Chart.AppVersion -}}
{{- printf "%s%s-%s:%s" .ctx.Values.global.imageRegistry .ctx.Values.image.repository .svc $tag -}}
{{- end -}}

{{/* Name of the Secret holding all credentials. */}}
{{- define "noether.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-secrets" (include "noether.fullname" .) -}}
{{- end -}}
{{- end -}}

{{/*
Shared env block: OFFLINE_MODE + LOG_LEVEL on every workload. Usage:
  {{- include "noether.commonEnv" . | nindent 12 }}
*/}}
{{- define "noether.commonEnv" -}}
- name: OFFLINE_MODE
  value: {{ .Values.global.offlineMode | quote }}
- name: LOG_LEVEL
  value: {{ .Values.global.logLevel | quote }}
{{- end -}}

{{/*
Postgres/Timescale connection env (host points at the in-cluster Service).
Usage: {{- include "noether.dbEnv" . | nindent 12 }}
*/}}
{{- define "noether.dbEnv" -}}
- name: POSTGRES_HOST
  value: {{ include "noether.fullname" . }}-timescaledb
- name: POSTGRES_PORT
  value: {{ .Values.postgres.port | quote }}
- name: POSTGRES_DB
  value: {{ .Values.postgres.db | quote }}
- name: POSTGRES_USER
  value: {{ .Values.postgres.user | quote }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "noether.secretName" . }}
      key: postgres-password
{{- end -}}

{{/* Kafka bootstrap env. */}}
{{- define "noether.kafkaEnv" -}}
- name: KAFKA_BOOTSTRAP
  value: {{ include "noether.fullname" . }}-redpanda:9092
- name: KAFKA_TOPIC_PLANT_TAGS
  value: {{ .Values.kafka.topicPlantTags | quote }}
{{- end -}}

{{/* Resolve resources: per-component override else defaultResources. */}}
{{- define "noether.resources" -}}
{{- if .res -}}
{{- toYaml .res -}}
{{- else -}}
{{- toYaml .ctx.Values.defaultResources -}}
{{- end -}}
{{- end -}}

{{/*
Init container that blocks until TCP deps are reachable, so app pods don't
CrashLoop while Redpanda/Timescale come up (spec: zero CrashLoopBackOff).
Usage: {{- include "noether.waitFor" (dict "ctx" . "deps" (list "timescaledb:5432" "redpanda:9092")) | nindent 8 }}
*/}}
{{- define "noether.waitFor" -}}
- name: wait-for-deps
  image: {{ include "noether.image" (dict "ctx" .ctx "ref" .ctx.Values.images.timescaledb) }}
  imagePullPolicy: {{ .ctx.Values.global.imagePullPolicy }}
  command:
    - /bin/sh
    - -c
    - |
      set -e
      {{- $fullname := include "noether.fullname" .ctx }}
      # timescale/timescaledb is Alpine-based: busybox `nc` is present,
      # bash /dev/tcp is not. Use `nc -z` for a portable TCP probe.
      for dep in {{ range .deps }}{{ printf "%s-%s " $fullname . }}{{ end }}; do
        host="${dep%%:*}"; port="${dep##*:}"
        echo "waiting for ${host}:${port} ..."
        until nc -z "${host}" "${port}" 2>/dev/null; do sleep 2; done
        echo "${host}:${port} is up"
      done
{{- end -}}

{{/* Scheduling hints shared by every workload pod spec. */}}
{{- define "noether.scheduling" -}}
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.affinity }}
affinity:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}
