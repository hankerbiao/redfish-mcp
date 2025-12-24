from typing import Dict, Optional
import uuid
from redfish_client.client import RedfishClient
from redfish_client.config import setup_logging, load_endpoints

setup_logging(console_level="INFO")
load_endpoints()

class ConnectionRegistry:
    def __init__(self) -> None:
        self._clients: Dict[str, RedfishClient] = {}

    def login(
        self,
        host: str,
        port: int = 443,
        username: str = "",
        password: str = "",
        verify_ssl: bool = False,
        timeout: int = 60,
        bmc_type: str = "default",
    ) -> str:
        client = RedfishClient(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            timeout=timeout,
            bmc_type=bmc_type,
        )
        if not client.login():
            return ""
        cid = str(uuid.uuid4())
        self._clients[cid] = client
        return cid

    def get(self, connection_id: str) -> Optional[RedfishClient]:
        return self._clients.get(connection_id)

    def logout(self, connection_id: str) -> bool:
        client = self._clients.pop(connection_id, None)
        if not client:
            return False
        return client.logout()

registry = ConnectionRegistry()

