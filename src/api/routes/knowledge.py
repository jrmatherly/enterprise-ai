"""Knowledge base management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.api.deps import CurrentUser, DB
from src.db.models import KnowledgeBase, KnowledgeBaseScope, Document, DocumentStatus


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
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        
        # TODO: Create Qdrant collection
        
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
    
    # Validate file type
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    }
    
    if file.content_type not in allowed_types:
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
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # TODO: Upload to MinIO
        # TODO: Queue for async processing
        
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
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
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
        
        # TODO: Delete from MinIO
        # TODO: Delete vectors from Qdrant
        
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
    
    # TODO: Generate embedding for query
    # TODO: Search Qdrant collection
    # TODO: Return results
    
    # Placeholder response
    return QueryResponse(
        query=body.query,
        results=[],
        total_results=0,
    )
