import json
import time
from pathlib import Path
from threading import Lock

from model.user import User
from model.device import Device

CACHE_FILE = 'task_timestamps.json'
_file_lock = Lock()


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