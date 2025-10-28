from loguru import logger

import tools
import time
from database import filter_available
from model.user import User
from model.device import Device
from task_batch import AsyncTaskThread
from taobao import get_sign, subscribe_live_msg_prepared, subscribe_live_msg_prepared_async
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import asyncio
import requests
import string
import random


def generate_random_string(length=5):
    # 定义可选字符：大小写字母 + 数字
    chars = string.ascii_letters + string.digits
    # 随机选择 length 个字符组成字符串
    return ''.join(random.choices(chars, k=length))


def get_proxy(url: str, num: int) -> list[str]:
    proxies = []
    for i in range(10):
        txt = requests.get(url).text
        p = [(p.replace("\r", "")).strip() for p in txt.split("\n") if p.strip()]
        print("拉取代理",p)
        proxies.extend(p)

        if len(proxies) >= num:
            break
    return proxies


class Watch:
    def __init__(self, cookies=[], devices=[], thread_nums=5, Multiple_num=1, log_fn=None, proxy_type="",
                 proxy_value="", live_id="", burst_mode: str = "preheat"):
        self.users = [User(tools.replace_cookie_item(i, "sgcookie", None)) for i in cookies]
        self.users = filter_available(users=self.users, isaccount=True, interval_hours=10)

        self.devices = []
        for device in devices:
            items = [item.strip() for item in device.split("\t") if item.strip()]
            if len(items) >= 5:
                self.devices.append(Device(items[0], items[1], items[2], items[3], items[4]))

        self.devices = filter_available(devices=self.devices, isaccount=False, interval_hours=10)

        self.thread_nums = thread_nums  # 现在是并发数
        self.Multiple_num = Multiple_num
        self.success_num = 0
        self.fail_num = 0

        self.task_thread = None  # Qt后台线程
        self.log_fun = log_fn

        self.proxy_type = proxy_type
        self.proxy_value = proxy_value
        self.live_id = live_id
        # 突发模式：preheat=预热签名后一次性发送；instant=即时签名+一次性发送
        self.burst_mode = burst_mode if burst_mode in ("preheat", "instant") else "preheat"

        # 添加网络请求异常处理
        try:
            response = requests.get(
                f"https://alive-interact.alicdn.com/livedetail/common/{live_id}",
                timeout=10  # 添加10秒超时
            )
            response.raise_for_status()  # 检查HTTP状态码
            self.info = response.json()

            if self.info == {}:
                raise ValueError("获取直播间数据失败")

        except requests.exceptions.Timeout:
            raise Exception("网络请求超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except ValueError as e:
            if "JSON" in str(e):
                raise Exception("数据解析失败，返回的不是有效的JSON格式")
            else:
                raise

    def get_proxys(self, num):
        if self.proxy_type == "direct":
            return [self.proxy_value.replace('{{random}}', generate_random_string()) for i in range(num)]
        else:
            return get_proxy(self.proxy_value, num)

    def start_task(self, ui_widget):
        """在后台线程启动任务，避免阻塞UI主线程"""
        if self.task_thread and self.task_thread.isRunning():
            self.log_fun("⚠️ 任务正在运行中，请勿重复启动")
            return
        threading.Thread(target=self._run_task, args=(ui_widget,), daemon=True).start()
        return

    def _run_task(self, ui_widget):
        def _finish_task(success=0, failed=0):
            """统一的任务完成处理，恢复UI状态"""
            try:
                ui_widget.start_btn.setEnabled(True)
                ui_widget.stop_btn.setEnabled(False)
                ui_widget.success_count.setText(str(success))
                ui_widget.fail_count.setText(str(failed))
                print(f"[DEBUG] UI状态已恢复: 成功={success}, 失败={failed}")
            except Exception as e:
                print(f"[DEBUG] 恢复UI状态失败: {e}")
        
        try:
            print(f"[DEBUG] _run_task 开始执行")
            print(f"[DEBUG] self.log_fun = {self.log_fun}")
            print(f"[DEBUG] users={len(self.users)}, devices={len(self.devices)}, Multiple_num={self.Multiple_num}")
            
            # 调试信息：显示可用的用户和设备数量
            msg1 = f"🔍 可用账号数: {len(self.users)} (过滤后)"
            msg2 = f"🔍 可用设备数: {len(self.devices)} (过滤后)"
            msg3 = f"🔍 操作倍数: {self.Multiple_num}"
            print(msg1)
            print(msg2)
            print(msg3)
            self.log_fun(msg1)
            self.log_fun(msg2)
            self.log_fun(msg3)
            
            # 检查设备数量
            if len(self.devices) == 0:
                err_msg = "❌ 没有可用的设备参数，请检查设备列表或等待6分钟后重试"
                print(err_msg)
                self.log_fun(err_msg)
                _finish_task(0, 0)
                return
            
            print(f"[DEBUG] 检查直播间信息")
            # 检查直播间信息
            if not self.info:
                err_msg2 = "❌ 直播间信息获取失败，无法创建任务"
                print(err_msg2)
                self.log_fun(err_msg2)
                _finish_task(0, 0)
                return
            
            account_id = self.info.get("accountId", "")
            live_id = self.info.get("liveId", "")
            topic = self.info.get("topic", "")
            
            print(f"[DEBUG] account_id={account_id}, live_id={live_id}, topic={topic[:20] if topic else 'None'}...")
            
            msg_info = f"🔍 直播间信息: accountId={account_id}, liveId={live_id}, topic={topic[:20]}..." if topic else ""
            print(msg_info)
            self.log_fun(msg_info)
            
            if not account_id or not live_id or not topic:
                err_msg = f"❌ 直播间信息不完整，请检查直播间ID是否正确"
                print(err_msg)
                self.log_fun(err_msg)
                print(f"   - accountId: {'✅' if account_id else '❌ 缺失'}")
                print(f"   - liveId: {'✅' if live_id else '❌ 缺失'}")
                print(f"   - topic: {'✅' if topic else '❌ 缺失'}")
                _finish_task(0, 0)
                return
            
            print(f"[DEBUG] 直播间信息检查通过")
        except Exception as e:
            print(f"[DEBUG] 初始化异常: {e}")
            err_msg3 = f"❌ 初始化错误: {str(e)}"
            print(err_msg3)
            self.log_fun(err_msg3)
            import traceback
            traceback.print_exc()
            _finish_task(0, 0)
            return

        print(f"[DEBUG] 准备进入模式选择，burst_mode={self.burst_mode}")
        
        # 预热签名：为每个设备参数尝试一次签名，失败则丢弃
        # 目的：确保算法签名服务与设备参数可用，避免突发时失败率过高
        def _build_sign_data(u: User, d: Device):
            # 与订阅接口一致的 data 结构（最小必要字段）
            import hashlib, json as _json, time as _time
            now_ms = int(_time.time() * 1000)
            # 构造 ext
            ext = {
                "ignorePv": "0",
                "liveClientParams": {
                    "pmClientType": "kmpLiveRoom",
                    "pmSession": f"{now_ms}PREHEAT",
                    "liveToken": f"{now_ms}_{live_id}_PH",
                    "livesource": "PlayBackToLive",
                    "entryLiveSource": "PlayBackToLive",
                    "isAD": "0",
                    "pvid": hashlib.md5(f"{now_ms}{u.uid}{live_id}".encode("utf-8")).hexdigest()
                },
                "liveServerParams": {
                    "accountId": account_id,
                    "liveId": live_id,
                    "status": "1"
                },
                "needEventWhenIgnorePv": "true"
            }
            json_data = {
                "appKey": "21646297",
                "ext": _json.dumps(ext, ensure_ascii=False),
                "from": u.nickname,
                "id": u.uid,
                "internalExt": "",
                "namespace": 1,
                "role": 3,
                "sdkVersion": "0.3.0",
                "tag": "",
                "topic": topic,
                "utdId": d.utdid
            }
            return _json.dumps(json_data, ensure_ascii=False)

        # 选择模式
        mode_msg = f"🧭 突发模式: {self.burst_mode}"
        print(mode_msg)
        self.log_fun(mode_msg)
        logger.info(f"开始执行突发任务，模式: {self.burst_mode}, 用户数: {len(self.users)}, 设备数: {len(self.devices)}, 倍数: {self.Multiple_num}")

        if self.burst_mode == "instant":
            # 直接即时签名 + 异步突发
            self.log_fun("🚀 突发发送开始（instant：签名+发送全部瞬发）...")
            total_tasks = len(self.users) * len(self.devices) * max(1, self.Multiple_num)
            self.log_fun(f"📊 预计任务总数: {total_tasks}")

            async def _burst_instant():
                total = len(self.users) * len(self.devices) * max(1, self.Multiple_num)
                success = 0
                failed = 0
                completed = 0
                start_ts = time.time()

                async def _sign_then_shoot(u, d):
                    import json as _json, hashlib as _hashlib
                    now_ms = int(time.time() * 1000)
                    ext = {
                        "ignorePv": "0",
                        "liveClientParams": {
                            "pmClientType": "kmpLiveRoom",
                            "pmSession": f"{now_ms}INSTANT",
                            "liveToken": f"{now_ms}_{live_id}_IN",
                            "livesource": "PlayBackToLive",
                            "entryLiveSource": "PlayBackToLive",
                            "isAD": "0",
                            "pvid": _hashlib.md5(f"{now_ms}{u.uid}{live_id}".encode("utf-8")).hexdigest()
                        },
                        "liveServerParams": {
                            "accountId": account_id,
                            "liveId": live_id,
                            "status": "1"
                        },
                        "needEventWhenIgnorePv": "true"
                    }
                    json_data = {
                        "appKey": "21646297",
                        "ext": _json.dumps(ext, ensure_ascii=False),
                        "from": u.nickname,
                        "id": u.uid,
                        "internalExt": "",
                        "namespace": 1,
                        "role": 3,
                        "sdkVersion": "0.3.0",
                        "tag": "",
                        "topic": topic,
                        "utdId": d.utdid
                    }
                    data_str = _json.dumps(json_data, ensure_ascii=False)
                    t_seconds = str(int(time.time()))

                    # 在线程池中执行阻塞式签名
                    loop = asyncio.get_running_loop()
                    ok_sign, sign_data = await loop.run_in_executor(
                        None,
                        lambda: get_sign(d, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data_str, t_seconds)
                    )
                    if not ok_sign or not isinstance(sign_data, dict):
                        logger.error(f"签名失败: 用户 {u.uid}, 设备 {d.utdid}")
                        return False, "签名失败"

                    # 异步发送
                    return await subscribe_live_msg_prepared_async(d, u, data_str, self.proxy_value, t_seconds, sign_data)

                tasks = []
                for u in self.users:
                    for d in self.devices:
                        for _ in range(max(1, self.Multiple_num)):
                            tasks.append(_sign_then_shoot(u, d))

                for coro in asyncio.as_completed(tasks):
                    ok, res = await coro
                    completed += 1
                    if ok:
                        success += 1
                        self.log_fun(f"{completed}. ✅ 刷量成功")
                    else:
                        failed += 1
                        error_detail = str(res) if res else "未知错误"
                        self.log_fun(f"{completed}. ❌ 失败: {error_detail[:100]}")
                    if completed % 10 == 0 or completed == total:
                        self.log_fun(f"进度: {completed}/{total}, 成功={success}, 失败={failed}")

                total_time = time.time() - start_ts
                self.log_fun(f"🏁 突发发送完成: 总计={total}, 成功={success}, 失败={failed}, 耗时={total_time:.2f}s")
                return success, failed

            try:
                result = asyncio.run(_burst_instant())
                if result and len(result) == 2:
                    _finish_task(result[0], result[1])
                else:
                    _finish_task(0, 0)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(_burst_instant())
                loop.close()
                if result and len(result) == 2:
                    _finish_task(result[0], result[1])
                else:
                    _finish_task(0, 0)
            except Exception as e:
                print(f"[DEBUG] instant模式执行异常: {e}")
                import traceback
                traceback.print_exc()
                _finish_task(0, 0)
            return

        # 并发预热（preheat）：逐任务签名，失败自动切换设备直至成功
        preheat_msg = "🧪 开始预热签名（逐任务签名，失败自动切换设备）..."
        print(preheat_msg)
        self.log_fun(preheat_msg)
        total_expected = len(self.users) * len(self.devices) * max(1, self.Multiple_num)
        expect_msg = f"📊 预计预热任务总数: {total_expected}"
        print(expect_msg)
        self.log_fun(expect_msg)
        ready = []  # (user, device, seconds, sign_data, data_str)

        def sign_for_target(u: User, start_idx: int):
            total_dev = len(self.devices)
            for step in range(total_dev):
                d = self.devices[(start_idx + step) % total_dev]
                data_str_local = _build_sign_data(u, d)
                t_seconds_local = str(int(time.time()))
                ok, sign_data_local = get_sign(d, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data_str_local, t_seconds_local)
                if ok and isinstance(sign_data_local, dict):
                    return True, (u, d, t_seconds_local, sign_data_local, data_str_local)
            return False, None

        # 目标任务（按 user × devices × Multiple_num 构造），并给出设备起点，失败时轮换
        targets = []  # (user, start_idx)
        for u in self.users:
            total_dev = len(self.devices)
            if total_dev == 0:
                continue
            for i in range(total_dev):
                for k in range(max(1, self.Multiple_num)):
                    targets.append((u, (i + k) % total_dev))

        with ThreadPoolExecutor(max_workers=max(1, self.thread_nums)) as pre_executor:
            futs = [pre_executor.submit(sign_for_target, u, start_idx) for (u, start_idx) in targets]
            total_targets = len(futs)
            done_cnt = 0
            succ_cnt = 0
            for fut in as_completed(futs):
                try:
                    ok, packed = fut.result(timeout=20)
                    if ok and packed:
                        ready.append(packed)
                        succ_cnt += 1
                    # 全失败则跳过
                except Exception:
                    pass
                done_cnt += 1
                if done_cnt % 50 == 0 or done_cnt == total_targets:
                    prog = f"预热进度: {done_cnt}/{total_targets}, 成功={succ_cnt}, 失败={done_cnt - succ_cnt}"
                    print(prog)
                    self.log_fun(prog)

        if not ready:
            fail_preheat = "❌ 预热失败：没有可用的设备参数"
            print(fail_preheat)
            self.log_fun(fail_preheat)
            _finish_task(0, 0)
            return

        ready_msg = f"✅ 预热完成，可用设备参数: {len(ready)}"
        print(ready_msg)
        self.log_fun(ready_msg)

        # 突发异步：使用 asyncio + httpx.AsyncClient 瞬发
        burst_start = "🚀 突发发送开始（asyncio，不等待前序返回）..."
        print(burst_start)
        self.log_fun(burst_start)

        async def _burst_async():
            total = len(ready) * max(1, self.Multiple_num)
            success = 0
            failed = 0
            completed = 0
            start_ts = time.time()

            async def _shoot(u, d, t_seconds, sign_data, data_str, proxy):
                try:
                    ok, res = await subscribe_live_msg_prepared_async(d, u, data_str, proxy, t_seconds, sign_data)
                except Exception as e:
                    ok, res = False, str(e)
                # 若出现非法签名，尝试轮换设备重新签名再发送（最多重试2次）
                if (not ok) and isinstance(res, str) and ("ILEGEL_SIGN" in res or "非法" in res):
                    try:
                        base_idx = self.devices.index(d) if d in self.devices else 0
                    except Exception:
                        base_idx = 0
                    max_retry = min(2, max(0, len(self.devices) - 1))
                    for step in range(1, max_retry + 1):
                        nd = self.devices[(base_idx + step) % len(self.devices)]
                        # 重新构造数据并签名
                        import json as _json, hashlib as _hashlib
                        now_ms2 = int(time.time() * 1000)
                        ext2 = {
                            "ignorePv": "0",
                            "liveClientParams": {
                                "pmClientType": "kmpLiveRoom",
                                "pmSession": f"{now_ms2}RETRY",
                                "liveToken": f"{now_ms2}_{self.live_id}_RT",
                                "livesource": "PlayBackToLive",
                                "entryLiveSource": "PlayBackToLive",
                                "isAD": "0",
                                "pvid": _hashlib.md5(f"{now_ms2}{u.uid}{self.live_id}".encode("utf-8")).hexdigest()
                            },
                            "liveServerParams": {"accountId": self.info.get("accountId",""), "liveId": self.live_id, "status": "1"},
                            "needEventWhenIgnorePv": "true"
                        }
                        jd2 = {
                            "appKey": "21646297",
                            "ext": _json.dumps(ext2, ensure_ascii=False),
                            "from": u.nickname,
                            "id": u.uid,
                            "internalExt": "",
                            "namespace": 1,
                            "role": 3,
                            "sdkVersion": "0.3.0",
                            "tag": "",
                            "topic": self.info.get("topic",""),
                            "utdId": nd.utdid
                        }
                        data2 = _json.dumps(jd2, ensure_ascii=False)
                        t2 = str(int(time.time()))
                        ok_sign, sd2 = get_sign(nd, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data2, t2)
                        if ok_sign and isinstance(sd2, dict):
                            self.log_fun(f"🔁 设备轮换重试 step={step} devid={nd.devid[:8]}…")
                            try:
                                ok2, res2 = await subscribe_live_msg_prepared_async(nd, u, data2, proxy, t2, sd2)
                            except Exception as e2:
                                ok2, res2 = False, str(e2)
                            if ok2:
                                return ok2, res2
                    # 仍失败
                return ok, res

            tasks = []
            for u, d, t_seconds, sign_data, data_str in ready:
                for _ in range(max(1, self.Multiple_num)):
                    tasks.append(_shoot(u, d, t_seconds, sign_data, data_str, self.proxy_value))

            send_msg = f"📤 开始发送 {len(tasks)} 个任务..."
            print(send_msg)
            self.log_fun(send_msg)
            logger.info(f"突发发送: 创建了 {len(tasks)} 个异步任务")

            for coro in asyncio.as_completed(tasks):
                ok, res = await coro
                completed += 1
                if ok:
                    success += 1
                    succ_msg = f"{completed}. ✅ 刷量成功"
                    print(succ_msg)
                    self.log_fun(succ_msg)
                else:
                    failed += 1
                    # 确保错误信息不为空
                    error_detail = str(res) if res else "未知错误"
                    fail_msg = f"{completed}. ❌ 失败: {error_detail[:100]}"
                    print(fail_msg)
                    self.log_fun(fail_msg)
                if completed % 10 == 0 or completed == total:
                    prog_msg = f"进度: {completed}/{total}, 成功={success}, 失败={failed}"
                    print(prog_msg)
                    self.log_fun(prog_msg)

            total_time = time.time() - start_ts
            finish_msg = f"🏁 突发发送完成: 总计={total}, 成功={success}, 失败={failed}, 耗时={total_time:.2f}s"
            print(finish_msg)
            self.log_fun(finish_msg)
            
            # 返回结果用于更新UI
            return success, failed

        # 在普通线程环境中运行事件循环
        try:
            result = asyncio.run(_burst_async())
            if result and len(result) == 2:
                _finish_task(result[0], result[1])
            else:
                _finish_task(0, 0)
        except RuntimeError:
            # 如果已有事件循环（极少数情况），fallback到新loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_burst_async())
            loop.close()
            if result and len(result) == 2:
                _finish_task(result[0], result[1])
            else:
                _finish_task(0, 0)
        except Exception as e:
            print(f"[DEBUG] 任务执行异常: {e}")
            import traceback
            traceback.print_exc()
            _finish_task(0, 0)
        return

        self.log_fun(f"正在载入代理，任务数量: {len(tasks)}")
        
        # 根据代理配置设置代理
        if self.proxy_type == "direct" and self.proxy_value:
            # 直接填写代理模式：每个任务使用相同的代理（支持{{random}}占位符）
            self.log_fun(f"🔌 使用直接填写代理模式: {self.proxy_value}")
            for i, task in enumerate(tasks):
                # 如果代理中包含{{random}}，为每个任务生成不同的随机字符串
                proxy_with_random = self.proxy_value.replace('{{random}}', generate_random_string())
                tasks[i]["proxy"] = proxy_with_random
        elif self.proxy_type == "url" and self.proxy_value:
            # API URL模式：从URL获取代理列表
            self.log_fun(f"🔌 使用API代理模式，正在拉取代理...")
            try:
                proxies = self.get_proxys(len(tasks))
                if len(proxies) < len(tasks):
                    self.log_fun(f"⚠️ 代理数量不足: 需要{len(tasks)}个，实际{len(proxies)}个，将重复使用代理")
                    # 如果代理不够，循环使用
                    for i, task in enumerate(tasks):
                        tasks[i]["proxy"] = proxies[i % len(proxies)]
                else:
                    for i, task in enumerate(tasks):
                        tasks[i]["proxy"] = proxies[i]
                self.log_fun(f"✅ 已分配 {len(proxies)} 个代理")
            except Exception as e:
                self.log_fun(f"❌ 获取代理失败: {str(e)}，将使用直连")
        for i, task in enumerate(tasks):
            tasks[i]["proxy"] = ''
        else:
            # 未配置代理，使用直连
            self.log_fun(f"⚠️ 未配置代理，将使用直连")

        self.log_fun(f"📋 总任务数: {len(tasks)}")

        # 兼容旧路径：如果仍保留 tasks（理论不会走到此处）
        self.task_thread = AsyncTaskThread([], max_concurrent=self.thread_nums)

        # 连接信号槽
        self.task_thread.log_signal.connect(lambda msg: self.log_fun(msg))
        self.task_thread.progress_signal.connect(lambda status: self._update_progress(ui_widget, status))
        self.task_thread.finished_signal.connect(lambda result: self._on_finished(ui_widget, result))

        # 启动线程
        self.task_thread.start()
        self.log_fun("🚀 任务已启动")

    def stop_task(self):
        """停止任务"""
        if self.task_thread and self.task_thread.isRunning():
            self.task_thread.stop()
            self.log_fun("⏹️ 正在停止任务...")
        else:
            self.log_fun("⚠️ 没有正在运行的任务")

    def _update_progress(self, ui_widget, status):
        """更新进度（在UI线程中执行）"""
        ui_widget.success_count.setText(str(status['success']))
        ui_widget.fail_count.setText(str(status['failed']))
        self.success_num = status['success']
        self.fail_num = status['failed']

    def _on_finished(self, ui_widget, result):
        """任务完成回调"""
        self.log_fun(f"🏁 任务全部完成: 总计={result['total']}, 成功={result['success']}, 失败={result['failed']}")
        self.success_num = result['success']
        self.fail_num = result['failed']

        # 恢复按钮状态：启用开始按钮，禁用停止按钮
        ui_widget.start_btn.setEnabled(True)
        ui_widget.stop_btn.setEnabled(False)
