apiVersion: v1
kind: Secret
metadata:
  name: postgres-auth
type: Opaque
data:
  postgres-password: {{ .Values.postgresql.auth.password | b64enc }}
  postgres-username: {{ .Values.postgresql.auth.username | b64enc }}
  postgres-database: {{ .Values.postgresql.auth.database | b64enc }}
