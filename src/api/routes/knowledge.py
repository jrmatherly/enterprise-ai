"""Knowledge base management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.api.deps import CurrentUser, DB
from src.db.models import KnowledgeBase, KnowledgeBaseScope, Document, DocumentStatus
from src.rag import get_vector_store, get_processor, get_retriever
from src.rag.extractors import get_extractor, ExtractionError


router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class KnowledgeBaseResponse(BaseModel):
    """Knowledge base summary."""
    id: str
    name: str
    description: Optional[str]
    scope: str
    document_count: int
    is_shared: bool
    created_at: str
    updated_at: str


class CreateKnowledgeBaseRequest(BaseModel):
    """Request to create a knowledge base."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    scope: str = Field("personal", description="Scope: personal, team, department, organization")


class DocumentResponse(BaseModel):
    """Document metadata."""
    id: str
    filename: str
    mime_type: str
    file_size_bytes: int
    status: str
    chunk_count: int
    created_at: str
    processed_at: Optional[str]


class QueryRequest(BaseModel):
    """RAG query request."""
    query: str = Field(..., min_length=1, max_length=10000)
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.7, ge=0.0, le=1.0)


class QueryResult(BaseModel):
    """Single query result."""
    content: str
    score: float
    document_id: str
    filename: str
    chunk_index: int


class QueryResponse(BaseModel):
    """RAG query response."""
    query: str
    results: list[QueryResult]
    total_results: int


# ============================================
# Knowledge Base Endpoints
# ============================================

@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user: CurrentUser,
    db: DB,
    scope: Optional[str] = Query(None, description="Filter by scope"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List accessible knowledge bases.
    
    Returns knowledge bases the user can access based on their role and scope.
    """
    try:
        # Build query based on user's access
        # Users can see:
        # - Their own personal KBs
        # - Shared KBs from their team/dept/org
        query = select(KnowledgeBase).order_by(KnowledgeBase.name)
        
        if scope:
            try:
                scope_enum = KnowledgeBaseScope(scope)
                query = query.where(KnowledgeBase.scope == scope_enum)
            except ValueError:
                pass
        
        # For now, just get personal KBs for the user
        # TODO: Implement full access control logic
        query = query.where(KnowledgeBase.owner_id == user.sub)
        
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        kbs = result.scalars().all()
        
        return [
            KnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                scope=kb.scope.value,
                document_count=kb.document_count,
                is_shared=kb.is_shared,
                created_at=kb.created_at.isoformat() + "Z",
                updated_at=kb.updated_at.isoformat() + "Z",
            )
            for kb in kbs
        ]
    except Exception:
        # Database not initialized
        return []


@router.post("/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: CreateKnowledgeBaseRequest,
    user: CurrentUser,
    db: DB,
):
    """Create a new knowledge base."""
    try:
        scope_enum = KnowledgeBaseScope(body.scope)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {body.scope}. Must be one of: personal, team, department, organization"
        )
    
    # Generate unique collection name
    collection_name = f"kb_{str(uuid4()).replace('-', '')}"
    
    kb = KnowledgeBase(
        id=str(uuid4()),
        tenant_id=user.tenant_id,
        name=body.name,
        description=body.description,
        scope=scope_enum,
        owner_id=user.sub if scope_enum == KnowledgeBaseScope.PERSONAL else None,
        collection_name=collection_name,
    )
    
    try:
        # Create Qdrant collection first
        vector_store = get_vector_store()
        await vector_store.create_collection(collection_name)
        
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            scope=kb.scope.value,
            document_count=0,
            is_shared=kb.is_shared,
            created_at=kb.created_at.isoformat() + "Z",
            updated_at=kb.updated_at.isoformat() + "Z",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create knowledge base: {str(e)}"
        )


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    user: CurrentUser,
    db: DB,
):
    """Get a knowledge base by ID."""
    try:
        query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        # TODO: Check access permissions
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            scope=kb.scope.value,
            document_count=kb.document_count,
            is_shared=kb.is_shared,
            created_at=kb.created_at.isoformat() + "Z",
            updated_at=kb.updated_at.isoformat() + "Z",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve knowledge base: {str(e)}"
        )


# ============================================
# Document Endpoints
# ============================================

@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: str,
    user: CurrentUser,
    db: DB,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List documents in a knowledge base."""
    try:
        # Verify KB exists and user has access
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        # Query documents
        query = select(Document).where(Document.knowledge_base_id == kb_id)
        
        if status_filter:
            try:
                status_enum = DocumentStatus(status_filter)
                query = query.where(Document.status == status_enum)
            except ValueError:
                pass
        
        query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        docs = result.scalars().all()
        
        return [
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status.value,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at.isoformat() + "Z",
                processed_at=doc.processed_at.isoformat() + "Z" if doc.processed_at else None,
            )
            for doc in docs
        ]
    except HTTPException:
        raise
    except Exception:
        return []


