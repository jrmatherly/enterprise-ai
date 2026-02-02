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
