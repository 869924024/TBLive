from loguru import logger
import time
import threading
from SunnyNet.Event import HTTPEvent
from SunnyNet.SunnyNet import SunnyNet as Sunny
import psutil
import os
import subprocess
import socket


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

    print(f"找到 {len(found_processes)} 个匹配的进程:\n")
    for proc in found_processes:
        print(f"PID: {proc['pid']}")
        print(f"名称: {proc['name']}")
        print(f"命令: {proc['cmdline']}")
        print("-" * 80)

    # 终止进程
    print("\n开始终止进程...")
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

        except psutil.NoSuchProcess:
            print(f"✗ 进程 {proc_info['pid']} 已不存在")
        except psutil.AccessDenied:
            print(f"✗ 权限不足，无法终止进程 {proc_info['pid']} ({proc_info['name']})")
        except Exception as e:
            print(f"✗ 终止进程 {proc_info['pid']} 时出错: {e}")

    return killed_count


def get_free_port():
    # 创建一个 socket 实例
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))  # 绑定到任意地址，端口为0让系统自动分配空闲端口
    port = s.getsockname()[1]  # 获取被分配的端口
    s.close()
    return port


TARGET_HEADERS = ["x-umt", "x-sgext", "x-mini-wua", "x-ttid", "x-utdid", "x-devid"]


def manage_file_line(filename, check_string, write_string):
    if check_string == "":
        return ""
    """
    管理文件内容：自动创建文件或追加内容，确保无空行

    参数:
        filename: 文件名
        check_string: 判断字符串，用于检查是否已存在
        write_string: 写入行字符串，不存在时追加

    返回:
        str: 'exists' 表示内容已存在，'added' 表示已追加内容，'created' 表示已创建新文件
    """
    import os

    # 如果文件不存在，创建新文件并写入
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(write_string)
        return 'created'

    # 文件存在，读取内容
    with open(filename, 'r', encoding='utf-8') as f:
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
                    logger.info("捕获到设备信息: " + str_data)
                    manage_file_line("设备.txt", headers_dict.get("x-devid", ""), str_data)
                    self.is_captured = True
                    self.deviceInfo = str_data
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
        kill_processes_by_keyword("MuMu", True)
    
    def _get_mumu(self):
        """延迟导入 MuMu 模块"""
        if self._mumu_module is None:
            try:
                from mumu.mumu import Mumu
                self._mumu_module = Mumu
            except Exception as e:
                print(f"导入 MuMu 模块失败: {e}")
                return None
        return self._mumu_module

    def create_emulator(self):
        """完整的任务流程"""
        Mumu = self._get_mumu()
        if Mumu is None:
            return False, "MuMu 模块导入失败"
        
        try:
            mm = Mumu()

            # 创建模拟器
            index = mm.core.create(1)
            if len(index) < 1:
                return False, "模拟器创建失败"
            self.index = index[0]
            print("设备：" + str(self.index))
            mumu = Mumu().select(self.index)
            return True, mumu
        except Exception as e:
            return False, f"创建模拟器时出错: {e}"

    def start_emulator(self, mm):
        # 设置分辨率
        mm.screen.resolution_mobile()
        mm.screen.resolution(900, 1600)
        mm.screen.dpi(320)
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
        try:
            mm.power.shutdown()
            mm.power.stop()
            mm.info.info_all()
            time.sleep(3)
            mm.core.delete()
            kill_processes_by_keyword("MuMu", True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(str(e))
            pass
        try:
            Mumu = self._get_mumu()
            if Mumu is not None:
                m2 = Mumu().all()
                m2.power.shutdown()
                m2.power.stop()
                m2.core.delete()
            kill_processes_by_keyword("MuMu", True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(str(e))
            pass

    def task(self):
        # 如果 service 未初始化（独立调用），则先初始化
        if not hasattr(self, 'service') or self.service is None:
            kill_process_by_port(2025)
            self.service = SunnyNetService(port=2025)
            if not self.service.start():
                return False, "SunnyNet服务启动失败"
            time.sleep(2)  # 等待服务完全启动

        self.service.is_captured = False
        success, mm = self.create_emulator()
        if not success:
            return success, mm

        if not self.start_emulator(mm):
            self.shutdown_del(mm)
            return False, "模拟器启动失败"
        time.sleep(1.5)
        if not self.install_app(mm):
            self.shutdown_del(mm)
            return False, "APP安装失败"

        if not self.launch_app(mm):
            self.shutdown_del(mm)
            return False, "APP运行失败"
        # 秒启动时间
        for i in range(10):
            mm.adb.click(440, 1142)
            if self.service.is_captured:
                break
            time.sleep(1)

        self.shutdown_del(mm)
        return True, "运行完成"

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

    def start_task(self):
        kill_process_by_port(2025)
        self.service = SunnyNetService(port=2025)
        self.service.start()
        self.end = False
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def end_task(self):
        if self.thread:
            self.thread.join(timeout=5)

    def stop_task(self):
        kill_processes_by_keyword("MuMu", True)
        self.service.stop()
        self.end = True
        threading.Thread(target=self.end_task, daemon=True).start()

    def get_status(self):
        return self.running


if __name__ == '__main__':
    gen = Gen()
    try:
        result = gen.task()
        print(f"✅ 任务完成: {result}")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断任务")
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
