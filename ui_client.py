"""
淘宝直播刷量客户端 - 简化版UI
专为工人傻瓜式操作设计，去掉设备采集功能
"""

import os
import json
import logging
import threading
import requests
import re
import time
import math
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QFileDialog, QTextEdit, QFrame, QLabel, QScrollArea
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
from database import filter_available, save_timestamp, mark_cookies_banned, is_cookie_banned
from model.user import User
import tools


def setup_logging():
    """配置日志系统"""
    # 创建logs目录（如果不存在）
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 日志文件名：按日期命名
    log_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f'ui_client_{log_date}.log')
    error_log_file = os.path.join(logs_dir, f'error_{log_date}.log')
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 清除已有的处理器（避免重复添加）
    logger.handlers.clear()
    
    # 文件处理器：所有日志（INFO及以上）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)
    
    # 错误文件处理器：只记录错误和异常（ERROR及以上）
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(error_handler)
    
    # 控制台处理器：DEBUG及以上（可选，保留控制台输出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    return logger


# 初始化日志
logger = setup_logging()


class ClientUI(FluentWindow):
    """刷量客户端主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("淘宝直播刷量客户端 v1.0")
        self.resize(1200, 1000)
        
        # 数据存储
        self.cookies = []  # Cookie列表
        self.devices = []  # 设备列表
        self.device_ids = {}  # 设备字符串到设备ID的映射（用于锁定）
        self.cookie_ids = {}  # Cookie UID到Cookie ID的映射（用于标记封禁）
        self.client_key = ""  # 客户端密钥
        self.api_url = "http://localhost:5000"  # API地址
        self.proxy = ""  # 代理地址
        self.tasks_per_ip = 30  # 代理分配任务数（默认30）
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
                    self.proxy = config.get('proxy', '')
                    self.tasks_per_ip = config.get('tasks_per_ip', 30)
                    # 加载设备ID映射（如果存在）
                    if 'device_ids' in config:
                        self.device_ids = config.get('device_ids', {})
                        logger.info(f"[加载] 已加载 {len(self.device_ids)} 个设备ID映射")
                    else:
                        self.device_ids = {}
                    
                    # 加载Cookie ID映射（如果存在）
                    if 'cookie_ids' in config:
                        self.cookie_ids = config.get('cookie_ids', {})
                        logger.info(f"[加载] 已加载 {len(self.cookie_ids)} 个Cookie ID映射")
                    else:
                        self.cookie_ids = {}
                    
                    # 更新配置页面
                    self.config_page.client_key_input.setText(self.client_key)
                    self.config_page.api_url_input.setText(self.api_url)
                    
                    # 更新主页面代理输入框和代理分配任务数
                    self.main_page.proxy_input.setText(self.proxy)
                    self.main_page.tasks_per_ip_spin.setValue(self.tasks_per_ip)
                    
                    # 更新主页面显示
                    self.main_page.update_data_display()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 保存前先从主页面获取最新的代理值和代理分配任务数
            self.proxy = self.main_page.proxy_input.text().strip()
            self.tasks_per_ip = self.main_page.tasks_per_ip_spin.value()
            
            config = {
                'client_key': self.client_key,
                'api_url': self.api_url,
                'cookies': self.cookies,
                'devices': self.devices,
                'proxy': self.proxy,
                'tasks_per_ip': self.tasks_per_ip,
                'device_ids': self.device_ids,  # 保存设备ID映射（用于锁定）
                'cookie_ids': self.cookie_ids  # 保存Cookie ID映射（用于标记封禁）
            }
            with open('client_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
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
        self.task_started_at = None  # 任务开始时间
        
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
        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 创建内容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
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
        
        # 添加弹性空间
        layout.addStretch()
        
        # 将内容容器放入滚动区域
        scroll_area.setWidget(content_widget)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
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
        
        # 第三行：代理分配任务数
        config_layout2_5 = QHBoxLayout()
        tasks_per_ip_label = BodyLabel("代理分配任务数:")
        tasks_per_ip_label.setFixedWidth(100)
        config_layout2_5.addWidget(tasks_per_ip_label)
        
        self.tasks_per_ip_spin = SpinBox()
        self.tasks_per_ip_spin.setMinimum(1)
        self.tasks_per_ip_spin.setMaximum(1000)
        self.tasks_per_ip_spin.setValue(30)
        self.tasks_per_ip_spin.setFixedWidth(120)
        # 值变化时自动保存
        self.tasks_per_ip_spin.valueChanged.connect(lambda: self.parent_window.save_config())
        config_layout2_5.addWidget(self.tasks_per_ip_spin)
        
        hint_label2 = CaptionLabel("(每个代理IP分配的任务数，默认30)")
        hint_label2.setStyleSheet("color: #888;")
        config_layout2_5.addWidget(hint_label2)
        config_layout2_5.addStretch()
        layout.addLayout(config_layout2_5)
        
        # 第四行：代理设置
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
            # 检查是否被封禁
            is_banned = is_cookie_banned(u.uid)
            
            # 获取昵称并解码 Unicode 转义序列（仅用于显示）
            nick = u.nickname or "(无昵称)"
            if nick != "(无昵称)":
                try:
                    # 解码 \uXXXX 格式的 Unicode 编码
                    nick = nick.encode('utf-8').decode('unicode_escape')
                except:
                    try:
                        # 兼容处理
                        nick = nick.encode('latin1').decode('unicode_escape')
                    except:
                        pass  # 解码失败就保持原样
            
            # 优先级：封禁 > 冷却中 > 可用
            if is_banned:
                tag = "封禁"
            elif is_free:
                tag = "可用"
            else:
                tag = "冷却中"
            
            display = f"{nick}  unb={u.uid}  [{tag}]"
            self.cookie_select.addItem(display)
            self._cookie_options.append((display, c, u.uid))

        # 默认选择第一个"可用"的（排除被封禁的）；若没有，则第一个非封禁的
        default_index = 0
        for idx, (_, c, uid) in enumerate(self._cookie_options):
            # 只选择可用且未被封禁的
            if uid in available_uids and not is_cookie_banned(uid):
                default_index = idx
                break
        
        # 如果没有可用的，至少选择一个非封禁的
        if default_index == 0:
            for idx, (_, c, uid) in enumerate(self._cookie_options):
                if not is_cookie_banned(uid):
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
        tasks_per_ip = self.tasks_per_ip_spin.value()
        
        # 保存配置（包括代理分配任务数）
        self.parent_window.save_config()
        
        # 判断代理类型（与ui.py保持一致）
        if not proxy:
            proxy_type = ""
            proxy_value = ""
        elif proxy.startswith(('http://', 'https://')):
            # 如果是完整URL且包含参数（可能是代理API），使用url模式
            if '?' in proxy or 'key=' in proxy or '.txt' in proxy:
                proxy_type = "url"
                proxy_value = proxy
            else:
                # 否则是直接代理地址
                proxy_type = "direct"
                proxy_value = proxy
        else:
            # 其他情况（可能是API参数），也使用url模式
            proxy_type = "url"
            proxy_value = proxy
        
        # ===== 优先使用本地资源，服务器模式用于锁定 =====
        use_server_mode = False  # 标记是否使用服务器模式
        
        # 检查是否有本地资源
        has_local_data = len(self.parent_window.cookies) > 0 and len(self.parent_window.devices) > 0
        
        # 如果配置了API且有本地数据，使用服务器锁定模式
        if has_local_data and self.parent_window.client_key and self.parent_window.api_url:
            # 使用本地资源 + 服务器锁定模式
            self.log("🔄 使用本地资源（服务器锁定模式）...")
            
            # 使用本地缓存的资源
            chosen_cookie = self.selected_cookie or (self.parent_window.cookies[0] if self.parent_window.cookies else "")
            self.task_cookies = [chosen_cookie]
            
            # 传入所有设备，由Watch自动过滤冷却期并选取可用的
            self.task_devices = self.parent_window.devices
            
            # 标记为服务器模式（预热后会锁定）
            use_server_mode = True
            
            # 检查device_ids映射是否存在（应该在拉取设备时已经建立）
            if not self.parent_window.device_ids or len(self.parent_window.device_ids) == 0:
                logger.warning("[警告] device_ids映射为空，锁定功能可能不可用。请重新从服务器拉取设备。")
            
            # 显示目标使用数量
            if use_device_num > 0:
                self.log(f"✅ 本地资源：{len(self.task_cookies)} 个Cookie，{len(self.task_devices)} 个设备池（目标使用 {use_device_num} 个，自动过滤冷却期）")
            else:
                self.log(f"✅ 本地资源：{len(self.task_cookies)} 个Cookie，{len(self.task_devices)} 个设备（全部使用，自动过滤冷却期）")
        
        # 如果没有本地数据，提示用户拉取
        if not use_server_mode:
            # 检查本地数据
            if len(self.parent_window.cookies) == 0:
                self.show_error("没有可用的Cookie，请在配置页面导入或从服务器拉取")
                return
            
            if len(self.parent_window.devices) == 0:
                self.show_error("没有可用的设备，请在配置页面导入或从服务器拉取")
                return
            
            # 纯本地模式（无服务器锁定）
            self.log("🔄 使用纯本地模式（无服务器锁定）...")
            chosen_cookie = self.selected_cookie or (self.parent_window.cookies[0] if self.parent_window.cookies else "")
            self.task_cookies = [chosen_cookie]
            
            # 传入所有设备，由Watch自动过滤冷却期并选取可用的
            self.task_devices = self.parent_window.devices
            
            total_devices = len(self.parent_window.devices)
            
            # 显示目标使用数量
            if use_device_num > 0:
                self.log(f"✅ 本地模式：使用 {len(self.task_cookies)} 个Cookie，{total_devices} 个设备池（目标使用 {use_device_num} 个，自动过滤冷却期）")
            else:
                self.log(f"✅ 本地模式：使用 {len(self.task_cookies)} 个Cookie，{total_devices} 个设备（全部使用，自动过滤冷却期）")
        
        # 标记使用的模式（用于任务结束时判断是否需要释放）
        self.using_server_mode = use_server_mode
        
        # 初始化任务资源ID（预热完成后会更新）
        self.task_device_ids = []
        self.task_cookie_ids = []
        
        # 记录任务开始时间
        from datetime import datetime
        self.task_started_at = datetime.now()

        # 在流程中自动获取操作前数据
        self.fetch_before_data()
        
        self.log("=" * 60)
        self.log("🚀 开始刷量任务")
        self.log(f"📊 模式: {'服务器模式（多客户端）' if use_server_mode else '本地模式（单机）'}")
        self.log(f"📊 直播间ID: {live_id}")
        self.log(f"📊 Cookie数: {len(self.task_cookies)}")
        self.log(f"📊 设备数: {len(self.task_devices)}")
        self.log(f"📊 操作倍数: {multiple}")
        if proxy_type and proxy_value:
            self.log(f"📊 代理模式: {proxy_type} - {'API模式' if proxy_type == 'url' else '直接代理'}")
            if proxy_type == "url":
                self.log(f"📊 代理配置: {proxy_value[:50]}..." if len(proxy_value) > 50 else f"📊 代理配置: {proxy_value}")
            else:
                self.log(f"📊 代理地址: {proxy_value}")
        else:
            self.log("📊 代理模式: 不使用代理")
        self.log("=" * 60)
        
        # 禁用按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.is_running = True
        
        # 预热完成回调：锁定资源
        def on_preheat_complete_callback(used_device_strings, used_cookie_uids=None):
            """预热完成回调：锁定实际使用的设备和Cookie"""
            if not use_server_mode:
                return  # 本地模式不需要锁定
            
            try:
                logger.info(f"[锁定] 开始锁定资源，收到 {len(used_device_strings)} 个设备，{len(used_cookie_uids or [])} 个Cookie")
                
                # ===== 1. 锁定设备 =====
                device_ids = []
                if used_device_strings:
                    # 检查device_ids映射是否存在（应该已经在任务开始时获取）
                    if not hasattr(self.parent_window, 'device_ids') or not self.parent_window.device_ids:
                        logger.warning("[锁定] ⚠️ device_ids映射为空，无法锁定设备（任务开始时应该已经获取）")
                        self.log("⚠️ 无法锁定设备：设备ID映射未建立")
                    else:
                        # 将设备字符串转换为设备ID
                        device_ids_map = {}
                        for dev_str in used_device_strings:
                            dev_str_clean = dev_str.strip()  # 去除首尾空格和换行
                            logger.debug(f"[锁定] 查找设备: {dev_str_clean[:80]}...")
                            
                            # 尝试精确匹配
                            if dev_str_clean in self.parent_window.device_ids:
                                dev_id = self.parent_window.device_ids[dev_str_clean]
                                if dev_id:
                                    device_ids_map[dev_str_clean] = dev_id
                                    logger.debug(f"[锁定] ✓ 找到设备ID: {dev_id}")
                                else:
                                    logger.warning(f"[锁定] ✗ 设备ID为空")
                            else:
                                # 尝试模糊匹配（处理可能的格式差异）
                                found = False
                                for stored_dev_str, stored_dev_id in self.parent_window.device_ids.items():
                                    stored_dev_str_clean = stored_dev_str.strip()
                                    if stored_dev_str_clean == dev_str_clean:
                                        device_ids_map[dev_str_clean] = stored_dev_id
                                        logger.debug(f"[锁定] ✓ 模糊匹配找到设备ID: {stored_dev_id}")
                                        found = True
                                        break
                                if not found:
                                    logger.warning(f"[锁定] ✗ 未找到匹配的设备")
                                    if len(self.parent_window.device_ids) > 0:
                                        sample_keys = list(self.parent_window.device_ids.keys())[:3]
                                        logger.debug(f"[锁定] device_ids字典中有 {len(self.parent_window.device_ids)} 个key，示例: {sample_keys}")
                        
                        device_ids = list(device_ids_map.values())
                        logger.info(f"[锁定] 总共找到 {len(device_ids)} 个设备ID")
                
                # ===== 2. 锁定Cookie（只有云端拉取的Cookie才有ID，本地导入的没有）=====
                cookie_ids = []
                if used_cookie_uids:
                    # 检查cookie_ids映射是否存在（只有云端拉取的Cookie才有映射）
                    if hasattr(self.parent_window, 'cookie_ids') and self.parent_window.cookie_ids:
                        for uid in used_cookie_uids:
                            cookie_id = self.parent_window.cookie_ids.get(uid)
                            if cookie_id:
                                cookie_ids.append(cookie_id)
                                logger.debug(f"[锁定] ✓ 找到Cookie ID: {cookie_id} (UID: {uid[:10]}...)")
                            else:
                                logger.debug(f"[锁定] Cookie UID {uid[:10]}... 没有ID映射（可能是本地导入的），跳过锁定")
                        
                        if cookie_ids:
                            logger.info(f"[锁定] 总共找到 {len(cookie_ids)} 个Cookie ID（云端拉取的）")
                        else:
                            logger.info(f"[锁定] 所有Cookie都是本地导入的，无需锁定")
                    else:
                        logger.info(f"[锁定] Cookie ID映射为空（所有Cookie都是本地导入的），无需锁定")
                
                # ===== 3. 调用锁定接口 =====
                if device_ids or cookie_ids:
                    logger.info(f"[锁定] 调用锁定接口，锁定 {len(cookie_ids)} 个Cookie，{len(device_ids)} 个设备...")
                    api_url = self.parent_window.api_url.rstrip('/')
                    response = requests.post(
                        f"{api_url}/api/lock_resources",
                        json={
                            'client_key': self.parent_window.client_key,
                            'cookie_ids': cookie_ids,
                            'device_ids': device_ids
                        },
                        timeout=15
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result.get('success'):
                        data = result.get('data', {})
                        locked_cookies = data.get('locked_cookies', 0)
                        locked_devices = data.get('locked_devices', 0)
                        
                        msg_parts = []
                        if locked_cookies > 0:
                            msg_parts.append(f"{locked_cookies} 个Cookie")
                        if locked_devices > 0:
                            msg_parts.append(f"{locked_devices} 个设备")
                        
                        if msg_parts:
                            msg = f"🔒 已锁定 {'和'.join(msg_parts)}（防止其他客户端使用）"
                            self.log(msg)
                            logger.info(f"[锁定] 锁定成功: {locked_cookies} 个Cookie，{locked_devices} 个设备")
                        
                        # 保存锁定的资源ID，用于任务结束时释放
                        self.task_device_ids = device_ids
                        self.task_cookie_ids = cookie_ids
                    else:
                        error_msg = result.get('message', '未知错误')
                        self.log(f"⚠️ 锁定资源失败: {error_msg}")
                        logger.error(f"[锁定] 锁定失败: {error_msg}")
                else:
                    self.log("⚠️ 没有需要锁定的资源（可能都是本地导入的）")
                    logger.info(f"[锁定] 没有需要锁定的资源")
                    # 即使没有锁定，也要保存空列表（用于释放时判断）
                    self.task_device_ids = []
                    self.task_cookie_ids = []
                    
            except requests.exceptions.RequestException as e:
                self.log(f"⚠️ 锁定资源时网络错误: {str(e)}")
                logger.error(f"[锁定] 网络错误: {str(e)}", exc_info=True)
                import traceback
                traceback.print_exc()
            except Exception as e:
                self.log(f"⚠️ 锁定资源时出错: {str(e)}")
                logger.error(f"[锁定] 异常: {str(e)}", exc_info=True)
                import traceback
                traceback.print_exc()
        
        # 创建Watch实例并启动任务（在新线程中运行）
        def run_task():
            try:
                # ===== 使用申请到的或本地的资源运行任务 =====
                self.parent_window.watch_instance = Watch(
                    cookies=self.task_cookies,
                    devices=self.task_devices,
                    thread_nums=5,
                    Multiple_num=multiple,
                    tasks_per_ip=tasks_per_ip,  # 使用UI配置的值
                    use_device_num=use_device_num,  # 由Watch自动从设备池中过滤并选取可用设备
                    log_fn=self.log,
                    proxy_type=proxy_type,
                    proxy_value=proxy_value,
                    live_id=live_id,
                    burst_mode="preheat",
                    on_preheat_complete=on_preheat_complete_callback  # 预热完成回调
                )
                
                # 启动任务（任务执行期间不访问数据库）
                self.parent_window.watch_instance._run_task(self)
                
            except Exception as e:
                self.log(f"❌ 任务执行失败: {str(e)}")
                import traceback
                traceback.print_exc()
                # 任务异常失败时，也要释放资源
                # 注意：如果预热完成回调已经执行，task_device_ids已设置；如果没有，则无需释放
                # 释放逻辑会在task_finished_signal中统一处理
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

        # ===== 检测并标记 robot Cookie（任务完成后）=====
        def mark_robot_cookies():
            """标记出现 robot 错误的 Cookie 为被封禁"""
            try:
                # 从 Watch 实例获取出现 robot 错误的 Cookie UID
                robot_cookie_uids = []
                if hasattr(self.parent_window, 'watch_instance') and self.parent_window.watch_instance:
                    watch_instance = self.parent_window.watch_instance
                    if hasattr(watch_instance, 'robot_cookies'):
                        # robot_cookies 是一个 set，即使没有元素也是存在的
                        if watch_instance.robot_cookies and len(watch_instance.robot_cookies) > 0:
                            robot_cookie_uids = list(watch_instance.robot_cookies)
                            logger.info(f"[Cookie检测] 从 Watch 实例获取到 {len(robot_cookie_uids)} 个 robot Cookie UID")
                        else:
                            logger.debug(f"[Cookie检测] Watch 实例中没有 robot Cookie（robot_cookies 为空或为 None）")
                else:
                    logger.warning(f"[Cookie检测] Watch 实例不存在，无法获取 robot Cookie")
                
                if not robot_cookie_uids:
                    logger.debug(f"[Cookie检测] 没有需要标记的 robot Cookie（robot_cookies 为空）")
                    # 在 UI 中也显示一下，方便调试
                    self.log(f"ℹ️ 本次任务没有检测到 robot 错误，Cookie 状态正常")
                    return  # 没有 robot cookies，无需处理
                
                logger.info(f"[Cookie检测] 检测到 {len(robot_cookie_uids)} 个 Cookie 出现 robot 错误，开始标记...")
                self.log(f"⚠️ 检测到 {len(robot_cookie_uids)} 个 Cookie 出现 robot 错误，正在标记为封禁...")
                
                # 1. 本地标记为被封禁（无论云端还是本地模式都要保存）
                marked_count = mark_cookies_banned(robot_cookie_uids)
                if marked_count > 0:
                    self.log(f"🔒 已在本地标记 {marked_count} 个 Cookie 为封禁状态（robot 检测）")
                    logger.info(f"[Cookie检测] 已在本地标记 {marked_count} 个 Cookie 为封禁状态")
                
                # 2. 如果是云端模式，同时更新服务器状态（status=2 表示封禁）
                if hasattr(self, 'using_server_mode') and self.using_server_mode:
                    if hasattr(self.parent_window, 'client_key') and hasattr(self.parent_window, 'api_url') and self.parent_window.client_key and self.parent_window.api_url:
                        try:
                            api_url = self.parent_window.api_url.rstrip('/')
                            
                            # 根据 Cookie UID 查找对应的 Cookie ID（使用已保存的映射）
                            cookie_ids_to_update = []
                            if hasattr(self.parent_window, 'cookie_ids') and self.parent_window.cookie_ids:
                                for uid in robot_cookie_uids:
                                    cookie_id = self.parent_window.cookie_ids.get(uid)
                                    if cookie_id:
                                        cookie_ids_to_update.append(cookie_id)
                            
                            # 如果有 Cookie ID，批量更新服务器状态
                            if cookie_ids_to_update:
                                updated_count = 0
                                for cookie_id in cookie_ids_to_update:
                                    try:
                                        response = requests.post(
                                            f"{api_url}/api/update_cookie_status",
                                            json={
                                                'client_key': self.parent_window.client_key,
                                                'cookie_id': cookie_id,
                                                'status': 2  # 2=封禁
                                            },
                                            timeout=10
                                        )
                                        response.raise_for_status()
                                        result = response.json()
                                        if result.get('success'):
                                            updated_count += 1
                                    except Exception as e:
                                        logger.warning(f"[Cookie检测] 更新Cookie状态失败 (ID: {cookie_id}): {str(e)}")
                                
                                if updated_count > 0:
                                    self.log(f"🔒 云端模式：已在服务器标记 {updated_count} 个 Cookie 为封禁状态")
                                    logger.info(f"[Cookie检测] 云端模式：已在服务器标记 {updated_count} 个 Cookie 为封禁状态")
                                else:
                                    self.log(f"⚠️ 云端模式：服务器更新失败（本地已标记）")
                            else:
                                self.log(f"ℹ️ 云端模式：未找到 Cookie ID 映射（本地导入的 Cookie），仅做本地标记")
                                logger.info(f"[Cookie检测] 云端模式：未找到 Cookie ID 映射，仅做本地标记")
                            
                        except Exception as e:
                            logger.error(f"[Cookie检测] 更新服务器状态时出错: {str(e)}", exc_info=True)
                            self.log(f"⚠️ 更新服务器状态失败（本地已标记）: {str(e)}")
                
                # 3. 刷新 Cookie 下拉列表（排除被封禁的 Cookie）
                self.refresh_cookie_select()
                
                self.log(f"✅ Cookie 封禁标记完成：{marked_count} 个 Cookie 已标记，下次使用时将自动排除")
                
            except Exception as e:
                logger.error(f"[Cookie检测] 标记 robot Cookie 时出错: {str(e)}", exc_info=True)
                self.log(f"⚠️ 标记 Cookie 封禁状态时出错: {str(e)}")
        
        # 在后台线程标记 robot Cookie（不影响UI响应）
        threading.Thread(target=mark_robot_cookies, daemon=True).start()

        # ===== 任务结束后：释放资源（仅服务器模式）=====
        def release_resources_async():
            # 只有服务器模式才需要释放资源
            if hasattr(self, 'using_server_mode') and self.using_server_mode:
                # 即使任务失败，也要释放资源（只要有锁定的资源）
                task_cookie_ids = getattr(self, 'task_cookie_ids', [])
                task_device_ids = getattr(self, 'task_device_ids', [])
                
                if task_cookie_ids or task_device_ids:
                    try:
                        api_url = self.parent_window.api_url.rstrip('/')
                        response = requests.post(
                            f"{api_url}/api/release_resources",
                            json={
                                'client_key': self.parent_window.client_key,
                                'cookie_ids': task_cookie_ids,
                                'device_ids': task_device_ids,
                                'cooldown_hours': 12
                            },
                            timeout=15
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if result.get('success'):
                            self.log(f"✅ {result.get('message')}")
                            logger.info(f"[释放] 释放成功: {result.get('message')}")
                        else:
                            self.log(f"⚠️ 释放资源失败: {result.get('message')}")
                            logger.error(f"[释放] 释放失败: {result.get('message')}")
                            
                    except Exception as e:
                        self.log(f"⚠️ 释放资源时出错: {str(e)}")
                        logger.error(f"[释放] 释放时出错: {str(e)}", exc_info=True)
                else:
                    # 没有锁定的资源，可能都是本地导入的或预热失败
                    logger.info(f"[释放] 没有需要释放的资源（可能都是本地导入的或预热失败）")
            else:
                # 本地模式：使用本地冷却逻辑
                if hasattr(self, 'selected_user_uid') and self.selected_user_uid:
                    try:
                        from database import save_timestamp
                        save_timestamp(self.selected_user_uid)
                        self.log("🔒 已标记该Cookie进入12小时冷却（本地）")
                        # 刷新下拉可用状态
                        self.refresh_cookie_select()
                    except Exception as e:
                        pass
        
        # 在后台线程释放资源（不影响UI响应）
        release_thread = threading.Thread(target=release_resources_async, daemon=True)
        release_thread.start()
        
        # ===== 任务完成后：刷新可用数量（UI展示）=====
        def refresh_available_count():
            """刷新界面显示的可用Cookie和设备数量"""
            # 等待释放完成
            release_thread.join(timeout=5)
            
            # 如果配置了API，重新拉取可用数量
            if self.parent_window.client_key and self.parent_window.api_url:
                try:
                    api_url = self.parent_window.api_url.rstrip('/')
                    # 刷新时拉取所有 Cookie（包括冷却期的），用于完整显示
                    # 使用 include_cooldown=true 参数，获取所有 is_locked=0 的 Cookie
                    response = requests.post(
                        f"{api_url}/api/allocate_resources",
                        json={
                            'client_key': self.parent_window.client_key,
                            'cookie_count': 0,  # 获取所有
                            'device_count': 0,  # 获取所有
                            'include_cooldown': True  # 包含冷却期的 Cookie（用于完整显示）
                        },
                        timeout=10
                    )
                    result = response.json()
                    
                    if result.get('success'):
                        data = result.get('data', {})
                        cookies_data = data.get('cookies', [])
                        devices_data = data.get('devices', [])
                        
                        # ===== 合并本地 Cookie 和服务器 Cookie（保留本地导入的）=====
                        server_cookies = [c['cookie'] for c in cookies_data]
                        server_cookie_uids = set()
                        for c in cookies_data:
                            uid = c.get('uid')
                            if uid:
                                server_cookie_uids.add(uid)
                        
                        # 获取当前本地 Cookie 列表
                        local_cookies = self.parent_window.cookies or []
                        
                        # 提取本地 Cookie 的 UID（用于判断哪些是本地导入的）
                        local_cookie_uids = set()
                        for cookie_str in local_cookies:
                            try:
                                cookie_normalized = tools.replace_cookie_item(cookie_str, "sgcookie", None)
                                user = User(cookie_normalized)
                                if user and user.uid:
                                    local_cookie_uids.add(user.uid)
                            except:
                                continue
                        
                        # 保留本地导入的 Cookie（不在服务器上的）
                        local_only_cookies = []
                        for cookie_str in local_cookies:
                            try:
                                cookie_normalized = tools.replace_cookie_item(cookie_str, "sgcookie", None)
                                user = User(cookie_normalized)
                                if user and user.uid and user.uid not in server_cookie_uids:
                                    # 这个是本地导入的 Cookie，保留它
                                    local_only_cookies.append(cookie_str)
                            except:
                                # 如果解析失败，也保留（可能是格式特殊）
                                if cookie_str not in server_cookies:
                                    local_only_cookies.append(cookie_str)
                        
                        # 合并：先放服务器 Cookie，再放本地导入的 Cookie
                        merged_cookies = server_cookies + local_only_cookies
                        
                        # 更新本地缓存（合并后的 Cookie 列表）
                        self.parent_window.cookies = merged_cookies
                        self.parent_window.devices = [d['device_string'] for d in devices_data]
                        
                        # 更新 Cookie ID 映射（只更新服务器 Cookie 的映射）
                        if not hasattr(self.parent_window, 'cookie_ids'):
                            self.parent_window.cookie_ids = {}
                        for c in cookies_data:
                            cookie_id = c.get('id')
                            cookie_uid = c.get('uid')
                            if cookie_uid and cookie_id:
                                self.parent_window.cookie_ids[cookie_uid] = cookie_id
                        
                        self.parent_window.save_config()
                        
                        local_count = len(local_only_cookies)
                        server_count = len(server_cookies)
                        self.log(f"🔄 可用资源已更新：{len(merged_cookies)} 个Cookie（服务器：{server_count}，本地：{local_count}），{len(self.parent_window.devices)} 个设备")
                        logger.info(f"[刷新] Cookie 合并完成：服务器 {server_count} 个，本地 {local_count} 个，总计 {len(merged_cookies)} 个")
                        
                        # 更新界面显示
                        self.parent_window.main_page.update_data_display()
                        # 刷新 Cookie 下拉列表
                        self.refresh_cookie_select()
                except Exception as e:
                    self.log(f"⚠️ 刷新可用数量失败: {str(e)}")
        
        # 在后台刷新可用数量
        threading.Thread(target=refresh_available_count, daemon=True).start()

        # 只有任务真正执行了（有成功或失败），才获取操作后数据并输出汇总
        if success > 0 or failed > 0:
            live_id = self.live_id_input.text().strip()
            if live_id:
                # 先立即拉一次作为基线
                self.fetch_after_data(live_id)

                # 基于经验：100 次成功 ≈ 1s 传播延迟，但最少3秒
                base_wait = max(5, math.ceil(success / 100))
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
            
            # 达到上限时也记录任务日志（使用最终观看数）
            def update_task_log_async():
                """异步更新任务日志到服务器（使用最终观看数）"""
                if hasattr(self, 'using_server_mode') and self.using_server_mode:
                    if hasattr(self.parent_window, 'client_key') and hasattr(self.parent_window, 'api_url') and self.parent_window.client_key and self.parent_window.api_url:
                        live_id = self.live_id_input.text().strip()
                        if live_id and (getattr(self, 'success_count', 0) > 0 or getattr(self, 'fail_count', 0) > 0):
                            try:
                                api_url = self.parent_window.api_url.rstrip('/')
                                started_at_str = None
                                if hasattr(self, 'task_started_at') and self.task_started_at:
                                    started_at_str = self.task_started_at.strftime('%Y-%m-%d %H:%M:%S')
                                
                                response = requests.post(
                                    f"{api_url}/api/log_task",
                                    json={
                                        'client_key': self.parent_window.client_key,
                                        'live_id': live_id,
                                        'view_count_before': getattr(self, 'view_count_before', 0),
                                        'view_count_after': getattr(self, 'view_count_after', 0),
                                        'success_count': getattr(self, 'success_count', 0),
                                        'fail_count': getattr(self, 'fail_count', 0),
                                        'started_at': started_at_str
                                    },
                                    timeout=10
                                )
                                response.raise_for_status()
                                result = response.json()
                                if result.get('success'):
                                    task_log_id = result.get('data', {}).get('task_log_id', 0)
                                    logger.info(f"[日志] ✅ 任务日志已记录（最终观看数，ID: {task_log_id}）")
                            except Exception as e:
                                logger.error(f"[日志] ⚠️ 记录任务日志时出错: {str(e)}", exc_info=True)
            
            threading.Thread(target=update_task_log_async, daemon=True).start()
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
            
            # 轮询稳定后更新任务日志（使用最终的观看数）
            def update_task_log_async():
                """异步更新任务日志到服务器（使用最终观看数）"""
                if hasattr(self, 'using_server_mode') and self.using_server_mode:
                    if hasattr(self.parent_window, 'client_key') and hasattr(self.parent_window, 'api_url') and self.parent_window.client_key and self.parent_window.api_url:
                        live_id = self.live_id_input.text().strip()
                        if live_id and (getattr(self, 'success_count', 0) > 0 or getattr(self, 'fail_count', 0) > 0):
                            try:
                                api_url = self.parent_window.api_url.rstrip('/')
                                started_at_str = None
                                if hasattr(self, 'task_started_at') and self.task_started_at:
                                    started_at_str = self.task_started_at.strftime('%Y-%m-%d %H:%M:%S')
                                
                                response = requests.post(
                                    f"{api_url}/api/log_task",
                                    json={
                                        'client_key': self.parent_window.client_key,
                                        'live_id': live_id,
                                        'view_count_before': getattr(self, 'view_count_before', 0),
                                        'view_count_after': getattr(self, 'view_count_after', 0),  # 使用最终观看数
                                        'success_count': getattr(self, 'success_count', 0),
                                        'fail_count': getattr(self, 'fail_count', 0),
                                        'started_at': started_at_str
                                    },
                                    timeout=10
                                )
                                response.raise_for_status()
                                result = response.json()
                                if result.get('success'):
                                    task_log_id = result.get('data', {}).get('task_log_id', 0)
                                    logger.info(f"[日志] ✅ 任务日志已更新（最终观看数，ID: {task_log_id}）")
                            except Exception as e:
                                logger.error(f"[日志] ⚠️ 更新任务日志时出错: {str(e)}", exc_info=True)
            
            threading.Thread(target=update_task_log_async, daemon=True).start()
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
    
    # 定义信号用于跨线程通信
    cookie_fetch_success = pyqtSignal(int, float)  # (数量, 耗时)
    cookie_fetch_error = pyqtSignal(str)  # 错误消息
    device_fetch_success = pyqtSignal(int, float)  # (数量, 耗时)
    device_fetch_error = pyqtSignal(str)  # 错误消息
    progress_update = pyqtSignal(str)  # 进度条内容更新
    
    def __init__(self, parent: ClientUI):
        super().__init__(parent)
        self.setObjectName("configPage")  # 设置对象名称
        self.parent_window = parent
        self._progress_bar = None  # 存储进度条引用
        self.setup_ui()
        
        # 连接信号到槽函数
        self.cookie_fetch_success.connect(self._on_cookie_fetch_success)
        self.cookie_fetch_error.connect(self._on_cookie_fetch_error)
        self.device_fetch_success.connect(self._on_device_fetch_success)
        self.device_fetch_error.connect(self._on_device_fetch_error)
        self.progress_update.connect(self._on_progress_update)
    
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
        """从API远程拉取Cookie（分批拉取，显示进度）"""
        if not self.parent_window.client_key:
            self.show_error("请先配置客户端密钥")
            return
        
        # 创建进度提示并保存到实例变量
        self._progress_bar = InfoBar.info(
            title="正在拉取Cookie",
            content="准备拉取Cookie数据...",
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=-1,  # 持续显示
            parent=self
        )
        
        # 异步执行，分批拉取
        def fetch_async():
            import time
            import traceback
            start_time = time.time()
            all_cookies = []
            batch_size = 500  # 每批500个Cookie
            
            try:
                logger.info(f"[拉取Cookie] 开始拉取Cookie，API地址: {self.parent_window.api_url}")
                api_url = self.parent_window.api_url.rstrip('/')
                url = f"{api_url}/api/allocate_resources"
                
                batch_num = 0
                cookie_offset = 0
                
                while True:
                    batch_num += 1
                    logger.debug(f"[拉取Cookie] 拉取第 {batch_num} 批，offset={cookie_offset}")
                    
                    # 更新进度提示（通过实例变量访问）
                    progress_text = f"正在拉取第 {batch_num} 批Cookie（每批{batch_size}个）..."
                    try:
                        if self._progress_bar:
                            self._progress_bar.setContent(progress_text)
                    except:
                        pass
                    
                    # 分批拉取
                    data = {
                        'client_key': self.parent_window.client_key,
                        'cookie_count': batch_size,  # 每次500个
                        'device_count': -1,  # 不拉取设备
                        'cookie_offset': cookie_offset,
                        'include_cooldown': True  # 包含冷却期的 Cookie（用于完整显示）
                    }
                    
                    logger.debug(f"[拉取Cookie] 发送请求: {data}")
                    response = requests.post(url, json=data, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    logger.debug(f"[拉取Cookie] 收到响应: success={result.get('success')}, cookies数量={len(result.get('data', {}).get('cookies', []))}")
                    
                    if not result.get('success'):
                        msg = result.get('message', '未知错误')
                        logger.error(f"[拉取Cookie] 请求失败: {msg}")
                        self.cookie_fetch_error.emit(f"拉取失败: {msg}")
                        return
                    
                    cookies_data = result.get('data', {}).get('cookies', [])
                    if not cookies_data:
                        logger.debug(f"[拉取Cookie] 没有更多Cookie了")
                        # 没有更多数据了
                        break
                    
                    # 添加到总列表（保留完整数据，包括 ID 和 UID）
                    all_cookies.extend(cookies_data)
                    logger.debug(f"[拉取Cookie] 已累计拉取 {len(all_cookies)} 个Cookie")
                    
                    # 如果返回数量小于batch_size，说明已经是最后一批
                    if len(cookies_data) < batch_size:
                        logger.debug(f"[拉取Cookie] 最后一批，返回了 {len(cookies_data)} 个")
                        break
                    
                    # 更新偏移量
                    cookie_offset += batch_size
                
                # 拉取完成
                logger.info(f"[拉取Cookie] 拉取完成，总共 {len(all_cookies)} 个Cookie")
                
                elapsed = time.time() - start_time
                
                if all_cookies:
                    # 保存到配置（同时保存 Cookie ID 映射）
                    logger.debug(f"[拉取Cookie] 保存到配置...")
                    
                    # 提取 Cookie 字符串和建立 ID 映射
                    cookies_str = [item['cookie'] for item in all_cookies]
                    if not hasattr(self.parent_window, 'cookie_ids'):
                        self.parent_window.cookie_ids = {}
                    
                    # 建立 Cookie UID 到 Cookie ID 的映射
                    cookie_id_count = 0
                    for item in all_cookies:
                        try:
                            cookie_id = item.get('id')
                            cookie_uid = item.get('uid')
                            if cookie_uid and cookie_id:
                                self.parent_window.cookie_ids[cookie_uid] = cookie_id
                                cookie_id_count += 1
                        except:
                            continue
                    
                    if cookie_id_count > 0:
                        logger.info(f"[拉取Cookie] ✅ 已建立 {cookie_id_count} 个Cookie的ID映射（用于标记封禁）")
                    
                    # 保存 Cookie 列表（只保存字符串）
                    self.parent_window.cookies = cookies_str
                    self.parent_window.save_config()
                    
                    # 发射成功信号（会在主线程中处理UI更新）
                    count = len(cookies_str)
                    logger.debug(f"[拉取Cookie] 发射成功信号：count={count}, elapsed={elapsed}")
                    self.cookie_fetch_success.emit(count, elapsed)
                else:
                    logger.warning(f"[拉取Cookie] 没有可用的Cookie")
                    self.cookie_fetch_error.emit("服务器上没有可用的Cookie")
                    
            except requests.Timeout as e:
                logger.error(f"[拉取Cookie] 请求超时: {e}")
                self.cookie_fetch_error.emit("❌ 请求超时，请检查网络或服务器")
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.error(f"[拉取Cookie] 异常: {err_msg}", exc_info=True)
                self.cookie_fetch_error.emit(f"❌ 拉取失败: {err_msg}")
        
        # 启动后台线程
        threading.Thread(target=fetch_async, daemon=True).start()
    
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
        self.parent_window.cookie_ids = {}  # 同时清空Cookie ID映射
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
        """从API远程拉取设备（分批拉取，显示进度）"""
        if not self.parent_window.client_key:
            self.show_error("请先配置客户端密钥")
            return
        
        # 创建进度提示并保存到实例变量
        self._progress_bar = InfoBar.info(
            title="正在拉取设备",
            content="准备拉取设备数据...",
            orient=Qt.Horizontal,
            isClosable=False,
            position=InfoBarPosition.TOP,
            duration=-1,  # 持续显示
            parent=self
        )
        
        # 异步执行，分批拉取
        def fetch_async():
            import time
            import traceback
            start_time = time.time()
            all_devices = []
            batch_size = 1000  # 每批1000个
            
            try:
                logger.info(f"[拉取设备] 开始拉取设备，API地址: {self.parent_window.api_url}")
                api_url = self.parent_window.api_url.rstrip('/')
                url = f"{api_url}/api/allocate_resources"
                
                batch_num = 0
                device_offset = 0  # 初始化偏移量
                
                while True:
                    batch_num += 1
                    logger.debug(f"[拉取设备] 拉取第 {batch_num} 批，offset={device_offset}")
                    
                    # 拉取前显示进度（使用信号确保在主线程更新）
                    if batch_num == 1:
                        progress_text = f"正在拉取第 1 批设备..."
                    else:
                        current_count = len(all_devices)
                        elapsed = time.time() - start_time
                        progress_text = f"已拉取 {current_count} 个设备 | 第 {batch_num} 批 | 耗时 {elapsed:.1f}秒"
                    
                    # 发射进度更新信号
                    self.progress_update.emit(progress_text)
                    
                    # 构建请求数据（包含偏移量）
                    data = {
                        'client_key': self.parent_window.client_key,
                        'cookie_count': -1,  # -1=不拉取Cookie
                        'device_count': batch_size,  # 每次1000个
                        'device_offset': device_offset  # 添加偏移量
                    }
                    
                    logger.debug(f"[拉取设备] 发送请求: {data}")
                    response = requests.post(url, json=data, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    logger.debug(f"[拉取设备] 收到响应: success={result.get('success')}, devices数量={len(result.get('data', {}).get('devices', []))}")
                    
                    if not result.get('success'):
                        msg = result.get('message', '未知错误')
                        logger.error(f"[拉取设备] 请求失败: {msg}")
                        self.device_fetch_error.emit(f"拉取失败: {msg}")
                        return
                    
                    devices_data = result.get('data', {}).get('devices', [])
                    if not devices_data:
                        logger.debug(f"[拉取设备] 没有更多设备了")
                        # 没有更多数据了
                        break
                    
                    # 添加到总列表
                    all_devices.extend(devices_data)
                    logger.debug(f"[拉取设备] 已累计拉取 {len(all_devices)} 个设备")
                    
                    # 拉取后更新进度，显示最新数量（使用信号）
                    current_count = len(all_devices)
                    elapsed = time.time() - start_time
                    progress_text_after = f"✓ 已拉取 {current_count} 个设备 | 耗时 {elapsed:.1f}秒"
                    
                    # 发射进度更新信号
                    self.progress_update.emit(progress_text_after)
                    
                    # 如果返回数量小于batch_size，说明已经是最后一批
                    if len(devices_data) < batch_size:
                        logger.debug(f"[拉取设备] 最后一批，返回了 {len(devices_data)} 个")
                        break
                    
                    # 更新偏移量，准备拉取下一批
                    device_offset += batch_size
                
                # 拉取完成
                logger.info(f"[拉取设备] 拉取完成，总共 {len(all_devices)} 个设备")
                elapsed = time.time() - start_time
                
                if all_devices:
                    # 提取设备字符串
                    devices = [item['device_string'] for item in all_devices]
                    device_ids = [item['id'] for item in all_devices]
                    
                    # 保存到配置
                    logger.info(f"[拉取设备] 保存设备到配置...")
                    self.parent_window.devices = devices
                    if not hasattr(self.parent_window, 'device_ids'):
                        self.parent_window.device_ids = {}
                    
                    # 建立设备字符串到设备ID的映射（用于锁定）
                    device_id_count = 0
                    for idx, dev_str in enumerate(devices):
                        # 规范化设备字符串（去除首尾空格和换行）作为key
                        dev_str_normalized = dev_str.strip()
                        dev_id = device_ids[idx] if idx < len(device_ids) else None
                        if dev_id:
                            # 同时存储原始格式和规范化格式（以防万一）
                            self.parent_window.device_ids[dev_str] = dev_id
                            self.parent_window.device_ids[dev_str_normalized] = dev_id
                            device_id_count += 1
                    
                    logger.info(f"[拉取设备] ✅ 已建立 {device_id_count} 个设备的ID映射（用于锁定）")
                    self.parent_window.save_config()
                    
                    # 发射成功信号
                    count = len(devices)
                    logger.debug(f"[拉取设备] 发射成功信号：count={count}, elapsed={elapsed}")
                    self.device_fetch_success.emit(count, elapsed)
                else:
                    logger.warning(f"[拉取设备] 没有可用的设备")
                    self.device_fetch_error.emit("服务器上没有可用的设备")
                    
            except requests.Timeout as e:
                logger.error(f"[拉取设备] 请求超时: {e}")
                self.device_fetch_error.emit("❌ 请求超时，请检查网络或服务器")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"[拉取设备] 连接错误: {e}")
                self.device_fetch_error.emit("❌ 无法连接到服务器，请检查API地址和网络连接")
            except requests.exceptions.RequestException as e:
                err_msg = str(e)
                logger.error(f"[拉取设备] 请求错误: {err_msg}")
                self.device_fetch_error.emit(f"❌ 请求失败: {err_msg}")
            except Exception as e:
                err_msg = str(e)
                logger.error(f"[拉取设备] 未知异常: {err_msg}", exc_info=True)
                self.device_fetch_error.emit(f"❌ 拉取失败: {err_msg}")
        
        # 启动后台线程
        threading.Thread(target=fetch_async, daemon=True).start()
    
    def clear_devices(self):
        """清空设备"""
        self.parent_window.devices = []
        self.parent_window.device_ids = {}  # 同时清空设备ID映射
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
        device_count = len(self.parent_window.devices)
        device_ids_count = len(getattr(self.parent_window, 'device_ids', {}))
        self.device_count_label.setText(f"当前数量: {device_count}" + (f" (已映射ID: {device_ids_count})" if device_ids_count > 0 else ""))
        
        # 显示前5个设备的预览（包含数据库ID）
        preview_text = ""
        for i, device in enumerate(self.parent_window.devices[:5]):
            device_id = None
            if hasattr(self.parent_window, 'device_ids') and self.parent_window.device_ids:
                # 尝试查找设备ID（先原始格式，再规范化格式）
                device_id = self.parent_window.device_ids.get(device) or self.parent_window.device_ids.get(device.strip())
            
            if device_id:
                preview_text += f"{i+1}. [ID:{device_id}] {device[:60]}...\n"
            else:
                preview_text += f"{i+1}. [ID:未映射] {device[:60]}...\n"
        
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
    
    # ==== 信号槽函数 ====
    def _on_progress_update(self, progress_text):
        """更新进度条内容的槽函数"""
        try:
            # 每次都更新进度条
            # 关闭旧的进度条
            if self._progress_bar:
                try:
                    self._progress_bar.close()
                except:
                    pass
            
            # 创建新的进度条显示最新进度
            self._progress_bar = InfoBar.info(
                title="正在拉取设备",
                content=progress_text,
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=-1,  # 持续显示
                parent=self
            )
            logger.debug(f"[进度条] 进度条已更新: {progress_text}")
        except Exception as e:
            logger.error(f"[进度条] 更新进度条失败: {e}")
    
    def _on_cookie_fetch_success(self, count, elapsed):
        """Cookie拉取成功的槽函数"""
        logger.debug(f"[信号槽] Cookie拉取成功，count={count}, elapsed={elapsed}")
        if self._progress_bar:
            try:
                self._progress_bar.close()
            except:
                pass
            self._progress_bar = None
        self.update_cookie_display()
        self.show_success(f"✅ 成功拉取 {count} 个Cookie（耗时 {elapsed:.1f}秒）")
    
    def _on_cookie_fetch_error(self, message):
        """Cookie拉取失败的槽函数"""
        logger.error(f"[信号槽] Cookie拉取失败，message={message}")
        if self._progress_bar:
            try:
                self._progress_bar.close()
            except:
                pass
            self._progress_bar = None
        self.show_error(message)
    
    def _on_device_fetch_success(self, count, elapsed):
        """设备拉取成功的槽函数"""
        logger.debug(f"[信号槽] 设备拉取成功，count={count}, elapsed={elapsed}")
        if self._progress_bar:
            try:
                self._progress_bar.close()
            except:
                pass
            self._progress_bar = None
        logger.debug(f"[信号槽] 开始更新设备显示...")
        self.update_device_display()
        logger.debug(f"[信号槽] 显示成功提示...")
        self.show_success(f"✅ 成功拉取 {count} 个设备（耗时 {elapsed:.1f}秒）")
        logger.debug(f"[信号槽] 设备拉取完成回调结束")
    
    def _on_device_fetch_error(self, message):
        """设备拉取失败的槽函数"""
        if self._progress_bar:
            try:
                self._progress_bar.close()
            except:
                pass
            self._progress_bar = None
        self.show_error(message)


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

