from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict

from utils.logger_manager import get_logger

from .embedding import BGEM3Embedder
from .vector_store import MilvusVectorStore
from ..core.models import KnowledgeBase


class KnowledgeService:
    """知识库服务：整合向量存储和嵌入模型。"""

    def __init__(self, vector_store: MilvusVectorStore, embedder: BGEM3Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.logger = get_logger(self.__class__.__name__)

    def add_knowledge(self, title: str, content: str) -> int:
        """添加知识到向量库与MySQL。"""
        embedding = self.embedder.get_embeddings(content)[0]
        metadata = json.dumps({"title": title}, ensure_ascii=False)

        # 注意：Milvus集合字段必须与schema完全一致
        self.vector_store.add_documents([
            {
                "embedding": embedding,
                "content": content,
                "metadata": metadata,
                "source": title,
                "doc_type": "text",
                "chunk_id": str(uuid.uuid4()),
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        ])

        knowledge = KnowledgeBase(title=title, content=content)
        knowledge.save()
        return knowledge.id

    def search_relevant_knowledge(
        self,
        query: str,
        top_k: int = 5,
        min_score_threshold: float = 0.6,
    ) -> str:
        """检索相关知识并合并返回。"""
        query_embedding = self.embedder.get_embeddings(query)[0]
        self.logger.info(
            "知识库查询context: '%s'\n向量维度: %s\n",
            query,
            len(query_embedding),
        )

        # 先取更多结果，后续再做过滤
        search_k = top_k * 3
        results = self.vector_store.search(query_embedding, top_k=search_k)

        # 1) 过滤相似度阈值
        threshold_filtered = [
            item for item in results if item["score"] >= min_score_threshold
        ]
        self.logger.info("知识库相似度阈值过滤后结果: %s", threshold_filtered)

        # 2) 按分数排序
        sorted_results = sorted(
            threshold_filtered, key=lambda x: x["score"], reverse=True
        )

        # 3) 关键字过滤
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 1]
        keyword_filtered = []
        for item in sorted_results:
            content = item.get("content", "")
            if any(keyword in content for keyword in keywords):
                keyword_filtered.append(item)
            elif len(keyword_filtered) < 2:
                keyword_filtered.append(item)
        self.logger.info("知识库关键字过滤后结果: %s", keyword_filtered)

        # 4) 取前 top_k
        top_results = keyword_filtered[:top_k]
        self.logger.info("知识库前 top_k 结果: %s", top_results)

        # 5) 拼接内容
        content_list = [item["content"] for item in top_results if "content" in item]
        if not content_list:
            return ""

        return "\n\n".join(content_list)
