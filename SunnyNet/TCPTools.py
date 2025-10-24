from ctypes import create_string_buffer

from SunnyNet.SunnyDLL import DLLSunny as __dll

TARGET_CLIENT = 1
""" 消息发送目标常量：发送到客户端。 """
TARGET_SERVER = 2
""" 消息发送目标常量：发送到服务器。 """

def SendMessage(SendTarget: int, TheologyID: int, message: bytes) -> bool:
    """
     对这个请求使用指定代理请求请求
    :param SendTarget: 发送目标 请使用 TCPtools.TARGET_SERVER 或 TCPtools.TARGET_CLIENT

    :return: 成功返回 True,失败返回 False。
    """
    if not isinstance(SendTarget, int):
        raise TypeError("参数类型错误")
    if not isinstance(TheologyID, int):
        raise TypeError("参数类型错误")
    if not isinstance(message, bytes):
        raise TypeError("参数类型错误")
    if SendTarget == TARGET_SERVER:
        return bool(__dll.TcpSendMsg(TheologyID, create_string_buffer(message), len(message)))
    return bool(__dll.TcpSendMsgClient(TheologyID, create_string_buffer(message), len(message)))


def Close(TheologyID: int) -> bool:
    """
    关闭指定TCP会话
    :return: 如果成功则返回 true；否则返回 false。
    """
    if not isinstance(TheologyID, int):
        raise TypeError("参数类型错误")
    return bool(__dll.TcpCloseClient(TheologyID))
