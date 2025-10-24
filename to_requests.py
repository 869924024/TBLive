import tools
from database import filter_available
from model.user import User
from model.device import Device
from task_batch import AsyncTaskThread
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
                 proxy_value="", live_id=""):
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
        """
        开始任务

        Args:
            ui_widget: TaskPage对象，用于连接信号槽更新UI
        """
        if self.task_thread and self.task_thread.isRunning():
            self.log_fun("⚠️ 任务正在运行中，请勿重复启动")
            return

        # 构建任务列表
        tasks = []
        for user in self.users:
            for device in self.devices:
                for _ in range(self.Multiple_num):
                    tasks.append({
                        "user": user,
                        "device": device,
                        "proxy": self.proxy_value,
                        "account_id": self.info.get("accountId", ""),
                        "live_id": self.info.get("liveId", ""),
                        "topic": self.info.get("topic", ""),
                    })

        self.log_fun("正在载入代理，任务数量: " + str(len(tasks)))

        proxy = self.get_proxys(len(tasks))
        if len(proxy) < len(tasks):
            self.log_fun(f"📋 代理数量过少: {len(proxy)}")
            return

        for i, task in enumerate(tasks):
            tasks[i]["proxy"] = proxy[i]

        self.log_fun(f"📋 总任务数: {len(tasks)}")

        # 创建后台线程
        self.task_thread = AsyncTaskThread(tasks, max_concurrent=self.thread_nums)

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
