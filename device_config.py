"""
设备参数配置模块
提供真实的iOS设备配置，避免被识别为robot
"""
import random
from tools import get_random_gps


class DeviceConfig:
    """设备配置类"""
    
    # iOS版本池（真实存在的版本，避免使用过新或不存在的版本）
    IOS_VERSIONS = [
        "14.0",  # iPhone 12系列默认版本
        "14.1",
        "14.2",
        "14.3",
        "14.4",
        "14.5",
        "14.6",
        "14.7",
        "14.8",
        "15.0",  # iPhone 13系列默认版本
        "15.1",
        "15.2",
        "15.3",
        "15.4",
        "15.5",
        "15.6",
        "15.7",
        "16.0",  # iPhone 14系列默认版本
        "16.1",
        "16.2",
        "16.3",
        "16.4",
        "16.5",
        "16.6",
        "17.0",  # iPhone 15系列默认版本
        "17.1",
        "17.2",
        "17.3",
        "17.4",
        "17.5"
    ]
    
    # iPhone机型池（真实机型标识符）
    IPHONE_MODELS = [
        # iPhone 12系列 (iOS 14+)
        ("iPhone13,1", "iPhone 12 mini"),
        ("iPhone13,2", "iPhone 12"),
        ("iPhone13,3", "iPhone 12 Pro"),
        ("iPhone13,4", "iPhone 12 Pro Max"),
        
        # iPhone 11系列 (iOS 13+)
        ("iPhone12,1", "iPhone 11"),
        ("iPhone12,3", "iPhone 11 Pro"),
        ("iPhone12,5", "iPhone 11 Pro Max"),
        
        # iPhone XS/XR系列 (iOS 12+)
        ("iPhone11,2", "iPhone XS"),
        ("iPhone11,4", "iPhone XS Max"),
        ("iPhone11,6", "iPhone XS Max"),
        ("iPhone11,8", "iPhone XR"),
        
        # iPhone X (iOS 11+)
        ("iPhone10,3", "iPhone X"),
        ("iPhone10,6", "iPhone X"),
        
        # iPhone 8系列 (iOS 11+)
        ("iPhone10,1", "iPhone 8"),
        ("iPhone10,4", "iPhone 8"),
        ("iPhone10,2", "iPhone 8 Plus"),
        ("iPhone10,5", "iPhone 8 Plus"),
        
        # iPhone 13系列 (iOS 15+)
        ("iPhone14,2", "iPhone 13 Pro"),
        ("iPhone14,3", "iPhone 13 Pro Max"),
        ("iPhone14,4", "iPhone 13 mini"),
        ("iPhone14,5", "iPhone 13"),
        
        # iPhone 14系列 (iOS 16+)
        ("iPhone14,7", "iPhone 14"),
        ("iPhone14,8", "iPhone 14 Plus"),
        ("iPhone15,2", "iPhone 14 Pro"),
        ("iPhone15,3", "iPhone 14 Pro Max"),
    ]
    
    # 淘宝App版本池（稳定版本，避免过新导致被识别）
    TAOBAO_APP_VERSIONS = [
        "10.51.0",
        "10.52.0",
        "10.53.0",
        "10.54.1",  # 成功案例中的版本
        "10.54.10",
    ]
    
    @classmethod
    def get_random_ios_device(cls):
        """
        生成随机的iOS设备配置
        
        返回:
            dict: 包含设备所有信息的字典
        """
        # 随机选择iOS版本
        ios_version = random.choice(cls.IOS_VERSIONS)
        
        # 根据iOS版本选择合适的iPhone机型
        # iOS 14 -> iPhone 8-12
        # iOS 15 -> iPhone 11-13
        # iOS 16 -> iPhone 12-14
        # iOS 17 -> iPhone 13-15
        ios_major = int(ios_version.split('.')[0])
        
        if ios_major == 14:
            # iPhone 8-12系列
            suitable_models = [m for m in cls.IPHONE_MODELS if 'iPhone10' in m[0] or 'iPhone11' in m[0] or 'iPhone12' in m[0] or 'iPhone13' in m[0]]
        elif ios_major == 15:
            # iPhone 11-13系列
            suitable_models = [m for m in cls.IPHONE_MODELS if 'iPhone12' in m[0] or 'iPhone13' in m[0] or 'iPhone14' in m[0]]
        elif ios_major == 16:
            # iPhone 12-14系列
            suitable_models = [m for m in cls.IPHONE_MODELS if 'iPhone13' in m[0] or 'iPhone14' in m[0] or 'iPhone15' in m[0]]
        elif ios_major >= 17:
            # iPhone 13+系列
            suitable_models = [m for m in cls.IPHONE_MODELS if 'iPhone14' in m[0] or 'iPhone15' in m[0]]
        else:
            # 默认使用所有机型
            suitable_models = cls.IPHONE_MODELS
        
        model_id, model_name = random.choice(suitable_models)
        
        # 随机选择淘宝App版本
        app_version = random.choice(cls.TAOBAO_APP_VERSIONS)
        
        # 生成随机GPS（广东省范围）
        gps_location = get_random_gps("guangdong")
        
        # 生成User-Agent
        # 格式: MTOPSDK/2.5.3.42 (iOS;14.0;Apple;iPhone10,3) DeviceType(Phone)
        user_agent = f"MTOPSDK%2F2.5.3.42%20%28iOS%3B{ios_version}%3BApple%3B{model_id}%29%20DeviceType%28Phone%29"
        
        # 生成x-ttid
        # 格式: 201200@taobao_iphone_10.54.1
        x_ttid = f"201200%40taobao_iphone_{app_version}"
        
        # Accept-Language (iOS风格)
        accept_language = random.choice([
            "zh-CN,zh-Hans;q=0.9",
            "zh-cn",
            "zh-Hans-CN;q=1.0"
        ])
        
        # a-orange-dq 参数
        # 成功案例: appKey=21380790&appVersion=10.54.1&clientAppIndexVersion=1120251027212100834
        # 失败案例: appKey=21380790&appVersion=10.54.10&clientAppIndexVersionDp=1120251027212100834&clientAppIndexVersionSwitch=2025102711021448024
        # 注意：不要添加 Dp 和 Switch 参数
        a_orange_dq = f"appKey%3D21380790%26appVersion%3D{app_version}%26clientAppIndexVersion%3D1120251027212100834"
        
        return {
            "ios_version": ios_version,
            "model_id": model_id,
            "model_name": model_name,
            "app_version": app_version,
            "user_agent": user_agent,
            "x_ttid": x_ttid,
            "x_app_ver": app_version,
            "x_app_edition": "ST",  # 标准版
            "accept_language": accept_language,
            "a_orange_dq": a_orange_dq,
            "gps_location": gps_location,
            "device_type": "Phone",
            "platform": "iOS"
        }
    
    @classmethod
    def print_device_info(cls, device_config):
        """打印设备配置信息（用于调试）"""
        print("=" * 60)
        print("📱 设备配置信息")
        print("=" * 60)
        print(f"设备型号: {device_config['model_name']} ({device_config['model_id']})")
        print(f"iOS版本: {device_config['ios_version']}")
        print(f"淘宝版本: {device_config['app_version']}")
        print(f"GPS位置: {device_config['gps_location']}")
        print("-" * 60)
        print("HTTP请求头参数:")
        print(f"  User-Agent: {device_config['user_agent']}")
        print(f"  x-app-ver: {device_config['x_app_ver']}")
        print(f"  x-ttid: {device_config['x_ttid']}")
        print(f"  Accept-Language: {device_config['accept_language']}")
        print(f"  a-orange-dq: {device_config['a_orange_dq']}")
        print(f"  x-location: {device_config['gps_location']}")
        print("=" * 60)


