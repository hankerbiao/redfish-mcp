from typing import Optional, Dict, Any, List
import os
import time
from loguru import logger
from .base import ResourceBase
from redfish_client.config import get_endpoint


class FirmwareService(ResourceBase):
    """固件服务类，用于处理固件更新相关操作。

    职责概述：
    - 查询固件清单与详细信息
    - 上传固件文件（包含获取任务 URI 的便捷方法）
    - 触发 SimpleUpdate 并跟踪任务进度
    - 轮询任务状态直到完成/失败
    - 检测上传占位条目（Id 以 New 开头）
    - 删除已上传的占位条目
    """

    def __init__(self, client):
        super().__init__(client)

    def _get_service_path(self, service_name: str, default: str) -> str:
        """优先从配置中获取路径，否则使用默认路径。

        参数：
        - service_name: 端点名称（例如 FirmwareInventory/StartUpdate）
        - default: 未配置时的默认路径
        """
        path = get_endpoint(self._client.bmc_type, service_name)
        if path:
            return path
        return default

    def get_firmware_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """查询可升级的固件集合。

        返回值：Members 数组（每个成员含 `@odata.id`、`Id` 等）或 None
        """
        path = self._get_service_path("FirmwareInventory", "/redfish/v1/UpdateService/FirmwareInventory")

        logger.info(f"获取固件清单: {path}")
        response = self._client.get(path)
        if response.status_code == 200:
            data = response.json()
            members = data.get("Members", [])
            logger.info(f"发现 {len(members)} 个固件条目")
            return members
        else:
            logger.error(f"获取固件清单失败: {response.status_code} {response.text}")
            return None

    def get_firmware_info(self, firmware_id: str) -> Optional[Dict[str, Any]]:
        """查询指定固件条目详情。

        入参可为完整 `@odata.id` 或集合下的 `Id`。
        """
        base_path = self._get_service_path("FirmwareInventory", "/redfish/v1/UpdateService/FirmwareInventory")
        path = firmware_id if firmware_id.startswith("/redfish/") else f"{base_path}/{firmware_id}"
        logger.info(f"获取固件详细信息: {path}")
        response = self._client.get(path)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"获取固件 {firmware_id} 失败: {response.status_code} {response.text}")
            return None

    def get_firmware_inventory_expanded(self) -> Optional[List[Dict[str, Any]]]:
        """查询固件清单并使用 `$expand=.` 展开当前层级详情。

        用于一次性获取 `Members` 的详细字段，便于判定上传占位条目。
        """
        path = self._get_service_path("FirmwareInventory", "/redfish/v1/UpdateService/FirmwareInventory")
        path = f"{path}?$expand=."
        logger.info(f"获取固件清单(展开): {path}")
        response = self._client.get(path)
        if response.status_code == 200:
            data = response.json()
            return data.get("Members", [])
        else:
            logger.error(f"获取固件清单失败: {response.status_code} {response.text}")
            return None

    def preset_save_config(self, service_name: str, flag: bool) -> bool:
        path = self._get_service_path("UpdateService", "/redfish/v1/UpdateService")
        if "bmc" in service_name.lower():
            save_config_payload = {"Oem": {"Public": {"PreserveBmcConfig": flag}}}
        else:
            save_config_payload = {"Oem": {"Public": {"PreserveBiosConfig": flag}}}

        logger.info(
            f"执行不保存配置升级设置 UpdateService: path={path},save_config_payload:{save_config_payload} ")
        etag_resp = self._client.get(path)
        etag = etag_resp.headers.get('ETag') or etag_resp.headers.get('etag')
        headers = {"Content-Type": "application/json"}
        if etag:
            headers["If-Match"] = etag
            # headers["etag"] = etag
        response = self._client.patch(path, json=save_config_payload, headers=headers)
        if response.status_code in [200, 202, 204]:
            return True
        logger.error(f"SimpleUpdate 失败: {response.status_code} {response.text}")
        return False

    def upload_image(self, file_path: str) -> bool:
        """上传固件文件（表单方式）。

        - 默认上传至 `FirmwareInventory` 集合
        - 某些厂商需要附带 `uploadTarget` 指定目标条目
        """
        if not os.path.exists(file_path):
            logger.error(f"固件文件不存在: {file_path}")
            return False

        target_uri = self._get_service_path("FirmwareInventory", "/redfish/v1/UpdateService/FirmwareInventory")

        size = os.path.getsize(file_path)
        if size == 0:
            logger.error(f"固件文件为空: {file_path}")
            return False
        logger.info(f"开始上传固件: src={file_path} size={size}B target={target_uri}")
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}

                # 构造表单数据
                data = {}
                response = self._client.post(target_uri, files=files, data=data)

                if response.status_code in [200, 201, 202]:
                    logger.info(
                        f"固件上传成功: status={response.status_code} length={len(response.content) if response.content else 0}B")
                    # 等待上传成功
                    self.wait_for_new_firmware_marker()

                    return True
                else:
                    logger.error(f"固件上传失败: {response.status_code} {response.text}")
                    return False
        except Exception as e:
            logger.error(f"固件上传异常: {e}")
            return False

    def power_cycle(self, system_id: str = "1") -> bool:
        path = f"/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset"
        payload = {"ResetType": "ForcePowerCycle"}
        logger.info(f"执行电源循环: path={path} payload={payload}")
        response = self._client.post(path, json=payload)
        if response.status_code in [200, 202, 204]:
            return True
        logger.error(f"电源循环失败: {response.status_code} {response.text}")
        return False

    def simple_update(self, service_name) -> Optional[str]:
        """触发 SimpleUpdate 并返回任务 URI（如有）。

        某些实现需在上传后配合 `@Redfish.OperationApplyTime="OnStartUpdateRequest"` 使用。
        """
        path = self._get_service_path("StartUpdate", "/redfish/v1/UpdateService/Actions/UpdateService.StartUpdate")
        target = self._get_service_path(service_name, '')

        payload = {
            "ForceUpdate": True,
            "Targets": [target]
        }

        logger.info(
            f"执行 SimpleUpdate: path={path} targets={payload.get('Targets')} save_config={payload.get('SaveConfig')}")
        response = self._client.post(path, json=payload)

        if response.status_code in [200, 202]:
            # 尝试从 Location 头获取 Task URI
            task_location = response.headers.get("Location")
            if not task_location:
                # 尝试从响应体获取
                body = response.json()
                task_location = body.get("@odata.id")

            logger.info(f"升级请求已接受, 任务 URI: {task_location}")
            return task_location
        else:
            logger.error(f"升级请求失败: {response.status_code} {response.text}")
            return None

    def get_task_status(self, task_uri: str) -> Optional[Dict[str, Any]]:
        """查询任务状态（`TaskState`/`TaskStatus`/`PercentComplete`）。"""
        logger.info(f"查询任务状态: {task_uri}")
        response = self._client.get(task_uri)

        if response.status_code == 200:
            data = response.json()
            state = data.get("TaskState", "Unknown")
            status = data.get("TaskStatus", "Unknown")
            logger.info(f"任务状态: state={state} status={status} percent={data.get('PercentComplete')}")
            return data
        else:
            logger.error(f"获取任务状态失败: {response.status_code} {response.text}")
            return None

    def wait_for_task_completion(self, task_uri: str, interval: int = 5, timeout: int = 900) -> Optional[
        Dict[str, Any]]:
        """轮询任务直至完成/失败或超时。

        - interval: 轮询间隔秒
        - timeout: 最长等待秒
        返回：最终任务对象，或 None（失败/超时）
        """
        logger.info(f"等待任务完成: {task_uri} interval={interval}s timeout={timeout}s")
        start = time.time()
        attempts = 0
        while True:
            if time.time() - start > timeout:
                logger.error("等待任务超时")
                return None
            resp = self._client.get(task_uri)
            if not resp or resp.status_code != 200:
                logger.error(f"查询任务失败: status={resp.status_code if resp else 'N/A'}")
                return None
            data = resp.json()
            state = data.get("TaskState")
            status = data.get("TaskStatus")
            percent = data.get("PercentComplete")
            attempts += 1
            logger.info(
                f"任务进度: state={state} status={status} percent={percent} attempts={attempts} elapsed={int(time.time() - start)}s")
            if state in ["Completed"]:
                return data
            if state in ["Exception", "Cancelled", "Failed"]:
                return data
            time.sleep(interval)

    def wait_for_new_firmware_marker(self, prefix: str = "New", interval: int = 3, timeout: int = 300) -> Optional[
        Dict[str, Any]]:
        """轮询固件清单，直到出现以 `prefix` 开头的占位条目。

        用于判断上传已被服务端接收但尚未应用。返回匹配的成员对象。
        """
        start = time.time()
        attempts = 0
        while True:
            if time.time() - start > timeout:
                logger.error("等待 New* 固件条目标记超时")
                return None
            members = self.get_firmware_inventory_expanded()
            if isinstance(members, list):
                for m in members:
                    mid = m.get("Id")
                    oid = m.get("@odata.id", "")
                    if (isinstance(mid, str) and mid.startswith(prefix)) or ("/New" in oid):
                        logger.info(f"检测到上传标记条目: {mid or oid}")
                        return m
            attempts += 1
            logger.debug(f"未检测到 {prefix}* 条目，继续轮询: attempts={attempts} interval={interval}s")
            time.sleep(interval)

    def delete_uploaded_firmware(self) -> bool:
        """删除最新检测到的上传占位条目（自动检索）。

        无参：内部先调用 `wait_for_new_firmware_marker()` 获取目标，再执行 DELETE。
        """
        marker = self.wait_for_new_firmware_marker(prefix="New", interval=3, timeout=300)
        if not marker:
            logger.error("未检测到已上传的 New* 固件条目")
            return False
        fid = marker.get("Id")
        oid = marker.get("@odata.id")
        base_path = self._get_service_path("FirmwareInventory", "/redfish/v1/UpdateService/FirmwareInventory")
        path = oid if isinstance(oid, str) and oid.startswith("/redfish/") else (f"{base_path}/{fid}" if fid else None)
        if not path:
            logger.error("无法解析固件条目标识")
            return False
        logger.info(f"删除已上传固件: id={fid} path={path}")
        resp = self._client.delete(path)
        if not resp:
            logger.error("删除请求无响应")
            return False
        if resp.status_code in [200, 202, 204]:
            try:
                body = resp.json()
                if isinstance(body, dict) and "error" in body:
                    err = body.get("error") or {}
                    code = err.get("code")
                    message = err.get("message")
                    if code and "Success" in code:
                        logger.info(f"删除成功: {code} {message}")
                        return True
            except Exception:
                pass
            if resp.status_code in [202, 204]:
                logger.info(f"删除请求接受/无内容: {resp.status_code}")
                return True
            if isinstance(resp.text, str) and ("Success" in resp.text or "completed successfully" in resp.text):
                logger.info("删除成功: 文本确认")
                return True
        logger.error(f"删除失败: {resp.status_code} {resp.text}")
        return False
