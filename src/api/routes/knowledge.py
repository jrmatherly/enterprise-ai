"""Knowledge base management endpoints."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.api.deps import DB, CurrentUser
from src.auth.oidc import UserClaims
from src.core.config import get_settings
from src.db.models import Document, DocumentStatus, KnowledgeBase, KnowledgeBaseScope
from src.rag import get_processor, get_retriever, get_vector_store
from src.rag.extractors import ExtractionError, get_extractor

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base summary."""

    id: str
    name: str
    description: str | None
    scope: str
    document_count: int
    is_shared: bool
    created_at: str
    updated_at: str


class CreateKnowledgeBaseRequest(BaseModel):
    """Request to create a knowledge base."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
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
    processed_at: str | None


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
# Access Control Helpers
# ============================================


def can_access_kb(kb: KnowledgeBase, user: "UserClaims") -> bool:
    """Check if a user can access a knowledge base.

    Access rules:
    - Personal KB: only owner can access
    - Team/Department/Organization: user must be in shared_with or same tenant
    """
    from src.db.models import KnowledgeBaseScope

    if kb.scope == KnowledgeBaseScope.PERSONAL:
        # Personal KBs are only accessible by owner
        return kb.owner_id == user.sub

    # For shared KBs, check if user is in shared_with list
    if user.sub in (kb.shared_with or []):
        return True

    # Or if any of user's groups are in shared_with
    for group in user.groups or []:
        if group in (kb.shared_with or []):
            return True

    # For team/dept/org scope, check tenant match
    return kb.tenant_id == user.tenant_id


# ============================================
# Knowledge Base Endpoints
# ============================================


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user: CurrentUser,
    db: DB,
    scope: str | None = Query(None, description="Filter by scope"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List accessible knowledge bases.

    Returns knowledge bases the user can access based on their role and scope.
    """
    from sqlalchemy import or_

    try:
        # Build query based on user's access
        # Users can see:
        # - Their own personal KBs (owner_id matches)
        # - Shared KBs where they're in shared_with list
        # - Team/Dept/Org KBs in their tenant
        query = select(KnowledgeBase).order_by(KnowledgeBase.name)

        if scope:
            try:
                scope_enum = KnowledgeBaseScope(scope)
                query = query.where(KnowledgeBase.scope == scope_enum)
            except ValueError:
                pass

        # Access control: personal OR shared with user OR same tenant for non-personal
        access_conditions = [
            # Personal KBs owned by user
            KnowledgeBase.owner_id == user.sub,
            # Same tenant for non-personal KBs
            (KnowledgeBase.tenant_id == user.tenant_id)
            & (KnowledgeBase.scope != KnowledgeBaseScope.PERSONAL),
        ]
        query = query.where(or_(*access_conditions))

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


@router.post(
    "/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED
)
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
            detail=f"Invalid scope: {body.scope}. Must be one of: personal, team, department, organization",
        ) from None

    # Generate unique collection name
    collection_name = f"kb_{str(uuid4()).replace('-', '')}"

    # Get embedding model from config
    settings = get_settings()

    kb = KnowledgeBase(
        id=str(uuid4()),
        tenant_id=user.tenant_id,
        name=body.name,
        description=body.description,
        scope=scope_enum,
        owner_id=user.sub if scope_enum == KnowledgeBaseScope.PERSONAL else None,
        collection_name=collection_name,
        embedding_model=settings.embedding_model,  # Use configured model
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
            detail=f"Failed to create knowledge base: {e!s}",
        ) from None


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )

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
            detail=f"Failed to retrieve knowledge base: {e!s}",
        ) from None


@router.delete("/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str,
    user: CurrentUser,
    db: DB,
):
    """Delete a knowledge base and all its documents.

    Only the owner (for personal scope) or users with appropriate permissions
    can delete a knowledge base.
    """
    try:
        query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(query)
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check ownership for personal KBs, or access for shared KBs
        if kb.scope == KnowledgeBaseScope.PERSONAL and kb.owner_id != user.sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can delete this knowledge base",
            )
        if kb.scope != KnowledgeBaseScope.PERSONAL and not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )

        # Delete Qdrant collection
        try:
            vector_store = get_vector_store()
            await vector_store.delete_collection(kb.collection_name)
        except Exception:
            pass  # Continue even if Qdrant delete fails

        # Delete all documents in this KB
        delete_docs_query = select(Document).where(Document.knowledge_base_id == kb_id)
        docs_result = await db.execute(delete_docs_query)
        for doc in docs_result.scalars().all():
            await db.delete(doc)

        # Delete the knowledge base
        await db.delete(kb)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete knowledge base: {e!s}",
        ) from None


# ============================================
# Document Endpoints
# ============================================


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    kb_id: str,
    user: CurrentUser,
    db: DB,
    status_filter: str | None = Query(None, alias="status"),
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
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


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
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
    # Verify KB exists and user has access
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify knowledge base: {e!s}",
        ) from None

    # Validate file type using extractor
    extractor = get_extractor()
    if not extractor.supports(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT, MD",
        ) from None

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
            collection_name=kb.collection_name,
            tenant_id=user.tenant_id,
            acl_users=[user.sub],
            acl_groups=user.groups,
            metadata={"filename": file.filename, "mime_type": file.content_type},
        )

        # Update document status
        if result.success:
            doc.status = DocumentStatus.COMPLETED
            doc.chunk_count = result.chunk_count
            doc.processed_at = datetime.now(UTC)

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
            detail=f"Failed to process document: {e!s}",
        ) from None


@router.delete(
    "/knowledge-bases/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    kb_id: str,
    doc_id: str,
    user: CurrentUser,
    db: DB,
):
    """Delete a document from a knowledge base."""
    try:
        # Get the knowledge base first to get collection_name
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        kb_result = await db.execute(kb_query)
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )

        query = select(Document).where(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id,
        )
        result = await db.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Delete vectors from Qdrant
        try:
            processor = await get_processor()
            await processor.delete_document(doc_id, kb.collection_name)
        except Exception:
            pass  # Continue even if Qdrant delete fails

        # Update KB document count
        kb.document_count = max(0, kb.document_count - 1)

        await db.delete(doc)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {e!s}",
        ) from None


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
    # Verify KB exists and user has access
    try:
        kb_query = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        result = await db.execute(kb_query)
        kb = result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify knowledge base: {e!s}",
        ) from None

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
        doc_ids = list({c.document_id for c in chunks})
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {e!s}"
        ) from None


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify knowledge base",
        ) from None

    try:
        from src.rag import get_semantic_cache

        cache = await get_semantic_cache()
        stats = await cache.get_stats(kb_id)
        return CacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {e!s}",
        ) from None


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
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Check access permissions
        if not can_access_kb(kb, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this knowledge base"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify knowledge base",
        ) from None

    try:
        from src.rag import get_semantic_cache

        cache = await get_semantic_cache()
        await cache.invalidate(kb_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {e!s}",
        ) from None
