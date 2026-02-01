# Azure AI Foundry Setup Guide

This guide covers setting up Azure AI Foundry for the Enterprise AI Platform, including multi-region model access.

---

## Understanding Azure AI Foundry Architecture

### The Multi-Region Challenge

**Problem:** Azure AI Foundry models are only available in specific regions. Different models may require different regions:
- GPT-4o might be in East US
- GPT-5 might only be in East US 2
- Claude models are in East US 2 and Sweden Central

**Azure's Limitation:** A single Azure AI Foundry resource cannot span multiple regions.

### Solutions

| Approach | Complexity | Best For |

|----------|------------|----------|
| **Multiple Endpoints (our approach)** | Low | MVP, development |
| **Azure API Management Gateway** | Medium | Production with load balancing |
| **Cross-Region Consumption** | Low | Single model in different region |

For MVP, we'll use **multiple endpoints with model-based routing** in the application layer.

---

## Recommended Architecture

### Option 1: Multiple Foundry Resources (Recommended for MVP)

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
│                                                          │
│   Model Router (picks endpoint based on model name)     │
│                                                          │
└────────────┬───────────────────────────┬────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────────┐   ┌────────────────────────┐
│  Azure AI Foundry      │   │  Azure AI Foundry      │
│  (East US)             │   │  (East US 2)           │
│                        │   │                        │
│  • gpt-4o-mini         │   │  • gpt-5               │
│  • gpt-4o              │   │  • claude-sonnet-4.5   │
│  • text-embedding-ada  │   │                        │
└────────────────────────┘   └────────────────────────┘
```

### Option 2: Azure API Management (Production)

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Azure API Management                        │
│                                                          │
│   • Unified endpoint                                     │
│   • Load balancing                                       │
│   • Failover / circuit breaker                          │
│   • Rate limiting                                        │
│   • Authentication                                       │
└────────┬─────────────────────────────────┬──────────────┘
         │                                 │
         ▼                                 ▼
┌────────────────────┐           ┌────────────────────┐
│  East US Foundry   │           │  East US 2 Foundry │
└────────────────────┘           └────────────────────┘
```

---

## Setup: Multiple Foundry Resources

### Step 1: Create Foundry Resources

Create a resource in each region where you need model access.

#### East US Resource
```bash
# Azure CLI
az cognitiveservices account create \
  --name "eai-foundry-eastus" \
  --resource-group "rg-enterprise-ai" \
  --kind "AIServices" \
  --sku "S0" \
  --location "eastus" \
  --yes
```

#### East US 2 Resource
```bash
az cognitiveservices account create \
  --name "eai-foundry-eastus2" \
  --resource-group "rg-enterprise-ai" \
  --kind "AIServices" \
  --sku "S0" \
  --location "eastus2" \
  --yes
```

### Step 2: Deploy Models

#### Via Azure Portal
1. Go to each Foundry resource
2. Navigate to Model Deployments
3. Deploy the models available in that region:
   - **East US:** gpt-4o, gpt-4o-mini, text-embedding-ada-002
   - **East US 2:** gpt-5, Claude models (if available)

#### Via Azure CLI
```bash
# Deploy gpt-4o-mini in East US
az cognitiveservices account deployment create \
  --name "eai-foundry-eastus" \
  --resource-group "rg-enterprise-ai" \
  --deployment-name "gpt-4o-mini" \
  --model-name "gpt-4o-mini" \
  --model-version "2024-07-18" \
  --model-format "OpenAI" \
  --sku-capacity 10 \
  --sku-name "Standard"
```

### Step 3: Get Endpoints and Keys

```bash
# East US endpoint and key
az cognitiveservices account show \
  --name "eai-foundry-eastus" \
  --resource-group "rg-enterprise-ai" \
  --query "properties.endpoint"

az cognitiveservices account keys list \
  --name "eai-foundry-eastus" \
  --resource-group "rg-enterprise-ai"

# East US 2 endpoint and key
az cognitiveservices account show \
  --name "eai-foundry-eastus2" \
  --resource-group "rg-enterprise-ai" \
  --query "properties.endpoint"

az cognitiveservices account keys list \
  --name "eai-foundry-eastus2" \
  --resource-group "rg-enterprise-ai"
```

---

## Configuration Design

### Environment Variables

All Azure AI configuration should be externalized to environment variables:

