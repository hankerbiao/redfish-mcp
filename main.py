from redfish_client.client import RedfishClient
from redfish_client.config import setup_logging, logger, load_endpoints

if __name__ == '__main__':
    # 配置统一日志
    setup_logging(console_level='DEBUG')

    # 加载接口配置
    load_endpoints()
    host = "10.32.131.133"
    client = RedfishClient(host=host, port=443, username='ADMIN', password='ADMIN', verify_ssl=False,
                           timeout=60, bmc_type="default")

    if client.login():
        logger.info("示例：登录成功")
        # 示例：固件服务操作
        logger.info("--- 开始升级固件服务 ---")
        # members = client.firmware.get_firmware_inventory()
        # for member in members:
        #     print(member)
        # client.firmware.preset_save_config('ActiveBIOSTarget',False)  # 设置保留/不保留 配置
        # 上传文件
        # client.firmware.upload_image('VDYH011017-U01.tar')  # 上传
        # client.firmware.simple_update('ActiveBIOSTarget')  # 开始更新
        # client.firmware.power_cycle()  # 执行 power cycle
        if client.logout():
            logger.info("示例：注销成功")
        else:
            logger.error("示例：注销失败")
    else:
        logger.error("示例：登录失败")
