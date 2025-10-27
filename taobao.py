import httpx
from loguru import logger

import tools
import os

from database import save_timestamp
from model.user import User
from model.device import Device
import json
import time
import urllib.parse
import hashlib
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# 全局签名缓存池
sign_cache = {}
sign_cache_lock = threading.Lock()


# 全局 requests 会话 (复用连接)
# _session = requests.Session()
# _session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=500, max_retries=1))
# _session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=500, max_retries=1))


def test_proxy(proxy_str):
    """测试代理是否可用，返回出口IP"""
    try:
        # 解析代理
        if not proxy_str or proxy_str == "":
            return False, "未配置代理"
        
        proxy_url = proxy_str
        if proxy_str.startswith('http://') or proxy_str.startswith('socks5://'):
            proxy_url = proxy_str
        elif proxy_str.count(':') == 3:
            parts = proxy_str.split(':')
            ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
            proxy_url = f'http://{username}:{password}@{ip}:{port}'
        elif proxy_str.count(':') == 1:
            proxy_url = f'socks5://{proxy_str}'
        else:
            proxy_url = f'socks5://{proxy_str}'
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # 测试代理连通性 - 访问一个IP查询服务
        print(f"🧪 正在测试代理: {proxy_url}")
        resp = requests.get('https://api.ipify.org?format=json', 
                           proxies=proxies, 
                           timeout=10)
        
        if resp.status_code == 200:
            ip_info = resp.json()
            exit_ip = ip_info.get('ip', '未知')
            return True, f"✅ 代理可用，出口IP: {exit_ip}"
        else:
            return False, f"❌ 代理响应异常: {resp.status_code}"
            
    except Exception as e:
        return False, f"❌ 代理连接失败: {str(e)[:100]}"


def subscribe_live_msg(
        device: Device,
        user: User,
        account_id: str,
        live_id: str,
        topic: str,
        proxy: str
):
    """订阅直播消息 - 同步版本"""
    # 统一获取时间戳，确保data和请求头的时间戳一致
    now_seconds = int(time.time())  # 秒级时间戳
    now = now_seconds * 1000  # 毫秒时间戳
    
    # 添加小的随机偏移（-200ms到+200ms），避免批量请求时间戳完全相同
    # 注意：偏移范围不能太大，否则会触发 "invalid timestamp" 错误
    import random
    random_offset = random.randint(-200, 200)
    now = now + random_offset

    pm_session = f"{now}{tools.get_random_string()}"
    live_token = f"{now}_{live_id}_{tools.get_random_string(4, True)}"

    # 计算 watchId
    watch_id_str = f"{now}{user.uid}{live_id}"
    watch_id = hashlib.md5(watch_id_str.encode("utf-8")).hexdigest().upper()

    # 构造 ext 参数
    ext = {
        "ignorePv": "0",
        "liveClientParams": {
            "livesource": "PlayBackToLive",
            "entryLiveSource": "PlayBackToLive",
            "liveToken": live_token,
            "spm-cnt": "a2141.8001249",
            "isAD": "0",
            "watchId": watch_id,
            "kandianid": "null_null",
            "pmClientType": "kmpLiveRoom",
            "pmSession": pm_session
        },
        "liveServerParams": {
            "accountId": account_id,
            "liveId": live_id,
            "status": "1"
        },
        "needEventWhenIgnorePv": "true"
    }

    # 调用 API，传递时间戳确保一致性
    result = call_app_api(
        device,
        user,
        {
            "appKey": "21646297",
            "ext": json.dumps(ext, ensure_ascii=False),
            "from": user.nickname,
            "id": user.uid,
            "internalExt": "",
            "namespace": 1,
            "role": 3,
            "sdkVersion": "0.3.0",
            "tag": "",
            "topic": topic,
            "utdId": device.utdid
        },
        "mtop.taobao.powermsg.msg.subscribe",
        "1.0",
        proxy,
        now_seconds  # 传递秒级时间戳
    )
    logger.debug(f"订阅直播消息结果: {result}")
    return result


