from .base import BaseCache
from .memory import MemoryCache
from .file import FileCache
from .redis_cache import RedisCache
from .mongo_cache import MongoCache
from .django_cache import DjangoCache


def create_cache(cache_type: str = "memory", **config) -> BaseCache:
    """
    创建缓存实例的工厂函数
    :param cache_type: 缓存类型 ('memory', 'file', 'redis', 'mongodb', 'django', 'django_settings', 'mysql', 'postgresql', 'sqlite', 'mariadb')
    :param config: 缓存配置参数
    """
    if cache_type == "memory":
        return MemoryCache()
    elif cache_type == "file":
        return FileCache(**config)
    elif cache_type == "redis":
        return RedisCache(**config)
    elif cache_type == "mongodb":
        return MongoCache(**config)
    elif cache_type == "django":
        return DjangoCache(**config)
    elif cache_type == "django_settings":
        return DjangoCache.from_django_settings(**config)
    elif cache_type in ("mysql", "postgresql", "sqlite", "mariadb"):
        from .sql_cache import SQLCache

        return SQLCache(**config)
    else:
        raise ValueError(f"Unsupported cache type: {cache_type}")


__all__ = [
    "BaseCache",
    "MemoryCache",
    "FileCache",
    "RedisCache",
    "MongoCache",
    "DjangoCache",
    "create_cache",
]
