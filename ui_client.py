"""
淘宝直播刷量客户端 - 简化版UI
专为工人傻瓜式操作设计，去掉设备采集功能
"""

import os
import json
import threading
import requests
import re
import time
import math
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QFileDialog, QTextEdit, QFrame, QLabel
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, Theme,
    PushButton, PrimaryPushButton, TransparentPushButton,
    BodyLabel, TitleLabel, SubtitleLabel, CaptionLabel,
    TextEdit, LineEdit, ComboBox,
    CardWidget,
    InfoBar, InfoBarPosition,
    FluentIcon as FIF,
    isDarkTheme, SpinBox
)

from to_requests import Watch  # 保持原有逻辑不变
from database import filter_available, save_timestamp
from model.user import User
import tools


class ClientUI(FluentWindow):
    """刷量客户端主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("淘宝直播刷量客户端 v1.0")
        self.resize(1200, 800)
        
        # 数据存储
        self.cookies = []  # Cookie列表
        self.devices = []  # 设备列表
        self.client_key = ""  # 客户端密钥
        self.api_url = "http://localhost:5000"  # API地址
        self.watch_instance = None  # Watch实例
        
        # 初始化UI
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """初始化界面"""
        # 创建主页面
        self.main_page = MainPage(self)
        self.addSubInterface(
            self.main_page,
            FIF.HOME,
            "刷量操作",
            NavigationItemPosition.TOP
        )
        
        # 创建配置页面
        self.config_page = ConfigPage(self)
        self.addSubInterface(
            self.config_page,
            FIF.SETTING,
            "配置管理",
            NavigationItemPosition.TOP
        )
        
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists('client_config.json'):
                with open('client_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.client_key = config.get('client_key', '')
                    self.api_url = config.get('api_url', 'http://localhost:5000')
                    self.cookies = config.get('cookies', [])
                    self.devices = config.get('devices', [])
                    
                    # 更新配置页面
                    self.config_page.client_key_input.setText(self.client_key)
                    self.config_page.api_url_input.setText(self.api_url)
                    
                    # 更新主页面显示
                    self.main_page.update_data_display()
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            config = {
                'client_key': self.client_key,
                'api_url': self.api_url,
                'cookies': self.cookies,
                'devices': self.devices
            }
            with open('client_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False


class MainPage(QWidget):
    """刷量操作主页面"""
    
    # 定义信号（用于线程安全的UI更新）
    log_signal = pyqtSignal(str)  # 日志信号
    success_signal = pyqtSignal(str)  # 成功提示信号
    error_signal = pyqtSignal(str)  # 错误提示信号
    task_finished_signal = pyqtSignal(int, int)  # 任务完成信号(success, failed)
    
    def __init__(self, parent: ClientUI):
        super().__init__(parent)
        self.setObjectName("mainPage")  # 设置对象名称
        self.parent_window = parent
        self.setup_ui()
        
        # 连接信号到槽函数
        self.log_signal.connect(self._log_slot)
        self.success_signal.connect(self._show_success_slot)
        self.error_signal.connect(self._show_error_slot)
        self.task_finished_signal.connect(self._task_finished_slot)
        
        # 定时器用于更新统计
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # 每秒更新一次
        
        # 任务状态
        self.is_running = False
        self.view_count_before = 0
        self.view_count_after = 0
        
        # 添加 success_count 和 fail_count 属性（兼容 Watch 类）
        self.success_count = None
        self.fail_count = None

        # 操作后数据轮询控制
        self._after_poll_active = False
        # 选中 Cookie（用于一批设备跑）
        self.selected_cookie = None
        self.selected_user_uid = None

        self._after_poll_intervals = []  # 秒
        self._after_poll_attempt = 0
        self._after_poll_last_increment = None
        self._after_poll_nochange = 0
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("淘宝直播刷量操作")
        layout.addWidget(title)
        
        # 第一行：淘口令输入区域
        share_code_card = self.create_share_code_card()
        layout.addWidget(share_code_card)
        
        # 第二行：数据统计卡片
        stats_card = self.create_stats_card()
        layout.addWidget(stats_card)
        
        # 第三行：操作配置
        operation_card = self.create_operation_card()
        layout.addWidget(operation_card)
        
        # 第四行：日志输出
        log_card = self.create_log_card()
        layout.addWidget(log_card)
        
    def create_share_code_card(self):
        """创建直播间ID输入卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel("📱 直播间信息")
        layout.addWidget(title)
        
        # 输入框
        input_layout = QHBoxLayout()
        
        label = BodyLabel("直播间ID:")
        label.setFixedWidth(100)
        input_layout.addWidget(label)
        
        self.live_id_input = LineEdit()
        self.live_id_input.setPlaceholderText("输入直播间ID，例如：123456789")
        self.live_id_input.textChanged.connect(self.on_live_id_changed)
        input_layout.addWidget(self.live_id_input)
        
        # 获取观看数按钮
        fetch_btn = PrimaryPushButton(FIF.SYNC, "获取观看数")
        fetch_btn.clicked.connect(self.fetch_current_view_count_direct)
        fetch_btn.setFixedWidth(120)
        input_layout.addWidget(fetch_btn)
        
        layout.addLayout(input_layout)
        
        # 当前观看数显示
        result_layout = QHBoxLayout()
        self.view_count_label = BodyLabel("当前观看数: --")
        result_layout.addWidget(self.view_count_label)
        result_layout.addStretch()
        
        layout.addLayout(result_layout)
        
        return card
    
    def create_stats_card(self):
        """创建统计卡片"""
        card = CardWidget(self)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)
        
        # Cookie数量
        cookie_layout = QVBoxLayout()
        cookie_title = CaptionLabel("可用Cookie")
        self.cookie_count_label = TitleLabel("0")
        self.cookie_count_label.setStyleSheet("color: #0078D4;")
        cookie_layout.addWidget(cookie_title)
        cookie_layout.addWidget(self.cookie_count_label)
        layout.addLayout(cookie_layout)
        
        # 设备数量
        device_layout = QVBoxLayout()
        device_title = CaptionLabel("可用设备")
        self.device_count_label = TitleLabel("0")
        self.device_count_label.setStyleSheet("color: #0078D4;")
        device_layout.addWidget(device_title)
        device_layout.addWidget(self.device_count_label)
        layout.addLayout(device_layout)
        
        # 操作前观看数
        before_layout = QVBoxLayout()
        before_title = CaptionLabel("操作前观看数")
        self.view_before_label = TitleLabel("--")
        self.view_before_label.setStyleSheet("color: #666;")
        before_layout.addWidget(before_title)
        before_layout.addWidget(self.view_before_label)
        layout.addLayout(before_layout)
        
        # 操作后观看数
        after_layout = QVBoxLayout()
        after_title = CaptionLabel("操作后观看数")
        self.view_after_label = TitleLabel("--")
        self.view_after_label.setStyleSheet("color: #666;")
        after_layout.addWidget(after_title)
        after_layout.addWidget(self.view_after_label)
        layout.addLayout(after_layout)
        
        # 增量
        increment_layout = QVBoxLayout()
        increment_title = CaptionLabel("增量")
        self.increment_label = TitleLabel("--")
        self.increment_label.setStyleSheet("color: #107C10;")
        increment_layout.addWidget(increment_title)
        increment_layout.addWidget(self.increment_label)
        layout.addLayout(increment_layout)
        
        return card
    
    def create_operation_card(self):
        """创建操作配置卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel("⚙️ 操作配置")
        layout.addWidget(title)

        # 选择 Cookie 行（在红框处）
        ck_layout = QHBoxLayout()
        ck_label = BodyLabel("选择Cookie:")
        ck_label.setFixedWidth(100)
        ck_layout.addWidget(ck_label)

        self.cookie_select = ComboBox()
        self.cookie_select.setPlaceholderText("自动选择一个未使用的Cookie（冷却12小时）")
        self.cookie_select.setMinimumWidth(360)
        self.cookie_select.currentIndexChanged.connect(self.on_cookie_selected)
        ck_layout.addWidget(self.cookie_select)
        ck_layout.addStretch()
        layout.addLayout(ck_layout)
        self.refresh_cookie_select()
        
        # 第一行：操作倍数
        config_layout1 = QHBoxLayout()
        multiple_label = BodyLabel("操作倍数:")
        multiple_label.setFixedWidth(100)
        config_layout1.addWidget(multiple_label)
        
        self.multiple_spin = SpinBox()
        self.multiple_spin.setMinimum(1)
        self.multiple_spin.setMaximum(100)
        self.multiple_spin.setValue(1)
        self.multiple_spin.setFixedWidth(120)
        config_layout1.addWidget(self.multiple_spin)
        config_layout1.addStretch()
        
        layout.addLayout(config_layout1)
        
        # 第二行：使用设备数
        config_layout2 = QHBoxLayout()
        device_num_label = BodyLabel("使用设备数:")
        device_num_label.setFixedWidth(100)
        config_layout2.addWidget(device_num_label)
        
        self.use_device_spin = SpinBox()
        self.use_device_spin.setMinimum(0)
        self.use_device_spin.setMaximum(9999)
        self.use_device_spin.setValue(0)
        self.use_device_spin.setFixedWidth(120)
        self.use_device_spin.setSpecialValueText("全部")  # 0显示为"全部"
        config_layout2.addWidget(self.use_device_spin)
        
        hint_label = CaptionLabel("(0=使用全部，其他=使用指定数量)")
        hint_label.setStyleSheet("color: #888;")
        config_layout2.addWidget(hint_label)
        config_layout2.addStretch()
        
        layout.addLayout(config_layout2)
        
        # 第三行：代理设置
        config_layout3 = QHBoxLayout()
        proxy_label = BodyLabel("代理地址:")
        proxy_label.setFixedWidth(100)
        config_layout3.addWidget(proxy_label)
        
        self.proxy_input = LineEdit()
        self.proxy_input.setPlaceholderText("留空则不使用代理")
        config_layout3.addWidget(self.proxy_input)
        
        layout.addLayout(config_layout3)
        
        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 开始刷量按钮
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始刷量")
        self.start_btn.clicked.connect(self.start_task)
        self.start_btn.setFixedWidth(150)
        button_layout.addWidget(self.start_btn)
        
        # 停止按钮
        self.stop_btn = PushButton(FIF.CLOSE, "停止")
        self.stop_btn.clicked.connect(self.stop_task)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFixedWidth(100)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        return card
    
    def create_log_card(self):
        """创建日志卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 标题和清空按钮
        title_layout = QHBoxLayout()
        title = SubtitleLabel("📝 操作日志")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        clear_btn = TransparentPushButton(FIF.DELETE, "清空")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        clear_btn.setFixedWidth(80)
        title_layout.addWidget(clear_btn)
        
        layout.addLayout(title_layout)
        
        # 日志文本框
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(250)
        layout.addWidget(self.log_text)
        
        return card
    
    def update_data_display(self):
        """更新数据显示"""
        self.cookie_count_label.setText(str(len(self.parent_window.cookies)))
        self.device_count_label.setText(str(len(self.parent_window.devices)))
        # 同步刷新下拉候选
        self.refresh_cookie_select()
    
    def on_live_id_changed(self, text):
        """直播间ID输入变化时的处理"""
        # 重置观看数显示
        if not text.strip():
            self.view_count_label.setText("当前观看数: --")
    
    def fetch_current_view_count_direct(self):
        """直接获取当前观看数"""
        live_id = self.live_id_input.text().strip()
        if not live_id:
            self.show_error("请输入直播间ID")
            return
        
        if not live_id.isdigit():
            self.show_error("直播间ID格式错误，请输入纯数字")
            return
        
        self.log(f"🔍 正在获取直播间 {live_id} 的观看数...")
        
        try:
            url = f"https://alive-interact.alicdn.com/livedetail/common/{live_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 从返回数据中提取观看数（根据实际API调整字段）
            view_count = data.get('data', {}).get('viewCount', 0)
            if view_count == 0:
                view_count = data.get('viewCount', 0)
            
            self.view_count_label.setText(f"当前观看数: {view_count:,}")
            self.log(f"✅ 当前观看数: {view_count:,}")

            # 同步为“操作前观看数”基线（用户点击该按钮通常希望作为基线）
            self.view_count_before = view_count
            self.view_before_label.setText(f"{view_count:,}")
            self.view_before_label.setStyleSheet("color: #0078D4;")
            
        except Exception as e:
            self.show_error(f"获取失败: {str(e)}")
            self.log(f"❌ 获取观看数失败: {str(e)}")
    
    def fetch_before_data(self):
        """获取操作前数据"""
        # 获取直播间ID
        live_id = self.live_id_input.text().strip()
        if not live_id:
            self.show_error("请先输入直播间ID")
            return
        
        if not live_id.isdigit():
            self.show_error("直播间ID格式错误，请输入纯数字")
            return
        
        self.log("📥 正在获取操作前数据...")
        
        try:
            # 获取观看数
            url = f"https://alive-interact.alicdn.com/livedetail/common/{live_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            view_count = data.get('data', {}).get('viewCount', 0)
            if view_count == 0:
                view_count = data.get('viewCount', 0)
            
            # 同步更新顶部“当前观看数”
            self.view_count_label.setText(f"当前观看数: {view_count:,}")

            self.view_count_before = view_count
            self.view_before_label.setText(f"{view_count:,}")
            self.view_before_label.setStyleSheet("color: #0078D4;")
            
            self.log(f"✅ 操作前观看数: {view_count:,}")
            self.show_success("操作前数据获取成功")
            
        except Exception as e:
            self.show_error(f"获取失败: {str(e)}")

    def refresh_cookie_select(self):
        """刷新可选 Cookie 下拉，优先展示未在12小时内使用的Cookie"""
        if not hasattr(self, 'cookie_select'):
            return
        self.cookie_select.blockSignals(True)
        self.cookie_select.clear()
        self._cookie_options = []  # [(display, cookie, uid)]

        cookies = self.parent_window.cookies or []
        raw_users = []
        for c in cookies:
            # 与核心逻辑一致：去掉 sgcookie 影响识别
            c2 = tools.replace_cookie_item(c, "sgcookie", None)
            u = User(c2)
            if u and u.uid:
                raw_users.append((c, u))

        # 去重：按同一 uid 的“最后一次出现”为准（最新导入/更新优先）
        seen_uids = set()
        dedup_list_reversed = []
        for c, u in reversed(raw_users):
            if u.uid not in seen_uids:
                seen_uids.add(u.uid)
                dedup_list_reversed.append((c, u))
        users = list(reversed(dedup_list_reversed))  # 还原为自然顺序（但保留“最后一次出现”的版本）

        # 过滤 12 小时内使用过的账号
        available_users = filter_available(users=[u for _, u in users], isaccount=True, interval_hours=12)
        available_uids = set(u.uid for u in available_users)

        # 优先将未使用的放前面
        ordered = []
        for c, u in users:
            if u.uid in available_uids:
                ordered.append((c, u, True))
        for c, u in users:
            if u.uid not in available_uids:
                ordered.append((c, u, False))

        # 填充下拉项
        for c, u, is_free in ordered:
            nick = u.nickname or "(无昵称)"
            tag = "可用" if is_free else "冷却中"
            display = f"{nick}  unb={u.uid}  [{tag}]"
            self.cookie_select.addItem(display)
            self._cookie_options.append((display, c, u.uid))

        # 默认选择第一个“可用”的；若没有，则第一个
        default_index = 0
        for idx, (_, c, uid) in enumerate(self._cookie_options):
            if uid in available_uids:
                default_index = idx
                break
        if self._cookie_options:
            self.cookie_select.setCurrentIndex(default_index)
            self.selected_cookie = self._cookie_options[default_index][1]
            self.selected_user_uid = self._cookie_options[default_index][2]
        self.cookie_select.blockSignals(False)

    def on_cookie_selected(self, index):
        if 0 <= index < len(getattr(self, '_cookie_options', [])):
            _, c, uid = self._cookie_options[index]
            self.selected_cookie = c
            self.selected_user_uid = uid
    
    def start_task(self):
        """开始刷量任务"""
        # 检查数据
        if len(self.parent_window.cookies) == 0:
            self.show_error("没有可用的Cookie，请在配置页面导入")
            return
        
        if len(self.parent_window.devices) == 0:
            self.show_error("没有可用的设备，请在配置页面获取")
            return
        
        # 获取直播间ID
        live_id = self.live_id_input.text().strip()
        if not live_id:
            self.show_error("请先输入直播间ID")
            return
        
        if not live_id.isdigit():
            self.show_error("直播间ID格式错误，请输入纯数字")
            return
        
        # 获取配置
        multiple = self.multiple_spin.value()
        use_device_num = self.use_device_spin.value()
        proxy = self.proxy_input.text().strip() or ""
        
        # 计算实际使用的设备数
        total_devices = len(self.parent_window.devices)
        actual_use_devices = use_device_num if use_device_num > 0 else total_devices

        # 在流程中自动获取操作前数据
        self.fetch_before_data()
        
        self.log("=" * 60)
        self.log("🚀 开始刷量任务")
        self.log(f"📊 直播间ID: {live_id}")
        self.log(f"📊 Cookie数: {len(self.parent_window.cookies)}")
        self.log(f"📊 可用设备总数: {total_devices}")
        self.log(f"📊 使用设备数: {actual_use_devices}")
        self.log(f"📊 操作倍数: {multiple}")
        self.log("=" * 60)
        
        # 禁用按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.is_running = True
        
        # 创建Watch实例并启动任务（在新线程中运行）
        def run_task():
            try:
                # 使用原有的Watch逻辑
                # 仅使用所选 Cookie 跑一批设备
                chosen_cookie = self.selected_cookie or (self.parent_window.cookies[0] if self.parent_window.cookies else "")
                self.parent_window.watch_instance = Watch(
                    cookies=[chosen_cookie],
                    devices=self.parent_window.devices,
                    thread_nums=5,
                    Multiple_num=multiple,
                    tasks_per_ip=30,
                    use_device_num=use_device_num,  # 使用配置的设备数
                    log_fn=self.log,
                    proxy_type="direct" if proxy else "",
                    proxy_value=proxy,
                    live_id=live_id,
                    burst_mode="preheat"
                )
                
                # 启动任务
                self.parent_window.watch_instance._run_task(self)
                
            except Exception as e:
                self.log(f"❌ 任务执行失败: {str(e)}")
                import traceback
                traceback.print_exc()
            finally:
                # 由 Watch 内部结束时直接触发 task_finished_signal，这里无需重复发送
                pass
        
        # 启动任务线程
        task_thread = threading.Thread(target=run_task, daemon=True)
        task_thread.start()
    
    def stop_task(self):
        """停止任务"""
        self.log("⏹️ 正在停止任务...")
        self.is_running = False
        # 这里可以添加停止逻辑
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def fetch_after_data(self, live_id):
        """获取操作后数据"""
        self.log("📥 正在获取操作后数据...")
        
        try:
            url = f"https://alive-interact.alicdn.com/livedetail/common/{live_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            view_count = data.get('data', {}).get('viewCount', 0)
            if view_count == 0:
                view_count = data.get('viewCount', 0)
            
            # 同步更新顶部“当前观看数”
            self.view_count_label.setText(f"当前观看数: {view_count:,}")

            self.view_count_after = view_count
            self.view_after_label.setText(f"{view_count:,}")
            self.view_after_label.setStyleSheet("color: #107C10;")
            
            # 计算增量
            increment = view_count - self.view_count_before
            self.increment_label.setText(f"+{increment:,}")
            
            self.log(f"✅ 操作后观看数: {view_count:,}")
            self.log(f"📈 增量: +{increment:,}")
            self.log("=" * 60)
            
            self.show_success(f"任务完成！增量: +{increment:,}")
            
        except Exception as e:
            self.log(f"⚠️ 获取操作后数据失败: {str(e)}")
    
    def update_stats(self):
        """更新统计数据"""
        pass  # 可以添加实时统计更新逻辑
    
    def _log_slot(self, message):
        """日志槽函数（主线程）"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _show_success_slot(self, message):
        """成功提示槽函数（主线程）"""
        try:
            InfoBar.success(
                title="成功",
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except:
            pass  # 忽略UI错误
    
    def _show_error_slot(self, message):
        """错误提示槽函数（主线程）"""
        try:
            InfoBar.error(
                title="错误",
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        except:
            pass  # 忽略UI错误
    
    def _task_finished_slot(self, success, failed):
        """任务完成槽函数（主线程）"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # 保存成功/失败计数供后续统计使用
        self.success_count = success
        self.fail_count = failed

        # 只有任务真正执行了（有成功或失败），才获取操作后数据并输出汇总
        if success > 0 or failed > 0:
            live_id = self.live_id_input.text().strip()
            if live_id:
                # 先立即拉一次作为基线
                self.fetch_after_data(live_id)

                # 基于经验：100 次成功 ≈ 1s 传播延迟
                base_wait = max(1, math.ceil(success / 100))
                # 生成轮询节奏（秒）：适度递增，封顶每次 30s，共计不超过 ~180s
                plan = [base_wait, base_wait, base_wait * 2, base_wait * 3, base_wait * 5]
                plan = [min(30, v) for v in plan]
                # 尝试次数与规模挂钩（小单少刷新，大单多刷新），上限 8 次
                extra = min(3, max(0, math.ceil(success / 500) - 1))
                plan = plan[: 5 + extra]

                # 初始化轮询状态
                self._after_poll_active = True
                self._after_poll_intervals = plan
                self._after_poll_attempt = 0
                self._after_poll_last_increment = self.view_count_after - self.view_count_before
                self._after_poll_nochange = 0

                total_est = sum(plan)
                self.log(f"⏳ 刷新监测已启动：预计 {len(plan)} 次刷新，约 {total_est}s 内稳定")
                self._schedule_next_after_poll(live_id)

                # 标记所选 Cookie 冷却（12 小时）
                if self.selected_user_uid:
                    try:
                        save_timestamp(self.selected_user_uid)
                        self.log("🔒 已标记该Cookie进入12小时冷却")
                        # 刷新下拉可用状态
                        self.refresh_cookie_select()
                    except Exception as _:
                        pass
        else:
            self.log("⚠️ 任务未执行，跳过增量统计")
            self.log("=" * 60)

    def _schedule_next_after_poll(self, live_id):
        """按计划安排下一次操作后数据刷新（UI 线程定时）"""
        if not self._after_poll_active:
            return
        if self._after_poll_attempt >= len(self._after_poll_intervals):
            # 达到上限，输出最终统计
            increment = self.view_count_after - self.view_count_before
            self.log(f"📊 任务统计: 刷量成功={self.success_count}, 失败={self.fail_count}，直播间实际新增={increment:,}")
            self.log("=" * 60)
            self._after_poll_active = False
            return

        wait_s = self._after_poll_intervals[self._after_poll_attempt]
        self.log(f"⌛ 将在 {wait_s}s 后再次刷新观看数...")

        QTimer.singleShot(int(wait_s * 1000), lambda: self._after_poll_tick(live_id))

    def _after_poll_tick(self, live_id):
        """执行一次刷新并决定是否继续"""
        if not self._after_poll_active:
            return
        self._after_poll_attempt += 1
        self.log(f"🔄 第{self._after_poll_attempt}次刷新操作后数据...")

        # 在 UI 线程直接调用现有获取函数
        self.fetch_after_data(live_id)

        current_increment = self.view_count_after - self.view_count_before
        if current_increment == self._after_poll_last_increment:
            self._after_poll_nochange += 1
        else:
            self._after_poll_nochange = 0
            self._after_poll_last_increment = current_increment

        # 稳定策略：连续两次无变化则认为已稳定
        if self._after_poll_nochange >= 2:
            self.log("✅ 增量已稳定，停止刷新")
            self._after_poll_active = False
            increment = self.view_count_after - self.view_count_before
            self.log(f"📊 任务统计: 刷量成功={self.success_count}, 失败={self.fail_count}，直播间实际新增={increment:,}")
            self.log("=" * 60)
            return

        # 否则继续下一轮
        self._schedule_next_after_poll(live_id)
    
    def log(self, message):
        """输出日志（线程安全）"""
        self.log_signal.emit(message)
    
    def show_success(self, message):
        """显示成功提示（线程安全）"""
        self.success_signal.emit(message)
    
    def show_error(self, message):
        """显示错误提示（线程安全）"""
        self.error_signal.emit(message)


