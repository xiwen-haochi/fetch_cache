import pytest
import os
import shutil
import httpx
from datetime import datetime, timedelta
from fetch_cache.core import HTTPClient
import respx
from pathlib import Path

base_dir = Path(__file__).parent.parent
TEST_BASE_URL = "http://test.com/api"
TEST_CACHE_DIR = base_dir / ".test_http_cache"
TEST_ENDPOINT = "/field_list"
TEST_RESPONSE_DATA = {"status": "success", "data": ["field1", "field2"]}


@pytest.fixture
def cleanup_cache():
    """清理测试缓存文件的 fixture"""
    if os.path.exists(TEST_CACHE_DIR):
        shutil.rmtree(TEST_CACHE_DIR)
    yield
    if os.path.exists(TEST_CACHE_DIR):
        shutil.rmtree(TEST_CACHE_DIR)


@pytest.fixture
def http_client():
    """创建 HTTPClient 实例的 fixture"""
    client = HTTPClient(
        base_url=TEST_BASE_URL,
        cache_type="file",
        cache_config={"cache_dir": TEST_CACHE_DIR},
        cache_ttl=3600,
    )
    yield client
    client.close()


@respx.mock
def test_http_client_get_with_file_cache(cleanup_cache, http_client):
    """测试带文件缓存的 GET 请求"""
    # 设置模拟路由
    route = respx.get(f"{TEST_BASE_URL}{TEST_ENDPOINT}").mock(
        return_value=httpx.Response(200, json=TEST_RESPONSE_DATA)
    )

    # 第一次请求，应该访问实际 URL
    response1 = http_client.get(TEST_ENDPOINT)
    assert response1 == TEST_RESPONSE_DATA
    assert route.call_count == 1

    # 第二次请求，应该从缓存获取
    response2 = http_client.get(TEST_ENDPOINT)
    assert response2 == TEST_RESPONSE_DATA
    assert route.call_count == 1

    # 验证缓存文件是否创建
    assert os.path.exists(TEST_CACHE_DIR)
    assert len(os.listdir(TEST_CACHE_DIR)) > 0
