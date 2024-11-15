import pytest
import os
import shutil
import httpx
from datetime import datetime, timedelta
from fetch_cache.core import HTTPClient, AsyncHTTPClient
import respx
import redis
from pathlib import Path
import json
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
env_file = os.getenv("ENV_FILE", ".env.test")
load_dotenv(BASE_DIR / env_file)

TEST_CACHE_DIR = BASE_DIR / ".test_http_cache"
TEST_BASE_URL = os.getenv("TEST_BASE_URL")  # http://test.com/api
TEST_ENDPOINT = os.getenv("TEST_ENDPOINT")  # field_list
TEST_RESPONSE_DATA = json.loads(
    os.getenv("TEST_RESPONSE_DATA")
)  # {"status": "success", "data": ["field1", "field2"]}
TEST_REDIS_CONFIG = json.loads(
    os.getenv("TEST_REDIS_CONFIG")
)  # {"host": "xxxxx", "port": 6379}
TEST_CACHE_KEY = os.getenv("TEST_CACHE_KEY")  # 51bd0e494f6f3566fb098d6d809073d2


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
