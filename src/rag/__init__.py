"""RAG (Retrieval-Augmented Generation) package.

Components:
- VectorStore: Qdrant client for vector operations
- Embedder: Azure OpenAI embedding service
- Chunker: Document chunking strategies
- Retriever: Semantic search with access control
- Processor: Document ingestion pipeline
- Extractor: Text extraction from PDF, DOCX, TXT, MD
"""

from src.rag.vector_store import VectorStore, get_vector_store
from src.rag.embedder import Embedder, get_embedder
from src.rag.retriever import Retriever, get_retriever, RetrievedChunk
from src.rag.processor import DocumentProcessor, get_processor, ProcessingResult
from src.rag.chunking import Chunk, get_chunker
from src.rag.extractors import DocumentExtractor, get_extractor, ExtractionError
from src.rag.semantic_cache import SemanticCache, get_semantic_cache

__all__ = [
    "VectorStore",
    "get_vector_store",
    "Embedder", 
    "get_embedder",
    "Retriever",
    "get_retriever",
    "RetrievedChunk",
    "DocumentProcessor",
    "get_processor",
    "ProcessingResult",
    "Chunk",
    "get_chunker",
    "DocumentExtractor",
    "get_extractor",
    "ExtractionError",
    "SemanticCache",
    "get_semantic_cache",
]
