from datetime import datetime, timedelta
from typing import Optional, Any
import threading
import json

from .base import BaseCache


class RedisCache(BaseCache):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: int = 5,
        connection_pool: Optional[dict] = None,
        **redis_kwargs,
    ):
        """
        Redis 缓存初始化
        :param host: Redis 主机
        :param port: Redis 端口
        :param db: 数据库编号
        :param password: 密码
        :param socket_timeout: 套接字超时时间
        :param connection_pool: 连接池配置
        :param redis_kwargs: 其他 Redis 参数，支持 cleanup_interval 参数设置默认过期时间（秒）
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis cache requires 'redis' package. "
                "Install it with: pip install redis"
            )

        # 提取 cleanup_interval 参数
        self.cleanup_interval = redis_kwargs.pop("cleanup_interval", None)

        # 配置连接池
        pool_kwargs = connection_pool or {}
        pool_kwargs.update(
            {
                "host": host,
                "port": port,
                "db": db,
                "password": password,
                "socket_timeout": socket_timeout,
                **redis_kwargs,
            }
        )

        self.redis = redis.Redis(**pool_kwargs)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis.get(key)
            if data is None:
                return None

            cache_data = json.loads(data)
            expires = datetime.fromisoformat(cache_data["expires"])

            if expires > datetime.now():
                return cache_data["value"]

            # 过期则删除
            self.delete(key)
            return None
        except Exception as e:
            print(f"Redis cache read error: {e}")
            return None

    def set(self, key: str, value: Any, expires: int) -> None:
        """
        设置缓存
        :param key: 键
        :param value: 值
        :param expires: 过期时间，如果未指定且存在 cleanup_interval，则使用 cleanup_interval
        """
        try:
            cache_data = {
                "value": value,
                "expires": (datetime.now() + timedelta(seconds=expires)).isoformat(),
            }
            self.redis.set(key, json.dumps(cache_data), ex=expires)
        except Exception as e:
            print(f"Redis cache write error: {e}")

    def delete(self, key: str) -> None:
        try:
            self.redis.delete(key)
        except Exception as e:
            print(f"Redis cache delete error: {e}")

    def clear(self) -> None:
        try:
            self.redis.flushdb()
        except Exception as e:
            print(f"Redis cache clear error: {e}")
