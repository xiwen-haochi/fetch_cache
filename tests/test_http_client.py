import pytest
import os
import shutil
import httpx
from datetime import datetime, timedelta
from fetch_cache.core import HTTPClient, AsyncHTTPClient
from fetch_cache.utils.async_sync import async_to_sync
import respx
import redis
from pathlib import Path
import json
import time
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
env_file = os.getenv("ENV_FILE", ".env.test")
load_dotenv(BASE_DIR / env_file)

TEST_CACHE_DIR = BASE_DIR / ".test_http_cache"
TEST_SQLITE_PATH = BASE_DIR / "cache.db"
TEST_SQLITE_PATH1 = BASE_DIR / "cache1.db"
TEST_BASE_URL = "http://test.com/api"
TEST_ENDPOINT = "field_list"
TEST_PG_PWD = os.getenv("TEST_PG_PWD")
TEST_PG_HOST = os.getenv("TEST_PG_HOST")
TEST_RESPONSE_DATA = {"status": "success", "data": ["field1", "field2"]}
TEST_REDIS_CONFIG = json.loads(
    os.getenv("TEST_REDIS_CONFIG")
)  # {"host": "xxxxx", "port": 6379}
TEST_CACHE_KEY = "51bd0e494f6f3566fb098d6d809073d2"


@pytest.fixture
def cleanup_cache():
    """清理测试缓存文件的 fixture"""
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR)
    yield
    if TEST_CACHE_DIR.exists():
        shutil.rmtree(TEST_CACHE_DIR)


@pytest.fixture
def redis_client():
    return redis.Redis(**TEST_REDIS_CONFIG)


@pytest.fixture
def cleanup_redis(redis_client):
    """清理测试 Redis 缓存"""
    redis_client.flushall()

    yield
    # 清理 Redis 缓存
    redis_client.flushall()


@pytest.fixture
def cleanup_sqlite():
    """清理测试 SQLite 缓存"""
    if TEST_SQLITE_PATH.exists():
        TEST_SQLITE_PATH.unlink()

    yield
    # if TEST_SQLITE_PATH.exists():
    #     TEST_SQLITE_PATH.unlink()


@pytest.fixture
def cleanup_sqlite1():
    """清理测试 SQLite 缓存"""
    if TEST_SQLITE_PATH1.exists():
        TEST_SQLITE_PATH1.unlink()

    yield
    # if TEST_SQLITE_PATH1.exists():
    #     TEST_SQLITE_PATH1.unlink()


@respx.mock
@pytest.mark.asyncio
async def test_http_client_get_with_async_file_cache(
    cleanup_cache,
):  # 添加 cleanup_cache fixture
    """测试带文件缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    async with AsyncHTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="file",
        cache_config={"cache_dir": TEST_CACHE_DIR},
        cache_ttl=3600,
    ) as client:
        response1 = await client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = await client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 验证缓存文件是否创建
        assert Path(TEST_CACHE_DIR).exists()
        assert len(list(Path(TEST_CACHE_DIR).glob("*"))) > 0


@respx.mock
def test_http_client_get_with_file_cache(
    cleanup_cache,
):  # 添加 cleanup_cache fixture
    """测试带文件缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    with HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="file",
        cache_config={"cache_dir": TEST_CACHE_DIR},
        cache_ttl=3600,
    ) as client:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 验证缓存文件是否创建
        assert Path(TEST_CACHE_DIR).exists()
        assert len(list(Path(TEST_CACHE_DIR).glob("*"))) > 0


@respx.mock
def test_http_client_get_with_redis_cache(cleanup_redis, redis_client):
    """测试带 Redis 缓存的 GET 请求"""
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    with HTTPClient(  # 注意这里使用的是同步的 HTTPClient
        base_url=TEST_BASE_URL,
        cache_type="redis",
        cache_config=TEST_REDIS_CONFIG,
        cache_ttl=3600,
    ) as client:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 验证 Redis 中的缓存值
        cached_data = redis_client.get(TEST_CACHE_KEY)
        assert cached_data is not None
        cached_json = json.loads(cached_data)
        assert cached_json["value"] == TEST_RESPONSE_DATA
        assert "expires" in cached_json

        # 第二次请求，应该从缓存获取
        response2 = client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1  # 请求次数应该仍然是1，因为使用了缓存


@respx.mock
@pytest.mark.asyncio
async def test_http_client_get_with_memory_cache():  # 添加 cleanup_cache fixture
    """测试带内存缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    async with AsyncHTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="memory",
        cache_ttl=3600,
    ) as client:
        response1 = await client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = await client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1


@respx.mock
def test_http_client_get_with_sync_memory_cache():  # 添加 cleanup_cache fixture
    """测试带内存缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    with HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="memory",
        cache_ttl=3600,
    ) as client:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1


@respx.mock
def test_http_client_get_with_sqlite_cache(cleanup_sqlite):
    """测试带 SQL 缓存的 GET 请求"""
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        side_effect=lambda request: time.sleep(1)
        or httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 使用独立的数据库文件路径
    db_path = "cache.db"

    client = HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="sqlite",
        cache_config={"engine_url": f"sqlite:///{db_path}"},
        cache_ttl=10,
    )
    try:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        response3 = client.get(TEST_ENDPOINT)
        assert response3 == TEST_RESPONSE_DATA
        assert route.call_count == 1

    finally:
        client.close()


@respx.mock
@pytest.mark.asyncio
async def test_http_client_get_with_async_sqlite_cache(cleanup_sqlite1):
    """测试带 SQL 缓存的 GET 请求"""
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 使用独立的数据库文件路径
    db_path = "cache1.db"

    async with AsyncHTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="sqlite",
        cache_config={"engine_url": f"sqlite:///{db_path}"},
        cache_ttl=1,
    ) as client:

        response1 = await client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        response3 = await client.get(TEST_ENDPOINT)
        assert response3 == TEST_RESPONSE_DATA
        assert route.call_count == 1


@respx.mock
def test_http_client_get_with_mysql_cache():  # 添加 cleanup_cache fixture
    """测试mysql缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    with HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="mysql",
        cache_config={"engine_url": "mysql+pymysql://root:123456@localhost:3306/test"},
        cache_ttl=2,
    ) as client:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_http_client_get_with_async_mysql_cache():
    """测试带 mysql 缓存的 GET 请求"""
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    async with AsyncHTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="mysql",
        cache_config={
            "engine_url": "mysql+pymysql://root:123456@localhost:3306/test",
            "table_name": "async_cache",
        },
        cache_ttl=1,
    ) as client:

        response1 = await client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        response3 = await client.get(TEST_ENDPOINT)
        assert response3 == TEST_RESPONSE_DATA
        assert route.call_count == 1


@respx.mock
def test_http_client_get_with_pg_cache():  # 添加 cleanup_cache fixture
    """测试pg缓存的 GET 请求"""
    # 修复：移除多余的元组包装，正确设置 mock 路由
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )
    from urllib.parse import quote

    # 第一次请求，应该访问实际 URL
    with HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="postgresql",
        cache_config={
            "engine_url": f"postgresql+psycopg2://root:{quote(TEST_PG_PWD)}@{TEST_PG_HOST}:5433/worksheet_manage"
        },
        cache_ttl=2,
    ) as client:
        response1 = client.get(TEST_ENDPOINT)
        assert response1 == TEST_RESPONSE_DATA
        assert route.call_count == 1

        # 第二次请求，应该从缓存获取
        response2 = client.get(TEST_ENDPOINT)
        assert response2 == TEST_RESPONSE_DATA
        assert route.call_count == 1
