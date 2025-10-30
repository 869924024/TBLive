from loguru import logger
import time
import threading
from SunnyNet.Event import HTTPEvent
from SunnyNet.SunnyNet import SunnyNet as Sunny
import psutil
import os
import subprocess
import socket
import sys

# Windows专用模块（Mac/Linux不支持）
if sys.platform == 'win32':
    import win32gui
    import win32con
    import win32api
else:
    # Mac/Linux上的占位符
    win32gui = None
    win32con = None
    win32api = None


def kill_process_by_port(port):
    """杀掉占用指定端口的进程"""
    try:
        # Windows下隐藏子进程窗口
        startupinfo = None
        creationflags = 0
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = 0x08000000  # CREATE_NO_WINDOW

        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True,
            capture_output=True,
            text=True,
            startupinfo=startupinfo,
            creationflags=creationflags
        )

        if result.stdout:
            # 提取所有 PID
            pids = set(line.split()[-1] for line in result.stdout.strip().split('\n') if line.split())

            # 杀掉进程
            for pid in pids:
                # Windows下隐藏子进程窗口
                startupinfo = None
                creationflags = 0
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                    creationflags = 0x08000000  # CREATE_NO_WINDOW

                subprocess.run(f'taskkill /F /PID {pid}', shell=True, startupinfo=startupinfo, creationflags=creationflags)
                print(f"✓ 已杀掉端口 {port} 的进程 (PID: {pid})")
        else:
            print(f"端口 {port} 没有被占用")

    except Exception as e:
        print(f"错误: {e}")


def kill_processes_by_keyword(keyword, force=False):
    """
    根据关键词查找并终止进程

    参数:
        keyword: 要搜索的关键词
        force: 是否强制终止(True使用SIGKILL, False使用SIGTERM)

    返回:
        终止的进程数量
    """
    if not keyword:
        print("错误: 请提供关键词")
        return 0

    killed_count = 0
    found_processes = []

    print(f"正在搜索包含关键词 '{keyword}' 的进程...")

    # 查找匹配的进程
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # 获取进程信息
            pid = proc.info['pid']
            name = proc.info['name'] or ""
            cmdline = proc.info['cmdline'] or []
            cmdline_str = " ".join(cmdline)

            # 检查关键词是否在进程名或命令行中
            if keyword.lower() in name.lower() or keyword.lower() in cmdline_str.lower():
                found_processes.append({
                    'pid': pid,
                    'name': name,
                    'cmdline': cmdline_str[:100]  # 限制显示长度
                })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # 显示找到的进程
    if not found_processes:
        print(f"未找到包含关键词 '{keyword}' 的进程")
        return 0

    print(f"找到 {len(found_processes)} 个匹配的进程:")
    for proc in found_processes:
        print(f"  - PID: {proc['pid']}, 名称: {proc['name']}")

    # 终止进程
    print(f"\n开始终止进程 (强制模式: {'是' if force else '否'})...")
    for proc_info in found_processes:
        try:
            proc = psutil.Process(proc_info['pid'])

            if force:
                proc.kill()  # SIGKILL - 强制终止
                print(f"✓ 已强制终止进程 {proc_info['pid']} ({proc_info['name']})")
            else:
                proc.terminate()  # SIGTERM - 正常终止
                print(f"✓ 已终止进程 {proc_info['pid']} ({proc_info['name']})")

            killed_count += 1
            
            # 等待进程完全终止
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                if force:
                    print(f"⚠ 进程 {proc_info['pid']} 强制终止后仍在运行")
                else:
                    # 如果正常终止失败，尝试强制终止
                    try:
                        proc.kill()
                        print(f"✓ 已强制终止进程 {proc_info['pid']} ({proc_info['name']})")
                    except:
                        pass

        except psutil.NoSuchProcess:
            print(f"✗ 进程 {proc_info['pid']} 已不存在")
        except psutil.AccessDenied:
            print(f"✗ 权限不足，无法终止进程 {proc_info['pid']} ({proc_info['name']})")
        except Exception as e:
            print(f"✗ 终止进程 {proc_info['pid']} 时出错: {e}")

    print(f"总共终止了 {killed_count} 个进程")
    return killed_count


def get_free_port():
    # 创建一个 socket 实例
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))  # 绑定到任意地址，端口为0让系统自动分配空闲端口
    port = s.getsockname()[1]  # 获取被分配的端口
    s.close()
    return port


