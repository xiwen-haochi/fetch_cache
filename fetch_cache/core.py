from datetime import datetime, timedelta
from typing import Optional
import httpx
from functools import lru_cache
from fetch_cache.cache import create_cache
from fetch_cache.utils.timing import timing_decorator
import hashlib


class HTTPClient(httpx.Client):
    def __init__(
        self,
        base_url,
        headers=None,
        cache_type: str = "memory",  # 默认使用内存缓存
        cache_config: Optional[dict] = None,  # 缓存配置
        cache_ttl: int = 3600,  # 缓存有效期（秒）
        retry_config: Optional[dict] = None,  # 新增重试配置参数
        **kwargs,
    ):
        # 处理重试配置
        if retry_config is not None:
            transport = httpx.HTTPTransport(
                retries=retry_config.get(
                    "retry_limits", 3
                )  # httpx 只支持简单的重试次数设置
            )
            kwargs["transport"] = transport

        super().__init__(
            timeout=kwargs.pop("timeout", 10),
            event_hooks={
                "request": [self.log_request],
                "response": [self.log_response],
            },
            **kwargs,
        )
        self.base_url = base_url
        self.headers = headers or {}

        # 处理缓存配置
        cache_config = cache_config or {}

        # 创建缓存实例
        self.cache = create_cache(cache_type, **cache_config)
        self.cache_ttl = cache_ttl

    @staticmethod
    def log_request(request):
        print(f"Request event hook: {request.method} {request.url}")

    @staticmethod
    def log_response(response):
        print(f"Response event hook: Status {response.status_code}")

    @staticmethod
    @lru_cache()
    def get_cache_key(
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> str:
        """获取缓存 key"""
        key = method + url + str(params or "") + str(data or "") + str(json_data or "")
        return hashlib.md5(key.encode()).hexdigest()

    @timing_decorator
    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
        **kwargs,
    ):
        url = str(self.base_url) + endpoint
        cache_key = self.get_cache_key(method, url, params, data, json_data)

        # 检查缓存
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        # 正确处理 headers
        headers = self.headers.copy()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        response = super().request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            headers=headers,
            **kwargs,
        )
        response_data = response.json()
        self.cache.set(cache_key, response_data, self.cache_ttl)
        return response_data


class AsyncHTTPClient(httpx.AsyncClient):
    """异步HTTP客户端，复用HTTPClient的缓存功能"""

    def __init__(
        self,
        base_url,
        headers=None,
        cache_type: str = "memory",
        cache_config: Optional[dict] = None,
        cache_ttl: int = 3600,
        **kwargs,
    ):
        # 处理base_url，确保末尾没有斜杠
        base_url = base_url.rstrip("/")
        super().__init__(
            base_url=base_url,
            headers=headers,
            timeout=kwargs.pop("timeout", 10),
            event_hooks={
                "request": [self.log_request],
                "response": [self.log_response],
            },
            **kwargs,
        )

        # 处理缓存配置
        cache_config = cache_config or {}

        # 创建缓存实例
        self.cache = create_cache(cache_type, **cache_config)
        self.cache_ttl = cache_ttl

    async def log_request(self, request):
        """记录请求信息"""
        print(f"Request event hook: {request.method} {request.url}")

    async def log_response(self, response):
        """记录响应信息"""
        print(f"Response event hook: {response.status_code} {response.url}")

    @staticmethod
    @lru_cache()
    def get_cache_key(
        method: str,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> str:
        """获取缓存 key"""
        key = method + url + str(params or "") + str(data or "") + str(json_data or "")
        return hashlib.md5(key.encode()).hexdigest()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
        **kwargs,
    ) -> httpx.Response:
        """重写请求方法，添加缓存支持"""
        # 处理URL，确保开头有斜杠
        url = str(self.base_url) + endpoint
        cache_key = self.get_cache_key(method, url, params, data, json_data)
        # 检查缓存
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            return cached_response

        # 正确处理 headers
        headers = self.headers.copy()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        response = await super().request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            headers=headers,
            **kwargs,
        )
        response_data = response.json()
        self.cache.set(cache_key, response_data, self.cache_ttl)
        return response_data


# ���试代码
# @respx.mock
# async def test_async():
#     async def delayed_response(request):
#         await asyncio.sleep(3)
#         return httpx.Response(
#             status_code=200, json={"data": {"bots": [{"id": 1, "name": "bot1"}]}}
#         )

#     route = respx.get(re.compile(r"http://api/v1/?/bots")).mock(
#         side_effect=delayed_response
#     )

#     async with AsyncHTTPClient(
#         base_url="http://api/v1", timeout=1.0, cache_type="memory"
#     ) as client:
#         try:
#             print("开始异步请求...")
#             response = await client.get("/bots")
#             print(f"Response: {response}")
#         except httpx.TimeoutException as e:
#             print(f"请求超时: {e}")
#         except Exception as e:
#             traceback.print_exc()
#             print(f"其他错误: {e}")

#     print(f"Route called times: {route.call_count}")


# if __name__ == "__main__":
#     print("\n=== 运行异步测试 ===")
#     asyncio.run(test_async())