def get_sign(device: Device, user: User, api, v, data, t):
    """获取签名 - 同步版本，带缓存"""
    # 生成缓存key
    cache_key = f"{api}_{data}_{t}_{device.utdid}_{user.uid}"

    # 检查缓存
    with sign_cache_lock:
        if cache_key in sign_cache:
            return True, sign_cache[cache_key]

    start_time = time.time()
    json_data = {
        "utdid": device.utdid,
        "umt": device.umt,
        "devid": device.devid,
        "miniwua": device.miniwua,
        "sgext": device.sgext,
        "ttid": device.ttid,
        "sid": user.sid,
        "uid": user.uid,
        "api": api,
        "v": v,
        "data": data,
        "t": t
    }

    # 不重试，直接请求
    try:
        resp = requests.post("http://localhost:9001/api/taobao/sign",
                             headers={"content-type": "application/json"},
                             json=json_data,
                             timeout=3)
        if resp.status_code != 200:
            # 返回简洁的错误消息，不返回完整的JSON
            return False, f"算法服务错误(HTTP {resp.status_code})"

        result = resp.json()

        # 缓存结果
        with sign_cache_lock:
            sign_cache[cache_key] = result
            # 限制缓存大小
            if len(sign_cache) > 1000:
                sign_cache.clear()

        return True, result
        
    except requests.exceptions.Timeout:
        return False, "算法服务超时"
    except Exception as e:
        return False, f"算法服务异常: {str(e)[:30]}"