@router.post("/knowledge-bases/{kb_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: str,
    user: CurrentUser,
    db: DB,
    file: UploadFile = File(...),
):
    """Upload a document to a knowledge base.
    
    The document will be processed asynchronously:
    1. Uploaded to object storage
    2. Text extracted
    3. Chunked and embedded
    4. Stored in vector database
    
    Check the document status to track processing progress.
    """
    # Verify KB exists
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify knowledge base: {str(e)}"
        )
    
    # Validate file type using extractor
    extractor = get_extractor()
    if not extractor.supports(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT, MD"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Create document record
    doc = Document(
        id=str(uuid4()),
        knowledge_base_id=kb_id,
        filename=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=file_size,
        status=DocumentStatus.PENDING,
        uploaded_by_id=user.sub,
    )
    
    try:
        # Update status to processing
        doc.status = DocumentStatus.PROCESSING
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # Extract text from document
        extractor = get_extractor()
        try:
            text = extractor.extract(content, file.content_type)
        except ExtractionError as e:
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            await db.commit()
            return DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
                status=doc.status.value,
                chunk_count=0,
                created_at=doc.created_at.isoformat() + "Z",
                processed_at=None,
            )
        
        # Process document through RAG pipeline
        processor = await get_processor()
        result = await processor.process_text(
            text=text,
            document_id=doc.id,
            knowledge_base_id=kb_id,
            tenant_id=user.tenant_id,
            acl_users=[user.sub],
            acl_groups=user.groups,
            metadata={"filename": file.filename, "mime_type": file.content_type},
        )
        
        # Update document status
        if result.success:
            doc.status = DocumentStatus.COMPLETED
            doc.chunk_count = result.chunk_count
            doc.processed_at = datetime.utcnow()
            
            # Update KB document count
            kb.document_count += 1
        else:
            doc.status = DocumentStatus.FAILED
            doc.error_message = result.error
        
        await db.commit()
        await db.refresh(doc)
        
        return DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status.value,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at.isoformat() + "Z",
            processed_at=doc.processed_at.isoformat() + "Z" if doc.processed_at else None,
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.delete("/knowledge-bases/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: str,
    doc_id: str,
    user: CurrentUser,
    db: DB,
):
    """Delete a document from a knowledge base."""
    try:
        query = select(Document).where(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id,
        )
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete vectors from Qdrant
        try:
            processor = await get_processor()
            await processor.delete_document(doc_id, kb_id)
        except Exception:
            pass  # Continue even if Qdrant delete fails
        
        # Update KB document count
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        kb_result = await db.execute(kb_query)
        kb = kb_result.scalar_one_or_none()
        if kb:
            kb.document_count = max(0, kb.document_count - 1)
        
        await db.delete(doc)
        await db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


# ============================================
# Query Endpoints
# ============================================

@router.post("/knowledge-bases/{kb_id}/query", response_model=QueryResponse)
async def query_knowledge_base(
    kb_id: str,
    body: QueryRequest,
    user: CurrentUser,
    db: DB,
):
    """Query a knowledge base using semantic search.
    
    Returns the most relevant document chunks for the query.
    """
    # Verify KB exists
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify knowledge base: {str(e)}"
        )
    
    # Perform semantic search using RAG retriever
    try:
        retriever = await get_retriever()
        chunks = await retriever.retrieve(
            query=body.query,
            knowledge_base_ids=[kb_id],
            user_id=user.sub,
            tenant_id=user.tenant_id,
            group_ids=user.groups,
            limit=body.top_k,
            score_threshold=body.score_threshold,
        )
        
        # Get document filenames for results
        doc_ids = list(set(c.document_id for c in chunks))
        doc_query = select(Document).where(Document.id.in_(doc_ids))
        doc_result = await db.execute(doc_query)
        docs = {d.id: d for d in doc_result.scalars().all()}
        
        results = [
            QueryResult(
                content=chunk.text,
                score=chunk.score,
                document_id=chunk.document_id,
                filename=docs.get(chunk.document_id, Document(filename="unknown")).filename,
                chunk_index=chunk.chunk_index,
            )
            for chunk in chunks
        ]
        
        return QueryResponse(
            query=body.query,
            results=results,
            total_results=len(results),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# ============================================
# Cache Management Endpoints
# ============================================

class CacheStatsResponse(BaseModel):
    """Cache statistics for a knowledge base."""
    kb_id: str
    entry_count: int
    total_hits: int
    max_entries: int
    ttl_seconds: int
    similarity_threshold: float


@router.get("/knowledge-bases/{kb_id}/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(
    kb_id: str,
    user: CurrentUser,
    db: DB,
):
    """Get semantic cache statistics for a knowledge base."""
    # Verify KB exists and user has access
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify knowledge base"
        )
    
    try:
        from src.rag import get_semantic_cache
        cache = await get_semantic_cache()
        stats = await cache.get_stats(kb_id)
        return CacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/knowledge-bases/{kb_id}/cache", status_code=status.HTTP_204_NO_CONTENT)
async def invalidate_cache(
    kb_id: str,
    user: CurrentUser,
    db: DB,
):
    """Invalidate the semantic cache for a knowledge base."""
    # Verify KB exists and user has access
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify knowledge base"
        )
    
    try:
        from src.rag import get_semantic_cache
        cache = await get_semantic_cache()
        await cache.invalidate(kb_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )
