# RedfishClient

一个轻量的 Redfish 客户端与固件更新工具集，聚焦于会话管理、资源访问与固件升级流程。代码结构清晰、可扩展，适合集成到自动化维护或制造测试流程中。

## 特性
- 会话鉴权与统一请求封装（支持 `X-Auth-Token`）
- 资源服务分层：`Systems`、`Firmware` 等服务的便捷入口
- 固件操作：上传镜像、触发 `SimpleUpdate`、轮询任务、删除占位条目、Power Cycle
- 端点可配置：通过 `endpoints.json` 适配不同 BMC 实现
- 结构化日志（控制台高可读性，文件详细排障）

## 目录结构

```
RedfishClient/
├─ main.py                          # 使用示例与演示流程
├─ endpoints.json                   # 端点配置（按 BMC 类型）
├─ redfish_client/
│  ├─ client.py                     # 客户端聚合器（传输、鉴权、资源入口）
│  ├─ config.py                     # 日志与端点加载/查询
│  ├─ auth/
│  │  ├─ base.py                    # 鉴权抽象基类
│  │  └─ session.py                 # 会话鉴权实现
│  ├─ transport/
│  │  ├─ base.py                    # 传输抽象基类
│  │  └─ requests.py                # 基于 requests 的传输实现
│  └─ resources/
│     ├─ base.py                    # 资源服务基类
│     ├─ systems.py                 # Systems 资源服务
│     └─ firmware.py                # 固件服务（上传/更新/任务/删除等）
└─ bmc_client/
   └─ bmc.py                        # 另一个 Web API 会话客户端（可选/示例）
```

## 使用 uv 管理依赖与环境

- 初始化并安装依赖：
  - `uv sync`
- 启动示例或服务：
  - 示例：`uv run python -m main`
  - MCP 服务：`uv run python -m mcp_server`
- 添加依赖：
  - 核心：`uv add requests loguru fastmcp`
  - 可选：`uv add --optional jsonpath`
- 升级依赖：
  - 全量：`uv sync --upgrade`
  - 指定：`uv add fastmcp@latest`
- 导出依赖（供非 uv 环境使用）：
  - `uv export -o requirements.txt`

## 快速开始

以固件升级流程为例（使用 uv 运行）：

```python
from redfish_client.client import RedfishClient
from redfish_client.config import setup_logging, load_endpoints

setup_logging(console_level='DEBUG')
load_endpoints()

client = RedfishClient(
    host="<BMC_IP>", port=443,
    username="<USER>", password="<PASS>",
    verify_ssl=False, timeout=60,
    bmc_type="default",  # 对应 endpoints.json 的键
)

if client.login():
    # 可选：设置升级是否保留 BIOS/BMC 配置
    client.firmware.preset_save_config('ActiveBIOSTarget', False)

    # 上传固件镜像（本地文件路径）
    client.firmware.upload_image('firmware.tar')

    # 触发更新（返回任务 URI，部分实现可能在响应体或 Location 头部）
    task_uri = client.firmware.simple_update('ActiveBIOSTarget')

    # 轮询任务直至完成（可根据需要处理返回对象）
    if task_uri:
        client.firmware.wait_for_task_completion(task_uri)

    # 执行 Power Cycle（部分平台要求）
    client.firmware.power_cycle()

    client.logout()
```

更多示例可参考 `main.py`。运行方式：`uv run python -m main`

启动后，可将 sse 服务地址配置到支持 MCP 服务的客户端中
如：
{
  "redfish-client": {
    "transport": "sse",
    "url": "http://10.2.48.155:8000/sse"
  }
}
📚 Docs:        https://gofastmcp.com  

## 端点配置

通过 `endpoints.json` 定义不同 BMC 类型的端点映射：

```json
{
  "default": {
    "SessionService": "/redfish/v1/SessionService/Sessions",
    "FirmwareInventory": "/redfish/v1/UpdateService/FirmwareInventory",
    "StartUpdate": "/redfish/v1/UpdateService/Actions/UpdateService.StartUpdate",
    "UpdateService": "/redfish/v1/UpdateService",
    "ActiveBIOSTarget": "/redfish/v1/UpdateService/FirmwareInventory/ActiveBIOS",
    "ActiveBMCTarget": "/redfish/v1/UpdateService/FirmwareInventory/ActiveBMC"
  }
}
```

- 通过 `load_endpoints()` 读取配置，再由 `get_endpoint(bmc_type, service)` 解析具体路径。
- 若某服务未配置，将回退到代码中的默认路径（如 `FirmwareInventory`）。

## 设计模式

- 抽象工厂 / 策略（Strategy）
  - `TransportBase` 与 `RequestsTransport`：以抽象基类定义传输接口，允许后续扩展不同 HTTP 客户端或协议实现。
  - `AuthBase` 与 `SessionAuth`：抽象鉴权流程，当前实现基于 Redfish 会话与 `X-Auth-Token`，可替换为其他认证策略。
- 外观（Facade）/ 聚合器
  - `RedfishClient` 聚合传输、鉴权与资源服务，提供统一的 `get/post/patch/delete` 与资源入口，简化上层调用。
- 服务分层（Service Layer）
  - `resources/*` 将具体资源（Systems、Firmware）封装为服务对象，职责明确，便于扩展与测试。
- 依赖注入（Constructor Injection）
  - `ResourceBase` 将客户端实例注入各服务，统一访问传输与鉴权上下文。
- 数据驱动配置
  - 使用 `endpoints.json` 以数据驱动端点，减少分支逻辑与硬编码，便于跨平台适配。

## 日志

- 通过 `setup_logging()` 统一配置控制台与文件日志：
  - 控制台：彩色输出、等级图标、方法/行号，便于交互式观察。
  - 文件：详细排障格式，按周轮转与保留。
- 常见请求/响应摘要与异常均有记录，适合问题定位与审计。

## 关键 API 速览

- 会话：`client.login()` / `client.logout()`
- 请求：`client.get/post/delete/patch(path, ...)`
- Systems：`client.systems.get_members()`、`get_member_details(member_path)`
- Firmware：
  - 查询：`get_firmware_inventory()`、`get_firmware_info(fid)`、`get_firmware_inventory_expanded()`
  - 上传：`upload_image(path)`（自动检测 `New*` 占位条目）
  - 更新：`preset_save_config(service, flag)`、`simple_update(service)`、`power_cycle()`
  - 任务：`get_task_status(uri)`、`wait_for_task_completion(uri)`、`wait_for_new_firmware_marker()`
  - 删除：`delete_uploaded_firmware()`

## 开发建议

- 若对接不同厂商/平台，优先通过 `endpoints.json` 添加/修改端点，再在服务层扩展兼容逻辑。
- 需要新增协议或传输方案时，实现 `TransportBase` 的子类并在 `RedfishClient` 中替换即可。
- 严禁在代码中硬编码敏感信息；使用外部配置或环境变量传递凭证。
