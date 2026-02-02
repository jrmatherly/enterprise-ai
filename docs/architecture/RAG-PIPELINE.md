# RAG Pipeline Architecture

This document describes the Retrieval-Augmented Generation (RAG) pipeline used in the Enterprise AI Platform.

## Overview

The RAG pipeline enables users to chat with their documents by:
1. Uploading documents to knowledge bases
2. Chunking and embedding document content
3. Storing vectors in Qdrant with access control metadata
4. Retrieving relevant context during chat
5. Injecting context into LLM prompts with citation support

## Components

### Embedder (`src/rag/embedder.py`)

Generates embeddings using Azure OpenAI's embedding models.

**Default Configuration:**
- Model: `text-embedding-3-large`
- Dimensions: 3072
- Batch size: 100 (for large documents)

### Vector Store (`src/rag/vector_store.py`)

Manages Qdrant collections for document storage and retrieval.

**Collection Schema:**
```json
{
  "vectors": {
    "size": 3072,
    "distance": "Cosine"
  },
  "payload_schema": {
    "text": "text",
    "document_id": "keyword",
    "chunk_index": "integer",
    "tenant_id": "keyword",
    "acl_users": "keyword[]",
    "acl_groups": "keyword[]",
    "metadata": "json"
  }
}
```

**Enterprise Optimizations:**
- Scalar quantization (4x memory reduction)
- On-disk payload storage for large text
- Tenant isolation via payload index

### Retriever (`src/rag/retriever.py`)

Orchestrates embedding generation and vector search with ACL filtering.

**Key Parameters:**
- `limit`: Maximum chunks to retrieve (default: 5)
- `score_threshold`: Minimum similarity score (default: 0.2)
- `max_chars`: Maximum context length (default: 8000)

## Embedding Model Considerations

### ⚠️ Important: Score Thresholds

**`text-embedding-3-large` produces lower similarity scores than other models.**

| Model | Typical Score Range | Recommended Threshold |

|-------|--------------------|-----------------------|
| `text-embedding-3-large` | 0.20 - 0.40 | **0.2** |
| `text-embedding-3-small` | 0.30 - 0.50 | 0.3 |
| `text-embedding-ada-002` | 0.70 - 0.90 | 0.7 |

**Common Mistake:** Using `score_threshold=0.5` with `text-embedding-3-large` will filter out ALL results, causing RAG to return empty context.

### Why Lower Scores?

`text-embedding-3-large` uses a different embedding space optimization that produces more discriminative but lower absolute similarity scores. This is by design and doesn't indicate worse performance—the relative ranking of results is still accurate.

## Access Control (ACL)

Every chunk stores ACL metadata for filtering:

```python
{
    "tenant_id": "org_123",      # Required: tenant isolation
    "acl_users": ["user_abc"],   # Users with direct access
    "acl_groups": ["dept_sales"] # Groups with access
}
```

**Filter Logic:**
```
tenant_id = current_tenant
AND (user_id IN acl_users OR any(group_ids) IN acl_groups)
```

## Knowledge Base Custom Instructions

Each knowledge base can have a custom `system_prompt` that provides domain-specific instructions to the LLM when that knowledge base is queried.

### How It Works

1. **KB Creation/Update:** Admins set `system_prompt` via the Knowledge Base API
2. **Chat Request:** User includes `knowledge_base_ids` in their chat request
3. **Prompt Assembly:** The runtime fetches and combines all KB system prompts
4. **System Prompt Injection:** Combined instructions are injected into the system prompt

### System Prompt Structure

The final system prompt is assembled in `AgentRuntime._build_system_prompt()`:

```
[Base Prompt - minimal if KB has custom instructions, full if not]

[GROUNDED MODE CONSTRAINTS - if any KB has grounded_only=true]

## Knowledge Base Instructions
[Combined KB system_prompts - if any knowledge bases have custom instructions]

<retrieved_context>
[RAG context with source citations - wrapped in tags for clear reference]
</retrieved_context>
```

**Key behaviors:**
- When KB provides custom instructions, the base prompt becomes minimal to allow persona override
- Retrieved context is wrapped in `<retrieved_context>` tags so KB instructions can reference it
- Grounding constraints appear before KB instructions when enabled

### Example KB System Prompt

