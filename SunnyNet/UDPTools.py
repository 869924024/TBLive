from SunnyNet.SunnyDLL import DLLSunny as __dll
from ctypes import create_string_buffer

TARGET_CLIENT = 1
""" 消息发送目标常量：发送到客户端。 """
TARGET_SERVER = 2
""" 消息发送目标常量：发送到服务器。 """

def SendMessage(SendTarget: int, TheologyID: int, message: bytes) -> bool:
    """
     对这个请求使用指定代理请求请求
    :param SendTarget: 发送目标 请使用 UDPTools.TARGET_SERVER 或 UDPTools.TARGET_CLIENT

    :return: 成功返回 True,失败返回 False。
    """
    if not isinstance(SendTarget, int):
        raise TypeError("参数类型错误")
    if not isinstance(TheologyID, int):
        raise TypeError("参数类型错误")
    if not isinstance(message, bytes):
        raise TypeError("参数类型错误")
    if SendTarget == TARGET_SERVER:
        return bool(__dll.UdpSendToServer(TheologyID, create_string_buffer(message), len(message)))
    return bool(__dll.UdpSendToClient(TheologyID, create_string_buffer(message), len(message)))
