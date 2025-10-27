from __future__ import annotations

import re
from urllib.parse import unquote
import random
import string

def get_cookie_item_value(cookies: str, name: str) -> str | None:
    """
    从 Cookie 字符串中获取指定名称的值
    """
    # 正则匹配 Cookie 项
    match = re.search(rf"(?:\s|;|^){re.escape(name)}=([^;]+)(?=;|$)", cookies)
    if match:
        # URL 解码 + 转义字符处理
        return unquote(match.group(1))
    return None

def replace_cookie_item(cookies: str, name: str, value: str | None) -> str:
    """
    替换或添加 Cookie 项
    """
    if value is None or value.strip() == "":
        # 删除 Cookie 项
        items = cookies.split(";")
        new_items = []
        for item in items:
            if not item.strip():
                continue
            key_value = item.strip().split("=", 1)
            key = key_value[0]
            if key != name:
                new_items.append(item.strip())
        return ";".join(new_items)

    # 检查是否已存在该 Cookie
    current_value = get_cookie_item_value(cookies, name)
    if current_value is None:
        # 添加新 Cookie
        if cookies and cookies.strip().endswith(";"):
            return f"{cookies}{name}={value}"
        return f"{cookies};{name}={value}"

    # 替换现有 Cookie
    return cookies.replace(f"{name}={current_value}", f"{name}={value}")

def get_random_string(length: int = 11, is_number: bool = False) -> str:
    """
    生成指定长度的随机字符串
    """
    if is_number:
        characters = string.digits
    else:
        characters = string.digits + string.ascii_uppercase
    return "".join(random.choice(characters) for _ in range(length))

def get_random_gps(region: str = "china") -> str:
    """
    生成随机GPS坐标（经度,纬度）
    
    参数：
        region: 区域范围
            - "china": 中国主要城市区域（默认）
            - "guangdong": 广东省范围
            - "beijing": 北京市范围
            - "shanghai": 上海市范围
            - "custom": 自定义范围（需修改代码）
    
    返回：
        格式化的GPS坐标字符串，如 "108.436181,22.776163"
    """
    # 定义不同区域的经纬度范围
    regions = {
        # 中国主要城市区域（更真实的范围）
        "china": {
            "lon_min": 100.0,  # 最小经度
            "lon_max": 125.0,  # 最大经度
            "lat_min": 20.0,   # 最小纬度
            "lat_max": 45.0    # 最大纬度
        },
        # 广东省（更精确的范围）
        "guangdong": {
            "lon_min": 109.0,
            "lon_max": 117.5,
            "lat_min": 20.0,
            "lat_max": 25.5
        },
        # 北京市
        "beijing": {
            "lon_min": 115.4,
            "lon_max": 117.5,
            "lat_min": 39.4,
            "lat_max": 41.1
        },
        # 上海市
        "shanghai": {
            "lon_min": 120.8,
            "lon_max": 122.0,
            "lat_min": 30.7,
            "lat_max": 31.5
        }
    }
    
    # 获取区域配置
    config = regions.get(region, regions["china"])
    
    # 生成随机经度（保留6位小数，更真实）
    longitude = round(random.uniform(config["lon_min"], config["lon_max"]), 6)
    
    # 生成随机纬度（保留6位小数，更真实）
    latitude = round(random.uniform(config["lat_min"], config["lat_max"]), 6)
    
    # 返回格式化的GPS字符串
    return f"{longitude},{latitude}"

def get_random_android_device() -> str:
    """
    生成随机的Android设备User-Agent
    保持MTOPSDK版本不变，只随机化厂商和机型
    
    返回：
        URL编码的User-Agent字符串
        格式: MTOPSDK%2F3.1.1.7+%28Android%3B{version}%3B{brand}%3B{model}%29+DeviceType%28Phone%29
    """
    # Android版本池（真实的Android版本）
    android_versions = [
        "9",    # Android 9 (Pie)
        "10",   # Android 10
        "11",   # Android 11
        "12",   # Android 12
        "13",   # Android 13
    ]
    
    # 设备池（品牌:机型）- 使用常见的真实设备
    devices = [
        # 小米系列
        ("Xiaomi", "MI 8"),
        ("Xiaomi", "MI 9"),
        ("Xiaomi", "MI 10"),
        ("Xiaomi", "MI 11"),
        ("Xiaomi", "MIX 2S"),
        ("Xiaomi", "MIX 3"),
        ("Xiaomi", "Redmi K30"),
        ("Xiaomi", "Redmi K40"),
        ("Xiaomi", "Redmi Note 9"),
        ("Xiaomi", "Redmi Note 10"),
        
        # 华为系列
        ("HUAWEI", "Mate 20"),
        ("HUAWEI", "Mate 30"),
        ("HUAWEI", "Mate 40"),
        ("HUAWEI", "P30"),
        ("HUAWEI", "P40"),
        ("HUAWEI", "nova 7"),
        
        # OPPO系列
        ("OPPO", "Find X2"),
        ("OPPO", "Find X3"),
        ("OPPO", "Reno5"),
        ("OPPO", "Reno6"),
        ("OPPO", "A93"),
        
        # vivo系列
        ("vivo", "X60"),
        ("vivo", "X70"),
        ("vivo", "iQOO 7"),
        ("vivo", "iQOO 8"),
        ("vivo", "S10"),
        
        # 三星系列
        ("samsung", "SM-G9730"),  # S10
        ("samsung", "SM-G9810"),  # S20
        ("samsung", "SM-G9980"),  # S21
        
        # 一加系列
        ("OnePlus", "7 Pro"),
        ("OnePlus", "8 Pro"),
        ("OnePlus", "9 Pro"),
        
        # 其他品牌
        ("realme", "GT"),
        ("Meizu", "18"),
    ]
    
    # 随机选择Android版本和设备
    android_version = random.choice(android_versions)
    brand, model = random.choice(devices)
    
    # 构建User-Agent（保持MTOPSDK版本3.1.1.7不变）
    # 原格式: MTOPSDK/3.1.1.7 (Android;10;Xiaomi;MIX 2S) DeviceType(Phone)
    user_agent = f"MTOPSDK/3.1.1.7 (Android;{android_version};{brand};{model}) DeviceType(Phone)"
    
    # URL编码（空格变成+，其他特殊字符编码）
    # 手动编码以匹配淘宝的格式
    user_agent_encoded = user_agent.replace("/", "%2F").replace(" ", "+").replace("(", "%28").replace(")", "%29").replace(";", "%3B")
    
    return user_agent_encoded