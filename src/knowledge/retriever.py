"""
知识检索器
"""
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.metrics.pairwise import cosine_similarity
import jieba
import re

from src.config.settings import settings
from src.storage.database import get_db_session
from src.storage.models import KnowledgeVector
from src.knowledge.vectorizer import KnowledgeVectorizer


class KnowledgeRetriever:
    """知识检索器"""
    
    def __init__(self, vectorizer: KnowledgeVectorizer = None, alpha: float = 0.7, beta: float = 0.3):
        self.vectorizer = vectorizer or KnowledgeVectorizer()
        self.alpha = alpha  # 向量搜索权重
        self.beta = beta    # 关键词搜索权重
    
    async def search(self, query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """混合搜索"""
        if not query or not query.strip():
            return []
        
        # 1. 生成查询向量
        query_vector = await self.vectorizer.generate_embedding(query)
        
        # 2. 向量搜索
        vector_results = await self.vector_search(query_vector, top_k * 2, filters)
        
        # 3. 关键词搜索
        keyword_results = await self.keyword_search(query, top_k * 2, filters)
        
        # 4. 结果融合
        fused_results = self.fuse_results(vector_results, keyword_results)
        
        # 5. 重排序
        reranked_results = await self.rerank(query, fused_results)
        
        return reranked_results[:top_k]
    
    async def vector_search(self, query_vector: np.ndarray, top_k: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """向量搜索"""
        async for session in get_db_session():
            # 获取所有向量
            query = session.query(KnowledgeVector)
            
            # 应用过滤器
            if filters:
                if 'category' in filters:
                    query = query.filter(KnowledgeVector.metadata['category'].astext == filters['category'])
                if 'tags' in filters:
                    for tag in filters['tags']:
                        query = query.filter(KnowledgeVector.metadata['tags'].contains([tag]))
            
            vectors = await query.all()
            
            if not vectors:
                return []
            
            # 计算相似度
            similarities = []
            for vector_record in vectors:
                vector_data = np.array(vector_record.vector)
                similarity = cosine_similarity([query_vector], [vector_data])[0][0]
                similarities.append({
                    "id": vector_record.id,
                    "document_id": vector_record.document_id,
                    "content": vector_record.content,
                    "similarity": float(similarity),
                    "metadata": vector_record.metadata
                })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            return similarities[:top_k]
    
    async def keyword_search(self, query: str, top_k: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """关键词搜索"""
        # 提取关键词
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        async for session in get_db_session():
            # 构建查询
            query_obj = session.query(KnowledgeVector)
            
            # 关键词匹配
            conditions = []
            for keyword in keywords:
                conditions.append(KnowledgeVector.content.contains(keyword))
            
            # 组合条件
            from sqlalchemy import or_
            query_obj = query_obj.filter(or_(*conditions))
            
            # 应用过滤器
            if filters:
                if 'category' in filters:
                    query_obj = query_obj.filter(KnowledgeVector.metadata['category'].astext == filters['category'])
                if 'tags' in filters:
                    for tag in filters['tags']:
                        query_obj = query_obj.filter(KnowledgeVector.metadata['tags'].contains([tag]))
            
            vectors = await query_obj.all()
            
            if not vectors:
                return []
            
            # 计算关键词匹配分数
            results = []
            for vector_record in vectors:
                content = vector_record.content.lower()
                score = 0
                
                # 计算关键词匹配度
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in content:
                        # 完全匹配得分更高
                        score += content.count(keyword_lower) * 2
                        
                        # 标题中出现得分更高
                        title = vector_record.metadata.get('document_title', '').lower()
                        if keyword_lower in title:
                            score += 5
                
                results.append({
                    "id": vector_record.id,
                    "document_id": vector_record.document_id,
                    "content": vector_record.content,
                    "score": float(score),
                    "metadata": vector_record.metadata,
                    "matched_keywords": [kw for kw in keywords if kw.lower() in content]
                })
            
            # 按分数排序
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return results[:top_k]
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        if not text:
            return []
        
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 分词
        words = list(jieba.cut(text))
        
        # 过滤停用词和短词
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '那', '些', '个', '为', '与', '及', '或', '但', '而', '因为', '所以'
        }
        
        keywords = []
        for word in words:
            word = word.strip()
            if len(word) > 1 and word not in stop_words:
                keywords.append(word)
        
        # 返回去重后的关键词
        return list(set(keywords))
    
    def fuse_results(self, vector_results: List[Dict[str, Any]], keyword_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """融合向量搜索和关键词搜索结果"""
        fused_scores = {}
        
        # 向量搜索结果加权
        for result in vector_results:
            doc_id = result["document_id"]
            # 归一化相似度分数
            normalized_score = result["similarity"] if result["similarity"] <= 1.0 else result["similarity"] / 100.0
            fused_scores[doc_id] = {
                "score": self.alpha * normalized_score,
                "content": result["content"],
                "metadata": result["metadata"],
                "vector_score": result["similarity"],
                "keyword_score": 0,
                "matched_keywords": []
            }
        
        # 关键词搜索结果加权
        for result in keyword_results:
            doc_id = result["document_id"]
            # 归一化关键词分数
            max_keyword_score = max([r["score"] for r in keyword_results]) if keyword_results else 1.0
            normalized_score = result["score"] / max_keyword_score if max_keyword_score > 0 else 0
            
            if doc_id in fused_scores:
                fused_scores[doc_id]["score"] += self.beta * normalized_score
                fused_scores[doc_id]["keyword_score"] = result["score"]
                fused_scores[doc_id]["matched_keywords"] = result.get("matched_keywords", [])
            else:
                fused_scores[doc_id] = {
                    "score": self.beta * normalized_score,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "vector_score": 0,
                    "keyword_score": result["score"],
                    "matched_keywords": result.get("matched_keywords", [])
                }
        
        # 排序并返回
        sorted_results = sorted(
            fused_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        return [
            {
                "document_id": doc_id,
                "score": data["score"],
                "content": data["content"],
                "metadata": data["metadata"],
                "vector_score": data["vector_score"],
                "keyword_score": data["keyword_score"],
                "matched_keywords": data["matched_keywords"]
            }
            for doc_id, data in sorted_results
        ]
    
    async def rerank(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """重排序结果"""
        # 简单的重排序逻辑：基于查询词在内容中的位置
        reranked_results = []
        
        for result in results:
            content = result["content"]
            query_lower = query.lower()
            content_lower = content.lower()
            
            # 计算位置分数（查询词出现的位置越靠前分数越高）
            position_score = 0
            if query_lower in content_lower:
                position = content_lower.find(query_lower)
                position_score = max(0, 1 - position / len(content))
            
            # 计算覆盖分数（查询词覆盖度）
            query_words = self.extract_keywords(query)
            coverage_score = 0
            if query_words:
                matched_words = sum(1 for word in query_words if word.lower() in content_lower)
                coverage_score = matched_words / len(query_words)
            
            # 综合分数
            final_score = result["score"] * 0.7 + position_score * 0.2 + coverage_score * 0.1
            
            reranked_result = result.copy()
            reranked_result["final_score"] = final_score
            reranked_result["position_score"] = position_score
            reranked_result["coverage_score"] = coverage_score
            
            reranked_results.append(reranked_result)
        
        # 按最终分数排序
        reranked_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return reranked_results
    
    def update_weights(self, alpha: float = None, beta: float = None):
        """更新权重"""
        if alpha is not None:
            self.alpha = alpha
        if beta is not None:
            self.beta = beta
        
        # 确保权重和为1
        total = self.alpha + self.beta
        if total > 0:
            self.alpha = self.alpha / total
            self.beta = self.beta / total
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        async for session in get_db_session():
            # 获取向量总数
            total_vectors = await session.query(KnowledgeVector).count()
            
            # 获取文档总数
            from src.storage.models import KnowledgeDocument
            total_documents = await session.query(KnowledgeDocument).filter(
                KnowledgeDocument.status == "vectorized"
            ).count()
            
            return {
                "total_vectors": total_vectors,
                "total_documents": total_documents,
                "search_weights": {
                    "vector_weight": self.alpha,
                    "keyword_weight": self.beta
                }
            }