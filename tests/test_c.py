import pytest
import os
import shutil
import httpx
from datetime import datetime, timedelta
from fetch_cache.core import HTTPClient, AsyncHTTPClient
from fetch_cache.utils.async_sync import async_to_sync
import respx
import time
from pathlib import Path
import json
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
env_file = os.getenv("ENV_FILE", ".env.test")
load_dotenv(BASE_DIR / env_file)
TEST_CACHE_DIR = BASE_DIR / ".test_http_cache"
TEST_SQLITE_PATH = BASE_DIR / "cache2.db"
TEST_SQLITE_PATH1 = BASE_DIR / "cache1.db"
TEST_BASE_URL = "http://test.com/api"
TEST_ENDPOINT = "field_list"
TEST_RESPONSE_DATA = {"status": "success", "data": ["field1", "field2"]}
TEST_REDIS_CONFIG = json.loads(
    os.getenv("TEST_REDIS_CONFIG")
)  # {"host": "xxxxx", "port": 6379}
TEST_CACHE_KEY = "51bd0e494f6f3566fb098d6d809073d2"


@pytest.fixture
def cleanup_sqlite():
    """清理测试 SQLite 缓存"""
    if TEST_SQLITE_PATH.exists():
        TEST_SQLITE_PATH.unlink()

    yield
    if TEST_SQLITE_PATH.exists():
        TEST_SQLITE_PATH.unlink()


@pytest.fixture
def cleanup_sqlite1():
    """清理测试 SQLite 缓存"""
    if TEST_SQLITE_PATH1.exists():
        TEST_SQLITE_PATH1.unlink()

    yield
    if TEST_SQLITE_PATH1.exists():
        TEST_SQLITE_PATH1.unlink()


@respx.mock
def test_http_client_get_with_sql_cache(cleanup_sqlite):
    """测试带 SQL 缓存的 GET 请求"""
    route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
        side_effect=lambda request: time.sleep(1)
        or httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 使用独立的数据库文件路径
    db_path = "cache2.db"

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


# @respx.mock
# @pytest.mark.asyncio
# async def test_http_client_get_with_async_sqlite_cache(cleanup_sqlite1):
#     """测试带 SQL 缓存的 GET 请求"""
#     route = respx.get(f"{TEST_BASE_URL}/field_list").mock(
#         return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
#     )

#     # 使用独立的数据库文件路径
#     db_path = "cache1.db"

#     async with AsyncHTTPClient(
#         base_url=TEST_BASE_URL,
#         cache_type="sqlite",
#         cache_config={"engine_url": f"sqlite:///{db_path}"},
#         cache_ttl=1,
#     ) as client:

#         response1 = await client.get(TEST_ENDPOINT)
#         assert response1 == TEST_RESPONSE_DATA
#         assert route.call_count == 1

#         response3 = await client.get(TEST_ENDPOINT)
#         assert response3 == TEST_RESPONSE_DATA
#         assert route.call_count == 1