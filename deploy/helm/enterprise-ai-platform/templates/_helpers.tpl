{{/*
Expand the name of the chart.
*/}}
{{- define "enterprise-ai-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "enterprise-ai-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "enterprise-ai-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "enterprise-ai-platform.labels" -}}
helm.sh/chart: {{ include "enterprise-ai-platform.chart" . }}
{{ include "enterprise-ai-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "enterprise-ai-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "enterprise-ai-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Backend name
*/}}
{{- define "enterprise-ai-platform.backend.name" -}}
{{- printf "%s-backend" (include "enterprise-ai-platform.fullname" .) }}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "enterprise-ai-platform.backend.labels" -}}
{{ include "enterprise-ai-platform.labels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "enterprise-ai-platform.backend.selectorLabels" -}}
{{ include "enterprise-ai-platform.selectorLabels" . }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Frontend name
*/}}
{{- define "enterprise-ai-platform.frontend.name" -}}
{{- printf "%s-frontend" (include "enterprise-ai-platform.fullname" .) }}
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "enterprise-ai-platform.frontend.labels" -}}
{{ include "enterprise-ai-platform.labels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "enterprise-ai-platform.frontend.selectorLabels" -}}
{{ include "enterprise-ai-platform.selectorLabels" . }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Create the name of the backend service account to use
*/}}
{{- define "enterprise-ai-platform.backend.serviceAccountName" -}}
{{- if .Values.backend.serviceAccount.create }}
{{- default (include "enterprise-ai-platform.backend.name" .) .Values.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the frontend service account to use
*/}}
{{- define "enterprise-ai-platform.frontend.serviceAccountName" -}}
{{- if .Values.frontend.serviceAccount.create }}
{{- default (include "enterprise-ai-platform.frontend.name" .) .Values.frontend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.frontend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend image
*/}}
{{- define "enterprise-ai-platform.backend.image" -}}
{{- printf "%s:%s" .Values.backend.image.repository (default .Chart.AppVersion .Values.backend.image.tag) }}
{{- end }}

{{/*
Frontend image
*/}}
{{- define "enterprise-ai-platform.frontend.image" -}}
{{- printf "%s:%s" .Values.frontend.image.repository (default .Chart.AppVersion .Values.frontend.image.tag) }}
{{- end }}

{{/*
PostgreSQL connection URL
*/}}
{{- define "enterprise-ai-platform.postgresql.url" -}}
{{- $host := .Values.externalServices.postgresql.host -}}
{{- $port := .Values.externalServices.postgresql.port -}}
{{- $db := .Values.externalServices.postgresql.database -}}
{{- $user := .Values.externalServices.postgresql.username -}}
postgresql+asyncpg://{{ $user }}:$(POSTGRES_PASSWORD)@{{ $host }}:{{ $port }}/{{ $db }}
{{- end }}

{{/*
PostgreSQL connection URL (sync driver for frontend/Prisma)
*/}}
{{- define "enterprise-ai-platform.postgresql.syncUrl" -}}
{{- $host := .Values.externalServices.postgresql.host -}}
{{- $port := .Values.externalServices.postgresql.port -}}
{{- $db := .Values.externalServices.postgresql.database -}}
{{- $user := .Values.externalServices.postgresql.username -}}
postgresql://{{ $user }}:$(POSTGRES_PASSWORD)@{{ $host }}:{{ $port }}/{{ $db }}
{{- end }}

{{/*
Qdrant URL
*/}}
{{- define "enterprise-ai-platform.qdrant.url" -}}
{{- $host := .Values.externalServices.qdrant.host -}}
{{- $port := .Values.externalServices.qdrant.port -}}
http://{{ $host }}:{{ $port }}
{{- end }}

{{/*
Langfuse URL
*/}}
{{- define "enterprise-ai-platform.langfuse.url" -}}
{{- $host := .Values.externalServices.langfuse.host -}}
{{- $port := .Values.externalServices.langfuse.port -}}
http://{{ $host }}:{{ $port }}
{{- end }}
