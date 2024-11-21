from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import threading
from .base import BaseCache


class DjangoCache(BaseCache):
    """Django Cache Adapter"""

    def __init__(
        self,
        use_django_cache: bool = True,  # 是否使用 Django 的缓存系统
        cache_alias: str = "default",  # Django 缓存别名
        use_django_db: bool = False,  # 是否使用 Django 的数据库
        db_alias: str = "default",  # Django 数据库别名
        table_name: str = "http_cache",  # 数据库表名
        **kwargs,
    ):
        """
        Django 缓存适配器初始化

        :param use_django_cache: 是否使用 Django 的缓存系统
        :param cache_alias: Django 缓存配置别名
        :param use_django_db: 是否使用 Django 的数据库
        :param db_alias: Django 数据库配置别名
        :param table_name: 数据库表名（仅在 use_django_db=True 时使用）
        """
        try:
            import django
            from django.conf import settings
            from django.core.cache import caches
            from django.apps import apps
        except ImportError:
            raise ImportError(
                "Django cache requires Django to be installed. "
                "Install it with: pip install django"
            )

        # 确保 Django 已配置
        if not apps.ready:
            raise RuntimeError(
                "Django apps are not ready. "
                "Make sure Django is properly configured and apps are loaded."
            )

        self._lock = threading.Lock()
        self.use_django_cache = use_django_cache
        self.use_django_db = use_django_db

        if use_django_cache:
            # 获取 Django 缓存后端
            self.django_cache = caches[cache_alias]

        if use_django_db:
            # 动态创建 Django 模型
            self._create_cache_model(table_name, db_alias)

    def _create_cache_model(self, table_name: str, db_alias: str) -> None:
        """动态创建 Django 模型"""
        from django.db import models

        class Meta:
            app_label = "fetch_cache"
            db_table = table_name
            indexes = [
                models.Index(fields=["key"]),
                models.Index(fields=["expires"]),
            ]

        # 动态创建模型类
        self.CacheModel = type(
            "HttpCache",
            (models.Model,),
            {
                "__module__": "fetch_cache.cache.django_cache",
                "Meta": Meta,
                "key": models.CharField(max_length=255, unique=True),
                "value": models.JSONField(),
                "expires": models.DateTimeField(),
                "created_at": models.DateTimeField(auto_now_add=True),
                "updated_at": models.DateTimeField(auto_now=True),
                "objects": models.Manager(),
            },
        )

        # 设置数据库连接
        self.CacheModel._meta.apps = apps
        self.CacheModel._meta.app_label = "fetch_cache"
        self.CacheModel._meta.db_table = table_name
        self.CacheModel._meta.using = db_alias

        # 创建数据库表
        from django.db import connections

        with connections[db_alias].schema_editor() as schema_editor:
            try:
                schema_editor.create_model(self.CacheModel)
            except Exception as e:
                print(f"Table creation error (might already exist): {e}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if self.use_django_cache:
                # 使用 Django 缓存
                return self.django_cache.get(key)

            elif self.use_django_db:
                # 使用 Django 数据库
                with self._lock:
                    try:
                        cache_obj = self.CacheModel.objects.get(
                            key=key, expires__gt=datetime.now()
                        )
                        return cache_obj.value
                    except self.CacheModel.DoesNotExist:
                        return None

            return None
        except Exception as e:
            print(f"Django cache read error: {e}")
            return None

    def set(self, key: str, value: Any, expires: int) -> None:
        """设置缓存值"""
        expires = datetime.now() + timedelta(seconds=expires)
        try:
            if self.use_django_cache:
                # 计算过期时间（秒）
                timeout = int((expires - datetime.now()).total_seconds())
                self.django_cache.set(key, value, timeout)

            elif self.use_django_db:
                with self._lock:
                    self.CacheModel.objects.update_or_create(
                        key=key, defaults={"value": value, "expires": expires}
                    )
        except Exception as e:
            print(f"Django cache write error: {e}")

    def delete(self, key: str) -> None:
        """删除缓存值"""
        try:
            if self.use_django_cache:
                self.django_cache.delete(key)

            elif self.use_django_db:
                with self._lock:
                    self.CacheModel.objects.filter(key=key).delete()
        except Exception as e:
            print(f"Django cache delete error: {e}")

    def clear(self) -> None:
        """清空所有缓存"""
        try:
            if self.use_django_cache:
                self.django_cache.clear()

            elif self.use_django_db:
                with self._lock:
                    self.CacheModel.objects.all().delete()
        except Exception as e:
            print(f"Django cache clear error: {e}")

    @classmethod
    def from_django_settings(
        cls,
        cache_alias: str = "default",
        db_alias: str = "default",
        prefer_cache: bool = True,
    ) -> "DjangoCache":
        """
        从 Django 设置创建缓存实例

        :param cache_alias: Django 缓存配置别名
        :param db_alias: Django 数据库配置别名
        :param prefer_cache: 优先使用缓存而不是数据库
        """
        from django.conf import settings

        # 检查 Django 缓存配置
        has_cache = hasattr(settings, "CACHES") and cache_alias in settings.CACHES

        # 检查 Django 数据库配置
        has_db = hasattr(settings, "DATABASES") and db_alias in settings.DATABASES

        if prefer_cache and has_cache:
            return cls(
                use_django_cache=True, use_django_db=False, cache_alias=cache_alias
            )
        elif has_db:
            return cls(use_django_cache=False, use_django_db=True, db_alias=db_alias)
        elif has_cache:
            return cls(
                use_django_cache=True, use_django_db=False, cache_alias=cache_alias
            )
        else:
            raise ValueError("No valid Django cache or database configuration found")
