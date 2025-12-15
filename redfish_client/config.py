import json
from loguru import logger
import sys
from typing import Dict, Optional


def setup_logging(console_level: str = "INFO", file_level: str = "DEBUG", logfile: str = "redfish.log") -> None:
    """配置统一日志。

    - 控制台输出：彩色、带图标，适合交互式观察。
    - 文件输出：详细排障日志（默认 DEBUG，包含进程/线程、文件与行号）。
    - 按周轮转，保留 4 周。
    """
    logger.remove()

    # 定义各级别图标与颜色
    logger.level("INFO", icon="💡", color="<blue>")
    logger.level("SUCCESS", icon="✅", color="<green>")
    logger.level("WARNING", icon="⚠️", color="<yellow>")
    logger.level("ERROR", icon="❌", color="<red>")
    logger.level("DEBUG", icon="🐞", color="<magenta>")

    # 控制台输出
    logger.add(
        sys.stdout,
        level=console_level,
        enqueue=True,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level.icon} {level.name:<8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )

    # 文件输出 (保持不变)
    logger.add(
        logfile,
        level=file_level,
        rotation="1 week",
        retention="4 weeks",
        encoding="utf-8",
        enqueue=True,
        format=(
            "[{time:YYYY-MM-DD HH:mm:ss}] | {level:<8} | "
            "{process.name}:{process.id} {thread.name} | "
            "{file}:{line} {function} | {message}"
        ),
    )


_ENDPOINTS: Dict[str, Dict[str, str]] = {}


def load_endpoints(path: str = "endpoints.json") -> None:
    """加载并解析接口配置文件。"""
    global _ENDPOINTS
    try:
        with open(path, "r") as f:
            _ENDPOINTS = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"无法加载或解析接口配置文件: {e}")
        _ENDPOINTS = {}


def get_endpoint(bmc_type: str, service: str) -> Optional[str]:
    """获取指定 BMC 类型和服务的接口地址。"""
    return _ENDPOINTS.get(bmc_type, {}).get(service)


__all__ = ["setup_logging", "logger", "load_endpoints", "get_endpoint"]
