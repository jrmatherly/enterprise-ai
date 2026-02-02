# Enterprise AI Platform Helm Chart

Helm chart for deploying the Enterprise AI Platform to Kubernetes.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.8+
- PV provisioner (for stateful dependencies if self-hosting)

### External Dependencies

This chart deploys only the core application (backend + frontend). You must deploy these dependencies separately:

| Service | Recommended Helm Chart | Managed Service Alternative |

|---------|----------------------|---------------------------|
| PostgreSQL | bitnami/postgresql | Azure Database for PostgreSQL, AWS RDS |
| Redis | bitnami/redis | Azure Cache for Redis, AWS ElastiCache |
| Qdrant | qdrant/qdrant | Qdrant Cloud |
| Langfuse | langfuse/langfuse | Langfuse Cloud |
| MinIO | minio/minio | Azure Blob Storage, AWS S3 |

## Installation

### Add Helm Repository (if publishing)

```bash
# If chart is published to a Helm repo
helm repo add enterprise-ai https://charts.example.com
helm repo update
```

### Install from Local Chart

```bash
# Create namespace
kubectl create namespace eai

# Install with default values
helm install eai ./deploy/helm/enterprise-ai-platform -n eai

# Install with production values
helm install eai ./deploy/helm/enterprise-ai-platform -n eai \
  -f ./deploy/helm/enterprise-ai-platform/values-production.yaml

# Install with local dev values
helm install eai ./deploy/helm/enterprise-ai-platform -n eai \
  -f ./deploy/helm/enterprise-ai-platform/values-local.yaml
```

### Create Required Secrets

Before installing, create the required secrets:

```bash
# PostgreSQL
kubectl create secret generic postgresql-credentials \
  --from-literal=password='your-postgres-password' -n eai

# Redis
kubectl create secret generic redis-credentials \
  --from-literal=password='your-redis-password' -n eai

# Langfuse
kubectl create secret generic langfuse-credentials \
  --from-literal=publicKey='pk-lf-xxx' \
  --from-literal=secretKey='sk-lf-xxx' -n eai

# Azure AI
kubectl create secret generic azure-ai-credentials \
  --from-literal=eastusEndpoint='https://xxx.openai.azure.com/' \
  --from-literal=eastusApiKey='xxx' -n eai

# Azure EntraID
kubectl create secret generic azure-entraid-credentials \
  --from-literal=tenantId='xxx' \
  --from-literal=clientId='xxx' \
  --from-literal=clientSecret='xxx' -n eai

# better-auth
kubectl create secret generic better-auth-credentials \
  --from-literal=secret="$(openssl rand -base64 32)" -n eai
```

## Configuration

See `values.yaml` for all configurable options. Key configurations:

### Scaling

```yaml
backend:
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60
```

### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  tls:
    enabled: true
  pathBased:
    enabled: true
    host: ai.yourcompany.com
```

### External Services

```yaml
externalServices:
  postgresql:
    host: postgresql.database.svc.cluster.local
    port: 5432
    database: eai
    username: eai
    existingSecret: postgresql-credentials
    secretKey: password
```

## Upgrading

```bash
helm upgrade eai ./deploy/helm/enterprise-ai-platform -n eai \
  -f ./deploy/helm/enterprise-ai-platform/values-production.yaml
```

## Uninstalling

```bash
helm uninstall eai -n eai
```

## Values Files

| File | Description |

|------|-------------|
| `values.yaml` | Default values with documentation |
| `values-production.yaml` | Production-optimized settings |
| `values-local.yaml` | Local Kubernetes (minikube/kind/Docker Desktop) |

## Templates

| Template | Description |

|----------|-------------|
| `backend-deployment.yaml` | FastAPI backend deployment |
| `backend-service.yaml` | Backend ClusterIP service |
| `backend-hpa.yaml` | Backend horizontal pod autoscaler |
| `backend-pdb.yaml` | Backend pod disruption budget |
| `frontend-deployment.yaml` | Next.js frontend deployment |
| `frontend-service.yaml` | Frontend ClusterIP service |
| `frontend-hpa.yaml` | Frontend horizontal pod autoscaler |
| `frontend-pdb.yaml` | Frontend pod disruption budget |
| `configmap.yaml` | Shared configuration |
| `ingress.yaml` | Ingress resource |
| `networkpolicy.yaml` | Network policies |

## Security

- Pods run as non-root user (UID 1000)
- Read-only root filesystem (where possible)
- All capabilities dropped
- Network policies restrict traffic flow
- Secrets managed externally (not in values)

### External Secrets Integration

For production, use External Secrets Operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: azure-ai-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: azure-keyvault
    kind: ClusterSecretStore
  target:
    name: azure-ai-credentials
  data:
    - secretKey: eastusEndpoint
      remoteRef:
        key: azure-ai-eastus-endpoint
```

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod -n eai -l app.kubernetes.io/component=backend
kubectl logs -n eai -l app.kubernetes.io/component=backend
```

### Check Secret Mounting

```bash
kubectl exec -n eai -it deploy/eai-backend -- env | grep -E "(DATABASE|REDIS|AZURE)"
```

### Test Connectivity

```bash
kubectl port-forward -n eai svc/eai-frontend 3001:3001
kubectl port-forward -n eai svc/eai-backend 8000:8000
```

## Contributing

See the main repository for contribution guidelines.