def find_mumu_window(vm_index, debug=False):
    """
    根据模拟器索引查找MuMu窗口句柄
    步骤：1.找父窗口(MuMu安装设备-X) 2.遍历子窗口找MuMuNxDevice
    """
    # 第一步：找父窗口 (MuMu安卓设备-X 或 MuMu安装设备-X 或 MuMu模拟器-X)
    def find_parent_callback(hwnd, parents):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # 匹配父窗口标题
            if (f"MuMu安卓设备-{vm_index}" in title or 
                f"MuMu安装设备-{vm_index}" in title or 
                f"MuMu模拟器-{vm_index}" in title or
                f"MuMu安卓设备{vm_index}" in title or
                f"MuMu安装设备{vm_index}" in title or 
                f"MuMu模拟器{vm_index}" in title):
                parents.append((hwnd, title))
        return True
    
    parent_windows = []
    win32gui.EnumWindows(find_parent_callback, parent_windows)
    
    if debug:
        print(f"[调试] 找到 {len(parent_windows)} 个父窗口")
        for hwnd, title in parent_windows:
            print(f"  - 父窗口: {hwnd}, 标题:'{title}'")
    
    if not parent_windows:
        if debug:
            print(f"[调试] 未找到父窗口 (MuMu安卓设备-{vm_index} 或 MuMu安装设备-{vm_index} 或 MuMu模拟器-{vm_index})")
        return None
    
    # 第二步：遍历每个父窗口的子窗口，找 MuMuNxDevice
    def find_child_callback(hwnd, children):
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        # 查找标题包含 Device 或 Player 的子窗口
        if "Device" in title or "Player" in title:
            children.append((hwnd, title, class_name))
        return True
    
    for parent_hwnd, parent_title in parent_windows:
        children = []
        try:
            win32gui.EnumChildWindows(parent_hwnd, find_child_callback, children)
            if debug:
                print(f"[调试] 父窗口 {parent_hwnd} 有 {len(children)} 个子窗口")
                for hwnd, title, cls in children:
                    print(f"    - 子窗口: {hwnd}, 标题:'{title}', 类:{cls}")
            
            # 找到第一个匹配的子窗口就返回
            if children:
                target_hwnd = children[0][0]
                if debug:
                    print(f"[调试] 返回子窗口: {target_hwnd}")
                return target_hwnd
        except Exception as e:
            if debug:
                print(f"[调试] 枚举子窗口失败: {e}")
    
    if debug:
        print(f"[调试] 未找到任何子窗口")
    return None


def click_window_background(hwnd, x, y):
    """
    使用Windows API后台点击窗口，不需要ADB
    
    :param hwnd: 窗口句柄
    :param x: 相对于窗口的x坐标
    :param y: 相对于窗口的y坐标
    :return: 是否成功
    """
    if not hwnd:
        return False
    
    try:
        # 计算坐标（MAKELONG）
        lParam = win32api.MAKELONG(x, y)
        
        # 发送鼠标按下消息
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
        time.sleep(0.05)  # 短暂延迟
        
        # 发送鼠标抬起消息
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        
        return True
    except Exception as e:
        print(f"后台点击失败: {e}")
        return False


TARGET_HEADERS = ["x-umt", "x-sgext", "x-mini-wua", "x-ttid", "x-utdid", "x-devid"]


# 全局文件锁，用于多线程写入文件时的同步
_global_file_lock = threading.Lock()

