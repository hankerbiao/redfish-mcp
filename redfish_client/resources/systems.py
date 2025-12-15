from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from loguru import logger

from redfish_client.resources.base import ResourceBase

if TYPE_CHECKING:
    from redfish_client.client import RedfishClient


class SystemsService(ResourceBase):
    """
    Redfish Systems 资源服务层。
    提供对 /redfish/v1/Systems 及其子资源的便捷访问。
    """

    def __init__(self, client: "RedfishClient") -> None:
        super().__init__(client)
        self._systems_path = "/redfish/v1/Systems"

    def get_members(self) -> Optional[List[Dict[str, Any]]]:
        """获取系统成员列表: GET /redfish/v1/Systems"""
        response = self._client.get(self._systems_path)
        if not response:
            logger.warning("获取系统成员列表失败: status=N/A")
            return None
        if response.status_code != 200:
            logger.warning(f"获取系统成员列表失败: status={response.status_code} {getattr(response, 'text', '')}")
            return None
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"解析系统成员列表失败: {e}")
            return None
        members = data.get("Members", [])
        if not isinstance(members, list):
            logger.error("Members 字段类型异常")
            return None
        logger.info(f"系统成员数量: {len(members)}")
        return members

    def get_member_details(self, member_path: str) -> Optional[Dict[str, Any]]:
        """获取单个系统成员详情: GET {member_path}"""
        response = self._client.get(member_path)
        if not response:
            logger.warning("获取系统成员详情失败: status=N/A")
            return None
        if response.status_code != 200:
            logger.warning(f"获取系统成员详情失败: status={response.status_code} {getattr(response, 'text', '')}")
            return None
        try:
            return response.json()
        except Exception as e:
            logger.error(f"解析系统成员详情失败: {e}")
            return None

    def get_members_formatted(self) -> Optional[str]:
        members = self.get_members()
        if members is None:
            return None
        rows = []
        for idx, m in enumerate(members, start=1):
            oid = m.get("@odata.id") if isinstance(m, dict) else None
            mid = m.get("Id") if isinstance(m, dict) else None
            rows.append(f"{idx:>3} | {mid or ''} | {oid or ''}")
        header = "Idx | Id  | @odata.id"
        return "\n".join([header] + rows)

    def get_member_details_formatted(self, member_path: str) -> Optional[str]:
        details = self.get_member_details(member_path)
        if details is None:
            return None
        keys = [
            "Id",
            "Name",
            "Manufacturer",
            "Model",
            "SerialNumber",
            "UUID",
            "PowerState",
        ]
        lines = []
        for k in keys:
            v = details.get(k)
            if v is not None:
                lines.append(f"{k}: {v}")
        status = details.get("Status")
        if isinstance(status, dict):
            health = status.get("Health")
            state = status.get("State")
            if health is not None:
                lines.append(f"Status.Health: {health}")
            if state is not None:
                lines.append(f"Status.State: {state}")
        return "\n".join(lines)


