import json
import time
from pathlib import Path
from threading import Lock

from model.user import User
from model.device import Device

CACHE_FILE = 'task_timestamps.json'
USED_DEVICES_FILE = 'used_devices.json'  # 已使用的设备记录
_file_lock = Lock()
_used_devices_lock = Lock()


def load_cache():
    """读取缓存，文件不存在或损坏时自动创建"""
    with _file_lock:
        if not Path(CACHE_FILE).exists():
            with open(CACHE_FILE, 'w') as f:
                json.dump({}, f)
            return {}

        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            # JSON 文件损坏，删除并重建
            print(f"警告: 缓存文件损坏，已自动删除重建。错误: {e}")
            Path(CACHE_FILE).unlink()  # 删除文件
            with open(CACHE_FILE, 'w') as f:
                json.dump({}, f)
            return {}


def save_timestamp(_id):
    """标记账户完成时间"""
    with _file_lock:
        # 先读取最新数据
        try:
            if Path(CACHE_FILE).exists():
                with open(CACHE_FILE, 'r') as f:
                    cache = json.load(f)
            else:
                cache = {}
        except (json.JSONDecodeError, ValueError) as e:
            # JSON 文件损坏，重建
            print(f"警告: 保存时发现缓存文件损坏，已重建。错误: {e}")
            cache = {}

        # 更新时间戳
        current_time = time.time()
        cache[_id] = current_time

        # 原子写入：先写临时文件，再替换
        temp_file = CACHE_FILE + '.tmp'
        try:
            with open(temp_file, 'w') as f:
                json.dump(cache, f, indent=2)
            Path(temp_file).replace(CACHE_FILE)
        except Exception as e:
            # 清理临时文件
            if Path(temp_file).exists():
                Path(temp_file).unlink()
            raise e


def filter_available(users=[User], devices=[Device], isaccount=False, interval_hours=10):
    """过滤出可执行的账户"""
    cache = load_cache()
    current_time = time.time()
    threshold = interval_hours * 3600

    available = []
    if isaccount:
        for user in users:
            if user.uid not in cache or (current_time - cache[user.uid]) >= threshold:
                available.append(user)
    else:
        for device in devices:
            if device.devid not in cache or (current_time - cache[device.devid]) >= threshold:
                available.append(device)
    return available


# ==================== 设备使用记录功能 ====================

def load_used_devices():
    """读取已使用设备记录"""
    with _used_devices_lock:
        if not Path(USED_DEVICES_FILE).exists():
            return {}
        
        try:
            with open(USED_DEVICES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"警告: 设备使用记录文件损坏，已重建。错误: {e}")
            return {}


def mark_device_used(device_id: str):
    """
    标记设备已使用
    
    Args:
        device_id: 设备ID (通常是 devid 或 utdid)
    """
    with _used_devices_lock:
        try:
            if Path(USED_DEVICES_FILE).exists():
                with open(USED_DEVICES_FILE, 'r') as f:
                    used_devices = json.load(f)
            else:
                used_devices = {}
        except (json.JSONDecodeError, ValueError):
            used_devices = {}
        
        # 记录使用时间
        used_devices[device_id] = time.time()
        
        # 原子写入
        temp_file = USED_DEVICES_FILE + '.tmp'
        try:
            with open(temp_file, 'w') as f:
                json.dump(used_devices, f, indent=2)
            Path(temp_file).replace(USED_DEVICES_FILE)
        except Exception as e:
            if Path(temp_file).exists():
                Path(temp_file).unlink()
            raise e


def filter_unused_devices(devices: list, interval_minutes: int = 10):
    """
    过滤出未使用的设备（或超过指定时间的设备）
    
    Args:
        devices: 设备列表
        interval_minutes: 时间间隔（分钟），默认10分钟
        
    Returns:
        未使用的设备列表
    """
    used_devices = load_used_devices()
    current_time = time.time()
    threshold = interval_minutes * 60  # 转换为秒
    
    available = []
    filtered_count = 0
    
    for device in devices:
        device_id = device.devid
        
        # 如果设备没有使用记录，或者已经超过时间间隔，则可用
        if device_id not in used_devices or (current_time - used_devices[device_id]) >= threshold:
            available.append(device)
        else:
            filtered_count += 1
            # 计算剩余时间
            remaining = threshold - (current_time - used_devices[device_id])
            # print(f"设备 {device_id[:16]}... 在 {remaining/60:.1f} 分钟后可用")
    
    if filtered_count > 0:
        print(f"📋 设备过滤: {len(devices)} 个设备，过滤掉 {filtered_count} 个（{interval_minutes}分钟内已使用），剩余 {len(available)} 个可用")
    
    return available


def clean_expired_device_records(interval_minutes: int = 10):
    """
    清理过期的设备使用记录（节省空间）
    
    Args:
        interval_minutes: 时间间隔（分钟）
    """
    with _used_devices_lock:
        try:
            if not Path(USED_DEVICES_FILE).exists():
                return
            
            with open(USED_DEVICES_FILE, 'r') as f:
                used_devices = json.load(f)
            
            current_time = time.time()
            threshold = interval_minutes * 60
            
            # 删除过期记录
            cleaned = {
                device_id: timestamp 
                for device_id, timestamp in used_devices.items()
                if (current_time - timestamp) < threshold
            }
            
            # 如果有变化，保存
            if len(cleaned) != len(used_devices):
                temp_file = USED_DEVICES_FILE + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(cleaned, f, indent=2)
                Path(temp_file).replace(USED_DEVICES_FILE)
                print(f"🧹 清理设备记录: 删除 {len(used_devices) - len(cleaned)} 条过期记录")
        
        except Exception as e:
            print(f"清理设备记录时出错: {e}")