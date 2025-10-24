from SunnyNet.SunnyDLL import DLLSunny as __dll
from ctypes import create_string_buffer

TARGET_CLIENT = 1
""" 消息发送目标常量：发送到客户端。 """
TARGET_SERVER = 2
""" 消息发送目标常量：发送到服务器。 """

WS_MESSAGE_TYPE_TEXT = 1
"""WebSocket 消息类型常量：文本消息。"""
WS_MESSAGE_TYPE_BINARY = 2
"""WebSocket 消息类型常量：二进制消息。"""
WS_MESSAGE_TYPE_CLOSE = 8
"""WebSocket 消息类型常量：关闭消息。"""
WS_MESSAGE_TYPE_PING = 9
"""WebSocket 消息类型常量：Ping 消息。"""
WS_MESSAGE_TYPE_PONG = 10
"""WebSocket 消息类型常量：Pong 消息。"""
WS_MESSAGE_TYPE_INVALID = -1
"""WebSocket 消息类型常量：无效消息。"""


def SendMessage(SendTarget: int, TheologyID: int, MessageType: int, message: bytes) -> bool:
    """
     对这个请求使用指定代理请求请求
    :param SendTarget: 发送目标 请使用 WebsocketTools.TARGET_CLIENT 或 WebsocketTools.TARGET_SERVER
    :param MessageType: ws消息类型 请使用 WebsocketTools.WS_MESSAGE_TYPE_TEXT 或 WebsocketTools.WS_MESSAGE_TYPE_BINARY 或 WebsocketTools.WS_MESSAGE_TYPE_CLOSE 或 WebsocketTools.WS_MESSAGE_TYPE_PING 或 WebsocketTools.WS_MESSAGE_TYPE_PONG 或 WebsocketTools.WS_MESSAGE_TYPE_INVALID

    :return: 成功返回 True,失败返回 False。
    """
    if not isinstance(SendTarget, int):
        raise TypeError("参数类型错误")
    if not isinstance(TheologyID, int):
        raise TypeError("参数类型错误")
    if not isinstance(MessageType, int):
        raise TypeError("参数类型错误")
    if not isinstance(message, bytes):
        raise TypeError("参数类型错误")
    if SendTarget == TARGET_SERVER:
        return bool(__dll.SendWebsocketBody(TheologyID, MessageType, create_string_buffer(message), len(message)))
    return bool(__dll.SendWebsocketClientBody(TheologyID, MessageType, create_string_buffer(message), len(message)))


def Close(TheologyID: int) -> bool:
    """
    断开指定连接
    :return: 成功返回 True,失败返回 False。
    """
    if not isinstance(TheologyID, int):
        raise TypeError("参数类型错误")
    return bool(__dll.CloseWebsocket(TheologyID))
