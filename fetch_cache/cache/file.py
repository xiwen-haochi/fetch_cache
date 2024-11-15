from datetime import datetime, timedelta
from typing import Optional, Any
import json
import threading
from pathlib import Path

from .base import BaseCache


class FileCache(BaseCache):
    def __init__(self, cache_dir: Optional[str | Path] = None):
        if cache_dir is None:
            current_file = Path(__file__).resolve()
            self.cache_dir = current_file.parent.parent / ".cache"
        else:
            self.cache_dir = Path(cache_dir).resolve()

        print(f"Cache directory: {self.cache_dir}")
        self._lock = threading.Lock()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._last_cleanup = datetime.now().timestamp()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 key 的 hash 值作为文件名，避免文件名过长或包含非法字符
        filename = key + ".json"
        return self.cache_dir / filename

    def _cleanup_expired(self) -> None:
        """清理过期的缓存文件"""
        try:
            current_time = datetime.now()
            with self._lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
                        expires = datetime.fromisoformat(cache_data["expires"])

                        if expires <= current_time:
                            cache_file.unlink(missing_ok=True)
                            print(f"Deleted expired cache file: {cache_file}")
                    except Exception as e:
                        print(f"Error cleaning up cache file {cache_file}: {e}")
                        # 如果文件损坏，直接删除
                        cache_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Cache cleanup error: {e}")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        cache_path = self._get_cache_path(key)

        try:
            with self._lock:
                if not cache_path.exists():
                    return None

                cache_data = json.loads(cache_path.read_text(encoding="utf-8"))
                expires = datetime.fromisoformat(cache_data["expires"])

                if expires > datetime.now():
                    return cache_data["value"]

                # 如果缓存过期，删除缓存文件
                cache_path.unlink(missing_ok=True)
                return None
        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def set(self, key: str, value: Any, expires: int) -> None:
        """设置缓存值"""
        cache_path = self._get_cache_path(key)

        try:
            cache_data = {
                "value": value,
                "expires": (datetime.now() + timedelta(seconds=expires)).isoformat(),
                "created_at": datetime.now().isoformat(),
            }

            with self._lock:
                cache_path.write_text(
                    json.dumps(cache_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except Exception as e:
            print(f"Cache write error: {e}")

    def delete(self, key: str) -> None:
        """删除缓存值"""
        try:
            cache_path = self._get_cache_path(key)
            with self._lock:
                cache_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"Cache delete error: {e}")

    def clear(self) -> None:
        """清空所有缓存"""
        try:
            with self._lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Cache clear error: {e}")
