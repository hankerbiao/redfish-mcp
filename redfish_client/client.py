from typing import Dict, Optional

from redfish_client.auth.session import SessionAuth
from redfish_client.resources.systems import SystemsService
from redfish_client.resources.firmware import FirmwareService
from redfish_client.transport.requests import RequestsTransport


class RedfishClient:
    """Redfish 客户端聚合器。

    - 管理底层传输、认证会话与资源服务入口。
    - 统一请求封装，自动合并默认头与鉴权头。
    """
    def __init__(self, host: str, port: int = 443, username: str = "", password: str = "", verify_ssl: bool = False,
                 timeout: int = 60, bmc_type: str = "default",https: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.bmc_type = bmc_type
        if https:
            protocol = "https"
        else:
            protocol = "http"
            self.port = 80

        base_url = f"{protocol}://{self.host}:{self.port}"
        print(base_url)
        self.transport = RequestsTransport(base_url=base_url, verify_ssl=False, timeout=timeout)
        self.auth = SessionAuth(self, username=username, password=password)
        self._systems = SystemsService(self)
        self._firmware = FirmwareService(self)

        self.default_headers: Dict[str, str] = {
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
        }

    def login(self) -> bool:
        return self.auth.login()

    def logout(self) -> bool:
        return self.auth.logout()

    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        merged = dict(self.default_headers)
        # 鉴权头覆盖默认头中的同名键
        merged.update(self.auth.default_restcall_header)
        if headers:
            merged.update(headers)
        return merged

    def request(self, method: str, path: str, headers: Optional[Dict[str, str]] = None, **kwargs):
        headers = self._merge_headers(headers)
        return self.transport.request(method, path, headers=headers, **kwargs)

    def get(self, path: str, **kwargs):

        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.request("PATCH", path, **kwargs)
    


    # Systems 资源便捷入口
    @property
    def systems(self) -> SystemsService:
        return self._systems

    # Firmware 资源便捷入口
    @property
    def firmware(self) -> FirmwareService:
        return self._firmware

__all__ = ["RedfishClient"]