def manage_file_line(filename, check_string, write_string):
    if check_string == "":
        return ""
    """
    管理文件内容：自动创建文件或追加内容，确保无空行
    线程安全版本

    参数:
        filename: 文件名
        check_string: 判断字符串，用于检查是否已存在
        write_string: 写入行字符串，不存在时追加

    返回:
        str: 'exists' 表示内容已存在，'added' 表示已追加内容，'created' 表示已创建新文件
    """
    import os

    with _global_file_lock:  # 使用锁保护文件操作
        # 如果文件不存在，创建新文件并写入
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(write_string)
            return 'created'

        # 文件存在，读取内容
        with open(filename, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()

        # 移除所有空行和每行末尾的空白字符
        lines = [line.rstrip() for line in lines if line.strip()]

        # 检查判断字符串是否存在于任何一行中
        for line in lines:
            if check_string in line:
                return 'exists'

        # 判断字符串不存在，追加写入
        with open(filename, 'w', encoding='utf-8') as f:
            # 写入所有现有行（已去除空行）
            for line in lines:
                f.write(line + '\n')
            # 追加新行
            f.write(write_string)

        return 'added'


from urllib.parse import unquote
from email.parser import Parser


class SunnyNetService:
    def __init__(self, port=2025, pid=[]):
        self.port = port
        self.app = None
        self.running = False
        self.thread = None
        self.error_message = None  # 存储错误信息
        self.pid = pid
        self.is_captured = False
        self.deviceInfo_by_pid = {}  # 改为字典：{pid: deviceInfo}
        self.deviceInfo_lock = threading.Lock()  # 保护字典的锁

    def http_callback(self, conn: HTTPEvent):
        headers = conn.get_request().get_headers()
        if all(h in headers for h in TARGET_HEADERS):
            headers_dict = Parser().parsestr(headers)
            headers_dict = dict(headers_dict.items())
            try:
                devid = unquote(headers_dict['x-devid'])
                miniwua = unquote(headers_dict['x-mini-wua'])
                umt = unquote(headers_dict['x-umt'])
                utdid = unquote(headers_dict['x-utdid'])
                sgext = unquote(headers_dict['x-sgext'])
                str_data = f"{devid}\t{miniwua}\t{sgext}\t{umt}\t{utdid}"
                if "null" not in str_data and umt != utdid and devid != "" and miniwua != "" and umt != "" and utdid != "" and sgext != "":
                    # 获取请求的PID
                    request_pid = conn.get_pid()
                    logger.info(f"捕获到设备信息 (PID: {request_pid}): {str_data}")
                    manage_file_line("设备.txt", headers_dict.get("x-devid", ""), str_data)
                    self.is_captured = True
                    # 根据PID存储deviceInfo
                    with self.deviceInfo_lock:
                        self.deviceInfo_by_pid[request_pid] = str_data
            except Exception as e:
                pass

    def _run(self):
        """内部运行方法"""
        try:
            self.app = Sunny()
            self.app.set_port(self.port)
            self.app.set_callback(self.http_callback, lambda x: None, lambda x: None,
                                  lambda x: None, lambda x: None, lambda x: None)
            self.app.install_cert_to_system()

            if not self.app.start():
                self.error_message = f"启动失败: {self.app.error()}"
                logger.error(self.error_message)
                self.running = False
                return

            if not self.app.open_drive(False):
                self.error_message = "驱动加载失败，需要管理员权限"
                logger.error(self.error_message)
                self.running = False
                return

            self.app.process_all(False, False)
            if self.pid != []:
                for p in self.pid:
                    self.app.process_add_pid(p)
            else:
                self.app.process_add_name("MuMuNxDevice.exe")
                self.app.process_add_name("MuMuVMMHeadless.exe")

            print(f"SunnyNet服务已启动: 0.0.0.0:{self.port}")

            while self.running:
                time.sleep(1)

        except Exception as e:
            import traceback
            print(traceback.print_exc())
            self.error_message = f"运行异常: {str(e)}"
            self.running = False
        finally:
            print("SunnyNet服务已停止")

    def start(self, timeout=5):
        """
        启动服务（非阻塞）

        Args:
            timeout: 等待启动的超时时间（秒）

        Returns:
            bool: 启动是否成功
        """
        if self.running:
            self.error_message = "服务已在运行中"
            return False

        self.error_message = None  # 清空之前的错误
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        # 等待启动完成或失败
        for _ in range(timeout * 10):
            time.sleep(0.1)
            if self.error_message:  # 启动失败
                return False
            if self.running and self.app and self.app.start:  # 启动成功
                return True

        # 超时
        if not self.running:
            self.error_message = self.error_message or "启动超时"
            return False

        return True

    def stop(self):
        """停止服务"""
        if not self.running:
            return

        print("正在停止服务...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def is_running(self):
        """检查服务状态"""
        self.self_running = self.running
        return self.self_running

    def get_error(self):
        """获取错误信息"""
        return self.error_message


class Gen:
    def __init__(self):
        self.index = -1
        self.end = False
        self.running = False
        self._mumu_module = None
        self.service = None  # 单个 SunnyNet 服务
        self.total_devices = 0  # 总设备数
        self.target_count = 0  # 目标设备数
        self.success_count = 0  # 成功生成的设备数
        self.window_count = 1  # 并发窗口数
        self.file_lock = threading.Lock()  # 文件写入锁
        self.create_lock = threading.Lock()  # 创建模拟器的锁，避免同时创建
        self.delete_lock = threading.Lock()  # 删除模拟器的锁，避免同时删除
        self.capture_lock = threading.Lock()  # 抓包锁，保护PID添加/移除和数据读取
        self.start_time = None  # 任务开始时间
        self.log_callback = None  # 日志回调函数
        # 注意：不在这里kill进程，因为任务会正常创建-使用-删除模拟器
    
    def _log(self, message):
        """统一日志输出"""
        print(message)  # 打印到控制台
        if self.log_callback:
            try:
                self.log_callback(message)  # 输出到UI
            except:
                pass
    
    def _get_mumu(self):
        """延迟导入 MuMu 模块"""
        if self._mumu_module is None:
            try:
                from mumu.mumu import Mumu
                self._mumu_module = Mumu
            except Exception as e:
                self._log(f"导入 MuMu 模块失败: {e}")
                return None
        return self._mumu_module
    
    def get_progress_info(self):
        """获取当前进度信息"""
        elapsed_time = 0
        if self.start_time:
            elapsed_time = int(time.time() - self.start_time)
        
        return {
            'success_count': self.success_count,
            'target_count': self.target_count,
            'elapsed_time': elapsed_time,
            'running': self.running
        }
    
    def set_log_callback(self, callback):
        """设置日志回调函数"""
        self.log_callback = callback

    def create_emulator_internal(self):
        """内部创建模拟器方法 - 调用者需要持有锁"""
        Mumu = self._get_mumu()
        if Mumu is None:
            return False, "MuMu 模块导入失败"
        
        try:
            mm = Mumu()

            # 创建模拟器
            index = mm.core.create(1)
            if len(index) < 1:
                return False, "模拟器创建失败"
            emulator_index = index[0]
            print(f"✅ 创建模拟器成功，索引: {emulator_index}")
            
            # 选择模拟器
            mumu = Mumu().select(emulator_index)
            return True, mumu
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"创建模拟器时出错: {e}"

    def start_emulator(self, mm):
        # 设置分辨率（最小配置，节省资源）
        mm.screen.resolution_mobile()
        mm.screen.resolution(360, 640)
        mm.screen.dpi(120)
        mm.power.start()
        flag = False
        for i in range(20):
            if self.end:
                break
            try:
                info = mm.info.get_info()
                if info["player_state"] == "start_finished":
                    print(f"模拟器启动完成 (耗时: {i+1}秒)")
                    flag = True
                    break
            except Exception as e:
                pass
            time.sleep(1)
            
        if not flag:
            print("模拟器启动超时")
            
        return flag

    def install_app(self, mm):
        apk_path = os.path.abspath(r'source/tm13.12.2.apk')
        print(f"尝试安装 APK: {apk_path}")
        
        if not os.path.exists(apk_path):
            print(f"APK 文件不存在: {apk_path}")
            return False
            
        try:
            mm.app.install(apk_path)
            print("APK 安装命令已执行")
        except Exception as e:
            print(f"APK 安装失败: {e}")
            return False
            
        flag = False
        for i in range(30):  # 增加等待时间到 30 秒
            if self.end:
                break
            try:
                info = mm.app.get_installed()
                print(f"检查安装状态 ({i+1}/30): 找到 {len(info)} 个应用")
                
                # 检查是否包含天猫应用
                for app in info:
                    if app.get('package') == 'com.tmall.wireless':
                        print(f"找到天猫应用: {app}")
                        flag = True
                        break
                        
            except Exception as e:
                print(f"检查安装状态时出错: {e}")
            time.sleep(1)
            if flag:
                break
                
        if flag:
            print("应用安装成功！")
        else:
            print("应用安装超时或失败")
            
        return flag

    def launch_app(self, mm):
        print("启动天猫应用...")
        mm.app.launch('com.tmall.wireless')
        flag = False
        for i in range(30):  # 增加等待时间，低配置启动应用可能较慢
            if self.end:
                break
            try:
                info = mm.app.state('com.tmall.wireless')
                if info == "running":
                    print(f"应用启动成功 (耗时: {i+1}秒)")
                    flag = True
                    break
            except Exception as e:
                pass
            time.sleep(1)
            
        if not flag:
            print("应用启动超时")
            
        return flag

    def stop_capture(self, service: SunnyNetService):
        service.stop()
        flag = False
        for i in range(20):
            if self.end:
                break
            try:
                if not service.is_running():
                    flag = True
            except Exception as e:
                pass
            time.sleep(0.3)
            if flag:
                break
        return flag

    def shutdown_del(self, mm):
        """完全清理单个模拟器 - 增强版，确保删除成功"""
        try:
            # 第一步：关闭模拟器
            for retry in range(3):  # 增加重试次数
                try:
                    mm.power.shutdown()
                    print("✓ 模拟器已关闭")
                    break
                except Exception as e:
                    if retry == 2:
                        print(f"⚠️ 关闭模拟器失败: {e}")
                    else:
                        time.sleep(1.0)  # 增加重试等待时间
            
            # 增加等待时间，确保进程完全停止
            time.sleep(2.5)
            
            # 第二步：停止模拟器进程
            for retry in range(3):  # 增加重试次数
                try:
                    mm.power.stop()
                    print("✓ 模拟器进程已停止")
                    break
                except Exception as e:
                    if retry == 2:
                        print(f"⚠️ 停止模拟器进程失败: {e}")
                    else:
                        time.sleep(1.0)  # 增加重试等待时间
            
            # 增加等待时间，确保进程完全停止
            time.sleep(2.5)
            
            # 第三步：删除模拟器（使用锁保护，避免同时删除）
            with self.delete_lock:
                delete_success = False
                for retry in range(5):  # 增加重试次数到5次
                    try:
                        mm.core.delete()
                        print("✓ 模拟器已删除")
                        delete_success = True
                        break
                    except Exception as e:
                        if retry == 4:
                            print(f"⚠️ 删除模拟器失败(已重试5次): {e}")
                            print("🔧 尝试强制清理进程...")
                            # 强制终止所有MuMu进程
                            try:
                                kill_processes_by_keyword("MuMuPlayer", force=True)
                                time.sleep(2)
                                # 再次尝试删除
                                try:
                                    mm.core.delete()
                                    print("✓ 强制清理后删除成功")
                                    delete_success = True
                                except:
                                    print("❌ 强制清理后仍然无法删除，跳过")
                            except Exception as force_e:
                                print(f"❌ 强制清理失败: {force_e}")
                        else:
                            print(f"⚠️ 删除失败，第{retry+1}次重试，等待1.5秒...")
                            time.sleep(1.5)  # 增加等待时间
                
                # 等待删除操作完成
                time.sleep(0.5)
            
            if delete_success:
                print("✅ 单个模拟器清理完成")
            else:
                print("⚠️ 单个模拟器清理未完全成功，可能有残留")
            
        except Exception as e:
            print(f"❌ 清理模拟器过程中出错: {e}")
            import traceback
            traceback.print_exc()

    def task(self, worker_id=None):
        """
        执行单个设备生成任务
        """
        # 使用共享的SunnyNet服务
        service = self.service
        if not service or not service.running:
            return False, "SunnyNet服务未启动"
        
        mm = None  # 初始化 mm，确保 finally 中可以访问
        try:
            # 使用锁保护创建和设置分辨率操作
            if worker_id:
                self._log(f"🔒 [窗口{worker_id}] 等待创建模拟器...")
            with self.create_lock:
                if worker_id:
                    self._log(f"✓ [窗口{worker_id}] 开始创建模拟器")
                success, mm = self.create_emulator_internal()
                if not success:
                    return success, mm
            
                # 在锁内完成分辨率设置（最小配置，节省资源）
                mm.screen.resolution_mobile()
                mm.screen.resolution(360, 640)
                mm.screen.dpi(120)
                log_prefix = f"[窗口{worker_id}]" if worker_id else ""
                self._log(f"✓ {log_prefix} 分辨率设置完成 (360x640, DPI:120)")
                
                # 创建完成后间隔一下，避免创建过快导致问题
                time.sleep(2.0)  # 增加延迟，确保系统稳定
            
            # 记录启动前的进程PID
            pids_before = set()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['MuMuNxDevice.exe', 'MuMuVMMHeadless.exe']:
                        pids_before.add(proc.info['pid'])
                except:
                    pass
            
            # 锁释放后，启动模拟器（可以并行）
            log_prefix = f"[窗口{worker_id}]" if worker_id else ""
            self._log(f"🚀 {log_prefix} 正在启动模拟器...")
            
            # 启动前稍作延迟，避免系统资源冲突
            time.sleep(1.0)
            mm.power.start()
            flag = False
            for i in range(25):  # 缩短到25秒超时
                if self.end:
                    self._log(f"⚠️ {log_prefix} 任务被中止")
                    return False, "任务被中止"
                try:
                    info = mm.info.get_info()
                    state = info.get("player_state", "unknown")
                    
                    # 每5秒输出一次状态
                    if i % 5 == 0 and i > 0:
                        self._log(f"  {log_prefix} [启动中] 状态: {state}, 已等待: {i}秒")
                    
                    if state == "start_finished":
                        self._log(f"✅ {log_prefix} 模拟器启动完成 (耗时: {i+1}秒)")
                        flag = True
                        break
                    elif state == "wait":
                        self._log(f"⚠️ {log_prefix} 模拟器进入等待状态 ({i}秒)")
                except Exception as e:
                    if i % 10 == 0:
                        self._log(f"  检查状态异常: {e}")
                time.sleep(1)
                
            if not flag:
                self._log(f"❌ {log_prefix} 模拟器启动超时(25秒)")
                return False, "模拟器启动超时"
            
            time.sleep(1.0)
            
            # 安装APP
            self._log(f"📦 {log_prefix} 正在安装APP...")
            if not self.install_app(mm):
                return False, "APP安装失败"
            self._log(f"✓ {log_prefix} APP安装完成")

            # 获取新启动的模拟器进程PID（启动后 - 启动前）
            self._log(f"🔍 {log_prefix} 正在获取模拟器进程PID...")
            pids_after = set()
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['MuMuNxDevice.exe', 'MuMuVMMHeadless.exe']:
                        pids_after.add(proc.info['pid'])
                except:
                    pass
            
            # 新增的PID就是当前模拟器的PID
            emulator_pids = list(pids_after - pids_before)
            
            if not emulator_pids:
                self._log(f"⚠️ {log_prefix} 未找到新增PID，将监听所有MuMu进程")
                emulator_pids = list(pids_after)  # fallback: 使用所有PID
            else:
                self._log(f"✓ {log_prefix} 找到新增 PID: {emulator_pids}")
            
            # 启动APP
            self._log(f"▶️ {log_prefix} 正在启动APP...")
            if not self.launch_app(mm):
                self._log(f"❌ {log_prefix} APP启动失败")
                return False, "APP运行失败"
            
            # 获取模拟器窗口句柄（用于后台点击）
            # 访问私有变量 __vm_index (Python名称修饰：_Mumu__vm_index)
            vm_index = mm._Mumu__vm_index
            self._log(f"🔍 {log_prefix} 正在查找窗口句柄 (模拟器索引:{vm_index})...")
            
            # 等待窗口显示，重试5次，每次等待更长时间
            window_hwnd = None
            for retry in range(5):
                window_hwnd = find_mumu_window(vm_index, debug=(retry==0))  # 第一次启用调试
                if window_hwnd:
                    self._log(f"✓ {log_prefix} 第{retry+1}次查找成功")
                    break
                if retry < 4:
                    wait_time = 2  # 等待2秒
                    self._log(f"  {log_prefix} 第{retry+1}次未找到，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
            
            if window_hwnd:
                self._log(f"✓ {log_prefix} 找到窗口句柄: {window_hwnd}")
            else:
                self._log(f"⚠️ {log_prefix} 未找到窗口句柄，将使用ADB点击")
            
            # 添加当前模拟器进程到监听列表
            self._log(f"📡 {log_prefix} 添加PID监听: {emulator_pids}")
            for pid in emulator_pids:
                service.app.process_add_pid(pid)
            
            time.sleep(0.5)  # 等待PID监听生效
            
            # 清空该PID的旧数据
            with service.deviceInfo_lock:
                for pid in emulator_pids:
                    service.deviceInfo_by_pid.pop(pid, None)
            
            # 等待抓包
            self._log(f"📶 {log_prefix} 开始抓包 (监听PID: {emulator_pids})...")
            captured_device_info = None
            
            # 添加随机初始延迟，让不同窗口的点击时间错开
            import random
            initial_offset = random.uniform(0, 0.5)  # 0-0.5秒随机延迟
            time.sleep(initial_offset)
            
            for i in range(30):  # 30
                if self.end:  # 检查是否被停止
                    self._log(f"⚠️ {log_prefix} 任务被中止(抓包阶段)")
                    return False, "任务被中止"
                
                # 点击界面（优先使用窗口句柄后台点击，完全绕过ADB）
                click_success = False
                
                # 方案1：窗口句柄点击（推荐，不会卡死）
                if window_hwnd:
                    try:
                        if click_window_background(window_hwnd, 176, 458):
                            click_success = True
                            if i == 0 or i % 3 == 0:
                                self._log(f"  👆 {log_prefix} [窗口句柄] 点击界面 (第{i+1}次)")
                    except Exception as e:
                        self._log(f"  ⚠️ {log_prefix} 窗口句柄点击失败: {e}，尝试ADB")
                
                # 方案2：ADB点击（fallback，可能卡死）
                if not click_success:
                    try:
                        mm.adb.click(176, 458)
                        if i == 0 or i % 3 == 0:
                            self._log(f"  👆 {log_prefix} [ADB] 点击界面 (第{i+1}次)")
                    except Exception as e:
                        self._log(f"  ⚠️ {log_prefix} 点击失败(第{i+1}次): {e}")
                
                # 增加点击间隔到1.5秒，降低并发压力
                time.sleep(1.5)
                
                # 检查是否有任何一个PID对应的数据被捕获
                with service.deviceInfo_lock:
                    for pid in emulator_pids:
                        if pid in service.deviceInfo_by_pid:
                            captured_device_info = service.deviceInfo_by_pid[pid]
                            # 删除已使用的数据
                            del service.deviceInfo_by_pid[pid]
                            self._log(f"✅ {log_prefix} 抓包成功！(PID: {pid}, 耗时: {i+1}秒)")
                            break
                
                if captured_device_info:
                    break
                
                # 每5秒输出一次进度
                if i > 0 and i % 3 == 0:  # 因为间隔是1.5秒，所以每3次约等于5秒
                    elapsed = int((i + 1) * 1.5)
                    self._log(f"  📊 {log_prefix} 抓包中... (已等待约{elapsed}秒/共45秒)")
            
            # 移除PID监听
            self._log(f"🔕 {log_prefix} 移除PID监听: {emulator_pids}")
            for pid in emulator_pids:
                service.app.process_del_pid(pid)
            
            if not captured_device_info:
                # 45秒后仍未抓到包
                self._log(f"⚠️ {log_prefix} 45秒内未抓到包，放弃当前模拟器")
                return False, "抓包超时"

            # 抓包成功
            self._log(f"✅ {log_prefix} 任务完成")
            return True, "运行完成"
            
        finally:
            # 无论如何都要清理模拟器
            if mm is not None:
                log_prefix = f"[窗口{worker_id}]" if worker_id else ""
                self._log(f"🧹 {log_prefix} 正在清理模拟器...")
                try:
                    self.shutdown_del(mm)
                    self._log(f"✓ {log_prefix} 模拟器已清理")
                except Exception as e:
                    self._log(f"❌ {log_prefix} 清理模拟器失败: {e}")

    def batch_generate_worker(self, worker_id):
        """
        单个工作线程，循环生成设备
        worker_id: 窗口编号
        """
        # 错开线程启动时间，避免同时启动多个模拟器导致卡顿
        initial_delay = (worker_id - 1) * 2.0  # 每个线程延迟2秒启动，避免冲突
        if initial_delay > 0:
            self._log(f"⏳ [窗口{worker_id}] 等待 {initial_delay} 秒后启动...")
            time.sleep(initial_delay)
        
        self._log(f"🔧 [窗口{worker_id}] 工作线程启动")
        
        while not self.end and self.success_count < self.target_count:
            try:
                # 使用共享的SunnyNet服务，通过PID区分不同窗口的数据
                success, result = self.task(worker_id=worker_id)
                
                if success:
                    # task成功返回意味着已经抓到了新设备
                    with self.file_lock:  # 使用锁保护计数器
                        self.success_count += 1
                        current = self.success_count
                    self._log(f"✅ [窗口{worker_id}] 成功生成设备 ({current}/{self.target_count})")
                else:
                    self._log(f"❌ [窗口{worker_id}] 生成失败: {result}")
                
                # 短暂休息（减少等待时间）
                time.sleep(0.5)
                
            except Exception as e:
                self._log(f"❌ [窗口{worker_id}] 异常: {e}")
                import traceback
                traceback.print_exc()
        
        self._log(f"🛑 [窗口{worker_id}] 工作线程结束")

    def _run_batch(self):
        """批量生成设备的主循环 - 共享SunnyNet服务 + PID区分"""
        try:
            self.running = True
            self.success_count = 0
            self.start_time = time.time()  # 记录开始时间
            self._log(f"⏰ 任务开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}")
            
            # 初始化共享的 SunnyNet 服务
            port = 2025
            self._log(f"🌐 初始化共享抓包服务 (端口: {port})...")
            kill_process_by_port(port)
            self.service = SunnyNetService(port=port, pid=[])  # 不预设PID
            
            if not self.service.start():
                error_msg = self.service.get_error()
                self._log(f"❌ SunnyNet 服务启动失败: {error_msg}")
                if "管理员权限" in error_msg:
                    self._log("⚠️ 【重要】请以管理员身份运行本程序！")
                self.running = False
                return
            
            self._log(f"✅ SunnyNet 共享服务已启动")
            time.sleep(2)  # 等待服务稳定
            
            # 验证服务是否真的在运行
            if not self.service.running:
                error_msg = self.service.get_error()
                self._log(f"❌ 服务启动后停止: {error_msg}")
                if "管理员权限" in error_msg or "驱动加载失败" in error_msg:
                    self._log("⚠️ 【重要】请以管理员身份运行本程序！")
                self.running = False
                return
            
            # 清理所有现有的MuMu模拟器
            self._log("🧹 正在清理所有现有的MuMu模拟器...")
            try:
                Mumu = self._get_mumu()
                if Mumu:
                    mm = Mumu()
                    # 使用新封装的delete_all方法
                    mm.core.delete_all()
                    self._log("✅ 所有模拟器已清理完成")
            except Exception as e:
                error_msg = str(e)
                # 可能是没有模拟器可删除
                if "not found" in error_msg.lower() or "不存在" in error_msg or "no player" in error_msg.lower():
                    self._log("✓ 没有需要清理的模拟器")
                else:
                    self._log(f"⚠️ 清理模拟器时出错: {e}")
            
            # 删除后等待系统稳定
            self._log("⏳ 等待删除完成，系统稳定中...")
            time.sleep(5)  # 等待5秒让系统完全处理删除操作
            
            # 重启MuMu控制台 - 先杀死所有MuMu进程
            self._log("🔄 正在重启MuMu控制台...")
            try:
                # 获取MuMuManager路径（先获取，后面需要用）
                Mumu = self._get_mumu()
                mumu_manager_path = None
                if Mumu:
                    mm = Mumu()
                    mumu_manager_path = mm._Mumu__mumu_manager
                
                # 第一步：使用kill_processes_by_keyword强制杀死所有包含"MuMu"的进程
                self._log("  🔪 正在杀死所有MuMu相关进程...")
                killed_count = kill_processes_by_keyword("MuMu", force=True)
                
                if killed_count > 0:
                    self._log(f"  ✓ 共杀死 {killed_count} 个进程")
                    time.sleep(3)  # 等待进程完全关闭
                else:
                    self._log("  ℹ️ 没有找到运行中的MuMu进程")
                
                # 第二步：验证进程已全部关闭
                remaining = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        name = proc.info['name'] or ""
                        cmdline = proc.info['cmdline'] or []
                        cmdline_str = " ".join(cmdline)
                        
                        # 检查关键词是否在进程名或命令行中
                        if "MuMu" in name or "MuMu" in cmdline_str:
                            remaining.append(f"{name}({proc.info['pid']})")
                    except:
                        pass
                
                if remaining:
                    self._log(f"  ⚠️ 仍有残留进程: {remaining}")
                else:
                    self._log("  ✓ 所有MuMu进程已完全关闭")
                
                # 第三步：重新启动MuMuManager
                if mumu_manager_path:
                    self._log(f"  🚀 正在启动MuMuManager: {mumu_manager_path}")
                    
                    # 启动MuMuManager（后台启动，不显示窗口）
                    startupinfo = None
                    creationflags = 0
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        creationflags = 0x08000000  # CREATE_NO_WINDOW
                    
                    subprocess.Popen([mumu_manager_path], 
                                   startupinfo=startupinfo, 
                                   creationflags=creationflags)
                    self._log(f"  ✓ MuMuManager已启动")
                    
                    # 等待MuMuManager完全启动
                    time.sleep(5)  # 增加等待时间
                    
                    # 验证MuMuManager是否真的启动了
                    manager_started = False
                    for proc in psutil.process_iter(['pid', 'name']):
                        try:
                            if proc.info['name'] == 'MuMuManager.exe':
                                self._log(f"  ✓ MuMuManager进程已运行 (PID: {proc.info['pid']})")
                                manager_started = True
                                break
                        except:
                            pass
                    
                    if manager_started:
                        self._log("✅ MuMu控制台重启成功")
                    else:
                        self._log("⚠️ MuMuManager可能未成功启动")
                else:
                    self._log("❌ 无法获取MuMuManager路径")
                    
            except Exception as e:
                self._log(f"⚠️ 重启MuMu控制台时出错: {e}")
                import traceback
                traceback.print_exc()
                self._log("  ℹ️ 继续执行任务...")
            
            self._log("⏳ 等待系统稳定...")
            time.sleep(3)  # 增加等待时间，让系统稳定
            
            self._log(f"📋 准备启动 {self.window_count} 个并发窗口，目标生成 {self.target_count} 个设备")
            self._log(f"💡 通过PID区分不同窗口的流量，完全并行，互不干扰！")
            time.sleep(1)
            
            # 创建工作线程
            threads = []
            for i in range(self.window_count):
                thread = threading.Thread(
                    target=self.batch_generate_worker, 
                    args=(i+1,),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
            
            # 等待所有线程完成
            for thread in threads:
                thread.join()
            
            self._log(f"🎉 批量生成完成！成功: {self.success_count}/{self.target_count}")
            
        except Exception as e:
            self._log(f"❌ 批量生成异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理共享服务
            if self.service:
                self._log("🧹 停止共享抓包服务...")
                self.service.stop()
                self.service = None
            self.running = False

    def _run(self):
        while True:
            try:
                self.running = True
                print(self.task())

                if self.end:
                    break
                time.sleep(3)
            except Exception as e:
                pass
        self.running = False

    def start_task(self, device_count=0, window_count=1):
        """
        启动设备生成任务
        
        Args:
            device_count: 要生成的设备数量，0表示无限循环
            window_count: 并发窗口数
        """
        self.end = False
        self.target_count = device_count if device_count > 0 else 999999
        self.window_count = max(1, min(window_count, 10))  # 限制在1-10之间
        
        if device_count > 0:
            # 批量生成模式
            self.thread = threading.Thread(target=self._run_batch, daemon=True)
        else:
            # 无限循环模式
            kill_process_by_port(2025)
            self.service = SunnyNetService(port=2025)
            self.service.start()
            self.thread = threading.Thread(target=self._run, daemon=True)
        
        self.thread.start()

    def end_task(self):
        if self.thread:
            self.thread.join(timeout=5)

    def stop_task(self):
        kill_processes_by_keyword("MuMu", True)
        
        # 停止服务
        if hasattr(self, 'service') and self.service:
            self.service.stop()
        
        self.end = True
        threading.Thread(target=self.end_task, daemon=True).start()

    def get_status(self):
        return self.running


if __name__ == '__main__':
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='批量生成设备参数')
    parser.add_argument('-n', '--num', type=int, default=0, 
                        help='要生成的设备数量（默认0表示一直运行）')
    parser.add_argument('-w', '--windows', type=int, default=1, 
                        help='并发窗口数（默认1，范围1-10）')
    
    args = parser.parse_args()
    
    device_count = args.num
    window_count = args.windows
    
    print("="*60)
    print("🚀 设备参数批量生成工具")
    print("="*60)
    if device_count > 0:
        print(f"📊 生成数量: {device_count} 个")
    else:
        print(f"📊 生成数量: 无限循环")
    print(f"🪟 并发窗口: {window_count} 个")
    print("="*60)
    print()
    
    gen = Gen()
    try:
        # 启动批量生成任务
        gen.start_task(device_count=device_count, window_count=window_count)
        
        # 等待任务完成或用户中断
        while gen.running:
            time.sleep(1)
        
        print(f"\n✅ 任务完成")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断任务")
        gen.stop_task()
    except Exception as e:
        import traceback
        print(f"❌ 任务执行出错: {e}")
        traceback.print_exc()
    finally:
        # 清理资源
        if hasattr(gen, 'service') and gen.service:
            gen.service.stop()
            print("🛑 SunnyNet服务已停止")
        kill_processes_by_keyword("MuMu", True)
        print("🧹 清理完成")
