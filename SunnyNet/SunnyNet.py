import ctypes
import inspect

from . import SunnyDLL
from .CertManager import CertManager
from ctypes import *
from typing import Callable

from .Event import HTTPEvent, TCPEvent, UDPEvent, WebSocketEvent
from .SunnyDLL import PtrToInt
from .tools import check_function_signature


def Version():
    """ 获取SunnyNet DLL版本 """
    return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.GetSunnyVersion())


class SunnyNet:
    """ SunnyNet网络中间件 """

    # 以下是常量信息
    """ 规则内走TCP """
    MustTcpRegexp_Within = False
    """ 规则外走TCP """
    MustTcpRegexp_Outside = True
    """ 证书使用规则，仅请求时使用 """
    CertRules_Request = 1
    """ 证书使用规则，解析和请求时都使用 """
    CertRules_Request_Response = 2
    """ 证书使用规则，仅解析时使用 """
    CertRules_Response = 3

    def __init__(self):
        """ 创建Sunny中间件对象, 可创建多个实例 """
        self.__ws_callback = SunnyDLL.WsCallback(self.__ws_callback__)
        self.__tcp_callback = SunnyDLL.TcpCallback(self.__tcp_callback__)
        self.__http_callback = SunnyDLL.HttpCallback(self.__http_callback__)
        self.__udp_callback = SunnyDLL.UDPCallback(self.__udp_callback__)
        self.__ScriptLogCallback = SunnyDLL.ScriptLogCallback(self.__ScriptLogCallback__)
        self.__ScriptCodeCallback = SunnyDLL.ScriptCodeCallback(self.__ScriptCodeCallback__)

        self.__ws_callback__py = None
        self.__tcp_callback__py = None
        self.__http_callback__py = None
        self.__udp_callback__py = None
        self.__ScriptLogCallback__py = None
        self.__ScriptCodeCallback__py = None

        self.__context = SunnyDLL.DLLSunny.CreateSunnyNet()

    def __del__(self):
        """ 释放SunnyNet资源 """
        SunnyDLL.DLLSunny.ReleaseSunnyNet(self.__context)

    def __http_callback__(self, SunnyContext, TheologyID, MessageId, EventType, Method, URL, Error, pid):
        if self.__http_callback__py is None:
            return
        _SunnyContext = PtrToInt(SunnyContext)
        _EventType = PtrToInt(EventType)
        _Method = SunnyDLL.BytesToText(Method)
        _URL = SunnyDLL.BytesToText(URL)
        _Error = SunnyDLL.BytesToText(Error)
        _pid = PtrToInt(pid)
        _TheologyID = PtrToInt(TheologyID)
        _MessageId = PtrToInt(MessageId)
        obj = HTTPEvent(_SunnyContext, _TheologyID, _MessageId, _EventType, _Method, _URL, _Error, _pid)
        self.__http_callback__py(obj)

    def __tcp_callback__(self, SunnyContext, LocalAddr, RemoteAddr, EventType, MessageId, data, ln, TheologyID, pid):
        if self.__tcp_callback__py is None:
            return
        _SunnyContext = PtrToInt(SunnyContext)
        _EventType = PtrToInt(EventType)
        _pid = PtrToInt(pid)
        _LocalAddr = SunnyDLL.BytesToText(LocalAddr)
        _RemoteAddr = SunnyDLL.BytesToText(RemoteAddr)
        _TheologyID = PtrToInt(TheologyID)
        _MessageId = PtrToInt(MessageId)
        _bs = SunnyDLL.PtrToByte(data, 0, ln)
        obj = TCPEvent(_SunnyContext, _LocalAddr, _RemoteAddr, _TheologyID, _MessageId, _EventType, _pid, _bs)
        self.__tcp_callback__py(obj)

    def __udp_callback__(self, SunnyContext, LocalAddr, RemoteAddr, EventType, MessageId, TheologyID, pid):
        if self.__udp_callback__py is None:
            return
        _SunnyContext = PtrToInt(SunnyContext)
        _EventType = PtrToInt(EventType)
        _pid = PtrToInt(pid)
        _LocalAddr = SunnyDLL.BytesToText(LocalAddr)
        _RemoteAddr = SunnyDLL.BytesToText(RemoteAddr)
        _TheologyID = PtrToInt(TheologyID)
        _MessageId = PtrToInt(MessageId)
        obj = UDPEvent(_SunnyContext, _LocalAddr, _RemoteAddr, _TheologyID, _MessageId, _EventType, _pid)
        self.__udp_callback__py(obj)

    def __ws_callback__(self, SunnyContext, TheologyID, MessageId, EventType, Method, URL, pid, wsType):
        if self.__ws_callback__py is None:
            return
        _SunnyContext = PtrToInt(SunnyContext)
        _EventType = PtrToInt(EventType)
        _Method = SunnyDLL.BytesToText(Method)
        _URL = SunnyDLL.BytesToText(URL)
        _pid = PtrToInt(pid)
        _TheologyID = PtrToInt(TheologyID)
        _MessageId = PtrToInt(MessageId)
        _wsType = PtrToInt(wsType)
        obj = WebSocketEvent(_SunnyContext, _TheologyID, _MessageId, _EventType, _Method, _URL, _pid, _wsType)
        self.__ws_callback__py(obj)

    def __ScriptLogCallback__(self, LogInfo):
        if self.__ScriptLogCallback__py == None:
            return
        self.__ScriptLogCallback__py(SunnyDLL.PointerToText(LogInfo))

    def __ScriptCodeCallback__(self, code, l):
        """
        设置回调函数
        """
        if self.__ScriptCodeCallback__py == None:
            return
        buff = SunnyDLL.PtrToByte(code, 0, l)
        try:
            ss = buff.decode('utf-8')
        except:
            ss = buff.decode('gbk')
        self.__ScriptCodeCallback__py(ss)

    def set_callback(self, http_callback: Callable[[HTTPEvent], None] = None,
                     tcp_callback: Callable[[TCPEvent], None] = None,
                     ws_callback: Callable[[WebSocketEvent], None] = None,
                     udp_callback: Callable[[UDPEvent], None] = None,
                     ScriptLogCallback: Callable[[str], None] = None,
                     ScriptCodeCallback: Callable[[str], None] = None) -> None:
        """
        设置回调函数
        :param http_callback: HTTP回调函数
        :param tcp_callback: TCP回调函数
        :param ws_callback: WebSocket回调函数
        :param udp_callback: UDP回调函数
        :param ScriptLogCallback: 脚本日志输出回调 需接收一个 str 参数
        :param ScriptCodeCallback: 脚本代码保存回调 需接收一个 str 参数
        """
        if not check_function_signature(ScriptCodeCallback, (str,), None):
            raise TypeError(f"Callback function type error {type(ScriptCodeCallback).__name__}")
        if not check_function_signature(ScriptLogCallback, (str,), None):
            raise TypeError(f"Callback function type error {type(ScriptLogCallback).__name__}")
        if not check_function_signature(http_callback, (HTTPEvent,), None):
            raise TypeError(f"Callback function type error {type(http_callback).__name__}")
        if not check_function_signature(tcp_callback, (TCPEvent,), None):
            raise TypeError(f"Callback function type error {type(tcp_callback).__name__}")
        if not check_function_signature(udp_callback, (UDPEvent,), None):
            raise TypeError(f"Callback function type error {type(udp_callback).__name__}")
        if not check_function_signature(ws_callback, (WebSocketEvent,), None):
            raise TypeError(f"Callback function type error {type(ws_callback).__name__}")
        self.__ws_callback__py = ws_callback
        self.__tcp_callback__py = tcp_callback
        self.__http_callback__py = http_callback
        self.__udp_callback__py = udp_callback
        self.__ScriptLogCallback__py = ScriptLogCallback
        self.__ScriptCodeCallback__py = ScriptCodeCallback

        SunnyDLL.DLLSunny.SetScriptCall(
            self.__context,
            self.__ScriptLogCallback,
            self.__ScriptCodeCallback
        )

        SunnyDLL.DLLSunny.SunnyNetSetCallback(
            self.__context,
            self.__http_callback,
            self.__tcp_callback,
            self.__ws_callback,
            self.__udp_callback
        )

    def context(self) -> int:
        """ 获取当前Sunny中间件的上下文 """
        return PtrToInt(self.__context)

    def random_ja3(self, enable) -> bool:
        """
        开启或关闭随机的JA3指纹请求
        :param enable: 是否开启随机JA3指纹
        :return: 操作结果，True表示成功
        """
        if not isinstance(enable, bool):
            raise TypeError("参数类型错误：enable 应为布尔值")
        return bool(SunnyDLL.DLLSunny.SetRandomTLS(self.__context, enable))

    def install_cert_to_system(self) -> bool:
        """ 安装中间件的证书到系统中，返回安装结果文本 """
        err = SunnyDLL.PointerToText(SunnyDLL.DLLSunny.SunnyNetInstallCert(self.__context))
        return any(x in err for x in (
            "添加到存储", "已经在存储中", "already in store", "CertUtil: -addstore command completed successfully."))

    def set_port(self, port) -> None:
        """ 在启动之前调用，设置中间件的端口 """
        if not isinstance(port, int):
            raise TypeError("参数类型错误：port 应为整数")
        SunnyDLL.DLLSunny.SunnyNetSetPort(self.__context, port)

    def set_OutRouterIP(self, ip) -> bool:
        """
        设置中间件出口IP函数-全局
        请输入网卡对应的内网IP地址
        输入空文本,则让系统自动选择
        ----
        你也可以在TCP/HTTP回调中对请求单独设置
        """
        if not isinstance(ip, str):
            raise TypeError("参数类型错误：ip 应为字符串")
        return bool(SunnyDLL.DLLSunny.SetOutRouterIP(self.__context, ip))

    def export_cert(self) -> str:
        """ 导出已设置的证书 """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.ExportCert(self.__context))

    def cancel_ie_proxy(self) -> None:
        """ 取消已设置的IE代理 """
        SunnyDLL.DLLSunny.CancelIEProxy(self.__context)

    def set_dns_server(self, server_name: str) -> None:
        """
        设置DNS服务器，仅支持TLS的DNS服务器（853端口）
        :param server_name: DNS服务器地址
        """
        if not isinstance(server_name, str):
            raise TypeError("参数类型错误：server_name 应为字符串")
        SunnyDLL.DLLSunny.SetDnsServer(self.__context, create_string_buffer(server_name.encode("utf-8")))

    def must_tcp(self, enable: bool) -> None:
        """
        开启或关闭TCP直连模式，HTTPS的数据无法解码
        :param enable: 是否开启TCP直连
        """
        if not isinstance(enable, bool):
            raise TypeError("参数类型错误：enable 应为布尔值")
        SunnyDLL.DLLSunny.SunnyNetMustTcp(self.__context, enable)

    def open_verify_user(self, enable: bool) -> None:
        """
        开启或关闭S5代理的身份验证模式
        :param enable: 是否开启身份验证模式
        """
        if not isinstance(enable, bool):
            raise TypeError("参数类型错误：enable 应为布尔值")
        SunnyDLL.DLLSunny.SunnyNetVerifyUser(self.__context, enable)

    def verify_user_add(self, username: str, password: str) -> None:
        """
        添加用户名和密码到身份验证模式
        :param username: 用户名
        :param password: 密码
        """
        if not isinstance(username, str) or not isinstance(password, str):
            raise TypeError("参数类型错误：username 和 password 应为字符串")
        SunnyDLL.DLLSunny.SunnyNetSocket5AddUser(
            self.__context,
            create_string_buffer(username.encode("utf-8")),
            create_string_buffer(password.encode("utf-8"))
        )

    def verify_user_del(self, username: str) -> None:
        """
        从身份验证模式中删除用户名
        :param username: 用户名
        """
        if not isinstance(username, str):
            raise TypeError("参数类型错误：username 应为字符串")
        SunnyDLL.DLLSunny.SunnyNetSocket5DelUser(self.__context, username)

    def start(self) -> bool:
        """ 启动中间件，绑定端口 """
        return bool(SunnyDLL.DLLSunny.SunnyNetStart(self.__context))

    def stop(self) -> None:
        """ 停止中间件并关闭IE代理 """
        self.cancel_ie_proxy()
        SunnyDLL.DLLSunny.SunnyNetClose(self.__context)

    def set_cert(self, cert_manager: CertManager) -> bool:
        """
        导入自己的证书
        :param cert_manager: CertManager对象
        :return: 是否设置成功
        """
        if not isinstance(cert_manager, CertManager):
            raise TypeError("参数类型错误：cert_manager 应为 CertManager 对象")
        result = SunnyDLL.DLLSunny.SunnyNetSetCert(self.__context, cert_manager.context())
        return bool(result)

    def set_script_page(self, page: str) -> str:
        """
        设置脚本编辑器页面
        :param page: 页面字符串
        :return: 当前页面路径或错误信息
        """
        if not isinstance(page, str):
            raise TypeError("参数类型错误：page 应为字符串")
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.SetScriptPage(self.__context, page))

    def is_script_code_supported(self) -> bool:
        """
        当前SDK是否支持脚本代码
        :return: 如果当前SDK是Mini 版本则不支持脚本代码。支持返回 true
        """
        return self.set_script_page("") != "no"

    def set_script_code(self, script_code: str) -> str:
        """
        加载用户的脚本代码
        :param script_code: 脚本代码字符串
        :return: 错误信息或空文本
        """
        if not isinstance(script_code, str):
            raise TypeError("参数类型错误：script_code 应为字符串")
        try:
            data = script_code.encode("gbk")
        except:
            data = script_code.encode("utf-8")
        return SunnyDLL.PointerToText(
            SunnyDLL.DLLSunny.SetScriptPage(self.__context, create_string_buffer(data), len(data)))

    def process_add_name(self, process_name: str) -> None:
        """
        添加指定的进程名进行捕获
        :param process_name: 进程名，例如 e.exe
        """
        if not isinstance(process_name, str):
            raise TypeError("参数类型错误：process_name 应为字符串")
        SunnyDLL.DLLSunny.ProcessAddName(self.__context, create_string_buffer(process_name.encode("utf-8")))

    def process_del_name(self, process_name: str) -> None:
        """
        删除指定的进程名，停止捕获
        :param process_name: 进程名，例如 e.exe
        """
        if not isinstance(process_name, str):
            raise TypeError("参数类型错误：process_name 应为字符串")
        SunnyDLL.DLLSunny.ProcessDelName(self.__context, create_string_buffer(process_name.encode("utf-8")))

    def process_add_pid(self, pid: int) -> None:
        """
        添加指定的进程PID进行捕获
        :param pid: 进程PID，例如 11223
        """
        if not isinstance(pid, int):
            raise TypeError("参数类型错误：pid 应为整数")
        SunnyDLL.DLLSunny.ProcessAddPid(self.__context, pid)

    def process_del_pid(self, pid: int) -> None:
        """
        删除指定的进程PID，停止捕获
        :param pid: 进程PID，例如 11223
        """
        if not isinstance(pid, int):
            raise TypeError("参数类型错误：pid 应为整数")
        SunnyDLL.DLLSunny.ProcessDelPid(self.__context, pid)

    def process_all(self, enable: bool, StopNetwork: bool) -> None:
        """
        开启或关闭所有进程的捕获
        :param enable: 是否捕获所有进程
        :param StopNetwork: 是否对所有进程断网一次
        """
        if not isinstance(enable, bool):
            raise TypeError("参数类型错误：enable 应为布尔值")
        if not isinstance(StopNetwork, bool):
            raise TypeError("参数类型错误：StopNetwork 应为布尔值")
        SunnyDLL.DLLSunny.ProcessALLName(self.__context, enable, StopNetwork)

    def process_cancel_all(self) -> None:
        """ 删除已设置的所有PID和进程名 """
        SunnyDLL.DLLSunny.ProcessCancelAll(self.__context)

    def error(self) -> str:
        """ 获取中间件启动时的错误信息 """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.SunnyNetError(self.__context))

    def set_http_request_max_update_length(self, max_update_length: int) -> bool:
        """
        设置HTTP请求的最大更新长度
        :param max_update_length: 最大更长度（字节） 默认：10240000 字节,如果超过此长度的POST数据,在回调函数中无法直接查看,请使用“Conn.Request.原始数据储存到文件”命令来储存
        :return: 是否设置成功
        """
        if not isinstance(max_update_length, int):
            raise TypeError("参数类型错误：max_update_length 应为整数")
        return bool(SunnyDLL.DLLSunny.SetHTTPRequestMaxUpdateLength(self.__context, max_update_length))

    def disable_tcp(self, disable: bool) -> bool:
        """
        禁止非HTTP/S的TCP连接
        :param disable: 是否禁用TCP
        :return: 是否成功
        """
        if not isinstance(disable, bool):
            raise TypeError("参数类型错误：disable 应为布尔值")
        return bool(SunnyDLL.DLLSunny.DisableTCP(self.__context, disable))

    def disable_udp(self, disable: bool) -> bool:
        """
        禁止非HTTP/S的UDP连接
        :param disable: 是否禁用UDP
        :return: 是否成功
        """
        if not isinstance(disable, bool):
            raise TypeError("参数类型错误：disable 应为布尔值")
        return bool(SunnyDLL.DLLSunny.DisableUDP(self.__context, disable))

    def cancel_proxy(self):
        """
        取消设置的上游代理
        """
        self.set_proxy("",0)
        
    def set_proxy(self, proxy_url: str,outTime:int) -> bool:
        """
        设置上游代理，仅支持S5代理或HTTP代理。

        :param proxy_url: 代理URL，格式示例：
                          - HTTP代理（带账号密码）：
                            http://admin:123456@127.0.0.1:8888
                          - S5代理（带账号密码）：
                            socket5://admin:123456@127.0.0.1:8888
                          - HTTP代理（无账号密码）：
                            http://127.0.0.1:8888
                          - S5代理（无账号密码）：
                            socket5://127.0.0.1:8888
        :param outTime: 代理超时(毫秒),默认30秒
        :return: 如果代理设置成功，返回True；否则返回False。
        """
        if not isinstance(proxy_url, str):
            raise TypeError("参数类型错误：proxy_url 应为字符串")
        if not isinstance(outTime, int):
            raise TypeError("参数类型错误：outTime 应为 int")
        return bool(SunnyDLL.DLLSunny.SetGlobalProxy(self.__context, create_string_buffer(proxy_url.encode("utf-8")),outTime))

    def set_proxy_rules(self, regexp: str) -> bool:
        """
        设置上游代理的正则表达式规则
        :param regexp: 不使用上游代理的Host列表
        :return: 是否设置成功
        """
        if not isinstance(regexp, str):
            raise TypeError("参数类型错误：regexp 应为字符串")
        return bool(SunnyDLL.DLLSunny.CompileProxyRegexp(self.__context, create_string_buffer(regexp.encode("utf-8"))))

    def set_must_tcp_regexp(self, regexp: str, rules_allow: bool) -> bool:
        """
        设置强制走TCP规则
        :param regexp: 正则表达式规则
        :param rules_allow: 规则类型，使用 MustTcpRegexp_Within 或 MustTcpRegexp_Outside
        :return: 是否设置成功
        """
        if not isinstance(regexp, str):
            raise TypeError("参数类型错误：regexp 应为字符串")
        if not isinstance(rules_allow, bool):
            raise TypeError("参数类型错误：rules_allow 应为布尔值")
        return bool(
            SunnyDLL.DLLSunny.SetMustTcpRegexp(self.__context, create_string_buffer(regexp.encode("utf-8")),
                                               rules_allow)
        )

    def set_ie_proxy(self) -> None:
        """ 将当前绑定的端口号设置为当前IE代理 """
        SunnyDLL.DLLSunny.SetIeProxy(self.__context)

    def open_drive(self, is_nfapi_dev: bool) -> bool:
        """
        加载驱动（仅允许一个中间件服务加载驱动）
        :param is_nfapi_dev: 是否加载NFAPI驱动,如果为 False 表示加载Proxifier驱动,【NFAPI驱动】win7请安装 KB3033929 补丁,【Proxifier驱动】不支持UDP，不支持32位操作系统
        :return: 是否加载成功
        """
        if not isinstance(is_nfapi_dev, bool):
            raise TypeError("参数类型错误：is_nfapi_dev 应为布尔值")
        return bool(SunnyDLL.DLLSunny.OpenDrive(self.__context, is_nfapi_dev))

    def un_drive(self) -> bool:
        """ 卸载驱动（仅在Windows上有效，需管理员权限）,如果卸载成功，会立即重启系统，只要没有重启系统，即为失败 """
        return bool(SunnyDLL.DLLSunny.UnDrive(self.__context))

    def add_http_certRules(self, host: str, cert_manager: CertManager, rules: int) -> None:
        """
        添加双向认证的证书
        :param host: 主机名
        :param cert_manager: CertManager对象
        :param rules: 证书使用规则
        """
        if not isinstance(host, str):
            raise TypeError("参数类型错误：host 应为字符串")
        if not isinstance(cert_manager, CertManager):
            raise TypeError("参数类型错误：cert_manager 应为 CertManager 对象")
        if not isinstance(rules, int):
            raise TypeError("参数类型错误：rules 应为整数")
        SunnyDLL.DLLSunny.AddHttpCertificate(
            create_string_buffer(bytes(host, 'utf-8')),
            cert_manager.context(),
            rules
        )

    def del_http_certRules(self, host: str) -> bool:
        """
        删除指定主机的证书
        :param host: 主机名
        :return: 是否删除成功
        """
        if not isinstance(host, str):
            raise TypeError("参数类型错误：host 应为字符串")
        return bool(SunnyDLL.DLLSunny.DelHttpCertificate(create_string_buffer(host.encode("utf-8"))))
