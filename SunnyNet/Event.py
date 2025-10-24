from ctypes import *
from typing import Union

from SunnyNet import tools, TCPTools, UDPTools, WebsocketTools
from SunnyNet.SunnyDLL import PointerToText, DLLSunny, PtrToInt, PtrToByte, PointerToBytes

from typing import Union


class Request:
    """
    HTTP 请求操作类

    该类用于处理 HTTP 请求，包括请求体、请求头、Cookies 等操作。
    """

    def __init__(self, message_id: int):
        """
        初始化 Request 实例。

        :param message_id: 消息 ID。
        """
        self.__message_id = message_id

    def raw_request_data_to_file(self, save_file: str) -> bool:
        """
        将原始请求数据保存到文件。
        请使用"Conn.Request().is_request_raw_body()" 来检查当前请求是否为原始body,如果是 将无法修改提交的Body,请使用此命令来储存原始提交数据到文件
        :param save_file: 要保存的文件路径。
        :return: 如果成功保存数据，返回 True；否则返回 False。
        """
        if not isinstance(save_file, str):
            raise TypeError("参数类型错误：save_file 应为字符串")
        try:
            encoded_file = save_file.encode("gbk")
        except UnicodeEncodeError:
            encoded_file = save_file.encode("utf-8")
        return bool(
            DLLSunny.RawRequestDataToFile(self.__message_id, create_string_buffer(encoded_file), len(encoded_file)))

    def is_request_raw_body(self) -> bool:
        """
        检查当前请求是否为原始 body。
        此请求是否为原始body 如果是 将无法修改提交的Body，请使用 "Conn.Request().raw_request_data_to_file(save_file)" 命令来储存到文件
        :return: 如果当前请求为原始 body，返回 True；否则返回 False。
        """
        return bool(DLLSunny.IsRequestRawBody(self.__message_id))

    def body_length(self) -> int:
        """ 获取 POST 提交数据长度。

        :return: 数据长度。
        """
        return PtrToInt(DLLSunny.GetRequestBodyLen(self.__message_id))

    def body(self) -> bytes:
        """ 获取 POST 提交数据字节数组。

        :return: POST 数据的字节数组。
        """
        ptr = DLLSunny.GetRequestBody(self.__message_id)
        data = PtrToByte(ptr, 0, self.body_length())
        DLLSunny.Free(ptr)
        return data

    def body_to_str(self) -> str:
        """ 获取 POST 提交数据字符串。

        :return: POST 数据的字符串形式。
        """
        try:
            return self.body().decode("gbk")
        except UnicodeDecodeError:
            return self.body().decode("utf-8")

    def set_body(self, data: bytes) -> bool:
        """ 修改 POST 提交数据字节数组。

        :param data: 新的字节数据。
        :return: 成功返回 True。
        """
        if not isinstance(data, bytes):
            raise TypeError("参数类型错误：data 应为字节数组")
        return PtrToInt(DLLSunny.SetRequestData(self.__message_id, create_string_buffer(data), len(data))) == 1

    def set_str(self, data: str) -> bool:
        """ 修改 POST 提交数据为字符串。

        :param data: 新的字符串数据。
        :return: 成功返回 True。
        """
        if not isinstance(data, str):
            return False
        try:
            return self.set_body(data.encode("gbk"))
        except UnicodeEncodeError:
            return self.set_body(data.encode("utf-8"))

    def set_request_timeout(self, timeout: int):
        """
        设置请求超时。

        :param timeout: 超时时间，单位【毫秒】。
        """
        if not isinstance(timeout, int):
            raise TypeError("参数类型错误：timeout 应为整数")
        DLLSunny.SetRequestOutTime(self.__message_id, timeout)

    def set_h2_config(self, config: str):
        """
        设置 HTTP/2 指纹。

        :param config: HTTP2指纹配置文件 如果强制请求发送时使用HTTP/1.1 请填入参数 "http/1.1"
        """
        if not isinstance(config, str):
            raise TypeError("参数类型错误：config 应为字符串")
        DLLSunny.SetRequestHTTP2Config(self.__message_id, config)

    def random_ja3(self) -> bool:
        """ 随机化请求的 JA3 指纹。

        :return: 如果成功随机化指纹，返回 True；否则返回 False。
        """
        return bool(DLLSunny.RandomRequestCipherSuites(self.__message_id))

    def set_proxy(self, proxy_url: str, timeout: int) -> bool:
        """
        设置请求的代理。

        :param proxy_url: 代理 URL。
        :param timeout: 超时时间。
        :return: 如果代理设置成功，返回 True；否则返回 False。
        """
        if not isinstance(proxy_url, str):
            raise TypeError("参数类型错误：proxy_url 应为字符串")
        if not isinstance(timeout, int):
            raise TypeError("参数类型错误：timeout 应为整数")
        return bool(
            DLLSunny.SetRequestProxy(self.__message_id, create_string_buffer(proxy_url.encode("utf-8")), timeout))

    def set_headers(self, headers: str):
        """
        重置完整的协议头。

        :param headers: 完整的协议头字符串。
        """
        if not isinstance(headers, str):
            raise TypeError("参数类型错误：headers 应为字符串")
        DLLSunny.SetRequestALLHeader(self.__message_id, create_string_buffer(headers.encode("utf-8")))

    def set_cookie(self, value: str):
        """ 设置请求全部 Cookies。

        :param value: Cookies 字符串，例如 a=1;b=2;c=3。
        """
        if not isinstance(value, str):
            raise TypeError("参数类型错误：value 应为字符串")
        DLLSunny.SetRequestAllCookie(self.__message_id, create_string_buffer(value.encode("utf-8")))

    def set_header(self, key: str, value: Union[list, tuple, str]):
        """
        设置多个同名的协议头。

        :param key: 协议头名称。
        :param value: 协议头值，可以是字符串、列表或元组。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        if isinstance(value, str):
            DLLSunny.SetRequestHeader(self.__message_id, create_string_buffer(key.encode("utf-8")),
                                      create_string_buffer(value.encode("utf-8")))
        elif isinstance(value, (list, tuple)):
            DLLSunny.SetRequestHeader(self.__message_id, create_string_buffer(key.encode("utf-8")),
                                      create_string_buffer(
                                          '\n'.join(str(element) for element in value).encode("utf-8")))
        else:
            raise ValueError("参数类型错误：value 应为字符串、列表或元组")

    def set_url(self, new_url: str):
        """
        设置新的 URL 地址。

        :param new_url: 新的 URL 地址。
        """
        if not isinstance(new_url, str):
            raise TypeError("参数类型错误：new_url 应为字符串")
        DLLSunny.SetRequestUrl(self.__message_id, create_string_buffer(new_url.encode("utf-8")))

    def set_cookie(self, key: str, value: str):
        """
        设置 Cookie。

        :param key: Cookie 名。
        :param value: Cookie 值。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        if not isinstance(value, str):
            raise TypeError("参数类型错误：value 应为字符串")
        DLLSunny.SetRequestCookie(self.__message_id, create_string_buffer(key.encode("utf-8")),
                                  create_string_buffer(value.encode("utf-8")))

    def del_header(self, key: str):
        """
        删除指定的协议头。

        :param key: 要删除的协议头名称。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        DLLSunny.DelRequestHeader(self.__message_id, create_string_buffer(key.encode("utf-8")))

    def remove_compression_mark(self):
        """ 删除协议头中的压缩标记。 """
        self.del_header("Accept-Encoding")

    def get_headers(self) -> str:
        """
        获取全部协议头。

        :return: 返回完整的协议头字符串。
        """
        return PointerToText(DLLSunny.GetRequestAllHeader(self.__message_id))

    def get_header(self, key: str) -> str:
        """
        获取指定协议头。

        :param key: 要获取的协议头名称。
        :return: 如果有多个同名协议头，将返回第一个。
        """
        array = self.get_header_array(key)
        return array[0] if array else ""

    def get_header_array(self, key: str) -> list:
        """
        获取指定协议头的数组。

        :param key: 要获取的协议头名称。
        :return: 返回协议头值的列表。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        return PointerToText(
            DLLSunny.GetRequestHeader(self.__message_id, create_string_buffer(key.encode("utf-8")))).split("\n")

    def get_proto(self) -> str:
        """
        获取请求的协议版本。

        :return: 返回请求的协议版本字符串。
        """
        return PointerToText(DLLSunny.GetRequestProto(self.__message_id))

    def get_cookies(self) -> str:
        """
        获取全部 Cookies。

        :return: 返回所有 Cookies 的字符串。
        """
        return PointerToText(DLLSunny.GetRequestALLCookie(self.__message_id))

    def get_cookie(self, key: str) -> str:
        """
        获取指定 Cookie。

        :param key: Cookie 名。
        :return: Cookie 值。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        ptr = DLLSunny.GetRequestCookie(self.__message_id, create_string_buffer(key.encode("utf-8")))
        return PointerToText(ptr)

    def get_cookie_value(self, key: str) -> str:
        """
        获取指定 Cookie 值（不带 Cookie 名）。

        :param key: Cookie 名。
        :return: Cookie 值。
        """
        cookie = self.get_cookie(key).split(f"{key}=")
        return cookie[1].replace(";", "").strip() if len(cookie) >= 2 else ""

    def del_headers(self) -> None:
        """ 删除全部协议头。 """
        headers = self.get_headers()
        for item in headers.split("\r\n"):
            name = item.split(":")[0]
            if name:
                self.del_header(name)

    def stop(self):
        """
        终止发送请求。

        使用本命令后，该请求将不会被发送出去。
        """
        self.set_header("Connection", "Close")


class Response:
    """
    HTTP 响应操作类

    该类用于处理 HTTP 响应，包括状态码、响应体、请求头等操作。
    """

    def __init__(self, message_id: int):
        """
        初始化 Response 实例。

        :param message_id: 消息 ID。
        """
        self.__message_id = message_id

    def set_status_code(self, status: int):
        """
        修改响应状态码。

        :param status: 状态码，若小于等于 0 则默认为 200。
        """
        if not isinstance(status, int):
            raise TypeError("参数类型错误：status 应为整数")
        if status <= 0:
            DLLSunny.SetResponseStatus(self.__message_id, 200)
            return
        DLLSunny.SetResponseStatus(self.__message_id, status)

    def get_status_code(self) -> int:
        """ 获取响应状态码。

        :return: 当前状态码。
        """
        return PtrToInt(DLLSunny.GetResponseStatusCode(self.__message_id))

    def status(self) -> str:
        """ 获取响应状态文本。

        :return: 状态文本。
        """
        res = PointerToText(DLLSunny.GetResponseStatus(self.__message_id))
        parts = res.split(" ")
        if len(parts) > 1:
            return " ".join(parts[1:]).strip()
        return ""

    def server_address(self) -> str:
        """ 获取服务器响应 IP 地址。

        :return: 服务器地址。
        """
        return PointerToText(DLLSunny.GetResponseServerAddress(self.__message_id))

    def body(self) -> bytes:
        """ 获取响应数据。

        :return: 原始字节数组。
        """
        ptr = DLLSunny.GetResponseBody(self.__message_id)
        data = PtrToByte(ptr, 0, self.body_length())
        DLLSunny.Free(ptr)
        return data

    def body_auto(self) -> bytes:
        """ 获取响应数据并自动解压缩。

        :return: 解压缩后的字节数据。
        """
        data = self.body()
        encoding = self.get_header("Content-Encoding").lower()
        if encoding == "gzip":
            return tools.GzipUnCompress(data) or data
        if encoding == "br":
            return tools.BrUnCompress(data) or data
        if encoding == "deflate":
            return tools.DeflateUnCompress(data) or data
        if encoding == "zstd":
            return tools.ZSTDUnCompress(data) or data
        if encoding == "zlib":
            return tools.ZlibUnCompress(data) or data
        return data

    def body_auto_str(self) -> str:
        """ 获取解压缩后的响应数据字符串。

        :return: 解压缩后的字符串。
        """
        data = self.body_auto()
        try:
            return data.decode("gbk")
        except UnicodeDecodeError:
            return data.decode("utf-8")

    def body_length(self) -> int:
        """ 获取响应数据长度。

        :return: 数据长度。
        """
        ptr = DLLSunny.GetResponseBodyLen(self.__message_id)
        return PtrToInt(ptr)

    def set_body(self, data: bytes):
        """ 修改响应数据。

        :param data: 新的字节数据。
        """
        if not isinstance(data, bytes):
            raise TypeError("参数类型错误：data 应为字节数组")
        DLLSunny.SetResponseData(self.__message_id, create_string_buffer(data), len(data))

    def set_body_str(self, data: str):
        """ 修改响应数据为字符串。

        :param data: 新的字符串数据。
        """
        if not isinstance(data, str):
            raise TypeError("参数类型错误：data 应为字符串")
        self.set_body(data.encode("utf-8"))

    def set_header(self, key: str, value: Union[list, tuple, str]):
        """ 设置协议头。

        :param key: 协议头名称。
        :param value: 协议头值，可以是字符串、列表或元组。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        if isinstance(value, str):
            DLLSunny.SetResponseHeader(self.__message_id, create_string_buffer(key.encode("utf-8")),
                                       create_string_buffer(value.encode("utf-8")))
        elif isinstance(value, (list, tuple)):
            DLLSunny.SetResponseHeader(self.__message_id, create_string_buffer(key.encode("utf-8")),
                                       create_string_buffer(
                                           '\n'.join(str(element) for element in value).encode("utf-8")))
        else:
            raise ValueError("参数类型错误：value 应为字符串、列表或元组")

    def set_all_header(self, headers: str) -> None:
        """ 重置所有协议头。

        :param headers: 完整的协议头字符串。
        """
        if not isinstance(headers, str):
            raise TypeError("参数类型错误：headers 应为字符串")
        DLLSunny.SetResponseAllHeader(self.__message_id, create_string_buffer(headers.encode("utf-8")))

    def del_header(self, name: str) -> None:
        """ 删除指定的协议头。

        :param name: 协议头名称。
        """
        if not isinstance(name, str):
            raise TypeError("参数类型错误：name 应为字符串")
        DLLSunny.DelResponseHeader(self.__message_id, create_string_buffer(name.encode("utf-8")))

    def get_all_header(self) -> str:
        """ 获取所有协议头。

        :return: 所有协议头的字符串。
        """
        return PointerToText(DLLSunny.GetAllHeader(self.__message_id))

    def del_all_header(self):
        """ 删除所有协议头。 """
        headers = self.get_all_header()
        for line in headers.split("\r\n"):
            parts = line.split(":")
            if parts:
                self.del_header(parts[0])

    def get_header(self, key: str) -> str:
        """ 获取指定协议头。

        :param key: 协议头名称。
        :return: 第一个匹配的协议头值。
        """
        array = self.get_header_array(key)
        return array[0] if array else ""

    def get_proto(self, key: str) -> str:
        """ 获取响应的协议版本。

        :param key: 协议头名称。
        :return: 协议版本字符串。
        """
        array = self.get_header_array(key)
        return array[0] if array else ""

    def get_header_array(self, key: str) -> list:
        """ 获取指定协议头的所有值。

        :param key: 协议头名称。
        :return: 协议头值的列表。
        """
        if not isinstance(key, str):
            raise TypeError("参数类型错误：key 应为字符串")
        key_buffer = create_string_buffer(key.encode("utf-8"))
        return PointerToText(DLLSunny.GetResponseHeader(self.__message_id, key_buffer)).replace("\r", "").split("\n")

