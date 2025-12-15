"""MCP 服务：基于 FastMCP 暴露 Redfish 相关工具

本服务提供以下工具（Tools）：
- redfish_login：登录 Redfish，返回连接 ID（用于后续调用）
- redfish_logout：登出指定连接
- get_machine_info：获取机器（Systems）成员列表及详情的关键信息
- login_and_get_machine_info：便捷地完成登录并直接返回机器信息
"""

from typing import Dict, List, Any
import uuid
from fastmcp import FastMCP
from redfish_client.client import RedfishClient
from redfish_client.config import setup_logging, load_endpoints

# FastMCP 服务实例名称，用于客户端识别与展示
mcp = FastMCP("Redfish MCP")

# 连接池：管理由 redfish_login 创建的客户端实例
# 键：connection_id（UUID 字符串）；值：RedfishClient 实例
CLIENTS: Dict[str, RedfishClient] = {}

def _redfish_login_impl(
    host: str,
    port: int = 443,
    username: str = "",
    password: str = "",
    verify_ssl: bool = False,
    timeout: int = 60,
    bmc_type: str = "default",
) -> str:
    setup_logging(console_level="INFO")
    load_endpoints()
    client = RedfishClient(
        host=host,
        port=port,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        timeout=timeout,
        bmc_type=bmc_type,
    )
    ok = client.login()
    if not ok:
        return ""
    cid = str(uuid.uuid4())
    CLIENTS[cid] = client
    return cid

def _get_machine_info_impl(connection_id: str) -> List[Dict[str, Any]]:
    client = CLIENTS.get(connection_id)
    if not client:
        return []
    members = client.systems.get_members()
    result: List[Dict[str, Any]] = []
    if isinstance(members, list):
        for m in members:
            path = m.get("@odata.id") if isinstance(m, dict) else None
            if not isinstance(path, str) or not path:
                continue
            details = client.systems.get_member_details(path)
            if isinstance(details, dict):
                info = {
                    "Id": details.get("Id"),
                    "Name": details.get("Name"),
                    "Manufacturer": details.get("Manufacturer"),
                    "Model": details.get("Model"),
                    "SerialNumber": details.get("SerialNumber"),
                    "UUID": details.get("UUID"),
                    "PowerState": details.get("PowerState"),
                    "Status": details.get("Status"),
                }
                result.append(info)
    return result

def _get_firmware_inventory_impl(connection_id: str) -> List[Dict[str, Any]]:
    client = CLIENTS.get(connection_id)
    if not client:
        return []
    members = client.firmware.get_firmware_inventory()
    return members or []

def _redfish_logout_impl(connection_id: str) -> bool:
    client = CLIENTS.pop(connection_id, None)
    if not client:
        return False
    return client.logout()

@mcp.tool
def redfish_login(
    host: str,
    port: int = 443,
    username: str = "",
    password: str = "",
    verify_ssl: bool = False,
    timeout: int = 60,
    bmc_type: str = "default",
) -> str:
    """登录 Redfish 并返回连接 ID，用于后续调用。

    参数：
    - host (str)：BMC 的主机地址或 IP，例如 "192.168.1.100"。
    - port (int, 默认 443)：HTTPS 端口。
    - username (str)：登录用户名。
    - password (str)：登录密码。
    - verify_ssl (bool, 默认 False)：是否验证 HTTPS 证书；自签名证书场景下通常为 False。
    - timeout (int, 默认 60)：请求超时时间（秒）。
    - bmc_type (str, 默认 "default")：端点类型键，需与 `endpoints.json` 中的配置匹配。

    返回：
    - str：连接 ID（UUID 字符串）；若登录失败，返回空字符串。

    说明：
    - 本函数会初始化日志并加载端点配置。
    - 创建并持久化 `RedfishClient`，后续通过 `connection_id` 访问。
    """
    return _redfish_login_impl(
        host=host,
        port=port,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        timeout=timeout,
        bmc_type=bmc_type,
    )

@mcp.tool
def redfish_logout(connection_id: str) -> bool:
    """登出指定连接并释放资源。

    参数：
    - connection_id (str)：通过 `redfish_login` 获得的连接 ID（UUID 字符串）。

    返回：
    - bool：成功为 True；若找不到连接或登出失败为 False。
    """
    return _redfish_logout_impl(connection_id)

@mcp.tool
def get_machine_info(connection_id: str) -> List[Dict[str, Any]]:
    """获取当前连接下的系统成员信息（简要字段集合）。

    参数：
    - connection_id (str)：通过 `redfish_login` 获得的连接 ID。

    返回：
    - List[Dict[str, Any]]：每个成员为一个字典，包含以下可能字段：
      - Id (str|None)
      - Name (str|None)
      - Manufacturer (str|None)
      - Model (str|None)
      - SerialNumber (str|None)
      - UUID (str|None)
      - PowerState (str|None)
      - Status (Dict[str, Any]|None)：通常包含 `Health` 与 `State`。

    说明：
    - 从 `/redfish/v1/Systems` 获取 `Members`，再逐个访问 `@odata.id` 拉取详情。
    - 若连接无效或接口异常，返回空列表。
    """
    return _get_machine_info_impl(connection_id)

@mcp.tool
def get_firmware_inventory(connection_id: str) -> List[Dict[str, Any]]:
    """获取可升级固件集合（FirmwareInventory 的 Members）。

    参数：
    - connection_id (str)：通过 `redfish_login` 获得的连接 ID（UUID 字符串）。

    返回：
    - List[Dict[str, Any]]：固件条目列表；每项通常包含：
      - `@odata.id` (str)：固件条目地址，用于后续详情访问
      - `Id` (str)：固件条目的标识符

    说明：
    - 调用 `FirmwareService.get_firmware_inventory()`，等价于访问 `/redfish/v1/UpdateService/FirmwareInventory`。
    - 若连接无效或请求失败，返回空列表而非抛出异常，便于调用方容错。
    """
    return _get_firmware_inventory_impl(connection_id)

@mcp.tool
def login_and_get_machine_info(
    host: str,
    port: int = 443,
    username: str = "",
    password: str = "",
    verify_ssl: bool = False,
    timeout: int = 60,
    bmc_type: str = "default",
) -> Dict[str, Any]:
    """便捷工具：登录并获取机器信息。

    参数：同 `redfish_login`。

    返回：
    - Dict[str, Any]：包含两个键：
      - connection_id (str)：登录成功的连接 ID；若登录失败为空字符串。
      - machines (List[Dict[str, Any]])：机器信息列表；登录失败时为空列表。
      - logged_out (bool)：是否已自动登出。

    说明：
    - 本函数在完成信息获取后会自动登出；无需额外调用。
    """
    cid = _redfish_login_impl(
        host=host,
        port=port,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        timeout=timeout,
        bmc_type=bmc_type,
    )
    info: List[Dict[str, Any]] = []
    logged_out: bool = False
    if cid:
        info = _get_machine_info_impl(cid)
        logged_out = _redfish_logout_impl(cid)
    return {"connection_id": cid, "machines": info, "logged_out": logged_out}

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
