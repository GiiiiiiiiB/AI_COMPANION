"""
知识向量化处理器
"""
import asyncio
import re
from typing import Dict, Any, List, Optional
from sentence_transformers import SentenceTransformer
import numpy as np

from src.config.settings import settings
from src.storage.database import get_db_session
from src.storage.models import KnowledgeDocument, KnowledgeVector


class KnowledgeVectorizer:
    """知识向量化处理器"""
    
    def __init__(self, embedding_model: str = None, chunk_size: int = 500, chunk_overlap: int = 50):
        self.embedding_model_name = embedding_model or settings.ai.embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载向量化模型"""
        try:
            self.model = SentenceTransformer(self.embedding_model_name)
        except Exception as e:
            print(f"Warning: Failed to load embedding model {self.embedding_model_name}: {e}")
            # 使用备用模型
            self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    async def vectorize_document(self, document_id: str) -> int:
        """文档向量化处理"""
        # 1. 获取文档内容
        async for session in get_db_session():
            doc = await session.get(KnowledgeDocument, document_id)
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            if doc.status != "processing":
                raise ValueError(f"Document {document_id} is not in processing status")
            
            content = doc.content
            category = doc.category
            tags = doc.tags or []
            
            # 2. 文本分块
            chunks = self.chunk_text(content)
            
            # 3. 生成向量
            vectors = []
            for i, chunk in enumerate(chunks):
                vector = await self.generate_embedding(chunk)
                vectors.append({
                    "document_id": document_id,
                    "chunk_index": i,
                    "content": chunk,
                    "vector": vector.tolist() if isinstance(vector, np.ndarray) else vector,
                    "metadata": {
                        "category": category,
                        "tags": tags,
                        "chunk_size": len(chunk),
                        "document_title": doc.filename
                    }
                })
            
            # 4. 保存到向量数据库
            await self.save_vectors(vectors)
            
            # 5. 更新文档状态
            doc.status = "vectorized"
            await session.commit()
            
            return len(vectors)
    
    def chunk_text(self, text: str) -> List[str]:
        """文本分块处理"""
        if not text:
            return []
        
        # 清理文本
        text = self._clean_text(text)
        
        # 按句子分割
        sentences = self._split_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # 如果当前块加上新句子超过限制，则保存当前块
            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # 添加重叠部分
                overlap_text = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else ""
                current_chunk = overlap_text + sentence
                current_size = len(current_chunk)
            else:
                current_chunk += sentence
                current_size += sentence_size
        
        # 保存最后一个块
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符但保留中文标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff。，！？；：""''（）【】《》]', '', text)
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        # 中文句子分割符
        sentence_delimiters = r'[。！？；]'
        
        # 分割句子
        sentences = re.split(sentence_delimiters, text)
        
        # 添加分割符回到句子中
        delimiters = re.findall(sentence_delimiters, text)
        
        result = []
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                if i < len(delimiters):
                    result.append(sentence.strip() + delimiters[i])
                else:
                    result.append(sentence.strip())
        
        return result
    
    async def generate_embedding(self, text: str) -> np.ndarray:
        """生成文本向量"""
        if not self.model:
            raise RuntimeError("Embedding model not loaded")
        
        # 限制文本长度
        if len(text) > 1000:
            text = text[:1000]
        
        # 生成向量
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    async def save_vectors(self, vectors: List[Dict[str, Any]]) -> None:
        """保存向量到数据库"""
        async for session in get_db_session():
            for vector_data in vectors:
                vector_record = KnowledgeVector(
                    document_id=vector_data["document_id"],
                    chunk_index=vector_data["chunk_index"],
                    content=vector_data["content"],
                    vector=vector_data["vector"],
                    metadata=vector_data["metadata"]
                )
                session.add(vector_record)
            
            await session.commit()
    
    async def get_document_vectors(self, document_id: str) -> List[Dict[str, Any]]:
        """获取文档的向量"""
        async for session in get_db_session():
            vectors = await session.query(KnowledgeVector).filter(
                KnowledgeVector.document_id == document_id
            ).order_by(KnowledgeVector.chunk_index).all()
            
            return [
                {
                    "id": vector.id,
                    "document_id": vector.document_id,
                    "chunk_index": vector.chunk_index,
                    "content": vector.content,
                    "vector": vector.vector,
                    "metadata": vector.metadata,
                    "created_at": vector.created_at
                }
                for vector in vectors
            ]
    
    async def delete_document_vectors(self, document_id: str) -> int:
        """删除文档的向量"""
        async for session in get_db_session():
            result = await session.query(KnowledgeVector).filter(
                KnowledgeVector.document_id == document_id
            ).delete()
            await session.commit()
            return result
    
    async def batch_vectorize_documents(self, document_ids: List[str]) -> Dict[str, int]:
        """批量向量化文档"""
        results = {}
        
        for document_id in document_ids:
            try:
                vector_count = await self.vectorize_document(document_id)
                results[document_id] = vector_count
            except Exception as e:
                results[document_id] = f"Error: {str(e)}"
        
        return results
    
    def update_chunking_params(self, chunk_size: int = None, chunk_overlap: int = None):
        """更新分块参数"""
        if chunk_size is not None:
            self.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.chunk_overlap = chunk_overlap
    
    async def get_vectorization_stats(self) -> Dict[str, Any]:
        """获取向量化统计信息"""
        async for session in get_db_session():
            # 获取已向量化的文档数量
            vectorized_docs = await session.query(KnowledgeDocument).filter(
                KnowledgeDocument.status == "vectorized"
            ).count()
            
            # 获取向量总数
            total_vectors = await session.query(KnowledgeVector).count()
            
            # 获取平均向量数量（每文档）
            if vectorized_docs > 0:
                avg_vectors_per_doc = total_vectors / vectorized_docs
            else:
                avg_vectors_per_doc = 0
            
            return {
                "vectorized_documents": vectorized_docs,
                "total_vectors": total_vectors,
                "average_vectors_per_document": round(avg_vectors_per_doc, 2)
            }