class HTTPEvent:
    """
    HTTP 回调事件

    该类用于表示 HTTP 事件，包括请求、响应和错误等操作。
    """

    EVENT_TYPE_REQUEST = 1
    """ HTTP 事件类型常量：发起请求。 """
    EVENT_TYPE_RESPONSE = 2
    """ HTTP 事件类型常量：请求完成。 """
    EVENT_TYPE_ERROR = 3
    """ HTTP 事件类型常量：请求错误。 """

    def __init__(self, sunny_context: int, theology_id: int, message_id: int, event_type: int,
                 method: str, url: str, error: str, pid: int):
        """
        初始化 HTTPEvent 实例。

        :param sunny_context: Sunny 上下文 ID。
        :param theology_id: 唯一的 Theology ID。
        :param message_id: 消息 ID。
        :param event_type: 事件类型。
        :param method: 请求方法。
        :param url: 请求的 URL。
        :param error: 错误信息。
        :param pid: 进程 ID。
        """
        self.__message_id = message_id
        self.__theology_id = theology_id
        self.__event_type = event_type
        self.__method = method
        self.__url = url
        self.__error = error
        self.__pid = pid
        self.__sunny_net_context = sunny_context
        self.__request = Request(message_id)
        self.__response = Response(message_id)
        self.__is_debug = error == "Debug"
        if self.__is_debug:
            self.__error = ""
        else:
            self.__error = error
        self.__client_ip = PointerToText(DLLSunny.GetRequestClientIp(message_id))

    def get_client_ip(self) -> str:
        """ 获取客户端 IP 地址。

        :return: 客户端 IP 地址。
        """
        return PointerToText(DLLSunny.GetRequestClientIp(self.__message_id))

    def set_OutRouterIP(self, ip) -> bool:
        """
        仅限在发起请求时使用
        请输入网卡对应的内网IP地址
        输入空文本,则让系统自动选择
        ----
        你也可以在中间件设置全局的出口地址
        """
        if not isinstance(ip, str):
            raise TypeError("参数类型错误：ip 应为字符串")
        return bool(DLLSunny.RequestSetOutRouterIP(self.__message_id, ip))

    def get_request(self) -> Request:
        """ 获取请求对象。

        :return: 请求对象。当事件类型为请求时有效。
        """
        return self.__request

    def get_response(self) -> Response:
        """ 获取响应对象。

        :return: 响应对象。当事件类型为请求或响应时有效。
        """
        return self.__response

    def get_theology_id(self) -> int:
        """ 获取唯一 ID。

        :return: 唯一 ID。
        """
        return self.__theology_id

    def get_sunny_net_context(self) -> int:
        """ 获取 SunnyNet 上下文 ID。

        :return: SunnyNet 上下文 ID。
        """
        return self.__sunny_net_context

    def get_message_id(self) -> int:
        """ 获取消息 ID。

        :return: 消息 ID。
        """
        return self.__message_id

    def get_event_type(self) -> int:
        """ 获取事件类型。

        请使用以下常量之一判断事件类型：
        - HTTPEvent.EVENT_TYPE_REQUEST
        - HTTPEvent.EVENT_TYPE_RESPONSE
        - HTTPEvent.EVENT_TYPE_ERROR

        :return: 事件类型。
        """
        return self.__event_type

    def get_url(self) -> str:
        """ 获取请求的 URL。

        :return: 请求的 URL。
        """
        return self.__url

    def get_error(self) -> str:
        """ 获取错误信息。

        :return: 错误信息。当事件类型为错误时有效。
        """
        return self.__error

    def get_method(self) -> str:
        """ 获取请求方法。

        :return: 请求方法。
        """
        return self.__method

    def get_pid(self) -> int:
        """ 获取进程 ID。

        :return: 进程 ID；如果返回 0，表示远程设备通过代理连接。
        """
        return self.__pid

    def is_debug(self) -> bool:
        """ 检查脚本代码是否通知下断。

        :return: 如果返回 True，表示脚本代码处理通知此请求需要下断。
        """
        return self.__is_debug

    def get_user(self) -> str:
        """ 获取用户信息。

        :return: 如果开启了身份验证模式，则返回客户端使用的 S5 账号。
        """
        return DLLSunny.SunnyNetGetSocket5User(self.__theology_id)


