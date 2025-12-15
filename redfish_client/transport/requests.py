
import requests
from requests.exceptions import RequestException
import urllib3
from loguru import logger
from typing import Optional, Dict

from redfish_client.transport.base import TransportBase

# 某些带自签名证书的 BMC/设备可能触发不安全证书警告；
# 在明确了解风险且需要关闭验证时，关闭该警告以减少日志噪音。
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestsTransport(TransportBase):
    """HTTP 传输层封装。

    参数:
        base_url: 服务器基础地址（例如 `https://host:443`）。
        verify_ssl: 是否校验 SSL 证书（默认 False，便于自签名证书的调试）。
        timeout: 请求超时时间（秒），防止请求长时间阻塞。
    """
    def __init__(self, base_url: str, verify_ssl: bool = False, timeout: int = 60):
        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        # 复用会话以提升性能（连接复用、Cookie/Headers 等上下文）。
        self.session = requests.Session()

    def full_url(self, path: str) -> str:
        """拼接完整请求地址。

        传入资源路径（如 `/redfish/v1/Systems`），返回完整 URL。
        """
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> requests.Response:
        """统一的请求入口。

        参数:
            method: HTTP 方法（GET/POST/DELETE 等）。
            path: 资源路径（以 `/` 开头）。
            headers: 额外请求头（与客户端默认头与鉴权头合并后传入）。
            **kwargs: 透传给 `requests.Session.request` 的其他参数（如 `json`, `params`）。

        返回:
            `requests.Response` 响应对象。

        异常:
            捕获并记录 `RequestException`，再向上抛出以便上层处理。
        """
        url = self.full_url(path)
        # 记录请求方法与目标地址、头部键、载荷大小，便于排障和审计。
        header_keys = list(headers.keys()) if headers else []
        json_payload = kwargs.get("json")
        params_payload = kwargs.get("params")
        data_payload = kwargs.get("data")
        json_size = len(str(json_payload)) if json_payload is not None else 0
        data_size = len(str(data_payload)) if data_payload is not None else 0
        logger.info(
            "HTTP 请求: {} {} | headers={} | json_size={} | data_size={} | params_keys={}",
            method,
            url,
            headers,
            json_size,
            data_size,
            list(params_payload.keys()) if isinstance(params_payload, dict) else None,
        )
        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout,
                # 当 `verify_ssl` 为 False 时允许自签名证书；为 True 时严格校验。
                verify=self.verify_ssl,
                **kwargs,
            )
            # 记录响应摘要信息：状态码、耗时、内容长度，并在 DEBUG 级别给出内容预览。
            elapsed_ms = int(resp.elapsed.total_seconds() * 1000) if resp.elapsed else None
            content_len = len(resp.content) if resp.content is not None else 0
            logger.info("HTTP 响应: {} {} | status={} | elapsed={}ms | length={}B", method, url, resp.status_code, elapsed_ms, content_len)
            preview = resp.text[:500] if isinstance(resp.text, str) else ""
            logger.debug("HTTP 响应预览: {} {} | {}", method, url, preview)
            return resp
        except RequestException as e:
            # 统一记录网络异常（连接失败、超时、证书错误等），并向上抛出。
            logger.error("HTTP 请求异常: {}", e)
            raise

__all__ = ["RequestsTransport", "RequestException"]
