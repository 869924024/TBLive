import httpx
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


def subscribe_live_msg(
        device: Device,
        user: User,
        account_id: str,
        live_id: str,
        topic: str,
        proxy: str
):
    """订阅直播消息 - 同步版本"""
    now = int(time.time() * 1000)  # 毫秒时间戳

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

    # 调用 API
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
        proxy
    )
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

    try:

        resp = requests.post("http://localhost:8999/api/taobao/sign",
                             headers={"content-type": "application/json"},
                             json=json_data,
                             timeout=3)
        if resp.status_code != 200:
            print("算法调用失败", device.utdid, resp.text, resp.status_code, time.time() - start_time)
            return False, resp.text

        result = resp.json()

        # 缓存结果
        with sign_cache_lock:
            sign_cache[cache_key] = result
            # 限制缓存大小
            if len(sign_cache) > 1000:
                sign_cache.clear()

        return True, result
    except Exception as e:
        print("签名请求异常", device.utdid, str(e))
        return False, str(e)


def call_app_api(
        device: Device,
        user: User,
        json_data: any,
        api: str,
        v: str,
        proxy: str
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
            return False, sign_data

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
            proxies = {
                'http': f'socks5://{proxy}',
                'https': f'socks5://{proxy}'
            }

        try:
            print("使用代理", proxies)
            resp = requests.post(
                f"https://guide-acs.m.taobao.com/gw/{api}/{v}/",
                headers=headers,
                data={'data': data},
                proxies=proxies,
                timeout=(3, 10)  # 连接超时3秒，读取超时10秒
            )
            # resp = requests.get(
            #     f"https://www.ipplus360.com/getIP",
            #     proxies=proxies,
            #     timeout=(3, 10)  # 连接超时3秒，读取超时10秒
            # )
            # print(resp.text)
            resp.raise_for_status()  # 抛出 HTTP 错误
            response_str = resp.text

        except Exception as e:
            print("请求淘宝网络异常", device.utdid, str(e))
            return False, "网络异常"

        if not response_str:
            return False, "请求失败"

        # 解析 JSON
        json_obj = json.loads(response_str)
        ret = json_obj["ret"]
        data = json_obj["data"]

        if "robot::not a normal request" in response_str:
            print("robot 封禁", "拉黑设备", device.utdid)
            th = threading.Thread(target=save_timestamp, args=(device.devid,))
            th.start()
        # 检查是否成功
        if not ret or "SUCCESS" not in ret[0]:
            print("请求失败", device.utdid, response_str[:200])
            return False, "失败" + str(ret[0])

        return True, data

    except Exception as e:
        print("API调用异常", device.utdid, str(e))
        return False, "出错" + str(e)