class TCPEvent:
    """
    TCP 回调事件

    该类用于表示 TCP 事件，包括连接、发送数据、接收数据和关闭连接等操作。
    """

    EVENT_TYPE_ABOUT = 4
    """ TCP 事件类型常量：即将开始连接。 """
    EVENT_TYPE_OK = 0
    """ TCP 事件类型常量：连接成功。 """
    EVENT_TYPE_SEND = 1
    """ TCP 事件类型常量：客户端发送数据。 """
    EVENT_TYPE_RECEIVE = 2
    """ TCP 事件类型常量：客户端收到数据。 """
    EVENT_TYPE_CLOSE = 3
    """ TCP 事件类型常量：连接关闭或连接失败。 """

    TARGET_CLIENT = 1
    """ 消息发送目标常量：发送到客户端。 """
    TARGET_SERVER = 2
    """ 消息发送目标常量：发送到服务器。 """

    def __init__(self, sunny_context: int, local_addr: str, remote_addr: str, theology_id: int,
                 message_id: int, event_type: int, pid: int, message_data: bytes):
        """
        初始化 TCPEvent 实例。

        :param sunny_context: Sunny 上下文 ID。
        :param local_addr: 本地地址。
        :param remote_addr: 远程地址。
        :param theology_id: 唯一 Theology ID。
        :param message_id: 消息 ID。
        :param event_type: 事件类型。
        :param pid: 进程 ID。
        :param message_data: 消息数据。
        """
        self.__message_id = message_id
        self.__theology_id = theology_id
        self.__event_type = event_type
        self.__remote_addr = remote_addr
        self.__local_addr = local_addr
        self.__data = message_data
        self.__pid = pid
        self.__sunny_net_context = sunny_context
        self.__request = Request(message_id)
        self.__response = Response(message_id)

    def get_theology_id(self) -> int:
        """ 获取唯一 ID。

        :return: 唯一 ID。
        """
        return self.__theology_id

    def set_OutRouterIP(self, ip) -> bool:
        """
        仅限在即将连接时使用
        请输入网卡对应的内网IP地址
        输入空文本,则让系统自动选择
        ----
        你也可以在中间件设置全局的出口地址
        """
        if not isinstance(ip, str):
            raise TypeError("参数类型错误：ip 应为字符串")
        return bool(DLLSunny.RequestSetOutRouterIP(self.__message_id, ip))

    def get_sunny_net_context(self) -> int:
        """ 获取 SunnyNet 上下文 ID。

        :return: SunnyNet 上下文 ID。
        """
        return self.__sunny_net_context

    def get_message_id(self) -> int:
        """ 获取消息 ID。

        :return: 消息 ID。
        """
        return self.__message_id

    def get_event_type(self) -> int:
        """ 获取事件类型。

        请使用以下常量之一判断事件类型：
        - TCPEvent.EVENT_TYPE_ABOUT
        - TCPEvent.EVENT_TYPE_OK
        - TCPEvent.EVENT_TYPE_SEND
        - TCPEvent.EVENT_TYPE_RECEIVE
        - TCPEvent.EVENT_TYPE_CLOSE

        :return: 事件类型。
        """
        return self.__event_type

    def get_local_addr(self) -> str:
        """ 获取请求来源地址。

        :return: 本地地址。
        """
        return self.__local_addr

    def get_remote_addr(self) -> str:
        """ 获取远程地址。

        :return: 远程地址。
        """
        return self.__remote_addr

    def get_pid(self) -> int:
        """ 获取进程 ID。

        :return: 进程 ID；如果返回 0，表示远程设备通过代理连接。
        """
        return self.__pid

    def get_body(self) -> bytes:
        """ 获取本次事件的数据。

        :return: 消息数据。
        """
        return self.__data

    def set_proxy(self, proxy_url: str,outTime:int) -> bool:
        """ 设置代理请求。

        :param proxy_url: 代理 URL，格式示例：
                          - HTTP 代理（带账号密码）：http://admin:123456@127.0.0.1:8888
                          - S5 代理（带账号密码）：socket5://admin:123456@127.0.0.1:8888
                          - HTTP 代理（无账号密码）：http://127.0.0.1:8888
                          - S5 代理（无账号密码）：socket5://127.0.0.1:8888

        :param outTime: 代理超时（毫秒,默认30秒）

        :return: 如果事件类型不是即将连接，则返回 False；否则成功返回 True，失败返回 False。
        """
        if self.__event_type != TCPEvent.EVENT_TYPE_ABOUT:
            return False
        if not isinstance(proxy_url, str):
            raise TypeError("参数类型错误：proxy_url 应为字符串")
        if not isinstance(outTime, int):
            raise TypeError("参数类型错误：outTime 应为 int")
        return bool(DLLSunny.SetTcpAgent(self.__message_id, create_string_buffer(proxy_url.encode("utf-8")),outTime))

    def redirect(self, new_address: str) -> bool:
        """ 重定向到另一个地址，仅限 TCP 回调，即将连接时使用。

        :param new_address: 带端口的 IP 地址，例如：8.8.8.8:443。
        :return: 如果事件类型不是即将连接，则返回 False；否则成功返回 True，失败返回 False。
        """
        if self.__event_type != TCPEvent.EVENT_TYPE_ABOUT:
            return False
        if not isinstance(new_address, str):
            raise TypeError("参数类型错误：new_address 应为字符串")
        return bool(DLLSunny.SetTcpConnectionIP(self.__message_id, create_string_buffer(new_address.encode("utf-8"))))

    def set_body(self, data: bytes) -> None:
        """ 修改本次事件发送/接收的数据。

        :param data: 新的数据，可以是字节数组。
        """
        if data is None:
            empty_data = bytearray()
            DLLSunny.SetTcpBody(self.__message_id, self.__event_type, create_string_buffer(empty_data), len(empty_data))
            return
        if not isinstance(data, bytes):
            raise TypeError("参数类型错误：data 应为字节数组")
        self.__data = data
        DLLSunny.SetTcpBody(self.__message_id, self.__event_type, create_string_buffer(data), len(data))

    def set_body_str(self, data: str) -> None:
        """
        修改本次事件发送/接收的数据。

        :param data: 新的数据，可以是字符串。
        """
        if data is None or data == "":
            self.set_body(None)
            return
        if not isinstance(data, str):
            raise TypeError("参数类型错误：data 应为字符串")
        try:
            body = data.encode("gbk")
        except UnicodeEncodeError:
            body = data.encode("utf-8")
        self.set_body(body)

    def send_message(self, send_target: int, message: bytes) -> bool:
        """ 发送消息。

        :param send_target: 发送目标，请使用 TCPEvent.TARGET_SERVER 或 TCPEvent.TARGET_CLIENT。

        :return: 成功返回 True，失败返回 False。
        """
        if not isinstance(send_target, int):
            raise TypeError("参数类型错误：send_target 应为整数")
        if not isinstance(message, bytes):
            raise TypeError("参数类型错误：message 应为字节数组")
        return TCPTools.SendMessage(send_target, self.__theology_id, message)

    def close(self) -> bool:
        """ 关闭当前 TCP 会话。

        :return: 如果成功返回 True，否则返回 False。
        """
        return TCPTools.Close(self.__theology_id)

    def get_user(self) -> str:
        """ 获取用户信息。

        :return: 如果开启了身份验证模式，则返回客户端使用的 S5 账号。
        """
        return DLLSunny.SunnyNetGetSocket5User(self.__theology_id)


