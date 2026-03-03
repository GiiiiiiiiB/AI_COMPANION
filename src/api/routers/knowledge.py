"""
知识库API路由
"""
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from typing import List, Dict, Any, Optional
import uuid

from src.knowledge import DocumentManager, KnowledgeRetriever, KnowledgeVectorizer
from src.api.main import verify_token, get_document_manager, get_knowledge_retriever

router = APIRouter()


@router.post("/knowledge/documents")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    tags: str = Form(""),
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """上传知识库文档"""
    try:
        # 读取文件内容
        content = await file.read()
        
        # 解析标签
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 上传文档
        result = await document_manager.upload_document(
            content,
            file.filename,
            category,
            tag_list
        )
        
        return {
            "status": "success",
            "document_id": result["document_id"],
            "filename": result["filename"],
            "category": result["category"],
            "tags": result["tags"],
            "status": result["status"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.get("/knowledge/documents")
async def search_documents(
    category: Optional[str] = None,
    tags: Optional[str] = None,
    status: Optional[str] = None,
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """搜索知识库文档"""
    try:
        # 解析标签
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None
        
        # 搜索文档
        documents = await document_manager.search_documents(category, tag_list, status)
        
        return {
            "documents": documents,
            "count": len(documents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")


@router.get("/knowledge/documents/{document_id}")
async def get_document(
    document_id: str,
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """获取文档详情"""
    try:
        document = await document_manager.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@router.delete("/knowledge/documents/{document_id}")
async def delete_document(
    document_id: str,
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """删除文档"""
    try:
        success = await document_manager.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "document_id": document_id,
            "message": "Document deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/knowledge/documents/{document_id}/vectorize")
async def vectorize_document(
    document_id: str,
    token: str = Depends(verify_token)
):
    """文档向量化处理"""
    try:
        vectorizer = KnowledgeVectorizer()
        
        # 向量化文档
        vector_count = await vectorizer.vectorize_document(document_id)
        
        return {
            "status": "success",
            "document_id": document_id,
            "vector_count": vector_count,
            "message": f"Document vectorized successfully with {vector_count} vectors"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to vectorize document: {str(e)}")


@router.get("/knowledge/search")
async def search_knowledge(
    q: str,
    top_k: int = 5,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    knowledge_retriever: KnowledgeRetriever = Depends(get_knowledge_retriever),
    token: str = Depends(verify_token)
):
    """搜索知识库"""
    try:
        # 构建过滤器
        filters = {}
        if category:
            filters["category"] = category
        if tags:
            filters["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # 搜索知识
        results = await knowledge_retriever.search(q, top_k, filters)
        
        return {
            "query": q,
            "results": results,
            "count": len(results),
            "filters": filters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search knowledge: {str(e)}")


@router.get("/knowledge/categories")
async def get_document_categories(
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """获取文档分类列表"""
    try:
        categories = await document_manager.get_document_categories()
        
        return {
            "categories": categories,
            "count": len(categories)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/knowledge/tags")
async def get_document_tags(
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """获取文档标签列表"""
    try:
        tags = await document_manager.get_document_tags()
        
        return {
            "tags": tags,
            "count": len(tags)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")


@router.get("/knowledge/stats")
async def get_knowledge_stats(
    token: str = Depends(verify_token)
):
    """获取知识库统计信息"""
    try:
        vectorizer = KnowledgeVectorizer()
        retriever = KnowledgeRetriever()
        
        # 获取向量化统计
        vector_stats = await vectorizer.get_vectorization_stats()
        
        # 获取搜索统计
        search_stats = await retriever.get_search_stats()
        
        return {
            "vectorization_stats": vector_stats,
            "search_stats": search_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge stats: {str(e)}")


@router.post("/knowledge/documents/batch-vectorize")
async def batch_vectorize_documents(
    document_ids: List[str],
    token: str = Depends(verify_token)
):
    """批量向量化文档"""
    try:
        vectorizer = KnowledgeVectorizer()
        
        # 批量向量化
        results = await vectorizer.batch_vectorize_documents(document_ids)
        
        success_count = sum(1 for result in results.values() if isinstance(result, int))
        error_count = len(results) - success_count
        
        return {
            "status": "success",
            "total_documents": len(document_ids),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch vectorize documents: {str(e)}")


@router.post("/knowledge/documents/{document_id}/update-status")
async def update_document_status(
    document_id: str,
    status: str = Form(...),
    document_manager: DocumentManager = Depends(get_document_manager),
    token: str = Depends(verify_token)
):
    """更新文档状态"""
    try:
        success = await document_manager.update_document_status(document_id, status)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "status": "success",
            "document_id": document_id,
            "new_status": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update document status: {str(e)}")


@router.get("/knowledge/documents/{document_id}/vectors")
async def get_document_vectors(
    document_id: str,
    token: str = Depends(verify_token)
):
    """获取文档的向量"""
    try:
        vectorizer = KnowledgeVectorizer()
        vectors = await vectorizer.get_document_vectors(document_id)
        
        return {
            "document_id": document_id,
            "vectors": vectors,
            "count": len(vectors)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document vectors: {str(e)}")


@router.delete("/knowledge/documents/{document_id}/vectors")
async def delete_document_vectors(
    document_id: str,
    token: str = Depends(verify_token)
):
    """删除文档的向量"""
    try:
        vectorizer = KnowledgeVectorizer()
        deleted_count = await vectorizer.delete_document_vectors(document_id)
        
        return {
            "status": "success",
            "document_id": document_id,
            "deleted_vectors": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document vectors: {str(e)}")