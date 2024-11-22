from typing import Optional, Dict, Any
import httpx
import hashlib

from fetch_cache.cache import create_cache


class HTTPClient(httpx.Client):
    def __init__(
        self,
        base_url,
        headers=None,
        cache_type: str = "memory",  # 默认使用内存缓存
        cache_config: Optional[Dict[str, Any]] = None,  # 缓存配置
        cache_ttl: int = 3600,  # 缓存有效期（秒）
        **kwargs,
    ):

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

        self.cache_ttl = cache_ttl
        if cache_ttl:
            self.cache = create_cache(cache_type, **cache_config)

    @staticmethod
    def log_request(request):
        pass
        # print(f"Request event hook: {request.method} {request.url}")

    @staticmethod
    def log_response(response):
        pass
        # print(f"Response event hook: Status {response.status_code}")

    @staticmethod
    def get_cache_key(
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> str:
        """获取缓存 key"""
        params_str = str(params or "")
        data_str = str(data or "")
        json_str = str(json or "")

        key = method + url + params_str + data_str + json_str
        return hashlib.md5(key.encode()).hexdigest()

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        url = str(self.base_url) + endpoint
        no_cache = kwargs.pop("no_cache", False)
        cache_key = self.get_cache_key(method, url, params, data, json)
        # 检查缓存
        if not no_cache and self.cache_ttl:
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
            json=json,
            headers=headers,
            **kwargs,
        )
        if response.status_code == 200 and "application/json" in response.headers.get(
            "content-type", ""
        ):
            if not no_cache and self.cache_ttl:
                response_data = response.json()
                self.cache.set(cache_key, response_data, self.cache_ttl)
                return response_data
            else:
                return response.json()
        return response

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs):
        """Convenience method for GET requests"""
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Convenience method for POST requests"""
        return self.request(
            "POST", endpoint, data=data, json=json, params=params, **kwargs
        )

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Convenience method for PUT requests"""
        return self.request(
            "PUT", endpoint, data=data, json=json, params=params, **kwargs
        )

    def close(self):
        """关闭客户端和缓存连接"""
        # 关闭缓存连接（如果存在）
        if self.cache_ttl and hasattr(self.cache, "_engine"):
            self.cache._engine.dispose()

        # 调用父类的 close 方法
        super().close()


class AsyncHTTPClient(httpx.AsyncClient):
    """异步HTTP客户端，复用HTTPClient的缓存功能"""

    def __init__(
        self,
        base_url,
        headers=None,
        cache_type: str = "memory",
        cache_config: Optional[Dict[str, Any]] = None,
        cache_ttl: int = 3600,
        **kwargs,
    ):
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
        self.base_url = base_url
        self.headers = headers or {}
        # 创建缓存实例
        self.cache_ttl = cache_ttl
        if cache_ttl:
            self.cache = create_cache(cache_type, **cache_config)

    async def log_request(self, request):
        """记录请求信息"""
        pass
        # print(f"Request event hook: {request.method} {request.url}")

    async def log_response(self, response):
        """记录响应信息"""
        pass
        # print(f"Response event hook: {response.status_code} {response.url}")

    @staticmethod
    def get_cache_key(
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> str:
        """获取缓存 key"""
        # 将字典转换为排序后的元组，确保生成稳定的字符串表示
        params_str = str(params or "")
        data_str = str(data or "")
        json_str = str(json or "")

        key = method + url + params_str + data_str + json_str
        return hashlib.md5(key.encode()).hexdigest()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> httpx.Response:
        """重写请求方法，添加缓存支持"""
        # 处理URL，确保开头有斜杠
        url = str(self.base_url) + endpoint
        no_cache = kwargs.pop("no_cache", False)
        if not no_cache and self.cache_ttl:
            print(f"cache_key: {method}, {url}, {params}, {data}, {json}")
            cache_key = self.get_cache_key(method, url, params, data, json)
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
            json=json,
            headers=headers,
            **kwargs,
        )
        if response.status_code == 200 and "application/json" in response.headers.get(
            "content-type", ""
        ):
            if not no_cache and self.cache_ttl:
                response_data = response.json()
                self.cache.set(cache_key, response_data, self.cache_ttl)
                return response_data
            else:
                return response.json()
        return response

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """Convenience method for async GET requests"""
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Convenience method for async POST requests"""
        return await self.request(
            "POST", endpoint, data=data, json=json, params=params, **kwargs
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Convenience method for async PUT requests"""
        return await self.request(
            "PUT", endpoint, data=data, json=json, params=params, **kwargs
        )

    async def close(self):
        """关闭异步客户端和缓存连接"""
        # 关闭缓存连接（如果存在）
        if self.cache_ttl and hasattr(self.cache, "_engine"):
            self.cache._engine.dispose()

        # 调用父类的 close 方法
        await super().close()