class UDPEvent:
    """
    UDP 回调事件

    该类用于表示 UDP 事件，包括关闭连接、发送数据和接收数据等操作。
    """

    EVENT_TYPE_CLOSED = 1
    """ UDP 事件类型常量：关闭。 """
    EVENT_TYPE_SEND = 2
    """ UDP 事件类型常量：客户端发送数据。 """
    EVENT_TYPE_RECEIVE = 3
    """ UDP 事件类型常量：客户端收到数据。 """

    TARGET_CLIENT = 1
    """ 消息发送目标常量：发送到客户端。 """
    TARGET_SERVER = 2
    """ 消息发送目标常量：发送到服务器。 """

    def __init__(self, sunny_context: int, local_addr: str, remote_addr: str, theology_id: int,
                 message_id: int, event_type: int, pid: int):
        """
        初始化 UDPEvent 实例。

        :param sunny_context: Sunny 上下文 ID。
        :param local_addr: 本地地址。
        :param remote_addr: 远程地址。
        :param theology_id: 唯一 Theology ID。
        :param message_id: 消息 ID。
        :param event_type: 事件类型。
        :param pid: 进程 ID。
        """
        self.__message_id = message_id
        self.__theology_id = theology_id
        self.__event_type = event_type
        self.__remote_addr = remote_addr
        self.__local_addr = local_addr
        self.__pid = pid
        self.__sunny_net_context = sunny_context
        self.__request = Request(message_id)
        self.__response = Response(message_id)

    def get_pid(self) -> int:
        """ 获取进程 ID。

        :return: 进程 ID；如果返回 0，表示远程设备通过代理连接。
        """
        return self.__pid

    def get_theology_id(self) -> int:
        """ 获取唯一 ID。

        :return: 唯一 ID。
        """
        return self.__theology_id

    def get_sunny_net_context(self) -> int:
        """ 获取 SunnyNet 上下文 ID。

        :return: SunnyNet 上下文 ID。
        """
        return self.__sunny_net_context

    def get_message_id(self) -> int:
        """ 获取消息 ID。

        :return: 消息 ID。
        """
        return self.__message_id

    def get_event_type(self) -> int:
        """ 获取事件类型。

        请使用以下常量之一判断事件类型：
        - UDPEvent.EVENT_TYPE_CLOSED
        - UDPEvent.EVENT_TYPE_SEND
        - UDPEvent.EVENT_TYPE_RECEIVE

        :return: 事件类型。
        """
        return self.__event_type

    def get_local_addr(self) -> str:
        """ 获取请求来源地址。

        :return: 本地地址。
        """
        return self.__local_addr

    def get_remote_addr(self) -> str:
        """ 获取远程地址。

        :return: 远程地址。
        """
        return self.__remote_addr

    def get_body(self) -> bytes:
        """ 获取本次事件的数据。

        :return: 消息数据。
        """
        ptr = DLLSunny.GetUdpData(self.__message_id)
        return PointerToBytes(ptr)

    def set_body(self, data: bytes) -> bool:
        """ 修改本次事件发送/接收的数据。

        :param data: 新的数据，可以是字节数组。

        :return: 如果成功设置数据则返回 True，否则返回 False。
        """
        if data is None:
            empty_data = bytearray()
            ptr = DLLSunny.SetUdpData(self.__message_id, create_string_buffer(empty_data), len(empty_data))
            return bool(ptr)
        if not isinstance(data, bytes):
            raise TypeError("参数类型错误：data 应为字节数组")
        ptr = DLLSunny.SetUdpData(self.__message_id, create_string_buffer(data), len(data))
        return bool(ptr)

    def set_body_str(self, data: str) -> None:
        """ 修改本次事件发送/接收的数据。

        :param data: 新的数据，可以是字符串。
        """
        if data is None or data == "":
            self.set_body(None)
            return
        if not isinstance(data, str):
            raise TypeError("参数类型错误：data 应为字符串")
        try:
            body = data.encode("gbk")
        except UnicodeEncodeError:
            body = data.encode("utf-8")
        self.set_body(body)

    def send_message(self, send_target: int, message: bytes) -> bool:
        """ 发送消息。

        :param send_target: 发送目标，请使用 UDPEvent.TARGET_SERVER 或 UDPEvent.TARGET_CLIENT。

        :return: 成功返回 True，失败返回 False。
        """
        if not isinstance(send_target, int):
            raise TypeError("参数类型错误：send_target 应为整数")
        if not isinstance(message, bytes):
            raise TypeError("参数类型错误：message 应为字节数组")
        return UDPTools.SendMessage(send_target, self.__theology_id, message)