```bash
# .env file structure for multi-region

# ============================================
# Azure AI Foundry - Primary (East US)
# ============================================
AZURE_AI_EASTUS_ENDPOINT=https://eai-foundry-eastus.openai.azure.com/
AZURE_AI_EASTUS_API_KEY=your-eastus-api-key
AZURE_AI_EASTUS_MODELS=gpt-4o,gpt-4o-mini,text-embedding-ada-002

# ============================================
# Azure AI Foundry - Secondary (East US 2)
# ============================================
AZURE_AI_EASTUS2_ENDPOINT=https://eai-foundry-eastus2.openai.azure.com/
AZURE_AI_EASTUS2_API_KEY=your-eastus2-api-key
AZURE_AI_EASTUS2_MODELS=gpt-5,claude-sonnet-4.5

# ============================================
# Model Routing Configuration
# ============================================
# JSON mapping of model -> region
AZURE_AI_MODEL_ROUTING={"gpt-4o":"eastus","gpt-4o-mini":"eastus","gpt-5":"eastus2","claude-sonnet-4.5":"eastus2","text-embedding-ada-002":"eastus"}

# Default model and region
AZURE_AI_DEFAULT_MODEL=gpt-4o-mini
AZURE_AI_DEFAULT_REGION=eastus

# ============================================
# API Version
# ============================================
AZURE_OPENAI_API_VERSION=2024-10-21
```

### Configuration Schema (config.py)

```python
# config.py
import os
import json
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AzureAIEndpoint:
    """Configuration for a single Azure AI Foundry endpoint."""
    endpoint: str
    api_key: str
    models: list[str]
    
@dataclass
class AzureAIConfig:
    """Multi-region Azure AI Foundry configuration."""
    endpoints: Dict[str, AzureAIEndpoint]
    model_routing: Dict[str, str]  # model_name -> region
    default_model: str
    default_region: str
    api_version: str
    
    @classmethod
    def from_env(cls) -> "AzureAIConfig":
        """Load configuration from environment variables."""
        endpoints = {}
        
        # Discover endpoints from environment
        # Pattern: AZURE_AI_{REGION}_ENDPOINT
        for key, value in os.environ.items():
            if key.startswith("AZURE_AI_") and key.endswith("_ENDPOINT"):
                region = key.replace("AZURE_AI_", "").replace("_ENDPOINT", "").lower()
                api_key_var = f"AZURE_AI_{region.upper()}_API_KEY"
                models_var = f"AZURE_AI_{region.upper()}_MODELS"
                
                endpoints[region] = AzureAIEndpoint(
                    endpoint=value,
                    api_key=os.environ.get(api_key_var, ""),
                    models=os.environ.get(models_var, "").split(",")
                )
        
        # Load model routing
        model_routing_json = os.environ.get("AZURE_AI_MODEL_ROUTING", "{}")
        model_routing = json.loads(model_routing_json)
        
        return cls(
            endpoints=endpoints,
            model_routing=model_routing,
            default_model=os.environ.get("AZURE_AI_DEFAULT_MODEL", "gpt-4o-mini"),
            default_region=os.environ.get("AZURE_AI_DEFAULT_REGION", "eastus"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        )
    
    def get_endpoint_for_model(self, model: str) -> AzureAIEndpoint:
        """Get the appropriate endpoint for a given model."""
        region = self.model_routing.get(model, self.default_region)
        return self.endpoints[region]
```

### Model Router Implementation

```python
# model_router.py
from openai import AzureOpenAI
from typing import Optional
from config import AzureAIConfig

class ModelRouter:
    """Routes requests to the appropriate Azure AI Foundry endpoint based on model."""
    
    def __init__(self, config: Optional[AzureAIConfig] = None):
        self.config = config or AzureAIConfig.from_env()
        self._clients: dict[str, AzureOpenAI] = {}
    
    def _get_client(self, region: str) -> AzureOpenAI:
        """Get or create an OpenAI client for a region."""
        if region not in self._clients:
            endpoint_config = self.config.endpoints[region]
            self._clients[region] = AzureOpenAI(
                api_key=endpoint_config.api_key,
                api_version=self.config.api_version,
                azure_endpoint=endpoint_config.endpoint
            )
        return self._clients[region]
    
    def get_client_for_model(self, model: str) -> AzureOpenAI:
        """Get the appropriate client for a given model."""
        endpoint = self.config.get_endpoint_for_model(model)
        region = self.config.model_routing.get(model, self.config.default_region)
        return self._get_client(region)
    
    def chat_completion(self, model: str, messages: list, **kwargs):
        """Route a chat completion request to the appropriate endpoint."""
        client = self.get_client_for_model(model)
        return client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    def list_available_models(self) -> list[str]:
        """List all available models across all endpoints."""
        models = []
        for endpoint in self.config.endpoints.values():
            models.extend(endpoint.models)
        return list(set(models))

# Usage
router = ModelRouter()

# Automatically routes to East US
response = router.chat_completion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Automatically routes to East US 2
response = router.chat_completion(
    model="gpt-5",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

---

## Using with Microsoft Agent Framework

```python
# agent_with_routing.py
import os
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from config import AzureAIConfig

