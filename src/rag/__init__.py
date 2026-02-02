"""RAG (Retrieval-Augmented Generation) package.

Components:
- VectorStore: Qdrant client for vector operations
- Embedder: Azure OpenAI embedding service
- Chunker: Document chunking strategies
- Retriever: Semantic search with access control
- Processor: Document ingestion pipeline
- Extractor: Text extraction from PDF, DOCX, TXT, MD
"""

from src.rag.chunking import Chunk, get_chunker
from src.rag.embedder import Embedder, get_embedder
from src.rag.extractors import DocumentExtractor, ExtractionError, get_extractor
from src.rag.processor import DocumentProcessor, ProcessingResult, get_processor
from src.rag.retriever import RetrievedChunk, Retriever, get_retriever
from src.rag.semantic_cache import SemanticCache, get_semantic_cache
from src.rag.vector_store import VectorStore, get_vector_store

__all__ = [
    "Chunk",
    "DocumentExtractor",
    "DocumentProcessor",
    "Embedder",
    "ExtractionError",
    "ProcessingResult",
    "RetrievedChunk",
    "Retriever",
    "SemanticCache",
    "VectorStore",
    "get_chunker",
    "get_embedder",
    "get_extractor",
    "get_processor",
    "get_retriever",
    "get_semantic_cache",
    "get_vector_store",
]