def call_app_api(
        device: Device,
        user: User,
        json_data: any,
        api: str,
        v: str,
        proxy: str,
        timestamp_seconds: int = None  # 可选的时间戳参数
):
    # 序列化数据
    if isinstance(json_data, str):
        data = json_data
    else:
        data = json.dumps(json_data, ensure_ascii=False)

    try:
        # 时间戳（秒）
        seconds = str(int(time.time()))

        # 签名
        success, sign_data = get_sign(device, user, api, v, data, seconds)
        if not success:
            # 简化错误消息，不返回算法服务的详细错误
            print(f"❌ 签名失败 [{device.utdid[:16]}...]: {sign_data[:100]}")
            return False, "签名生成失败"

        # 请求头
        headers = {
            "Accept-Encoding": "gzip",
            "user-agent": "MTOPSDK%2F3.1.1.7+%28Android%3B10%3BXiaomi%3BMIX+2S%29+DeviceType%28Phone%29",
            "x-app-ver": "10.51.0",
            "x-appkey": "21646297",
            "x-devid": urllib.parse.quote(device.devid),
            "x-extdata": "openappkey%3DDEFAULT_AUTH",
            "x-features": "27",
            "x-mini-wua": urllib.parse.quote(sign_data["miniwua"]),
            "x-pv": "6.3",
            "x-sgext": urllib.parse.quote(sign_data["sgext"]),
            "x-sid": user.sid,
            "x-sign": urllib.parse.quote(sign_data["sign"]),
            "x-t": seconds,
            "x-ttid": urllib.parse.quote(device.ttid),
            "x-uid": user.uid,
            "x-umt": urllib.parse.quote(device.umt),
            "x-utdid": urllib.parse.quote(device.utdid),
            "cookie": user.cookies
        }

        # 配置代理
        proxies = None
        if proxy and proxy != "":
            # 解析代理格式
            # 支持格式1: IP:PORT:USERNAME:PASSWORD (如 118.145.143.4:16816:eyiuximz:wlr3w19f)
            # 支持格式2: IP:PORT (原格式)
            # 支持格式3: socks5://... (完整URL格式)
            # 支持格式4: http://IP:PORT:USERNAME:PASSWORD (HTTP代理格式)
            proxy_url = proxy
            
            if proxy.startswith('socks5://') or proxy.startswith('http://') or proxy.startswith('https://'):
                # 格式3: 已经是完整URL，直接使用
                proxy_url = proxy
                print(f"🔌 使用代理(完整URL格式): {proxy_url}")
            elif proxy.count(':') == 3:
                # 格式1: IP:PORT:USERNAME:PASSWORD
                parts = proxy.split(':')
                ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                # 尝试HTTP代理（更通用）
                proxy_url = f'http://{username}:{password}@{ip}:{port}'
                print(f"🔌 使用HTTP代理: {ip}:{port} (用户名:{username})")
            elif proxy.count(':') == 1:
                # 格式2: IP:PORT (原格式，默认使用socks5)
                proxy_url = f'socks5://{proxy}'
                print(f"🔌 使用SOCKS5代理: {proxy}")
            else:
                # 其他格式，尝试作为 socks5 代理
                proxy_url = f'socks5://{proxy}'
                print(f"🔌 使用代理(其他格式): {proxy_url}")
            
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        else:
            print("⚠️ 未配置代理，使用直连")

        try:
            # 显示请求信息
            if proxies:
                print(f"📤 [{device.utdid[:16]}...] 通过代理发送请求到淘宝API")
            else:
                print(f"📤 [{device.utdid[:16]}...] 直连发送请求到淘宝API")
            
            resp = requests.post(
                f"https://guide-acs.m.taobao.com/gw/{api}/{v}/",
                headers=headers,
                data={'data': data},
                proxies=proxies,
                timeout=(10, 15)  # 增加超时：连接10秒，读取15秒（代理可能较慢）
            )
            
            # 显示响应信息
            if proxies:
                print(f"📥 [{device.utdid[:16]}...] 收到响应 (状态码: {resp.status_code}, 通过代理)")
            else:
                print(f"📥 [{device.utdid[:16]}...] 收到响应 (状态码: {resp.status_code}, 直连)")
            
            resp.raise_for_status()  # 抛出 HTTP 错误
            response_str = resp.text

        except requests.exceptions.Timeout as e:
            print(f"❌ 请求超时 [{device.utdid[:16]}...]: {str(e)[:100]}")
            return False, "请求超时（代理或网络较慢）"
        except requests.exceptions.ProxyError as e:
            print(f"❌ 代理错误 [{device.utdid[:16]}...]: {str(e)[:100]}")
            return False, "代理连接失败"
        except requests.exceptions.ConnectionError as e:
            print(f"❌ 连接错误 [{device.utdid[:16]}...]: {str(e)[:100]}")
            return False, "网络连接失败"
        except Exception as e:
            print(f"❌ 网络异常 [{device.utdid[:16]}...]: {str(e)[:100]}")
            return False, f"网络异常: {str(e)[:50]}"

        if not response_str:
            return False, "请求失败"

        # 解析 JSON
        json_obj = json.loads(response_str)
        ret = json_obj.get("ret", [])
        data = json_obj.get("data", {})

        # 检查是否被识别为机器人
        if "robot::not a normal request" in response_str:
            print("❌ robot 封禁", "拉黑设备", device.utdid)
            th = threading.Thread(target=save_timestamp, args=(device.devid,))
            th.start()
            return False, "robot::not a normal request"
        
        # 检查返回状态
        if not ret or "SUCCESS" not in ret[0]:
            print("❌ 请求失败", device.utdid, response_str[:200])
            return False, "失败: " + str(ret[0] if ret else "无返回")
        
        # 额外检查：验证 role 字段
        # role=5 表示成功订阅，role=1 可能表示失败或被识别为异常
        if isinstance(data, dict):
            role = data.get("role")
            if role == 5 or role == "5":
                print("✅ 刷量成功", device.utdid, f"role={role}")
                return True, data
            elif role == 1 or role == "1":
                print("⚠️ 返回成功但role=1（可能被识别）", device.utdid, response_str[:200])
                return False, f"role=1 (异常): {response_str[:100]}"
            else:
                # role 是其他值，记录但仍视为成功（因为ret是SUCCESS）
                print(f"⚠️ 返回成功但role={role}（未知状态）", device.utdid)
                return True, data
        
        # 如果 data 不是字典，直接返回
        return True, data

    except Exception as e:
        print("API调用异常", device.utdid, str(e))
        return False, "出错" + str(e)

