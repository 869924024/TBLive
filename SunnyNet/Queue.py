from ctypes import create_string_buffer

from SunnyNet import SunnyDLL


class Queue:
    """
    Sunny 队列

    这是一个表示队列的数据结构类，提供队列的基本操作，如入队、出队、检查是否为空等功能。
    """

    def __init__(self, identifier: str):
        """
        初始化 Queue 实例。

        :param identifier: 队列的唯一标识符。

        :raises TypeError: 如果 identifier 不是字符串类型。
        """
        if not isinstance(identifier, str):
            raise TypeError("参数错误：identifier 应为字符串类型")
        self._id = identifier

    def is_empty(self) -> bool:
        """
        检查队列是否为空。

        :return: 如果队列为空，返回 True；否则返回 False。
        """
        return self._id == "" or bool(SunnyDLL.DLLSunny.QueueIsEmpty(create_string_buffer(self._id.encode("utf-8"))))

    def release(self):
        """
        释放队列资源。

        如果队列 ID 为 ""，则不执行任何操作。
        """
        if self._id == "":
            return
        SunnyDLL.DLLSunny.QueueRelease(create_string_buffer(self._id.encode("utf-8")))

    def create(self) -> bool:
        """
        创建队列。若键名存在则会清空

        :return: 创建成功返回 True。
        """
        if self._id == "":
            return False
        SunnyDLL.DLLSunny.CreateQueue(create_string_buffer(self._id.encode("utf-8")))
        return True

    def reset(self):
        """
        重置队列，释放并重新创建队列。
        """
        if self._id == "":
            return
        self.release()
        self.create()

    def length(self) -> int:
        """
        获取队列的长度。

        :return: 返回队列中的元素数量。
        """
        if self._id == "":
            return 0
        return SunnyDLL.PtrToInt(SunnyDLL.DLLSunny.QueueLength(create_string_buffer(self._id.encode("utf-8"))))

    def push(self, data):
        """
        将数据推入队列。

        :param data: 可以是字节数组或字符串。
        """
        if self._id == "":
            return
        if isinstance(data, bytes):
            SunnyDLL.DLLSunny.QueuePush(create_string_buffer(self._id.encode("utf-8")), create_string_buffer(data),
                                        len(data))
        elif isinstance(data, str):
            encoded_data = data.encode("utf-8")
            SunnyDLL.DLLSunny.QueuePush(create_string_buffer(self._id.encode("utf-8")),
                                        create_string_buffer(encoded_data), len(encoded_data))
        else:
            raise TypeError("参数类型错误：data 应为字节数组或字符串")

    def pull(self) -> bytes:
        """
        从队列中弹出数据。

        :return: 返回弹出数据的字节数组，如果队列为空则返回空字节数组。
        """
        if self._id == "":
            return bytearray()
        pointer = SunnyDLL.DLLSunny.QueuePull(create_string_buffer(self._id.encode("utf-8")))
        return SunnyDLL.PointerToBytes(pointer)

    def pull_string(self) -> str:
        """
        从队列中弹出数据并转换为字符串。

        :return: 返回弹出数据的字符串表示。

        :raises TypeError: 如果数据无法转换为字符串。
        """
        byte_data = self.pull()
        try:
            return byte_data.decode("utf-8")
        except UnicodeDecodeError:
            raise TypeError("弹出数据成功，但转换字符串出错，可能不是标准字符串，请检查你的代码")