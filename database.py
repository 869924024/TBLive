import json
import time
from pathlib import Path
from threading import Lock

from model.user import User
from model.device import Device

CACHE_FILE = 'task_timestamps.json'
USED_DEVICES_FILE = 'used_devices.json'  # 已使用的设备记录
BANNED_COOKIES_FILE = 'banned_cookies.json'  # 被封禁的 Cookie 记录（robot 检测）
_file_lock = Lock()
_used_devices_lock = Lock()
_banned_cookies_lock = Lock()  # 被封禁 Cookie 记录的锁


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
    """过滤出可执行的账户（排除被封禁的 Cookie）"""
    cache = load_cache()
    current_time = time.time()
    threshold = interval_hours * 3600
    
    # 加载被封禁的 Cookie 列表
    banned_cookies = load_banned_cookies()

    available = []
    if isaccount:
        for user in users:
            # 检查是否被封禁
            if user.uid in banned_cookies:
                continue  # 跳过被封禁的 Cookie
            # 检查是否在冷却期
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


def filter_unused_devices(devices: list, interval_minutes: int = 720):
    """
    过滤出未使用的设备（或超过指定时间的设备）
    
    Args:
        devices: 设备列表
        interval_minutes: 时间间隔（分钟），默认720分钟（12小时）
        
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
        # 根据时间长短选择合适的单位
        if interval_minutes >= 60:
            time_str = f"{interval_minutes // 60}小时"
        else:
            time_str = f"{interval_minutes}分钟"
        print(f"📋 设备过滤: {len(devices)} 个设备，过滤掉 {filtered_count} 个（{time_str}内已使用），剩余 {len(available)} 个可用")
    
    return available


def clean_expired_device_records(interval_minutes: int = 720):
    """
    清理过期的设备使用记录（节省空间）
    
    Args:
        interval_minutes: 时间间隔（分钟），默认720分钟（12小时）
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


# ==================== Cookie 封禁记录功能 ====================

def load_banned_cookies():
    """读取被封禁的 Cookie UID 列表"""
    with _banned_cookies_lock:
        if not Path(BANNED_COOKIES_FILE).exists():
            return set()
        
        try:
            with open(BANNED_COOKIES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 如果是列表，转换为集合；如果是字典，提取键
                if isinstance(data, list):
                    return set(data)
                elif isinstance(data, dict):
                    # 如果存储格式是 {uid: timestamp}，提取所有键
                    return set(data.keys())
                else:
                    return set()
        except (json.JSONDecodeError, ValueError) as e:
            print(f"警告: 被封禁Cookie记录文件损坏，已重建。错误: {e}")
            return set()


def mark_cookie_banned(cookie_uid: str):
    """
    标记 Cookie 为被封禁（robot 检测）
    
    Args:
        cookie_uid: Cookie 的 UID (unb)
    """
    if not cookie_uid:
        return False
    
    with _banned_cookies_lock:
        try:
            if Path(BANNED_COOKIES_FILE).exists():
                with open(BANNED_COOKIES_FILE, 'r', encoding='utf-8') as f:
                    banned_cookies = json.load(f)
            else:
                banned_cookies = {}
            
            # 如果之前是列表格式，转换为字典
            if isinstance(banned_cookies, list):
                banned_cookies = {uid: time.time() for uid in banned_cookies}
            
            # 记录封禁时间
            banned_cookies[cookie_uid] = time.time()
            
            # 原子写入
            temp_file = BANNED_COOKIES_FILE + '.tmp'
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(banned_cookies, f, indent=2, ensure_ascii=False)
                Path(temp_file).replace(BANNED_COOKIES_FILE)
                return True
            except Exception as e:
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
                raise e
        except Exception as e:
            print(f"标记 Cookie 被封禁时出错: {e}")
            return False


def mark_cookies_banned(cookie_uids: list):
    """
    批量标记多个 Cookie 为被封禁
    
    Args:
        cookie_uids: Cookie UID 列表
    """
    if not cookie_uids:
        return 0
    
    count = 0
    for uid in cookie_uids:
        if mark_cookie_banned(uid):
            count += 1
    return count


def is_cookie_banned(cookie_uid: str) -> bool:
    """
    检查 Cookie 是否被封禁
    
    Args:
        cookie_uid: Cookie 的 UID
    
    Returns:
        bool: True 表示被封禁
    """
    if not cookie_uid:
        return False
    banned_cookies = load_banned_cookies()
    return cookie_uid in banned_cookies