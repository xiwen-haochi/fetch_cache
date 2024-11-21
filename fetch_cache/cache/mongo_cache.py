from datetime import datetime
from typing import Optional, Any, Dict
import threading

from .base import BaseCache


class MongoCache(BaseCache):
    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "cache_db",
        collection: str = "http_cache",
        **mongo_kwargs,
    ):
        """
        MongoDB 缓存初始化
        :param uri: MongoDB 连接 URI
        :param database: 数据库名称
        :param collection: 集合名称
        :param mongo_kwargs: 其他 MongoDB 客户端参数
        """
        try:
            import pymongo
            from pymongo import MongoClient
            from pymongo.collection import Collection
        except ImportError:
            raise ImportError(
                "MongoDB cache requires 'pymongo' package. "
                "Install it with: pip install pymongo"
            )

        # 创建客户端连接
        self.client = MongoClient(uri, **mongo_kwargs)
        self.db = self.client[database]
        self.collection: Collection = self.db[collection]
        self._lock = threading.Lock()

        # 创建索引
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """确保必要的索引存在"""
        try:
            # 为 key 创建唯一索引
            self.collection.create_index("key", unique=True)
            # 为过期时间创建索引
            self.collection.create_index("expires")
        except Exception as e:
            print(f"MongoDB index creation error: {e}")

    def _clean_expired(self) -> None:
        """清理过期的缓存数据"""
        try:
            self.collection.delete_many(
                {"expires": {"$lt": datetime.now().isoformat()}}
            )
        except Exception as e:
            print(f"MongoDB cleanup error: {e}")

    def get(self, key: str) -> Optional[Any]:
        try:
            # 定期清理过期数据
            self._clean_expired()

            # 查询数据
            doc = self.collection.find_one({"key": key})
            if doc is None:
                return None

            expires = datetime.fromisoformat(doc["expires"])
            if expires > datetime.now():
                return doc["value"]

            # 过期则删除
            self.delete(key)
            return None
        except Exception as e:
            print(f"MongoDB cache read error: {e}")
            return None

    def set(self, key: str, value: Any, expires: datetime) -> None:
        try:
            # 准备文档
            doc = {
                "key": key,
                "value": value,
                "expires": expires.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # 使用 upsert 操作
            self.collection.update_one({"key": key}, {"$set": doc}, upsert=True)
        except Exception as e:
            print(f"MongoDB cache write error: {e}")

    def delete(self, key: str) -> None:
        try:
            self.collection.delete_one({"key": key})
        except Exception as e:
            print(f"MongoDB cache delete error: {e}")

    def clear(self) -> None:
        try:
            self.collection.delete_many({})
        except Exception as e:
            print(f"MongoDB cache clear error: {e}")

    def __del__(self):
        """清理资源"""
        try:
            self.client.close()
        except:
            pass