class WebSocketEvent:
    """
    WebSocket 回调事件

    该类用于表示 WebSocket 事件，包括连接、发送和接收数据等操作。
    """

    EVENT_TYPE_CONNECTION_SUCCESS = 1
    """ WebSocket 事件类型常量：连接成功。 """
    EVENT_TYPE_SEND = 2
    """ WebSocket 事件类型常量：客户端发送数据。 """
    EVENT_TYPE_RECEIVE = 3
    """ WebSocket 事件类型常量：客户端收到数据。 """
    EVENT_TYPE_CLOSE = 4
    """ WebSocket 事件类型常量：断开连接。 """

    MESSAGE_TYPE_TEXT = 1
    """ WebSocket 消息类型常量：文本消息。 """
    MESSAGE_TYPE_BINARY = 2
    """ WebSocket 消息类型常量：二进制消息。 """
    MESSAGE_TYPE_CLOSE = 8
    """ WebSocket 消息类型常量：关闭消息。 """
    MESSAGE_TYPE_PING = 9
    """ WebSocket 消息类型常量：Ping 消息。 """
    MESSAGE_TYPE_PONG = 10
    """ WebSocket 消息类型常量：Pong 消息。 """
    MESSAGE_TYPE_INVALID = -1
    """ WebSocket 消息类型常量：无效消息。 """

    TARGET_CLIENT = 1
    """ 消息发送目标常量：发送到客户端。 """
    TARGET_SERVER = 2
    """ 消息发送目标常量：发送到服务器。 """

    def __init__(self, sunny_context: int, theology_id: int, message_id: int, event_type: int,
                 method: str, url: str, pid: int, ws_type: int):
        """
        初始化 WebSocketEvent 实例。

        :param sunny_context: Sunny 上下文 ID。
        :param theology_id: 唯一的 Theology ID。
        :param message_id: 消息 ID。
        :param event_type: 事件类型。
        :param method: 请求方法。
        :param url: 请求的 URL。
        :param pid: 进程 ID。
        :param ws_type: WebSocket 消息类型。
        """
        self.__message_id = message_id
        self.__theology_id = theology_id
        self.__event_type = event_type
        self.__method = method
        self.__url = url
        self.__pid = pid
        self.__sunny_net_context = sunny_context
        self.__request = Request(message_id)
        self.__ws_type = ws_type

    def get_pid(self) -> int:
        """ 获取进程 ID。

        :return: 如果返回 0，表示远程设备通过代理连接。
        """
        return self.__pid

    def get_theology_id(self) -> int:
        """ 获取唯一 ID。

        :return: 唯一 ID。
        """
        return self.__theology_id

    def get_sunny_net_context(self) -> int:
        """ 获取 SunnyNet 上下文 ID。

        :return: SunnyNet 上下文 ID。
        """
        return self.__sunny_net_context

    def get_user(self) -> str:
        """
        获取用户信息。

        :return: 如果开启了身份验证模式，则返回客户端使用的 S5 账号。
        """
        return DLLSunny.SunnyNetGetSocket5User(self.__theology_id)

    def get_message_id(self) -> int:
        """ 获取消息 ID。

        :return: 消息 ID。
        """
        return self.__message_id

    def get_event_type(self) -> int:
        """ 获取事件类型。

        请使用以下常量之一判断事件类型：
        - WebSocketEvent.EVENT_TYPE_CONNECTION_SUCCESS
        - WebSocketEvent.EVENT_TYPE_SEND
        - WebSocketEvent.EVENT_TYPE_RECEIVE
        - WebSocketEvent.EVENT_TYPE_CLOSE

        :return: 事件类型。
        """
        return self.__event_type

    def get_message_type(self) -> int:
        """ 获取当前 WebSocket 消息类型。

        请使用以下常量之一判断消息类型：
        - WebSocketEvent.MESSAGE_TYPE_TEXT
        - WebSocketEvent.MESSAGE_TYPE_BINARY
        - WebSocketEvent.MESSAGE_TYPE_CLOSE
        - WebSocketEvent.MESSAGE_TYPE_PING
        - WebSocketEvent.MESSAGE_TYPE_PONG
        - WebSocketEvent.MESSAGE_TYPE_INVALID

        :return: 消息类型。
        """
        return self.__ws_type

    def get_body(self) -> bytes:
        """ 获取事件的数据。

        :return: 本次事件的数据。
        """
        pointer = DLLSunny.GetWebsocketBody(self.__message_id)
        body_data = PtrToByte(pointer, 0, self.get_body_length())
        DLLSunny.Free(pointer)
        return body_data

    def get_body_length(self) -> int:
        """ 获取本次事件的数据长度。

        :return: 数据长度。
        """
        return PtrToInt(DLLSunny.GetWebsocketBodyLen(self.__message_id))

    def set_body(self, data: bytes) -> bool:
        """ 修改本次事件发送/接收的数据。

        :param data: 新的数据，可以是字节数组。
        :return: 如果设置成功返回 True，否则返回 False。
        """
        if data is None:
            empty_data = bytearray()
            pointer = DLLSunny.SetWebsocketBody(self.__message_id, create_string_buffer(empty_data), len(empty_data))
            return bool(pointer)
        if not isinstance(data, bytes):
            raise TypeError("参数类型错误：data 应为字节数组")
        pointer = DLLSunny.SetWebsocketBody(self.__message_id, create_string_buffer(data), len(data))
        return bool(pointer)

    def set_body_str(self, data: str) -> None:
        """ 修改本次事件发送/接收的数据。
        :param data: 新的数据，可以是字符串。
        """
        if data is None or data == "":
            self.set_body(None)
            return
        if not isinstance(data, str):
            raise TypeError("参数类型错误：data 应为字符串")
        try:
            body = data.encode("gbk")
        except UnicodeEncodeError:
            body = data.encode("utf-8")
        self.set_body(body)

    def send_message(self, send_target: int, message_type: int, message: bytes) -> bool:
        """ 发送消息。

        :param send_target: 发送目标，请使用 WebSocketEvent.TARGET_CLIENT 或 WebSocketEvent.TARGET_SERVER。
        :param message_type: WebSocket 消息类型，请使用 WebSocketEvent.MESSAGE_TYPE_TEXT 等常量。

        :return: 成功返回 True，失败返回 False。
        """
        if not isinstance(send_target, int):
            raise TypeError("参数类型错误：send_target 应为整数")
        if not isinstance(message_type, int):
            raise TypeError("参数类型错误：message_type 应为整数")
        if not isinstance(message, bytes):
            raise TypeError("参数类型错误：message 应为字节数组")
        return WebsocketTools.SendMessage(send_target, self.__theology_id, message_type, message)

    def close(self) -> bool:
        """ 关闭当前 WebSocket 会话。

        :return: 如果成功返回 True，否则返回 False。
        """
        return WebsocketTools.Close(self.__theology_id)

    def get_url(self) -> str:
        """ 获取请求的 URL。

        :return: 请求的 URL。
        """
        return self.__url

    def get_method(self) -> str:
        """ 获取请求方法。

        :return: 请求方法。
        """
        return self.__method

    def get_headers(self) -> str:
        """ 获取请求时的全部协议头。

        :return: 请求头。
        """
        return self.__request.get_headers()

    def get_cookies(self) -> str:
        """ 获取请求时的全部 Cookies。

        :return: 所有 Cookies。
        """
        return self.__request.get_cookies()

    def get_cookie(self, key: str) -> str:
        """ 获取指定 Cookie。

        :param key: Cookie 的键。
        :return: 指定 Cookie 的值。
        """
        return self.__request.get_cookie(key)

    def get_cookie_value(self, key: str) -> str:
        """ 获取指定 Cookie 的值，不包括 Cookie 的键。

        :param key: Cookie 的键。
        :return: 指定 Cookie 的值。
        """
        return self.__request.get_cookie_value(key)
