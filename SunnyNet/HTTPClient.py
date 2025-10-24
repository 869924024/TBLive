from ctypes import create_string_buffer

from SunnyNet import SunnyDLL, tools


class SunnyHTTPClient:
    """
    Sunny HTTPClient

    这是一个用于处理 HTTP 请求和响应的客户端类，支持设置代理、时间超时、请求头等功能。
    """

    def __init__(self):
        """
        初始化 SunnyHTTPClient 实例并创建 HTTP 客户端上下文。

        该方法会自动设置重定向为允许。
        """
        self.__client_context = SunnyDLL.DLLSunny.CreateHTTPClient()
        self.set_redirect(True)

    def __del__(self):
        """
        释放 SunnyHTTPClient 资源。

        在对象被销毁时，调用此方法以清理 HTTP 客户端上下文。
        """
        SunnyDLL.DLLSunny.RemoveHTTPClient(self.__client_context)

    def reset(self):
        """
        重置 HTTP 客户端上下文。

        该方法会移除当前的 HTTP 客户端并创建一个新的客户端。
        """
        SunnyDLL.DLLSunny.RemoveHTTPClient(self.__client_context)
        self.__client_context = SunnyDLL.DLLSunny.CreateHTTPClient()
        self.set_redirect(True)

    def get_error(self) -> str:
        """
        获取最后一个错误信息。

        :return: 返回错误信息的字符串表示。
        """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.HTTPClientGetErr(self.__client_context))

    def open(self, method: str, url: str):
        """
        打开 HTTP 请求。

        :param method: HTTP 方法（如 GET、POST）。
        :param url: 请求的 URL 地址。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(method, str):
            raise TypeError("参数类型错误")
        if not isinstance(url, str):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPOpen(self.__client_context, create_string_buffer(method.encode("utf-8")),
                                   create_string_buffer(url.encode("utf-8")))

    def set_OutRouterIP(self, ip) -> bool:
        """
        设置请求数据出口IP
        请输入网卡对应的内网IP地址
        输入空文本,则让系统自动选择
        """
        if not isinstance(ip, str):
            raise TypeError("参数类型错误：ip 应为字符串")
        return bool(SunnyDLL.DLLSunny.HTTPSetOutRouterIP(self.__client_context, ip))

    def set_header(self, name: str, value: str):
        """
        设置 HTTP 请求头。

        :param name: 请求头的名称。
        :param value: 请求头的值。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(name, str):
            raise TypeError("参数类型错误")
        if not isinstance(value, str):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPSetHeader(self.__client_context, create_string_buffer(name.encode("utf-8")),
                                        create_string_buffer(value.encode("utf-8")))

    def set_proxy(self, proxy_url: str) -> bool:
        """
        设置上游代理，仅支持 S5 代理或 HTTP 代理。

        :param proxy_url: 代理 URL，格式示例：
                          - HTTP 代理（带账号密码）：
                            http://admin:123456@127.0.0.1:8888
                          - S5 代理（带账号密码）：
                            socket5://admin:123456@127.0.0.1:8888
                          - HTTP 代理（无账号密码）：
                            http://127.0.0.1:8888
                          - S5 代理（无账号密码）：
                            socket5://127.0.0.1:8888

        :return: 如果代理设置成功，返回 True；否则返回 False。
        """
        if not isinstance(proxy_url, str):
            raise TypeError("参数类型错误")
        return bool(
            SunnyDLL.DLLSunny.HTTPSetProxyIP(self.__client_context, create_string_buffer(proxy_url.encode("utf-8"))))

    def get_request_header(self) -> str:
        """
        获取全部已经设置的请求头。

        :return: 返回请求头的字符串表示。
        """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.HTTPGetRequestHeader(self.__client_context))

    def set_request_ServerIP(self, ip: str):
        """
        设置请求实际连接地址
        设置后将不再使用URL或协议头中的HOST地址
        某些时候,协议头中的HOST以及URL中的地址不能修改,修改后请求无法发送，这种情况下有用。
        :param ip: 例如:8.8.8.8:443,只能IP+端口，如果格式错误，不会使用
        """
        if not isinstance(ip, str):
            raise TypeError("参数类型错误")
        return SunnyDLL.PointerToText(
            SunnyDLL.DLLSunny.HTTPSetServerIP(self.__client_context, create_string_buffer(ip.encode("utf-8"))))

    def set_timeouts(self, timeout: int):
        """
        设置请求的超时时间。

        :param timeout: 超时时间（单位：毫秒）。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(timeout, int):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPSetTimeouts(self.__client_context, timeout)

    def send(self, data=""):
        """
        发送请求数据。

        :param data: 可以是字节数组或字符串。

        :raises TypeError: 如果参数类型不正确。
        """
        if isinstance(data, bytes):
            SunnyDLL.DLLSunny.HTTPSendBin(self.__client_context, create_string_buffer(data), len(data))
            return
        if isinstance(data, str):
            encoded_data = data.encode("utf-8")
            SunnyDLL.DLLSunny.HTTPSendBin(self.__client_context, create_string_buffer(encoded_data), len(encoded_data))
            return
        raise TypeError("参数类型错误")

    def get_body_length(self) -> int:
        """
        获取响应内容的长度。

        :return: 响应内容的字节长度。
        """
        return SunnyDLL.PtrToInt(SunnyDLL.DLLSunny.HTTPGetBodyLen(self.__client_context))

    def get_headers(self) -> str:
        """
        获取响应的全部协议头。

        :return: 返回响应头的字符串表示。
        """
        return SunnyDLL.PointerToText(SunnyDLL.DLLSunny.HTTPGetHeads(self.__client_context))

    def get_response_header(self, name: str) -> str:
        """
        获取响应中指定的协议头。

        :param name: 协议头的名称。

        :return: 返回指定协议头的字符串表示。
        """
        return SunnyDLL.PointerToText(
            SunnyDLL.DLLSunny.HTTPGetHeader(self.__client_context, create_string_buffer(name.encode("utf-8"))))

    def set_redirect(self, allow: bool):
        """
        设置是否允许自动重定向。

        :param allow: 如果为 True，允许重定向；如果为 False，不允许重定向。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(allow, bool):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPSetRedirect(self.__client_context, allow)

    def get_status_code(self) -> int:
        """
        获取响应状态码。

        :return: 返回 HTTP 状态码。
        """
        return SunnyDLL.PtrToInt(SunnyDLL.DLLSunny.HTTPGetCode(self.__client_context))

    def get_body(self) -> bytes:
        """
        获取响应内容。

        :return: 返回响应内容的字节数组。
        """
        body_length = self.get_body_length()
        if body_length < 1:
            return b""
        body_pointer = SunnyDLL.DLLSunny.HTTPGetBody(self.__client_context)
        body_data = SunnyDLL.PtrToByte(body_pointer, 0, body_length)
        SunnyDLL.DLLSunny.Free(body_pointer)
        encoding = self.get_response_header("Content-Encoding").lower()

        # 根据编码格式进行解压
        if encoding == "gzip":
            decompressed_data = tools.GzipUnCompress(body_data)
            if len(decompressed_data) > 0:
                return decompressed_data
        if encoding == "br":
            decompressed_data = tools.BrUnCompress(body_data)
            if len(decompressed_data) > 0:
                return decompressed_data
        if encoding == "deflate":
            decompressed_data = tools.DeflateUnCompress(body_data)
            if len(decompressed_data) > 0:
                return decompressed_data
        if encoding == "zstd":
            decompressed_data = tools.ZSTDUnCompress(body_data)
            if len(decompressed_data) > 0:
                return decompressed_data
        if encoding == "zlib":
            decompressed_data = tools.ZlibUnCompress(body_data)
            if len(decompressed_data) > 0:
                return decompressed_data

        return body_data

    def get_body_string(self) -> str:
        """
        获取响应内容的字符串表示。

        尝试使用 GBK 解码，如果失败则使用 UTF-8 解码。

        :return: 返回响应内容的字符串表示。

        :raises TypeError: 如果响应内容无法转换为字符串。
        """
        response_body = self.get_body()
        try:
            return response_body.decode("gbk")
        except UnicodeDecodeError:
            try:
                return response_body.decode("utf-8")
            except UnicodeDecodeError:
                raise TypeError("获取数据成功,但是转为字符串失败,请检查这个请求是否响应的是字符串，例如响应的是图片？")

    def set_random_tls(self, enable: bool = True):
        """
        使用随机 TLS 指纹实现随机 Ja3 指纹。

        :param enable: 如果为 True，则启用随机 TLS 指纹；否则禁用。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(enable, bool):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPSetRandomTLS(self.__client_context, enable)

    def set_http2_config(self, config: str):
        """
        设置 HTTP/2 配置。在Open之后使用

        :param config: 请使用 tools.HTTP2_fp_Config_..... 常量模板之一。

        :raises TypeError: 如果参数类型不正确。
        """
        if not isinstance(config, str):
            raise TypeError("参数类型错误")
        SunnyDLL.DLLSunny.HTTPSetH2Config(self.__client_context, create_string_buffer(config.encode("utf-8")))
