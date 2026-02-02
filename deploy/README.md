# Deployment

This directory contains all deployment configurations for the Enterprise AI Platform.

## Directory Structure

```
deploy/
├── docker/                  # Docker build files
│   ├── Dockerfile.backend   # Production backend image
│   └── Dockerfile.frontend  # Production frontend image
├── helm/                    # Helm chart (recommended)
│   └── enterprise-ai-platform/
│       ├── Chart.yaml
│       ├── values.yaml
│       ├── values-production.yaml
│       ├── values-local.yaml
│       └── templates/
└── kubernetes/              # Raw Kubernetes manifests
    ├── base/               # Base manifests (Kustomize)
    ├── overlays/           # Environment-specific patches
    │   ├── development/
    │   └── production/
    └── secrets/            # Secret templates
```

## Deployment Options

### Option 1: Helm (Recommended)

Best for: Production deployments, GitOps, teams familiar with Helm.

```bash
# Install
helm install eai ./helm/enterprise-ai-platform -n eai --create-namespace \
  -f ./helm/enterprise-ai-platform/values-production.yaml

# Upgrade
helm upgrade eai ./helm/enterprise-ai-platform -n eai \
  -f ./helm/enterprise-ai-platform/values-production.yaml

# Uninstall
helm uninstall eai -n eai
```

See [helm/enterprise-ai-platform/README.md](helm/enterprise-ai-platform/README.md) for details.

### Option 2: Kustomize

Best for: Teams preferring raw manifests, kubectl-centric workflows.

```bash
# Development
kubectl apply -k kubernetes/overlays/development

# Production
kubectl apply -k kubernetes/overlays/production
```

See [kubernetes/README.md](kubernetes/README.md) for details.

### Option 3: Docker Compose (Local Development)

Best for: Local development with hot reload.

```bash
cd ../dev
docker compose up -d
```

See [../dev/README.md](../dev/README.md) for details.

## Architecture

```
┌─────────────┐     ┌─────────────┐
│   Ingress   │────▶│  Frontend   │──┐
│   (nginx)   │     │  (Next.js)  │  │
└─────────────┘     └─────────────┘  │
                           │         │
                           ▼         ▼
┌─────────────┐     ┌─────────────────────┐
│   Users     │────▶│       Backend       │
│             │     │      (FastAPI)      │
└─────────────┘     └─────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌─────────────┐     ┌─────────────┐    ┌───────────┐
│  PostgreSQL │     │    Redis    │    │   Qdrant  │
│  (Database) │     │   (Cache)   │    │  (Vector) │
└─────────────┘     └─────────────┘    └───────────┘
```

## External Dependencies

The platform requires these external services:

| Service | Purpose | Deployment Options |
|---------|---------|-------------------|
| PostgreSQL | Primary database, auth sessions | Bitnami Helm, Azure PostgreSQL, AWS RDS |
| Redis | Caching, rate limiting, queues | Bitnami Helm, Azure Cache, AWS ElastiCache |
| Qdrant | Vector database for RAG | Qdrant Helm, Qdrant Cloud |
| Langfuse | LLM observability | Langfuse Helm, Langfuse Cloud |
| MinIO | Object storage (optional) | MinIO Helm, Azure Blob, AWS S3 |

### Deploying Dependencies with Helm

```bash
# PostgreSQL
helm install postgres bitnami/postgresql -n database --create-namespace \
  --set auth.postgresPassword=secretpassword \
  --set auth.database=eai

# Redis
helm install redis bitnami/redis -n cache --create-namespace \
  --set auth.password=secretpassword

# Qdrant
helm install qdrant qdrant/qdrant -n vector --create-namespace

# Langfuse (see langfuse docs for full setup)
helm install langfuse langfuse/langfuse -n observability --create-namespace
```

## Secrets Management

⚠️ **Never commit real secrets to git!**

### Development

Use the secret templates in `kubernetes/secrets/` or create secrets directly:

```bash
kubectl create secret generic postgresql-credentials \
  --from-literal=password='your-password' -n eai
```

### Production

Use one of these approaches:

1. **External Secrets Operator** - Sync from Vault, AWS SM, Azure KV
2. **Sealed Secrets** - Encrypted secrets safe for git
3. **SOPS** - Mozilla's secrets operations tool
4. **ArgoCD Vault Plugin** - For GitOps with Vault

## CI/CD

### GitHub Actions

The repository includes a GitHub Actions workflow that:

1. Builds container images on push to main
2. Pushes to GitHub Container Registry (ghcr.io)
3. Runs security scans (Trivy)
4. Optionally deploys to staging/production

### GitOps (ArgoCD)

Example ArgoCD Application:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: enterprise-ai-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/jrmatherly/enterprise-ai.git
    targetRevision: main
    path: deploy/helm/enterprise-ai-platform
    helm:
      valueFiles:
        - values-production.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: eai-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Monitoring

### Prometheus + Grafana

Both backend and frontend expose metrics:

- Backend: `/metrics` (Prometheus format)
- Frontend: Via Next.js metrics

### Langfuse

LLM observability is built-in via Langfuse integration. Configure `LANGFUSE_*` environment variables.

## Scaling Considerations

### Backend

- CPU-bound for embedding generation
- Memory-bound for large context windows
- Scale horizontally based on request rate

### Frontend

- Mostly I/O bound (proxying to backend)
- Can run fewer replicas than backend
- Consider CDN for static assets

### Database

- Use read replicas for scaling reads
- Connection pooling (PgBouncer) for many connections
- Regular VACUUM and index maintenance

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**: Check node resources, PVC provisioning
2. **CrashLoopBackOff**: Check logs, secrets, database connectivity
3. **503 errors**: Check service endpoints, network policies
4. **Slow responses**: Check resource limits, database queries

### Debug Commands

```bash
# Pod status
kubectl get pods -n eai -o wide

# Pod logs
kubectl logs -n eai -l app.kubernetes.io/component=backend -f

# Describe pod
kubectl describe pod -n eai <pod-name>

# Exec into pod
kubectl exec -n eai -it deploy/eai-backend -- /bin/sh

# Check endpoints
kubectl get endpoints -n eai
```