```json
{
  "name": "HR Policies",
  "system_prompt": "When answering questions about HR policies:\n- Always cite the specific policy section\n- Include effective dates when relevant\n- Refer users to HR for sensitive topics\n- Never disclose individual employee information"
}
```

### Multiple Knowledge Bases

When a user queries multiple KBs, their system prompts are concatenated with double newlines:

```python
kb_instructions = "\n\n".join(prompts)  # From all selected KBs
```

### API Reference

**Create KB with instructions:**
```bash
POST /api/knowledge-bases
{
  "name": "Legal Docs",
  "description": "Legal agreements and contracts",
  "system_prompt": "Always include legal disclaimers..."
}
```

**Update KB instructions:**
```bash
PATCH /api/knowledge-bases/{id}
{
  "system_prompt": "Updated instructions..."
}
```

### Grounded Mode

Knowledge bases can enable **Grounded Mode** (`grounded_only: true`) to restrict the AI to ONLY respond using KB contents:

```bash
POST /api/knowledge-bases
{
  "name": "Store Policies",
  "system_prompt": "You are Store Operations...",
  "grounded_only": true
}
```

**When Grounded Mode is enabled:**
- AI receives strict constraints to only use `<retrieved_context>`
- If information isn't found, AI states: "I don't have information about that in my knowledge base"
- External knowledge, assumptions, and general information are blocked
- Every claim must be traceable to a source document

**Use Grounded Mode for:**
- Policy/compliance knowledge bases
- Legal or regulatory documents
- Product specifications requiring accuracy
- Training materials that must match official content

**Note:** If multiple KBs are queried and ANY has `grounded_only=true`, grounding is enforced for the entire response.

### Writing Custom Instructions

See the **[Custom Instructions Template](../reference/KB-CUSTOM-INSTRUCTIONS-TEMPLATE.md)** for:
- Fill-in template for writing effective instructions
- Examples for different use cases (operations, legal, IT support)
- Best practices and common mistakes
- How to reference `<retrieved_context>` in your instructions

## Citation Support

Retrieved chunks include source metadata for citations:

**Context Format:**
```
[1] First chunk of retrieved text...
[2] Second chunk of retrieved text...

---
Sources:
[1] Document.pdf (Section 15)
[2] Document.pdf (Section 42)
```

**System Prompt Instruction:**
The LLM is instructed to cite sources using bracket notation `[1]`, `[2]`, etc.

## Document Ingestion

### Chunking Strategy

Documents are chunked with:
- **Chunk size:** 1000 characters
- **Overlap:** 200 characters
- **Metadata preserved:** filename, mime_type, character positions

### Batch Processing

Large documents are processed in batches:
- Embedding batch: 100 chunks per API call
- Qdrant upsert batch: 100 points per request
- Timeout: 60 seconds per batch

## Configuration

### Environment Variables

```bash
# Embedding model
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Qdrant connection
QDRANT_HOST=localhost
QDRANT_PORT=6333

# RAG parameters (defaults in code)
# score_threshold=0.2
# chunk_size=1000
# chunk_overlap=200
```

## Troubleshooting

### RAG Returns Empty Results

1. **Check score_threshold:** Must be ≤ 0.3 for `text-embedding-3-large`
2. **Verify ACL filter:** User must be in `acl_users` or have matching group
3. **Check collection exists:** `curl http://localhost:6333/collections`
4. **Verify embeddings match:** Query and document embeddings must use same model

### Debug Logging

Enable debug output by checking backend logs:
```bash
docker logs eai-backend 2>&1 | grep -i "RAG\|Retriever\|VectorStore"
```

### Manual Qdrant Query

Test retrieval without ACL:
```bash
curl -X POST "http://localhost:6333/collections/{collection}/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5, "with_payload": ["text", "metadata"]}'
```

## Performance Tuning

### For Large Knowledge Bases (>10K documents)

1. Enable HNSW indexing with `ef_construct=128`
2. Use scalar quantization
3. Increase `score_threshold` slightly to reduce noise
4. Consider reducing `limit` to 3-4 chunks

### For Real-time Chat

1. Enable semantic caching for repeated queries
2. Use async batch processing for embedding
3. Pre-warm collections on startup

## Future Enhancements

- [ ] Page number extraction for PDFs
- [ ] Hybrid search (keyword + semantic)
- [ ] Re-ranking with cross-encoder
- [ ] Streaming chunk retrieval
- [ ] Multi-modal embeddings (images, tables)
