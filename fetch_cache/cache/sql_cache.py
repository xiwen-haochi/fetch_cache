from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import json
import threading
from contextlib import contextmanager
from .base import BaseCache


class SQLCache(BaseCache):
    """SQL Cache implementation supporting various SQL databases"""

    # 支持的数据库类型及其对应的依赖
    DB_DEPENDENCIES: Dict[str, Dict[str, str]] = {
        "mysql": {
            "package": "pymysql",
            "import_name": "pymysql",
            "install_cmd": "pip install pymysql",
        },
        "mariadb": {
            "package": "mariadb",
            "import_name": "mariadb",
            "install_cmd": "pip install mariadb",
        },
        "postgresql": {
            "package": "psycopg2-binary",
            "import_name": "psycopg2",
            "install_cmd": "pip install psycopg2-binary",
        },
        "sqlite": {
            "package": "sqlite3",
            "import_name": "sqlite3",
            "install_cmd": "Built-in with Python",
        },
    }

    def __init__(
        self,
        engine_url: str,
        table_name: str = "http_cache",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,  # 30分钟
        **engine_kwargs,
    ):
        """
        初始化 SQL 缓存

        :param engine_url: SQLAlchemy 引擎 URL，例如：
            - MySQL: 'mysql+pymysql://user:pass@localhost/dbname'
            - MariaDB: 'mariadb+mariadb://user:pass@localhost/dbname'
            - PostgreSQL: 'postgresql+psycopg2://user:pass@localhost/dbname'
            - SQLite: 'sqlite:///path/to/cache.db'
        :param table_name: 缓存表名，默认为 'http_cache'
        :param pool_size: 连接池大小
        :param max_overflow: 超出 pool_size 后最多可以创建的连接数
        :param pool_timeout: 获取连接的超时时间（秒）
        :param pool_recycle: 连接重置时间（秒）
        :param engine_kwargs: SQLAlchemy 引擎的额外参数
        """
        try:
            from sqlalchemy import create_engine, Table, Column, String, Text, MetaData
            from sqlalchemy.pool import QueuePool
        except ImportError:
            raise ImportError(
                "SQL cache requires 'sqlalchemy' package. "
                "Install it with: pip install sqlalchemy"
            )

        # 检查数据库类型并导入相应的驱动
        db_type = self._get_db_type(engine_url)
        if db_type in self.DB_DEPENDENCIES:
            self._import_db_driver(db_type)
        else:
            supported_dbs = ", ".join(self.DB_DEPENDENCIES.keys())
            raise ValueError(
                f"Unsupported database type. Supported types are: {supported_dbs}"
            )

        # 配置连接池
        pool_kwargs = {
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
        }
        engine_kwargs.update(pool_kwargs)

        # 创建引擎和表
        self.engine = create_engine(engine_url, **engine_kwargs)
        self.table_name = table_name
        self._lock = threading.Lock()
        self._local = threading.local()

        # 创建缓存表
        metadata = MetaData()
        self.cache_table = Table(
            table_name,
            metadata,
            Column("key", String(255), primary_key=True),
            Column("value", Text),
            Column("expires", String(50)),
            Column("created_at", String(50), default=datetime.now().isoformat()),
            Column("updated_at", String(50), onupdate=datetime.now().isoformat()),
        )

        # 创建表（如果不存在）
        metadata.create_all(self.engine)
        print(f"Cache table '{table_name}' initialized in {db_type} database")

    def _get_db_type(self, engine_url: str) -> str:
        """从引擎 URL 中提取数据库类型"""
        db_type = engine_url.split("+")[0].split(":")[0]
        return db_type

    def _import_db_driver(self, db_type: str) -> None:
        """导入数据库驱动"""
        dep_info = self.DB_DEPENDENCIES[db_type]
        try:
            __import__(dep_info["import_name"])
        except ImportError:
            raise ImportError(
                f"{db_type} cache requires '{dep_info['package']}' package. "
                f"Install it with: {dep_info['install_cmd']}"
            )

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        if not hasattr(self._local, "connection"):
            self._local.connection = self.engine.connect()

        try:
            yield self._local.connection
        except Exception as e:
            if hasattr(self._local, "connection"):
                self._local.connection.close()
                del self._local.connection
            raise e

    def get(self, key: str) -> Optional[Any]:
        try:
            with self._lock, self._get_connection() as conn:
                query = self.cache_table.select().where(self.cache_table.c.key == key)
                result = conn.execute(query).first()

                if result is None:
                    return None

                expires = datetime.fromisoformat(result.expires)
                if expires > datetime.now():
                    return json.loads(result.value)

                # 过期则删除
                self.delete(key)
                return None
        except Exception as e:
            print(f"SQL cache read error: {e}")
            return None

    def set(self, key: str, value: Any, expires: int) -> None:
        try:
            with self._lock, self._get_connection() as conn:
                expires = datetime.now() + timedelta(seconds=expires)
                # 使用 upsert 语法（根据数据库类型可能需要调整）
                stmt = self.cache_table.delete().where(self.cache_table.c.key == key)
                conn.execute(stmt)

                stmt = self.cache_table.insert().values(
                    key=key,
                    value=json.dumps(value),
                    expires=expires.isoformat(),
                    created_at=datetime.now().isoformat(),
                )
                conn.execute(stmt)
                conn.commit()
        except Exception as e:
            print(f"SQL cache write error: {e}")

    def delete(self, key: str) -> None:
        try:
            with self._lock, self._get_connection() as conn:
                stmt = self.cache_table.delete().where(self.cache_table.c.key == key)
                conn.execute(stmt)
                conn.commit()
        except Exception as e:
            print(f"SQL cache delete error: {e}")

    def clear(self) -> None:
        try:
            with self._lock, self._get_connection() as conn:
                conn.execute(self.cache_table.delete())
                conn.commit()
        except Exception as e:
            print(f"SQL cache clear error: {e}")

    def __del__(self):
        """清理资源"""
        if hasattr(self._local, "connection"):
            try:
                self._local.connection.close()
            except:
                pass
