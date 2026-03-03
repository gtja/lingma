from pymilvus import connections, Collection, utility, DataType
from pymilvus import CollectionSchema, FieldSchema
from typing import List, Dict, Any
import os
from django.conf import settings
from utils.logger_manager import get_logger

logger = get_logger(__name__)


class MilvusVectorStore:
    """Milvus向量数据库连接器"""

    def __init__(
        self,
        host: str = None,
        port: str = None,
        collection_name: str = None,
    ):
        vector_cfg = getattr(settings, "VECTOR_DB_CONFIG", {})
        self.host = host or vector_cfg.get("host") or os.getenv("MILVUS_HOST", "127.0.0.1")
        self.port = port or vector_cfg.get("port") or os.getenv("MILVUS_PORT", "19530")
        self.collection_name = (
            collection_name
            or vector_cfg.get("collection_name")
            or os.getenv("MILVUS_COLLECTION", "vv_knowledge_collection")
        )

        self._connect()
        self._ensure_collection()

    def _connect(self):
        """连接到Milvus服务器"""
        connections.connect(alias="default", host=self.host, port=self.port)

    def _ensure_collection(self):
        """检查集合存在，若不存在则创建"""
        logger.info("进入_ensure_collection方法")
        if not utility.has_collection(self.collection_name):
            logger.info(f"集合 {self.collection_name} 不存在，准备创建...")
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="upload_time", dtype=DataType.VARCHAR, max_length=50),
            ]
            schema = CollectionSchema(fields=fields, description="vv向量数据库集合")
            collection = Collection(name=self.collection_name, schema=schema)
            logger.info("集合创建成功")

            logger.info("准备创建索引...")
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64},
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            logger.info("索引创建成功")
            collection.load()
            return collection

        logger.info(f"集合 {self.collection_name} 已存在，直接返回")
        collection = Collection(self.collection_name)
        collection.load()
        return collection

    def add_data(self, data: List[Dict[str, Any]]):
        """添加数据到Milvus集合"""
        logger.info("进入add_data方法")
        collection = Collection(self.collection_name)
        collection.insert(data)
        collection.flush()

    def add_documents(self, documents: List[Dict[str, Any]]):
        """兼容接口：将 documents 转为 add_data"""
        return self.add_data(documents)

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()
        if len(query_vector) != 1024:
            raise ValueError(f"查询向量维度应为1024，当前为{len(query_vector)}")

        collection = Collection(self.collection_name)
        collection.load()

        search_params = {"metric_type": "COSINE", "params": {"ef": 32}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content", "metadata", "source", "doc_type", "chunk_id", "upload_time"],
        )

        ret = []
        for hits in results:
            for hit in hits:
                ret.append(
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "content": hit.entity.get("content"),
                        "metadata": hit.entity.get("metadata"),
                        "source": hit.entity.get("source"),
                        "doc_type": hit.entity.get("doc_type"),
                        "chunk_id": hit.entity.get("chunk_id"),
                        "upload_time": hit.entity.get("upload_time"),
                    }
                )

        collection.release()
        return ret
