# fetch-cache
🚧 警告：这是一个"能用就行"的项目！

💡 如果发现 bug，那一定是特性！

🔧 代码写得不够优雅？随时欢迎 PR！

🎯 目标是：能用 > 好用 > 很好用



一个支持多种缓存后端的 HTTP 客户端库，基于 httpx 开发，提供同步和异步支持,本项目是自用代码整理后的开源版本，功能可能不够完善，但核心功能已经可以正常使用。 欢迎根据实际需求修改代码，如果对你有帮助，请点个星！。

## 特性

- 基于 httpx 的现代 HTTP 客户端
- 支持同步和异步请求
- 内置多种缓存后端:
  - 内存缓存 (默认)
  - 文件缓存
  - Redis 缓存
  - SQL 缓存 (支持 MySQL、PostgreSQL、SQLite、MariaDB)
  - MongoDB 缓存 (实验性)
  - Django 缓存 (实验性)
- 灵活的缓存配置


## 安装

```bash
pip install fetch_cache
```

## 基础使用

### 同步客户端

```python
from fetch_cache import HTTPClient

# 创建客户端实例
client = HTTPClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token"},
    cache_type="memory",  # 默认使用内存缓存
    cache_ttl=3600,  # 缓存有效期(秒)
)

# 发送请求
response = client.request(
    method="GET",
    endpoint="/users",
    params={"page": 1}
)

# 不使用缓存
response = client.request(
    method="GET",
    endpoint="/users",
    no_cache=True
)

# 关闭客户端
client.close()
```

### 异步客户端

```python
import asyncio
from fetch_cache import AsyncHTTPClient

async def main():
    # 创建异步客户端实例
    client = AsyncHTTPClient(
        base_url="https://api.example.com",
        headers={"Authorization": "Bearer token"},
        cache_type="redis",
        cache_config={
            "host": "localhost",
            "port": 6379,
            "db": 0
        },
        cache_ttl=3600
    )

    # 发送异步请求
    response = await client.request(
        method="GET",
        endpoint="/users",
        params={"page": 1}
    )

    # 关闭客户端
    await client.close()

asyncio.run(main())
```

## 缓存配置

### 内存缓存 (默认)

最简单的缓存实现,数据存储在内存中,程序重启后缓存会丢失。

### 文件缓存

将缓存数据以 JSON 格式存储在本地文件系统中。

### Redis 缓存

使用 Redis 作为缓存后端,需要先安装 redis 包:

```bash
pip install redis
```

配置示例:

```python
client = HTTPClient(
    base_url="https://api.example.com",
    cache_type="redis",
    cache_config={
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "password": None,
        "socket_timeout": 5,
        "connection_pool": {
            "max_connections": 10
        }
    },
    cache_ttl=3600
)
```

### SQL 缓存

支持 MySQL、PostgreSQL、SQLite 和 MariaDB,需要先安装对应的数据库驱动:

```bash
# MySQL
pip install pymysql

# PostgreSQL 
pip install psycopg2-binary

# MariaDB
pip install mariadb

# SQLite (Python 内置)
```

配置示例:

```python
client = HTTPClient(
    base_url="https://api.example.com",
    cache_type="mysql",  # 或 postgresql、sqlite、mariadb
    cache_config={
        "engine_url": "mysql+pymysql://user:pass@localhost/dbname",
        "table_name": "http_cache",  # 可选,默认为 http_cache
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800
    },
    cache_ttl=3600
)
```

各数据库的 engine_url 格式:

- MySQL: `mysql+pymysql://user:pass@localhost/dbname`
- PostgreSQL: `postgresql+psycopg2://user:pass@localhost/dbname`
- SQLite: `sqlite:///path/to/cache.db`
- MariaDB: `mariadb+mariadb://user:pass@localhost/dbname`




