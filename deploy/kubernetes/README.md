# Kubernetes Manifests

Raw Kubernetes manifests for deploying the Enterprise AI Platform without Helm.

## Directory Structure

```
kubernetes/
├── base/                    # Base manifests (Kustomize-ready)
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── backend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── serviceaccount.yaml
│   ├── frontend/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── serviceaccount.yaml
│   └── shared/
│       ├── configmap.yaml
│       └── networkpolicy.yaml
├── overlays/
│   ├── development/         # Dev-specific patches
│   └── production/          # Prod-specific patches
└── secrets/                 # Secret templates (DO NOT commit actual values)
```

## Prerequisites

1. **Kubernetes Cluster** (1.25+)
2. **kubectl** configured for your cluster
3. **External Services Deployed:**
   - PostgreSQL (bitnami/postgresql or managed service)
   - Redis (bitnami/redis or managed service)
   - Qdrant (qdrant/qdrant or Qdrant Cloud)
   - Langfuse (langfuse/langfuse or Langfuse Cloud)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f base/namespace.yaml
```

### 2. Create Secrets

Copy the secret templates and fill in your values:

```bash
cp secrets/secrets-template.yaml secrets/secrets.yaml
# Edit secrets/secrets.yaml with your actual values
kubectl apply -f secrets/secrets.yaml -n eai
```

### 3. Deploy Using Kustomize

```bash
# Development
kubectl apply -k overlays/development

# Production
kubectl apply -k overlays/production
```

### 4. Verify Deployment

```bash
kubectl get pods -n eai
kubectl get svc -n eai
kubectl get ingress -n eai
```

## Using Helm Instead

For a more flexible deployment with built-in templating, use the Helm chart:

```bash
helm install eai ../helm/enterprise-ai-platform -n eai --create-namespace
```

See `../helm/enterprise-ai-platform/README.md` for Helm documentation.

## Secret Management

**⚠️ IMPORTANT: Never commit actual secrets to git!**

For production, use one of these approaches:

1. **External Secrets Operator** - Syncs secrets from HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
2. **Sealed Secrets** - Encrypts secrets that can be safely committed
3. **SOPS** - Mozilla's secret operations tool
4. **ArgoCD Vault Plugin** - For GitOps workflows

Example with External Secrets Operator:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: azure-ai-credentials
  namespace: eai
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
    - secretKey: eastusApiKey
      remoteRef:
        key: azure-ai-eastus-apikey
```

## Updating Deployments

After changing manifests:

```bash
kubectl apply -k overlays/production
```

For zero-downtime deployments:

```bash
kubectl rollout restart deployment/eai-backend -n eai
kubectl rollout restart deployment/eai-frontend -n eai
```

Monitor rollout:

```bash
kubectl rollout status deployment/eai-backend -n eai
```

## Troubleshooting

### Check Pod Logs

```bash
kubectl logs -n eai -l app.kubernetes.io/component=backend -f
kubectl logs -n eai -l app.kubernetes.io/component=frontend -f
```

### Describe Pod for Events

```bash
kubectl describe pod -n eai -l app.kubernetes.io/component=backend
```

### Check ConfigMap

```bash
kubectl get configmap -n eai eai-config -o yaml
```

### Test Connectivity

```bash
# Port forward to test locally
kubectl port-forward -n eai svc/eai-frontend 3001:3001
kubectl port-forward -n eai svc/eai-backend 8000:8000
```