if __name__ == "__main__":
    # 测试生成10个随机设备
    print("\n🎲 生成10个随机iOS设备配置：\n")
    
    for i in range(10):
        device = DeviceConfig.get_random_ios_device()
        print(f"设备 {i+1}:")
        print(f"  {device['model_name']} (iOS {device['ios_version']}) - 淘宝 {device['app_version']} - GPS: {device['gps_location']}")
        print()
    
    # 详细展示一个设备配置
    print("\n" + "="*60)
    print("详细配置示例:")
    print("="*60)
    device = DeviceConfig.get_random_ios_device()
    DeviceConfig.print_device_info(device)
    
    # 对比成功和失败的案例
    print("\n\n" + "="*60)
    print("🔍 关键差异对比 (成功 vs 失败)")
    print("="*60)
    print("\n失败案例特征:")
    print("  ❌ iOS 26.0.1 (不存在的版本)")
    print("  ❌ iPhone17,1 (可能不真实)")
    print("  ❌ 淘宝 10.54.10")
    print("  ❌ a-orange-dq 包含 clientAppIndexVersionDp 和 clientAppIndexVersionSwitch")
    print("  ❌ 缺少 x5sec/x5secdata")
    
    print("\n成功案例特征:")
    print("  ✅ iOS 14.0 (真实版本)")
    print("  ✅ iPhone10,3 (真实机型)")
    print("  ✅ 淘宝 10.54.1")
    print("  ✅ a-orange-dq 只包含基础参数")
    print("  ✅ 包含 x5sec/x5secdata")
    
    print("\n本配置特点:")
    print("  ✅ 使用真实的iOS版本 (14.0-17.5)")
    print("  ✅ 使用真实的iPhone机型标识符")
    print("  ✅ iOS版本与机型匹配")
    print("  ✅ 使用稳定的淘宝App版本")
    print("  ✅ 简化的a-orange-dq参数")
    print("  ✅ 随机GPS坐标（广东省范围）")
    print("="*60)

