from typing import List, Dict, Any
from .connection import registry

def redfish_login(
    host: str,
    port: int = 443,
    username: str = "",
    password: str = "",
    verify_ssl: bool = False,
    timeout: int = 60,
    bmc_type: str = "default",
) -> str:
    return registry.login(
        host=host,
        port=port,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
        timeout=timeout,
        bmc_type=bmc_type,
    )

def redfish_logout(connection_id: str) -> bool:
    return registry.logout(connection_id)

def get_machine_info(connection_id: str) -> List[Dict[str, Any]]:
    client = registry.get(connection_id)
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
                result.append(
                    {
                        "Id": details.get("Id"),
                        "Name": details.get("Name"),
                        "Manufacturer": details.get("Manufacturer"),
                        "Model": details.get("Model"),
                        "SerialNumber": details.get("SerialNumber"),
                        "UUID": details.get("UUID"),
                        "PowerState": details.get("PowerState"),
                        "Status": details.get("Status"),
                    }
                )
    return result

def get_firmware_inventory(connection_id: str) -> List[Dict[str, Any]]:
    client = registry.get(connection_id)
    if not client:
        return []
    members = client.firmware.get_firmware_inventory()
    return members or []

def login_and_get_machine_info(
    host: str,
    port: int = 443,
    username: str = "",
    password: str = "",
    verify_ssl: bool = False,
    timeout: int = 60,
    bmc_type: str = "default",
) -> Dict[str, Any]:
    cid = redfish_login(
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
        info = get_machine_info(cid)
        logged_out = redfish_logout(cid)
    return {"connection_id": cid, "machines": info, "logged_out": logged_out}

