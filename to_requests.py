from loguru import logger

import tools
import time
from database import filter_available, filter_unused_devices, mark_device_used, clean_expired_device_records
from model.user import User
from model.device import Device
from taobao import get_sign, subscribe_live_msg_prepared_async, subscribe_live_msg_prepared_async_with_client, build_subscribe_data
from proxy_manager import ProxyManager
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
    def __init__(self, cookies=[], devices=[], thread_nums=5, Multiple_num=1, tasks_per_ip=30, use_device_num=0, log_fn=None, proxy_type="",
                 proxy_value="", live_id="", burst_mode: str = "preheat"):
        self.users = [User(tools.replace_cookie_item(i, "sgcookie", None)) for i in cookies]
        self.users = filter_available(users=self.users, isaccount=True, interval_hours=10)

        self.devices = []
        for device in devices:
            items = [item.strip() for item in device.split("\t") if item.strip()]
            if len(items) >= 5:
                self.devices.append(Device(items[0], items[1], items[2], items[3], items[4]))

        # 第1步：过滤10小时内被封禁的设备
        available_devices = filter_available(devices=self.devices, isaccount=False, interval_hours=10)
        
        # 第2步：过滤10分钟内已使用的设备（避免短时间重复使用）
        available_devices = filter_unused_devices(available_devices, interval_minutes=10)
        
        # 定期清理过期的设备使用记录
        clean_expired_device_records(interval_minutes=10)
        
        total_available = len(available_devices)
        
        # 保存所有可用设备（用于预热时自动切换）
        self.all_available_devices = available_devices
        
        # 如果指定了使用设备数，记录但不立即限制（预热后再限制）
        if use_device_num > 0 and use_device_num < total_available:
            if log_fn:
                log_fn(f"🔧 目标使用设备数: {use_device_num} (预热时从 {total_available} 个可用设备中自动切换)")
            self.devices = available_devices  # 预热阶段先用全部
        else:
            self.devices = available_devices

        self.thread_nums = thread_nums  # 现在是并发数
        self.Multiple_num = Multiple_num
        self.tasks_per_ip = tasks_per_ip  # 每个IP分配的任务数
        self.use_device_num = use_device_num  # 使用设备数
        self.success_num = 0
        self.fail_num = 0

        self.task_thread = None  # Qt后台线程
        self.log_fun = log_fn

        self.proxy_type = proxy_type
        self.proxy_value = proxy_value
        self.live_id = live_id
        # 突发模式：preheat=预热签名后一次性发送；instant=即时签名+一次性发送
        self.burst_mode = burst_mode if burst_mode in ("preheat", "instant") else "preheat"
        
        # 代理池管理器（延迟初始化）
        self.proxy_manager = None

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
                err_msg = "❌ 没有可用的设备参数，请检查设备列表或等待12小时后重试"
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
        # 使用 taobao.py 中统一的构造函数

        # 选择模式
        mode_msg = f"🧭 突发模式: {self.burst_mode}"
        print(mode_msg)
        self.log_fun(mode_msg)
        logger.info(f"开始执行突发任务，模式: {self.burst_mode}, 用户数: {len(self.users)}, 设备数: {len(self.devices)}, 倍数: {self.Multiple_num}")

        # 计算实际任务数（使用目标设备数，而不是全部设备数）
        if self.use_device_num > 0:
            target_device_count = min(self.use_device_num, len(self.all_available_devices))
        else:
            target_device_count = len(self.devices)
        
        # 初始化代理池管理器（如果是URL类型代理）
        total_tasks = len(self.users) * target_device_count * max(1, self.Multiple_num)
        if self.proxy_type == "url" and self.proxy_value:
            try:
                self.log_fun("=" * 60)
                self.log_fun("🌐 开始初始化代理池...")
                self.log_fun(f"📊 总任务数: {total_tasks}")
                self.log_fun(f"📌 每IP分配任务数: {self.tasks_per_ip}")
                
                # 创建代理管理器（传入进度回调函数，实时显示测试进度）
                self.proxy_manager = ProxyManager(
                    self.proxy_value, 
                    tasks_per_ip=self.tasks_per_ip,
                    progress_callback=self.log_fun  # UI进度回调
                )
                
                # 初始化代理池（自动提取+测试）
                if self.proxy_manager.initialize_proxies(total_tasks):
                    self.proxy_manager.print_distribution_info()
                    self.log_fun("✅ 代理池初始化成功！")
                else:
                    self.log_fun("⚠️ 代理池初始化部分失败，将使用现有可用IP")
                
                self.log_fun("=" * 60)
            except Exception as e:
                self.log_fun(f"❌ 代理池初始化异常: {e}")
                self.log_fun("⚠️ 将不使用代理池，改用原始代理方式")
                self.proxy_manager = None

        if self.burst_mode == "instant":
            # 直接即时签名 + 异步突发
            self.log_fun("🚀 突发发送开始（instant：签名+发送全部瞬发）...")
            self.log_fun(f"📊 预计任务总数: {total_tasks}")

            async def _burst_instant():
                total = len(self.users) * len(self.devices) * max(1, self.Multiple_num)
                success = 0
                failed = 0
                completed = 0
                
                # 用于记录发送耗时的变量
                first_send_time = None
                last_send_time = None
                send_lock = asyncio.Lock()

                async def _sign_then_shoot(u, d, task_index):
                    nonlocal first_send_time, last_send_time
                    # 使用统一的构造函数
                    data_str, t_seconds = build_subscribe_data(u, d, account_id, live_id, topic)

                    # 在线程池中执行阻塞式签名
                    loop = asyncio.get_running_loop()
                    ok_sign, sign_data = await loop.run_in_executor(
                        None,
                        lambda: get_sign(d, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data_str, t_seconds)
                    )
                    if not ok_sign or not isinstance(sign_data, dict):
                        return False, "签名失败"

                    # 获取代理（使用代理池或原始代理）
                    if self.proxy_manager:
                        proxy = self.proxy_manager.get_proxy_for_task(task_index)
                    else:
                        proxy = self.proxy_value
                    
                    # 记录第一次和最后一次发送时间
                    send_time = time.time()
                    async with send_lock:
                        if first_send_time is None:
                            first_send_time = send_time
                        last_send_time = send_time
                    
                    # 异步发送
                    return await subscribe_live_msg_prepared_async(d, u, data_str, proxy, t_seconds, sign_data)

                tasks = []
                task_index = 0
                for u in self.users:
                    for d in self.devices:
                        for _ in range(max(1, self.Multiple_num)):
                            tasks.append(_sign_then_shoot(u, d, task_index))
                            task_index += 1

                # 开始执行任务
                start_ts = time.time()
                for coro in asyncio.as_completed(tasks):
                    ok, res = await coro
                    completed += 1
                    if ok:
                        success += 1
                    else:
                        failed += 1
                    # 只在特定进度点打印，减少日志开销
                    if completed % 100 == 0 or completed == total:
                        self.log_fun(f"进度: {completed}/{total}, 成功={success}, 失败={failed}")

                total_time = time.time() - start_ts
                send_duration = (last_send_time - first_send_time) if (first_send_time and last_send_time) else 0
                self.log_fun(f"⚡ 发送耗时: {send_duration:.3f}s (从第1个到最后1个请求发出)")
                self.log_fun(f"🏁 总耗时(含响应): {total_time:.2f}s | 成功={success}, 失败={failed}")
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
        preheat_msg = "🧪 开始预热签名（逐任务签名，失败自动从所有设备中切换）..."
        print(preheat_msg)
        self.log_fun(preheat_msg)
        
        # 如果指定了使用设备数，目标任务数就是指定的数量
        if self.use_device_num > 0:
            target_device_count = min(self.use_device_num, len(self.all_available_devices))
        else:
            target_device_count = len(self.devices)
        
        total_expected = len(self.users) * target_device_count * max(1, self.Multiple_num)
        expect_msg = f"📊 目标预热任务数: {total_expected} (从 {len(self.all_available_devices)} 个可用设备中选择)"
        print(expect_msg)
        self.log_fun(expect_msg)
        ready = []  # (user, device, seconds, sign_data, data_str)

        def sign_for_target(u: User, start_idx: int):
            # 🔥 关键：从所有可用设备中切换，而不是只从限制后的设备中切换
            total_dev = len(self.all_available_devices)
            for step in range(total_dev):
                d = self.all_available_devices[(start_idx + step) % total_dev]
                # 使用统一的构造函数
                data_str_local, t_seconds_local = build_subscribe_data(u, d, account_id, live_id, topic)
                ok, sign_data_local = get_sign(d, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data_str_local, t_seconds_local)
                if ok and isinstance(sign_data_local, dict):
                    return True, (u, d, t_seconds_local, sign_data_local, data_str_local)
            return False, None

        # 目标任务（按 user × target_device_count × Multiple_num 构造），并给出设备起点，失败时轮换
        targets = []  # (user, start_idx)
        for u in self.users:
            total_dev = len(self.all_available_devices)
            if total_dev == 0:
                continue
            # 根据目标设备数量生成任务
            for i in range(target_device_count):
                for k in range(max(1, self.Multiple_num)):
                    targets.append((u, (i + k) % total_dev))

        # ⚡ 优化4：预热并发数（根据签名服务性能调整）
        # 如果签名服务响应慢，降低并发可能反而更快（避免过载）
        preheat_workers = min(50, max(20, self.thread_nums * 5))  # 20-50之间
        self.log_fun(f"⚡ 预热并发数: {preheat_workers} (避免签名服务过载)")
        with ThreadPoolExecutor(max_workers=preheat_workers) as pre_executor:
            futs = [pre_executor.submit(sign_for_target, u, start_idx) for (u, start_idx) in targets]
            total_targets = len(futs)
            done_cnt = 0
            succ_cnt = 0
            for fut in as_completed(futs):
                try:
                    ok, packed = fut.result(timeout=30)  # 缩短超时到10秒
                    if ok and packed:
                        ready.append(packed)
                        succ_cnt += 1
                    # 全失败则跳过
                except Exception:
                    pass
                done_cnt += 1
                # ⚡ 优化5：减少日志输出频率（每100个或完成时）
                if done_cnt % 100 == 0 or done_cnt == total_targets:
                    prog = f"预热进度: {done_cnt}/{total_targets}, 成功={succ_cnt}, 失败={done_cnt - succ_cnt}"
                    print(prog)
                    self.log_fun(prog)

        if not ready:
            fail_preheat = "❌ 预热失败：没有可用的设备参数"
            print(fail_preheat)
            self.log_fun(fail_preheat)
            _finish_task(0, 0)
            return

        # 如果设置了使用设备数限制，确保预热成功的数量满足要求
        if self.use_device_num > 0 and len(ready) < total_expected:
            warn_msg = f"⚠️ 预热成功数 {len(ready)} 少于目标 {total_expected}，部分任务无法执行"
            print(warn_msg)
            self.log_fun(warn_msg)
        
        ready_msg = f"✅ 预热完成，获得 {len(ready)} 个可用设备参数 (目标: {total_expected})"
        print(ready_msg)
        self.log_fun(ready_msg)

        # 突发异步：使用 asyncio + httpx.AsyncClient 瞬发
        burst_start = "🚀 突发发送开始（asyncio，不等待前序返回）..."
        print(burst_start)
        self.log_fun(burst_start)

        async def _burst_preheat():
            total = len(ready)
            success = 0
            failed = 0
            completed = 0
            
            # 用于记录发送耗时的变量
            send_start_time = None
            send_end_time = None
            send_count = 0
            send_lock = asyncio.Lock()
            
            # 🔥 关键优化：创建按代理分组的 client 池，复用连接
            import httpx
            from collections import defaultdict
            
            # 按代理创建 client 字典
            client_pool = {}  # {proxy: client}
            
            def get_client_for_proxy(proxy):
                """获取或创建指定代理的 client"""
                if proxy not in client_pool:
                    client_kwargs = {
                        # ⚡ 优化1：缩短超时时间，快速失败
                        "timeout": httpx.Timeout(8.0, connect=4.0, read=6.0, write=4.0),
                        # ⚡ 优化2：大幅提升连接池，支持高并发
                        "limits": httpx.Limits(
                            max_connections=200,              # 提升到200（原50）
                            max_keepalive_connections=150,    # 提升到150（原30）
                            keepalive_expiry=60.0             # 延长到60秒（原30秒）
                        ),
                        # ⚡ 优化3：启用HTTP/2，单连接复用多请求
                        "http2": True
                    }
                    # 配置代理（支持多种格式）
                    if proxy and proxy != "":
                        # 解析代理格式
                        if not (proxy.startswith('socks5://') or proxy.startswith('http://') or proxy.startswith('https://')):
                            if proxy.count(':') == 3:
                                # 格式1: IP:PORT:USERNAME:PASSWORD（带认证）
                                parts = proxy.split(':')
                                ip, port, username, password = parts[0], parts[1], parts[2], parts[3]
                                proxy_url = f'http://{username}:{password}@{ip}:{port}'
                            elif proxy.count(':') == 1:
                                # 格式2: IP:PORT（无认证）
                                proxy_url = f'http://{proxy}'
                            else:
                                # 其他格式，默认加http://
                                proxy_url = f'http://{proxy}'
                        else:
                            # 格式3: 已带协议头（socks5://、http://、https://）
                            proxy_url = proxy
                        client_kwargs["proxies"] = proxy_url
                    
                    client_pool[proxy] = httpx.AsyncClient(**client_kwargs)
                
                return client_pool[proxy]

            async def _shoot(u, d, t_seconds, sign_data, data_str, proxy):
                nonlocal send_start_time, send_end_time, send_count
                
                # 记录发送时间（发出请求的时刻）
                async with send_lock:
                    if send_start_time is None:
                        send_start_time = time.time()
                    send_count += 1
                
                try:
                    # 根据代理获取对应的 client（相同代理复用同一个 client）
                    client = get_client_for_proxy(proxy)
                    ok, res = await subscribe_live_msg_prepared_async_with_client(
                        client, d, u, data_str, proxy, t_seconds, sign_data
                    )
                    # 记录最后一次请求完成的时间
                    async with send_lock:
                        send_end_time = time.time()
                except Exception as e:
                    ok, res = False, str(e)
                    async with send_lock:
                        send_end_time = time.time()
                # 若出现非法签名，尝试轮换设备重新签名再发送（最多重试2次）
                if (not ok) and isinstance(res, str) and ("ILEGEL_SIGN" in res or "非法" in res):
                    try:
                        base_idx = self.devices.index(d) if d in self.devices else 0
                    except Exception:
                        base_idx = 0
                    max_retry = min(2, max(0, len(self.devices) - 1))
                    for step in range(1, max_retry + 1):
                        nd = self.devices[(base_idx + step) % len(self.devices)]
                        # 使用统一的构造函数重新构造数据并签名
                        data2, t2 = build_subscribe_data(u, nd, self.info.get("accountId",""), self.live_id, self.info.get("topic",""))
                        ok_sign, sd2 = get_sign(nd, u, "mtop.taobao.powermsg.msg.subscribe", "1.0", data2, t2)
                        if ok_sign and isinstance(sd2, dict):
                            try:
                                ok2, res2 = await subscribe_live_msg_prepared_async(nd, u, data2, proxy, t2, sd2)
                            except Exception as e2:
                                ok2, res2 = False, str(e2)
                            if ok2:
                                return ok2, res2
                    # 仍失败
                return ok, res

            tasks = []
            task_devices = []  # 保存每个任务对应的设备（用于成功后标记）
            task_index = 0
            for u, d, t_seconds, sign_data, data_str in ready:
                # 获取代理（使用代理池或原始代理）
                if self.proxy_manager:
                    proxy = self.proxy_manager.get_proxy_for_task(task_index)
                else:
                    proxy = self.proxy_value
                tasks.append(_shoot(u, d, t_seconds, sign_data, data_str, proxy))
                task_devices.append(d)  # 保存设备引用
                task_index += 1

            send_msg = f"📤 ⚡ 开始发送 {len(tasks)} 个任务..."
            print(send_msg)
            self.log_fun(send_msg)
            logger.info(f"突发发送: 创建了 {len(tasks)} 个异步任务")

            # 开始执行任务
            start_ts = time.time()
            
            # 💥 关键：使用 gather 并发执行所有任务
            try:
                # 等待所有任务完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 显示连接池统计
                self.log_fun(f"🔌 使用了 {len(client_pool)} 个HTTP连接池（按代理分组复用）")
            finally:
                # 关闭所有 client
                for client in client_pool.values():
                    await client.aclose()
            
            # 计算实际发送耗时
            if send_start_time and send_end_time:
                send_duration = send_end_time - send_start_time
                self.log_fun(f"📊 请求发送统计: 共发出 {send_count} 个请求，耗时 {send_duration:.3f}s")
            
            # 统计结果
            self.log_fun("📊 开始统计响应结果...")
            fail_reasons = {}  # 统计失败原因
            marked_devices = []  # 已标记的设备（用于日志）
            for i, result in enumerate(results):
                device = task_devices[i]  # 获取对应的设备
                
                if isinstance(result, Exception):
                    failed += 1
                    error_msg = str(result)[:50]
                    fail_reasons[error_msg] = fail_reasons.get(error_msg, 0) + 1
                elif isinstance(result, tuple) and len(result) == 2:
                    ok, res = result
                    if ok:
                        success += 1
                        # 🔥 成功后标记设备已使用（10分钟内不再使用）
                        mark_device_used(device.devid)
                        marked_devices.append(device.devid)
                    else:
                        failed += 1
                        # 记录失败原因
                        error_msg = str(res)[:50] if res else "未知错误"
                        fail_reasons[error_msg] = fail_reasons.get(error_msg, 0) + 1
                else:
                    failed += 1
                    fail_reasons["返回格式错误"] = fail_reasons.get("返回格式错误", 0) + 1
                
                # 定期打印进度
                completed = i + 1
                if completed % 100 == 0 or completed == total:
                    self.log_fun(f"响应统计: {completed}/{total}, 成功={success}, 失败={failed}")
            
            # 显示失败原因统计
            if fail_reasons:
                self.log_fun("=" * 60)
                self.log_fun("📋 失败原因统计:")
                for reason, count in sorted(fail_reasons.items(), key=lambda x: x[1], reverse=True):
                    self.log_fun(f"  • {reason}: {count}次")
                self.log_fun("=" * 60)

            total_time = time.time() - start_ts
            self.log_fun(f"🏁 全部完成 | 总耗时: {total_time:.2f}s | 成功={success}, 失败={failed}")
            
            # 显示设备使用统计
            if marked_devices:
                unique_marked = len(set(marked_devices))
                self.log_fun(f"📝 设备使用记录: 已标记 {unique_marked} 个设备（10分钟内不可重复使用）")
            
            # 返回结果用于更新UI
            return success, failed

        # ⚡ 优化6：尝试使用uvloop加速（性能提升20-40%）
        try:
            import uvloop
            uvloop.install()
            uvloop_msg = "✅ 已启用uvloop加速（异步性能提升20-40%）"
            print(uvloop_msg)
            self.log_fun(uvloop_msg)
        except ImportError:
            pass  # uvloop未安装，使用默认事件循环
        
        # 在普通线程环境中运行事件循环
        try:
            result = asyncio.run(_burst_preheat())
            if result and len(result) == 2:
                _finish_task(result[0], result[1])
            else:
                _finish_task(0, 0)
        except RuntimeError:
            # 如果已有事件循环（极少数情况），fallback到新loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_burst_preheat())
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
