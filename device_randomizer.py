"""
User-Agent 随机化工具
用于降低批量请求的关联性（只随机化UA，避免影响签名验证）
"""
import random


class DeviceRandomizer:
    """User-Agent 随机化器"""
    
    # 常见手机型号池（小米、华为、OPPO、vivo等）
    PHONE_MODELS = [
        ("Xiaomi", "MIX 2S", "10"),
        ("Xiaomi", "MI 8", "10"),
        ("Xiaomi", "MI 9", "10"),
        ("Xiaomi", "MI 10", "11"),
        ("Xiaomi", "MI 10 Pro", "11"),
        ("Xiaomi", "Redmi K30", "10"),
        ("Xiaomi", "Redmi K40", "11"),
        ("Xiaomi", "Redmi Note 9", "10"),
        ("HUAWEI", "Mate 30", "10"),
        ("HUAWEI", "Mate 40", "10"),
        ("HUAWEI", "P30", "10"),
        ("HUAWEI", "P40", "10"),
        ("HUAWEI", "nova 7", "10"),
        ("OPPO", "Find X2", "10"),
        ("OPPO", "Find X3", "11"),
        ("OPPO", "Reno5", "11"),
        ("OPPO", "Reno6", "11"),
        ("OPPO", "A93", "10"),
        ("vivo", "X60", "11"),
        ("vivo", "X70", "11"),
        ("vivo", "S10", "11"),
        ("vivo", "iQOO 7", "11"),
        ("vivo", "Y73s", "10"),
        ("OnePlus", "8", "10"),
        ("OnePlus", "8T", "11"),
        ("OnePlus", "9", "11"),
        ("OnePlus", "9 Pro", "11"),
        ("Samsung", "Galaxy S10", "10"),
        ("Samsung", "Galaxy S20", "11"),
        ("Samsung", "Galaxy A52", "11"),
        ("Realme", "GT", "11"),
        ("Realme", "Q3", "11"),
    ]
    
    def __init__(self):
        """初始化随机化器"""
        self._cache = {}  # 用于缓存每个uid的固定UA
    
    def get_user_agent(self, uid: str, use_cache: bool = True) -> str:
        """
        为用户生成或获取 User-Agent
        
        Args:
            uid: 用户ID
            use_cache: 是否使用缓存（True=每个用户固定UA，False=每次随机）
            
        Returns:
            URL编码的 User-Agent 字符串
        """
        # 如果启用缓存且已有配置，直接返回
        if use_cache and uid in self._cache:
            return self._cache[uid]
        
        # 随机选择设备
        brand, model, android_ver = random.choice(self.PHONE_MODELS)
        
        # 构造User-Agent (URL编码格式)
        # 格式: MTOPSDK/3.1.1.7+(Android;版本;品牌;型号)+DeviceType(Phone)
        user_agent = f"MTOPSDK%2F3.1.1.7+%28Android%3B{android_ver}%3B{brand}%3B{model.replace(' ', '+')}%29+DeviceType%28Phone%29"
        
        # 如果启用缓存，保存配置
        if use_cache:
            self._cache[uid] = user_agent
        
        return user_agent
    
    def get_device_info(self, uid: str) -> str:
        """
        获取设备信息字符串（用于日志显示）
        
        Args:
            uid: 用户ID
            
        Returns:
            设备信息字符串，如 "Xiaomi MI 10 (Android 11)"
        """
        ua = self.get_user_agent(uid, use_cache=True)
        # 从UA中提取设备信息（简单解析）
        try:
            # MTOPSDK%2F3.1.1.7+%28Android%3B11%3BXiaomi%3BMI+10%29
            import urllib.parse
            decoded = urllib.parse.unquote(ua)
            # MTOPSDK/3.1.1.7+(Android;11;Xiaomi;MI 10)+DeviceType(Phone)
            parts = decoded.split(';')
            if len(parts) >= 4:
                android_ver = parts[1]
                brand = parts[2]
                model = parts[3].split(')')[0]
                return f"{brand} {model} (Android {android_ver})"
        except:
            pass
        return "Unknown Device"
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局单例
_randomizer = DeviceRandomizer()


def get_random_user_agent(uid: str, use_cache: bool = True) -> str:
    """
    获取用户的随机 User-Agent（便捷函数）
    
    Args:
        uid: 用户ID
        use_cache: 是否为每个用户固定UA（推荐True）
        
    Returns:
        URL编码的 User-Agent 字符串
    """
    return _randomizer.get_user_agent(uid, use_cache)


if __name__ == "__main__":
    # 测试代码
    print("=== User-Agent 随机化测试 ===\n")
    
    # 测试1: 同一用户多次获取（应该返回相同UA）
    print("测试1: 同一用户（启用缓存）")
    uid1 = "test_user_001"
    ua1_1 = get_random_user_agent(uid1, use_cache=True)
    ua1_2 = get_random_user_agent(uid1, use_cache=True)
    device_info = _randomizer.get_device_info(uid1)
    print(f"  第1次: {device_info}")
    print(f"  第2次: {device_info}")
    print(f"  是否相同: {ua1_1 == ua1_2}")
    print(f"  UA: {ua1_1}")
    
    # 测试2: 不同用户（应该返回不同UA）
    print("\n测试2: 不同用户的User-Agent")
    for i in range(10):
        uid = f"test_user_{i:03d}"
        ua = get_random_user_agent(uid, use_cache=True)
        device_info = _randomizer.get_device_info(uid)
        print(f"  用户{i+1}: {device_info}")
        print(f"         UA: {ua[:70]}...")
    
    # 测试3: 不使用缓存（每次都不同）
    print("\n测试3: 不使用缓存（同一用户每次不同）")
    uid_test = "test_random"
    for i in range(3):
        ua = get_random_user_agent(uid_test, use_cache=False)
        print(f"  第{i+1}次: {ua[:60]}...")

