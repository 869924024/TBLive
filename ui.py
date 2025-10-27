import os
import json
import threading
import multiprocessing
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, setTheme, Theme,
    PushButton, PrimaryPushButton, TransparentPushButton,
    BodyLabel, TitleLabel, SubtitleLabel, CaptionLabel,
    ListWidget, TextEdit, LineEdit, ComboBox, RadioButton,
    CardWidget,
    InfoBar, InfoBarPosition,
    FluentIcon as FIF,
    isDarkTheme
)

from to_requests import Watch
from generate_device import Gen, kill_processes_by_keyword


class AccountPage(QWidget):
    """账号和设备数据管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("accountPage")  # 设置对象名称
        self.parent_window = parent
        self.is_generating_device = False
        self.continuous_thread = None  # 连续生成线程
        self.setup_ui()
        self.gen_device = Gen()
        self.load_proxy_config()  # 加载保存的代理配置

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 页面标题和保存/载入按钮
        title_layout = QHBoxLayout()
        title = TitleLabel("账号和设备数据管理")
        title_layout.addWidget(title)
        title_layout.addStretch()

        # 保存和载入按钮
        save_config_btn = PrimaryPushButton(FIF.SAVE, "保存配置")
        save_config_btn.clicked.connect(self.save_all_config)
        save_config_btn.setFixedWidth(100)
        title_layout.addWidget(save_config_btn)

        load_config_btn = PrimaryPushButton(FIF.FOLDER, "载入配置")
        load_config_btn.clicked.connect(self.load_all_config)
        load_config_btn.setFixedWidth(100)
        title_layout.addWidget(load_config_btn)

        layout.addLayout(title_layout)

        # 水平布局
        h_layout = QHBoxLayout()
        h_layout.setSpacing(20)

        # 左侧：账号数据卡片
        account_card = self.create_account_card()
        h_layout.addWidget(account_card)

        # 右侧：设备数据卡片
        device_card = self.create_device_card()
        h_layout.addWidget(device_card)
        layout.addLayout(h_layout)

        # 代理和线程配置水平布局
        config_h_layout = QHBoxLayout()
        config_h_layout.setSpacing(20)

        # 代理配置区域
        proxy_card = self.create_proxy_card()
        config_h_layout.addWidget(proxy_card)

        # 线程配置区域
        thread_card = self.create_thread_card()
        config_h_layout.addWidget(thread_card)

        layout.addLayout(config_h_layout)

    def create_proxy_card(self):
        """创建代理配置卡片"""
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # 标题
        title = SubtitleLabel("🌐 代理配置")
        card_layout.addWidget(title)

        # 代理类型选择和保存按钮
        proxy_top_layout = QHBoxLayout()
        proxy_top_layout.setSpacing(20)

        # 左侧：代理类型选择
        proxy_type_layout = QHBoxLayout()
        proxy_type_layout.setSpacing(20)

        self.url_radio = RadioButton("API URL")
        self.url_radio.setChecked(True)
        self.url_radio.toggled.connect(self.on_proxy_type_changed)
        proxy_type_layout.addWidget(self.url_radio)

        self.direct_radio = RadioButton("直接填写代理")
        self.direct_radio.toggled.connect(self.on_proxy_type_changed)
        proxy_type_layout.addWidget(self.direct_radio)

        proxy_top_layout.addLayout(proxy_type_layout)

        # 提示信息
        tip_label = CaptionLabel("提示：代理api url为txt格式一行一个")
        proxy_top_layout.addWidget(tip_label)

        proxy_top_layout.addStretch()
        card_layout.addLayout(proxy_top_layout)

        # URL输入区域
        self.url_input_widget = QFrame()
        self.url_input_widget.setFrameStyle(QFrame.NoFrame)
        url_input_layout = QVBoxLayout(self.url_input_widget)
        url_input_layout.setContentsMargins(0, 0, 0, 0)

        self.url_input = LineEdit()
        self.url_input.setPlaceholderText("请输入代理API URL，例如：http://api.example.com/proxy")

        url_input_layout.addWidget(self.url_input)
        card_layout.addWidget(self.url_input_widget)

        # 直接填写代理区域
        self.direct_input_widget = QFrame()
        self.direct_input_widget.setFrameStyle(QFrame.NoFrame)
        direct_input_layout = QVBoxLayout(self.direct_input_widget)
        direct_input_layout.setContentsMargins(0, 0, 0, 0)

        self.direct_input = LineEdit()
        self.direct_input.setPlaceholderText("请输入代理地址，例如：http://127.0.0.1:8080")
        direct_input_layout.addWidget(self.direct_input)
        card_layout.addWidget(self.direct_input_widget)

        # 初始状态：隐藏直接填写区域
        self.direct_input_widget.hide()

        return card

    def on_proxy_type_changed(self):
        """代理类型切换事件"""
        if self.url_radio.isChecked():
            self.url_input_widget.show()
            self.direct_input_widget.hide()
        else:
            self.url_input_widget.hide()
            self.direct_input_widget.show()

    def get_proxy_config(self):
        """获取当前代理配置"""
        if self.url_radio.isChecked():
            return {
                'type': 'url',
                'value': self.url_input.text().strip()
            }
        else:
            return {
                'type': 'direct',
                'value': self.direct_input.text().strip()
            }

    def save_proxy_config(self):
        """保存代理配置到文件"""
        try:
            config = {
                'type': 'url' if self.url_radio.isChecked() else 'direct',
                'url_value': self.url_input.text().strip(),
                'direct_value': self.direct_input.text().strip()
            }

            with open('proxy_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            if self.parent_window:
                self.parent_window.add_log("✅ 代理配置已保存")

            InfoBar.success(
                title="保存成功",
                content="代理配置已保存到 proxy_config.json",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 保存代理配置失败: {str(e)}")

            InfoBar.error(
                title="保存失败",
                content=f"保存代理配置时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def load_proxy_config(self):
        """从文件加载代理配置"""
        try:
            if not os.path.exists('proxy_config.json'):
                return

            with open('proxy_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 设置代理类型
            if config.get('type') == 'direct':
                self.direct_radio.setChecked(True)
                self.url_radio.setChecked(False)
            else:
                self.url_radio.setChecked(True)
                self.direct_radio.setChecked(False)

            # 设置输入框的值
            self.url_input.setText(config.get('url_value', ''))
            self.direct_input.setText(config.get('direct_value', ''))

            # 更新显示状态
            self.on_proxy_type_changed()

        except Exception as e:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 加载代理配置失败: {str(e)}")

    def create_thread_card(self):
        """创建线程配置卡片"""
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # 标题
        title = SubtitleLabel("🔧 操作配置")
        card_layout.addWidget(title)

        # 线程配置水平布局
        thread_h_layout = QHBoxLayout()
        thread_h_layout.setSpacing(15)

        # 线程池大小配置
        pool_frame = QFrame()
        pool_frame.setFrameStyle(QFrame.NoFrame)
        pool_layout = QVBoxLayout(pool_frame)
        pool_layout.setContentsMargins(0, 0, 0, 0)
        pool_layout.setSpacing(5)

        pool_label = BodyLabel("线程池大小:")
        pool_layout.addWidget(pool_label)

        self.pool_size_input = LineEdit()
        cpu_cores = multiprocessing.cpu_count() * 2
        self.pool_size_input.setPlaceholderText(f"建议: {cpu_cores} (CPU核心数)")
        self.pool_size_input.setText(str(cpu_cores))  # 默认值为CPU核心数
        self.pool_size_input.setFixedWidth(120)
        pool_layout.addWidget(self.pool_size_input)

        thread_h_layout.addWidget(pool_frame)

        # 操作倍数配置
        multiplier_frame = QFrame()
        multiplier_frame.setFrameStyle(QFrame.NoFrame)
        multiplier_layout = QVBoxLayout(multiplier_frame)
        multiplier_layout.setContentsMargins(0, 0, 0, 0)
        multiplier_layout.setSpacing(5)

        multiplier_label = BodyLabel("操作倍数:")
        multiplier_layout.addWidget(multiplier_label)
        self.multiplier_input = LineEdit()
        self.multiplier_input.setPlaceholderText("例如：1-5")
        self.multiplier_input.setText("1")  # 默认值为1
        self.multiplier_input.setFixedWidth(120)
        multiplier_layout.addWidget(self.multiplier_input)
        thread_h_layout.addWidget(multiplier_frame)

        liveId_frame = QFrame()
        liveId_frame.setFrameStyle(QFrame.NoFrame)
        liveId_layout = QVBoxLayout(liveId_frame)
        liveId_layout.setContentsMargins(0, 0, 0, 0)
        liveId_layout.setSpacing(5)
        liveId_label = BodyLabel("直播间id:")
        liveId_layout.addWidget(liveId_label)
        self.liveId_input = LineEdit()
        self.liveId_input.setPlaceholderText("直播间id")
        self.liveId_input.setFixedWidth(120)
        liveId_layout.addWidget(self.liveId_input)
        thread_h_layout.addWidget(liveId_frame)

        # 添加伸缩空间
        thread_h_layout.addStretch()

        card_layout.addLayout(thread_h_layout)

        # 提示信息
        tip_label = CaptionLabel(f"提示：线程池大小建议设置为CPU核心数*2({cpu_cores})，操作倍数控制每个任务的执行次数")
        tip_label.setWordWrap(True)
        card_layout.addWidget(tip_label)

        return card

    def get_thread_config(self):
        """获取线程配置"""
        try:
            # 获取线程池大小
            pool_size = int(self.pool_size_input.text().strip())
            if pool_size < 1:
                pool_size = multiprocessing.cpu_count()  # 默认为CPU核心数

            # 获取操作倍数
            multiplier = int(self.multiplier_input.text().strip())
            if multiplier < 1:
                multiplier = 1  # 默认值为1


            return {
                'pool_size': pool_size,
                'multiplier': multiplier,
                "live_id": self.liveId_input.text().strip()
            }
        except ValueError:
            return {
                'pool_size': multiprocessing.cpu_count(),  # 如果输入无效，返回CPU核心数
                'multiplier': 1,  # 默认倍数为1
                "live_id": ""
            }

    def save_all_config(self):
        """保存所有配置到文件"""
        try:
            config = {
                'proxy_config': {
                    'type': 'url' if self.url_radio.isChecked() else 'direct',
                    'url_value': self.url_input.text().strip(),
                    'direct_value': self.direct_input.text().strip()
                },
                'thread_config': self.get_thread_config(),
                'accounts': []
            }

            # 获取账号列表数据
            for i in range(self.account_list.count()):
                config['accounts'].append(self.account_list.item(i).text())

            with open('all_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            if self.parent_window:
                self.parent_window.add_log("✅ 所有配置已保存到 all_config.json")

            InfoBar.success(
                title="保存成功",
                content="所有配置已保存到 all_config.json",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 保存配置失败: {str(e)}")

            InfoBar.error(
                title="保存失败",
                content=f"保存配置时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def load_all_config(self):
        """从文件加载所有配置"""
        try:
            if not os.path.exists('all_config.json'):
                InfoBar.warning(
                    title="文件不存在",
                    content="未找到配置文件 all_config.json",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            with open('all_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 加载代理配置
            proxy_config = config.get('proxy_config', {})
            if proxy_config.get('type') == 'direct':
                self.direct_radio.setChecked(True)
                self.url_radio.setChecked(False)
            else:
                self.url_radio.setChecked(True)
                self.direct_radio.setChecked(False)

            self.url_input.setText(proxy_config.get('url_value', ''))
            self.direct_input.setText(proxy_config.get('direct_value', ''))
            self.on_proxy_type_changed()

            # 加载线程配置
            thread_config = config.get('thread_config', {})
            self.pool_size_input.setText(str(thread_config.get('pool_size', multiprocessing.cpu_count())))
            self.multiplier_input.setText(str(thread_config.get('multiplier', 1)))
            self.liveId_input.setText(thread_config.get('live_id', ''))

            # 加载账号列表
            accounts = config.get('accounts', [])
            self.account_list.clear()
            for account in accounts:
                if account.strip():  # 只添加非空账号
                    self.account_list.addItem(account.strip())

            # 更新账号数量标签
            count = len([acc for acc in accounts if acc.strip()])
            self.account_count_label.setText(f"当前账号数: {count}")

            if self.parent_window:
                self.parent_window.add_log("✅ 配置已成功载入")

            InfoBar.success(
                title="载入成功",
                content="所有配置已成功载入",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 载入配置失败: {str(e)}")

            InfoBar.error(
                title="载入失败",
                content=f"载入配置时出错: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def create_account_card(self):
        """创建账号数据卡片"""
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # 标题
        title = SubtitleLabel("📋 账号数据")
        card_layout.addWidget(title)

        # 导入按钮
        import_btn = PrimaryPushButton(FIF.FOLDER, "导入账号文件")
        import_btn.clicked.connect(self.import_accounts)
        card_layout.addWidget(import_btn)

        # 账号数量标签
        self.account_count_label = CaptionLabel("当前账号数: 0")
        card_layout.addWidget(self.account_count_label)

        # 账号列表
        self.account_list = ListWidget()
        card_layout.addWidget(self.account_list)

        return card

    def create_device_card(self):
        """创建设备数据卡片"""
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # 标题
        title = SubtitleLabel("📱 设备数据")
        card_layout.addWidget(title)

        # 配置区域 - 水平布局
        config_h_layout = QHBoxLayout()
        config_h_layout.setSpacing(15)

        # 设备数量输入
        device_num_frame = QFrame()
        device_num_frame.setFrameStyle(QFrame.NoFrame)
        device_num_layout = QVBoxLayout(device_num_frame)
        device_num_layout.setContentsMargins(0, 0, 0, 0)
        device_num_layout.setSpacing(5)

        device_num_label = BodyLabel("生成设备数量:")
        device_num_layout.addWidget(device_num_label)

        self.device_num_input = LineEdit()
        self.device_num_input.setPlaceholderText("例如：10")
        self.device_num_input.setText("1")  # 默认值为1
        self.device_num_input.setFixedWidth(120)
        device_num_layout.addWidget(self.device_num_input)

        config_h_layout.addWidget(device_num_frame)

        # 窗口数（线程数）输入
        window_num_frame = QFrame()
        window_num_frame.setFrameStyle(QFrame.NoFrame)
        window_num_layout = QVBoxLayout(window_num_frame)
        window_num_layout.setContentsMargins(0, 0, 0, 0)
        window_num_layout.setSpacing(5)

        window_num_label = BodyLabel("并发窗口数:")
        window_num_layout.addWidget(window_num_label)

        self.window_num_input = LineEdit()
        self.window_num_input.setPlaceholderText("例如：3")
        self.window_num_input.setText("1")  # 默认值为1
        self.window_num_input.setFixedWidth(120)
        window_num_layout.addWidget(self.window_num_input)

        config_h_layout.addWidget(window_num_frame)

        # 添加伸缩空间
        config_h_layout.addStretch()

        card_layout.addLayout(config_h_layout)

        # 提示信息
        tip_label = CaptionLabel("提示：通过PID区分不同窗口的流量，所有操作完全并行，互不干扰！窗口数建议2-5个")
        tip_label.setWordWrap(True)
        card_layout.addWidget(tip_label)

        # 按钮水平布局
        button_h_layout = QHBoxLayout()
        button_h_layout.setSpacing(10)

        # 生成按钮
        self.device_generate_btn = PrimaryPushButton(FIF.PLAY, "开始生成设备")
        self.device_generate_btn.clicked.connect(self.toggle_device_generation)
        button_h_layout.addWidget(self.device_generate_btn)

        # 载入按钮
        self.device_loaded_btn = PrimaryPushButton(FIF.FOLDER, '载入"设备.txt"')
        self.device_loaded_btn.clicked.connect(self.load_existing_devices)
        button_h_layout.addWidget(self.device_loaded_btn)

        card_layout.addLayout(button_h_layout)

        # 设备数量标签
        self.device_count_label = CaptionLabel("当前设备数: 0")
        card_layout.addWidget(self.device_count_label)
        
        # 进度显示标签
        self.device_progress_label = CaptionLabel("生成进度: --/--")
        card_layout.addWidget(self.device_progress_label)
        
        # 耗时显示标签
        self.device_time_label = CaptionLabel("耗时: --")
        card_layout.addWidget(self.device_time_label)

        # 设备列表
        self.device_list = ListWidget()
        card_layout.addWidget(self.device_list)

        return card

    def import_accounts(self):
        """导入账号文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择账号文件", "", "文本文件 (*.txt);;所有文件 (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    accounts = f.readlines()
                    self.account_list.clear()
                    valid_accounts = []
                    for account in accounts:
                        account = account.strip()
                        if account:
                            self.account_list.addItem(account)
                            valid_accounts.append(account)

                    count = len(valid_accounts)
                    self.account_count_label.setText(f"当前账号数: {count}")

                    # 显示成功消息
                    InfoBar.success(
                        title="导入成功",
                        content=f"成功导入 {count} 个账号",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

                    if self.parent_window:
                        self.parent_window.add_log(f"✅ 成功导入 {count} 个账号")
            except Exception as e:
                InfoBar.error(
                    title="导入失败",
                    content=str(e),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                if self.parent_window:
                    self.parent_window.add_log(f"❌ 导入失败: {str(e)}")

    def format_elapsed_time(self, seconds):
        """格式化耗时显示"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}分{secs}秒"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}小时{minutes}分"
    
    def update_progress_display(self):
        """更新进度显示"""
        try:
            progress_info = self.gen_device.get_progress_info()
            
            # 更新进度标签
            success = progress_info['success_count']
            target = progress_info['target_count']
            if target == 999999:  # 无限循环模式
                self.device_progress_label.setText(f"生成进度: {success}个 (无限模式)")
            else:
                self.device_progress_label.setText(f"生成进度: {success}/{target}")
            
            # 更新耗时标签
            elapsed = progress_info['elapsed_time']
            self.device_time_label.setText(f"耗时: {self.format_elapsed_time(elapsed)}")
            
        except Exception as e:
            pass
    
    def toggle_device_generation(self):
        """切换设备生成状态"""
        if not self.is_generating_device:
            # 启动前先清理所有残留的MuMu进程，确保环境干净
            if self.parent_window:
                self.parent_window.add_log("🧹 清理残留进程...")
            kill_processes_by_keyword("MuMu", True)
            
            if self.gen_device.get_status():
                self.gen_device.stop_task()
                return

            # 获取用户输入
            try:
                device_count = int(self.device_num_input.text().strip())
                if device_count < 0:
                    device_count = 0  # 0表示无限循环
            except ValueError:
                device_count = 0  # 默认无限循环
            
            try:
                window_count = int(self.window_num_input.text().strip())
                if window_count < 1:
                    window_count = 1
                if window_count > 10:
                    window_count = 10
            except ValueError:
                window_count = 1  # 默认1个窗口

            # 设置日志回调，让generate_device的日志也输出到UI
            if self.parent_window:
                self.gen_device.set_log_callback(self.parent_window.add_log)

            # 开始生成
            self.is_generating_device = True
            self.device_generate_btn.setText("停止生成设备")
            self.device_generate_btn.setIcon(FIF.PAUSE)

            # 启动定时器持续刷新设备列表和进度
            self.device_refresh_timer = QTimer()
            self.device_refresh_timer.timeout.connect(self.load_existing_devices)
            self.device_refresh_timer.start(1000)  # 每秒刷新一次
            
            # 启动进度更新定时器
            self.progress_timer = QTimer()
            self.progress_timer.timeout.connect(self.update_progress_display)
            self.progress_timer.start(500)  # 每0.5秒更新一次进度

            # 传递参数启动任务
            self.gen_device.start_task(device_count=device_count, window_count=window_count)

            if self.parent_window:
                if device_count > 0:
                    self.parent_window.add_log(f"🔄 开始生成设备 (目标: {device_count}个, 并发: {window_count}个窗口)...")
                else:
                    self.parent_window.add_log(f"🔄 开始循环生成设备 (并发: {window_count}个窗口)...")
        else:
            # === 停止生成 ===
            
            # 停止生成
            self.is_generating_device = False
            self.device_generate_btn.setText("开始生成设备")
            self.device_generate_btn.setIcon(FIF.PLAY)

            # 停止定时器
            if hasattr(self, 'device_refresh_timer'):
                self.device_refresh_timer.stop()
            
            # 停止进度更新定时器
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            
            # 重置显示
            self.device_progress_label.setText("生成进度: --/--")
            self.device_time_label.setText("耗时: --")

            # 停止任务（内部会kill所有MuMu进程）
            self.gen_device.stop_task()

            if self.parent_window:
                self.parent_window.add_log("🛑 停止生成设备，正在清理所有模拟器...")

    def on_device_generated(self, success, data):
        """设备生成完成后的回调（在主线程中执行）"""
        if success:
            device_count = self.device_list.count() + 1
            self.device_list.addItem(str(data))
            self.device_list.scrollToBottom()
            self.device_count_label.setText(f"当前设备数: {device_count}")

            if self.parent_window:
                self.parent_window.add_log(f"✅ 成功生成设备: {str(data)[:50]}...")
        else:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 生成设备失败: {str(data)}")

    def on_generation_status(self, message):
        """生成状态消息回调"""
        if self.parent_window:
            self.parent_window.add_log(f"📡 {message}")

    def load_existing_devices(self):
        """加载现有设备数据并刷新列表"""
        try:
            if not os.path.exists("设备.txt"):
                return

            with open("设备.txt", 'r', encoding='utf-8') as f:
                devices = f.readlines()

            # 清空当前列表
            self.device_list.clear()

            # 过滤空行并添加到列表
            valid_devices = []
            for device in devices:
                device = device.strip()
                if device:
                    self.device_list.addItem(device)
                    valid_devices.append(device)

            # 更新设备数量
            count = len(valid_devices)
            self.device_count_label.setText(f"当前设备数: {count}")

        except Exception as e:
            if self.parent_window:
                self.parent_window.add_log(f"❌ 读取设备文件失败: {str(e)}")

    def generate_device(self):
        from generate_device import Gen
        """生成设备"""
        device_count = self.device_list.count() + 1
        success, data = Gen().task()
        if (success):
            self.device_list.addItem(str(data))
        self.device_list.scrollToBottom()
        self.device_count_label.setText(f"当前设备数: {device_count}")
        if self.parent_window:
            if not success:
                self.parent_window.add_log(f"生成设备失败: {str(data)}")


class TaskPage(QWidget):
    """任务操作页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("taskPage")  # 设置对象名称
        self.parent_window = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 页面标题
        title = TitleLabel("任务操作")
        layout.addWidget(title)

        # 控制区域
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        # 按钮卡片
        button_card = CardWidget(self)
        button_card.setFixedWidth(300)
        button_card.setFixedHeight(100)
        button_layout = QHBoxLayout(button_card)
        button_layout.setContentsMargins(20, 20, 20, 20)
        button_layout.setSpacing(15)

        button_layout.addStretch()
        self.start_btn = PrimaryPushButton(FIF.PLAY, "开始任务")
        self.start_btn.setFixedHeight(45)
        self.start_btn.clicked.connect(self.start_task)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = PushButton(FIF.CLOSE, "停止任务")
        self.stop_btn.setFixedHeight(45)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()
        control_layout.addWidget(button_card)

        # 计数器区域
        counter_layout = QHBoxLayout()
        counter_layout.setSpacing(15)

        # 成功任务卡片
        success_card = CardWidget(self)
        success_card.setFixedHeight(100)
        success_layout = QVBoxLayout(success_card)
        success_layout.setContentsMargins(20, 20, 20, 20)
        success_layout.setSpacing(10)

        self.success_count = TitleLabel("0")
        self.success_count.setAlignment(Qt.AlignCenter)

        success_layout.addWidget(BodyLabel("✅ 成功任务"))
        success_layout.addWidget(self.success_count)
        counter_layout.addWidget(success_card)

        # 失败任务卡片
        fail_card = CardWidget(self)
        fail_card.setFixedHeight(100)
        fail_layout = QVBoxLayout(fail_card)
        fail_layout.setContentsMargins(20, 20, 20, 20)
        fail_layout.setSpacing(10)

        self.fail_count = TitleLabel("0")
        self.fail_count.setAlignment(Qt.AlignCenter)

        fail_layout.addWidget(BodyLabel("❌ 失败任务"))
        fail_layout.addWidget(self.fail_count)
        counter_layout.addWidget(fail_card)

        control_layout.addLayout(counter_layout)
        layout.addLayout(control_layout)

        # 日志区域卡片
        log_card = CardWidget(self)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(15)

        log_header_layout = QHBoxLayout()
        log_title = SubtitleLabel("📝 运行日志")
        log_header_layout.addWidget(log_title)
        log_header_layout.addStretch()

        clear_log_btn = TransparentPushButton(FIF.DELETE, "清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_header_layout.addWidget(clear_log_btn)

        log_layout.addLayout(log_header_layout)

        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_card)

    def get_account_data(self):
        """获取账号数据"""
        accounts = []
        if self.parent_window and self.parent_window.account_page:
            account_list = self.parent_window.account_page.account_list
            for i in range(account_list.count()):
                accounts.append(account_list.item(i).text())
        return accounts

    def get_device_data(self):
        """获取设备数据"""
        devices = []
        if self.parent_window and self.parent_window.account_page:
            device_list = self.parent_window.account_page.device_list
            for i in range(device_list.count()):
                devices.append(device_list.item(i).text())
        return devices

    def get_proxy_config(self):
        """获取代理配置"""
        if self.parent_window and self.parent_window.account_page:
            return self.parent_window.account_page.get_proxy_config()
        return {'type': 'url', 'value': ''}

    def get_thread_config(self):
        """获取线程配置"""
        if self.parent_window and self.parent_window.account_page:
            return self.parent_window.account_page.get_thread_config()
        return {
            'pool_size': multiprocessing.cpu_count(),  # 默认为CPU核心数
            'multiplier': 1,  # 默认倍数为1
            'live_id': ""
        }

    def start_task(self):
        """开始任务"""

        # 检查父窗口和账号页面
        if not self.parent_window:
            return
        if not self.parent_window.account_page:
            return
        accounts = self.get_account_data()
        devices = self.get_device_data()
        proxy_config = self.get_proxy_config()
        thread_config = self.get_thread_config()
        # 输出详细的数据信息
        self.parent_window.add_log("=" * 50)


        # 账号数据信息
        self.parent_window.add_log(f"🔹 账号数据总数: {len(accounts)}")

        # 设备数据信息
        self.parent_window.add_log(f"🔹 设备数据总数: {len(devices)}")

        # 数据验证
        if not accounts:
            self.parent_window.add_log("⚠️ 验证失败: 没有可用的账号数据，请先导入账号")
            return

        if not devices:
            self.parent_window.add_log("⚠️ 验证失败: 没有可用的设备数据，请先生成设备")
            return

        # if not proxy_config['value']:
        #     self.parent_window.add_log("⚠️ 验证失败: 代理配置不能为空，请填写代理信息")
        #     return

        if not thread_config['live_id']:
            self.parent_window.add_log("⚠️ 验证失败: 直播间ID不能为空，请填写直播间ID")
            return

        self.parent_window.add_log("✅ 所有数据验证通过！")

        # TODO: 在这里添加实际的任务执行逻辑
        # 这里可以调用其他模块来执行具体的任务
        # 创建Watch实例
        try:
            self.watch = Watch(
                cookies=accounts,
                devices=devices,
                thread_nums=thread_config['pool_size'],
                Multiple_num=thread_config['multiplier'],
                live_id=thread_config['live_id'],
                log_fn=self.parent_window.add_log,
                proxy_type=proxy_config['type'],
                proxy_value=proxy_config['value'],
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.parent_window.add_log("❌ 初始化错误"+str(e))
            return


        # 启动任务（传入self以便更新UI）
        self.watch.start_task(self)

        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 连接停止按钮
        self.stop_btn.clicked.connect(self.stop_task)

    def stop_task(self):
        """停止任务"""
        if hasattr(self, 'watch'):
            self.watch.stop_task()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_text.append("🗑️ 日志已清空")


class MainWindow(FluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("淘宝刷cookie")
        self.resize(1200, 800)
        setTheme(Theme.AUTO)
        self.navigationInterface.setReturnButtonVisible(False)
        self.setup_ui()

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 停止设备生成
        if self.account_page.is_generating_device:
            self.account_page.gen_device.stop_task()
            if hasattr(self.account_page, 'device_refresh_timer'):
                self.account_page.device_refresh_timer.stop()
        self.add_log("🔴 程序正在关闭...")
        event.accept()  # 接受关闭事件

    def setup_ui(self):
        # 创建子页面
        self.account_page = AccountPage(self)
        self.task_page = TaskPage(self)

        # 添加子界面到导航
        self.addSubInterface(
            self.account_page,
            FIF.DOCUMENT,
            "①导入所需数据",
            NavigationItemPosition.TOP
        )

        self.addSubInterface(
            self.task_page,
            FIF.COMMAND_PROMPT,
            "②任务操作",
            NavigationItemPosition.TOP
        )

    def add_log_th(self, message):
        """添加日志到任务页面"""
        # 检查日志行数，如果超过1000行则自动备份并清空
        log_content = self.task_page.log_text.toPlainText()
        log_lines = log_content.split('\n') if log_content else []

        if len(log_lines) >= 1000:
            # 备份旧日志
            self.save_old_logs(log_lines)
            # 清空当前日志
            self.task_page.log_text.clear()
            # 添加清空日志的提示信息
            self.task_page.log_text.append("🗑️ 日志已超过1000行，自动备份并清空")

        self.task_page.log_text.append(message)

    def add_log(self, message):
        QTimer.singleShot(0, lambda: self.add_log_th(message))

    def save_old_logs(self, log_lines):
        """保存旧日志到文件"""
        try:
            # 创建logs目录（如果不存在）
            if not os.path.exists('logs'):
                os.makedirs('logs')

            # 生成带时间戳的日志文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f'logs/old_log_{timestamp}.txt'

            # 将日志写入文件
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write(f"日志备份时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"日志行数: {len(log_lines)}\n")
                f.write("=" * 50 + "\n")
                for line in log_lines:
                    f.write(line + "\n")

            # 添加备份成功的信息到控制台（可选）
            print(f"✅ 日志已备份到: {log_filename}")

        except Exception as e:
            # 如果备份失败，打印错误信息但不影响正常日志功能
            print(f"❌ 备份日志失败: {str(e)}")