config = AzureAIConfig.from_env()

def create_agent(model: str, name: str, instructions: str):
    """Create an agent using the appropriate endpoint for the model."""
    endpoint_config = config.get_endpoint_for_model(model)
    
    # Option 1: API Key auth
    return AzureOpenAIResponsesClient(
        endpoint=endpoint_config.endpoint,
        api_key=endpoint_config.api_key,
        api_version=config.api_version,
    ).create_agent(
        name=name,
        instructions=instructions,
        model=model,
    )
    
    # Option 2: Azure CLI auth (comment out api_key above)
    # return AzureOpenAIResponsesClient(
    #     endpoint=endpoint_config.endpoint,
    #     credential=AzureCliCredential(),
    #     api_version=config.api_version,
    # ).create_agent(
    #     name=name,
    #     instructions=instructions,
    #     model=model,
    # )

# Usage
agent = create_agent(
    model="gpt-4o-mini",  # Routes to East US
    name="AssistantBot",
    instructions="You are a helpful assistant."
)
```

---

## RBAC Configuration

For each Foundry resource, users need appropriate roles:

### Required Roles

| Role | Permissions |

|------|-------------|
| **Cognitive Services OpenAI User** | Use deployed models |
| **Cognitive Services OpenAI Contributor** | Use + manage deployments |
| **Cognitive Services Contributor** | Full management access |

### Assign Roles

```bash
# Get your user object ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Assign role for East US resource
az role assignment create \
  --assignee $USER_ID \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/{sub-id}/resourceGroups/rg-enterprise-ai/providers/Microsoft.CognitiveServices/accounts/eai-foundry-eastus"

# Assign role for East US 2 resource
az role assignment create \
  --assignee $USER_ID \
  --role "Cognitive Services OpenAI User" \
  --scope "/subscriptions/{sub-id}/resourceGroups/rg-enterprise-ai/providers/Microsoft.CognitiveServices/accounts/eai-foundry-eastus2"
```

---

## Secrets Management

### Development: .env file
```bash
# Keep .env out of source control
echo ".env" >> .gitignore
```

### Production Options

| Option | Recommendation |

|--------|----------------|
| **Azure Key Vault** | Best for Azure deployments |
| **Kubernetes Secrets** | Good for K8s with sealed-secrets or external-secrets |
| **1Password** | You already use this |
| **Environment variables** | Injected by deployment pipeline |

### Kubernetes Secret Example
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: azure-ai-credentials
type: Opaque
stringData:
  AZURE_AI_EASTUS_ENDPOINT: "https://eai-foundry-eastus.openai.azure.com/"
  AZURE_AI_EASTUS_API_KEY: "your-key"
  AZURE_AI_EASTUS2_ENDPOINT: "https://eai-foundry-eastus2.openai.azure.com/"
  AZURE_AI_EASTUS2_API_KEY: "your-key"
  AZURE_AI_MODEL_ROUTING: '{"gpt-4o":"eastus","gpt-5":"eastus2"}'
```

---

## Future: Azure API Management Gateway

When ready for production, consider adding Azure API Management:

### Benefits
- Single endpoint for all models
- Load balancing across regions
- Automatic failover
- Rate limiting
- Analytics and monitoring
- Circuit breaker pattern

### Resources
- [Azure OpenAI Gateway Multi-Backend](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/azure-openai-gateway-multi-backend)
- [Smart Load Balancing for OpenAI](https://github.com/Azure-Samples/openai-apim-lb)

---

## Checklist

### Per Region
- [ ] Create Foundry resource
- [ ] Deploy required models
- [ ] Note endpoint URL
- [ ] Get API key (or configure RBAC)
- [ ] Assign user roles

### Configuration
- [ ] Create .env file with all endpoints
- [ ] Define model routing JSON
- [ ] Set default model and region
- [ ] Test each endpoint individually

### Verification
```python
# test_all_endpoints.py
from config import AzureAIConfig
from model_router import ModelRouter

config = AzureAIConfig.from_env()
router = ModelRouter(config)

# Test each configured model
for model in router.list_available_models():
    try:
        response = router.chat_completion(
            model=model,
            messages=[{"role": "user", "content": "Say 'test successful'"}],
            max_tokens=10
        )
        print(f"✅ {model}: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ {model}: {e}")
```

---

*Document created: 2026-01-31*
