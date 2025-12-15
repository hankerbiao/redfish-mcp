from __future__ import annotations
import json
from typing import Dict, TYPE_CHECKING
from loguru import logger
from requests.exceptions import RequestException

from redfish_client.auth.base import AuthBase
from redfish_client.config import get_endpoint

if TYPE_CHECKING:
    from redfish_client.client import RedfishClient


class SessionAuth(AuthBase):
    """维护 Redfish 会话与鉴权信息。

    - 负责登录与登出，提取并管理 `X-Auth-Token`。
    - 暴露可复用的认证头，用于后续所有资源请求。
    """

    def __init__(self, client: "RedfishClient", username: str, password: str):
        self._client = client
        self.username = username
        self.password = password
        self.is_logged_in = False
        self.session_path: str = ""

        # 供其他请求复用的认证头
        self._default_restcall_header: Dict[str, str] = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:55.0) Gecko/20100101 Firefox/55.0',
            'X-Auth-Token': "",
            'X-Requested-With': 'XMLHttpRequest'
        }

    @property
    def default_restcall_header(self) -> Dict[str, str]:
        return self._default_restcall_header

    def login(self) -> bool:
        path = get_endpoint(self._client.bmc_type, "SessionService")
        if not path:
            logger.error(f"未找到 {self._client.bmc_type} 的 SessionService 端点")
            return False

        payload = {"UserName": self.username, "Password": self.password}

        logger.info("开始登录: 用户 {} path {} payload {}", self.username, path,
                    json.dumps({"UserName": self.username, "Password": "***"}))
        try:
            response = self._client.transport.request("POST", path, json=payload)
        except RequestException:
            response = None

        if response is None or response.status_code not in [200, 201]:
            logger.error("登录失败: 状态码 {} 内容: {}", getattr(response, "status_code", "N/A"),
                         getattr(response, "text", "")[:200])
            return False

        self.is_logged_in = True
        self.session_path = response.headers.get("Location", "")
        token = response.headers.get('x-auth-token', "")
        self._default_restcall_header.update({'X-Auth-Token': token})

        logger.info(f"登录成功: session_path={self.session_path} | token_len={len(token)}")
        return True

    def logout(self) -> bool:
        if not self.is_logged_in or not self.session_path:
            logger.warning("未登录或无会话路径，无需登出")
            return False

        try:
            logger.debug(f"准备登出: session_path={self.session_path}")
            response = self._client.transport.request("DELETE", self.session_path, headers=self.default_restcall_header)
            if response.status_code >= 400:
                logger.error("登出失败: 状态码 {}", response.status_code)
                return False
        except RequestException as e:
            logger.error("登出请求异常: {}", e)
            return False

        self.is_logged_in = False
        self.session_path = ""
        self._default_restcall_header['X-Auth-Token'] = ""
        logger.info("登出成功: 状态码 {}", response.status_code)
        return True


__all__ = ["SessionAuth"]