class ConfigPage(QWidget):
    """配置管理页面"""
    
    def __init__(self, parent: ClientUI):
        super().__init__(parent)
        self.setObjectName("configPage")  # 设置对象名称
        self.parent_window = parent
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = TitleLabel("配置管理")
        layout.addWidget(title)
        
        # API配置卡片
        api_card = self.create_api_config_card()
        layout.addWidget(api_card)
        
        # Cookie管理卡片
        cookie_card = self.create_cookie_card()
        layout.addWidget(cookie_card)
        
        # 设备管理卡片
        device_card = self.create_device_card()
        layout.addWidget(device_card)
        
        layout.addStretch()
    
    def create_api_config_card(self):
        """创建API配置卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel("🔐 云端配置")
        layout.addWidget(title)
        
        # API地址
        api_layout = QHBoxLayout()
        api_label = BodyLabel("API地址:")
        api_label.setFixedWidth(100)
        api_layout.addWidget(api_label)
        
        self.api_url_input = LineEdit()
        self.api_url_input.setText("http://localhost:5000")
        api_layout.addWidget(self.api_url_input)
        
        layout.addLayout(api_layout)
        
        # 客户端密钥
        key_layout = QHBoxLayout()
        key_label = BodyLabel("客户端密钥:")
        key_label.setFixedWidth(100)
        key_layout.addWidget(key_label)
        
        self.client_key_input = LineEdit()
        self.client_key_input.setPlaceholderText("例如：client_key_001")
        key_layout.addWidget(self.client_key_input)
        
        save_btn = PrimaryPushButton(FIF.SAVE, "保存")
        save_btn.clicked.connect(self.save_api_config)
        save_btn.setFixedWidth(100)
        key_layout.addWidget(save_btn)
        
        layout.addLayout(key_layout)
        
        return card
    
    def create_cookie_card(self):
        """创建Cookie管理卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_layout = QHBoxLayout()
        title = SubtitleLabel("🍪 Cookie管理")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        count_label = BodyLabel(f"当前数量: {len(self.parent_window.cookies)}")
        self.cookie_count_label = count_label
        title_layout.addWidget(count_label)
        
        layout.addLayout(title_layout)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        # 手动输入
        manual_btn = PushButton(FIF.EDIT, "手动输入")
        manual_btn.clicked.connect(self.manual_input_cookie)
        button_layout.addWidget(manual_btn)
        
        # 从文件导入
        import_btn = PushButton(FIF.FOLDER, "从文件导入")
        import_btn.clicked.connect(self.import_cookie_from_file)
        button_layout.addWidget(import_btn)
        
        # 远程拉取
        fetch_btn = PrimaryPushButton(FIF.CLOUD_DOWNLOAD, "远程拉取")
        fetch_btn.clicked.connect(self.fetch_cookie_from_api)
        button_layout.addWidget(fetch_btn)
        
        # 清空
        clear_btn = TransparentPushButton(FIF.DELETE, "清空")
        clear_btn.clicked.connect(self.clear_cookies)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Cookie预览
        self.cookie_preview = TextEdit()
        self.cookie_preview.setReadOnly(True)
        self.cookie_preview.setMaximumHeight(150)
        self.cookie_preview.setPlaceholderText("Cookie列表预览...")
        layout.addWidget(self.cookie_preview)
        
        return card
    
    def create_device_card(self):
        """创建设备管理卡片"""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_layout = QHBoxLayout()
        title = SubtitleLabel("📱 设备管理")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        count_label = BodyLabel(f"当前数量: {len(self.parent_window.devices)}")
        self.device_count_label = count_label
        title_layout.addWidget(count_label)
        
        layout.addLayout(title_layout)
        
        # 按钮行
        button_layout = QHBoxLayout()
        
        # 从文件导入
        import_btn = PushButton(FIF.FOLDER, "从文件导入")
        import_btn.clicked.connect(self.import_device_from_file)
        button_layout.addWidget(import_btn)
        
        # 远程拉取（主要方式）
        fetch_btn = PrimaryPushButton(FIF.CLOUD_DOWNLOAD, "远程拉取")
        fetch_btn.clicked.connect(self.fetch_device_from_api)
        button_layout.addWidget(fetch_btn)
        
        # 清空
        clear_btn = TransparentPushButton(FIF.DELETE, "清空")
        clear_btn.clicked.connect(self.clear_devices)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 设备预览
        self.device_preview = TextEdit()
        self.device_preview.setReadOnly(True)
        self.device_preview.setMaximumHeight(150)
        self.device_preview.setPlaceholderText("设备列表预览...")
        layout.addWidget(self.device_preview)
        
        return card
    
    def save_api_config(self):
        """保存API配置"""
        self.parent_window.client_key = self.client_key_input.text().strip()
        self.parent_window.api_url = self.api_url_input.text().strip()
        
        if self.parent_window.save_config():
            self.show_success("云端配置保存成功")
        else:
            self.show_error("云端配置保存失败")
    
    def manual_input_cookie(self):
        """手动输入Cookie"""
        from PyQt5.QtWidgets import QDialog, QTextEdit, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("手动输入Cookie")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        label = BodyLabel("每行一个Cookie:")
        layout.addWidget(label)
        
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("粘贴Cookie内容，每行一个...")
        layout.addWidget(text_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_():
            cookies_text = text_edit.toPlainText().strip()
            if cookies_text:
                new_cookies = [line.strip() for line in cookies_text.split('\n') if line.strip()]
                merged = (self.parent_window.cookies or []) + new_cookies
                deduped = self._deduplicate_cookies_by_uid(merged)
                replaced = len(merged) - len(deduped)
                self.parent_window.cookies = deduped
                self.parent_window.save_config()
                self.update_cookie_display()
                self.show_success(f"已去重：新增 {len(new_cookies)} 条，覆盖 {replaced} 条重复")
    
    def import_cookie_from_file(self):
        """从文件导入Cookie"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Cookie文件",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    new_cookies = [line.strip() for line in f if line.strip()]
                merged = (self.parent_window.cookies or []) + new_cookies
                deduped = self._deduplicate_cookies_by_uid(merged)
                replaced = len(merged) - len(deduped)
                self.parent_window.cookies = deduped
                self.parent_window.save_config()
                self.update_cookie_display()
                self.show_success(f"已去重：新增 {len(new_cookies)} 条，覆盖 {replaced} 条重复")
                
            except Exception as e:
                self.show_error(f"导入失败: {str(e)}")
    
    def fetch_cookie_from_api(self):
        """从API远程拉取Cookie"""
        if not self.parent_window.client_key:
            self.show_error("请先配置客户端密钥")
            return
        
        try:
            # 自动处理 URL 末尾斜杠
            api_url = self.parent_window.api_url.rstrip('/')
            url = f"{api_url}/api/fetch_cookies"
            data = {
                'client_key': self.parent_window.client_key,
                'limit': 100
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                cookies = [item['cookie'] for item in result.get('data', [])]
                merged = (self.parent_window.cookies or []) + cookies
                deduped = self._deduplicate_cookies_by_uid(merged)
                replaced = len(merged) - len(deduped)
                self.parent_window.cookies = deduped
                self.parent_window.save_config()
                self.update_cookie_display()
                self.show_success(f"成功拉取 {len(cookies)} 个，覆盖 {replaced} 条重复")
            else:
                self.show_error(f"拉取失败: {result.get('message')}")
                
        except Exception as e:
            self.show_error(f"拉取失败: {str(e)}")
    
    # ===== 工具方法：按 unb 去重，后导入覆盖先导入 =====
    def _deduplicate_cookies_by_uid(self, cookies):
        """按用户 unb 去重；后出现的覆盖先出现的，保持外在顺序"""
        if not cookies:
            return []
        uid_to_cookie = {}
        # 逆序保留“最后一次出现”
        for c in reversed(cookies):
            c2 = tools.replace_cookie_item(c, "sgcookie", None)
            u = User(c2)
            uid = u.uid or ("__no_uid__:" + c[:80])
            if uid not in uid_to_cookie:
                uid_to_cookie[uid] = c
        # 还原顺序
        return list(reversed(list(uid_to_cookie.values())))
    
    def clear_cookies(self):
        """清空Cookie"""
        self.parent_window.cookies = []
        self.parent_window.save_config()
        self.update_cookie_display()
        self.show_success("Cookie已清空")
    
    def import_device_from_file(self):
        """从文件导入设备"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择设备文件",
            "",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    devices = [line.strip() for line in f if line.strip()]
                
                self.parent_window.devices.extend(devices)
                self.parent_window.save_config()
                self.update_device_display()
                self.show_success(f"成功导入 {len(devices)} 个设备")
                
            except Exception as e:
                self.show_error(f"导入失败: {str(e)}")
    
    def fetch_device_from_api(self):
        """从API远程拉取设备"""
        if not self.parent_window.client_key:
            self.show_error("请先配置客户端密钥")
            return
        
        try:
            # 自动处理 URL 末尾斜杠
            api_url = self.parent_window.api_url.rstrip('/')
            url = f"{api_url}/api/fetch_devices"
            data = {
                'client_key': self.parent_window.client_key,
                'limit': 100
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                devices = [item['device_string'] for item in result.get('data', [])]
                self.parent_window.devices = devices
                self.parent_window.save_config()
                self.update_device_display()
                self.show_success(f"成功拉取 {len(devices)} 个设备")
            else:
                self.show_error(f"拉取失败: {result.get('message')}")
                
        except Exception as e:
            self.show_error(f"拉取失败: {str(e)}")
    
    def clear_devices(self):
        """清空设备"""
        self.parent_window.devices = []
        self.parent_window.save_config()
        self.update_device_display()
        self.show_success("设备已清空")
    
    def update_cookie_display(self):
        """更新Cookie显示"""
        self.cookie_count_label.setText(f"当前数量: {len(self.parent_window.cookies)}")
        
        # 显示前5个Cookie的预览
        preview_text = ""
        for i, cookie in enumerate(self.parent_window.cookies[:5]):
            preview_text += f"{i+1}. {cookie[:80]}...\n"
        
        if len(self.parent_window.cookies) > 5:
            preview_text += f"\n...还有 {len(self.parent_window.cookies) - 5} 个"
        
        self.cookie_preview.setText(preview_text)
        
        # 更新主页面显示
        self.parent_window.main_page.update_data_display()
        # 刷新主页面 Cookie 下拉
        if hasattr(self.parent_window, 'main_page'):
            self.parent_window.main_page.refresh_cookie_select()
    
    def update_device_display(self):
        """更新设备显示"""
        self.device_count_label.setText(f"当前数量: {len(self.parent_window.devices)}")
        
        # 显示前5个设备的预览
        preview_text = ""
        for i, device in enumerate(self.parent_window.devices[:5]):
            preview_text += f"{i+1}. {device[:80]}...\n"
        
        if len(self.parent_window.devices) > 5:
            preview_text += f"\n...还有 {len(self.parent_window.devices) - 5} 个"
        
        self.device_preview.setText(preview_text)
        
        # 更新主页面显示
        self.parent_window.main_page.update_data_display()
    
    def show_success(self, message):
        """显示成功提示"""
        InfoBar.success(
            title="成功",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def show_error(self, message):
        """显示错误提示"""
        InfoBar.error(
            title="错误",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )


if __name__ == '__main__':
    import sys
    
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    # 设置主题
    setTheme(Theme.AUTO)
    
    window = ClientUI()
    window.show()
    
    sys.exit(app.exec_())

