import struct
import ctypes
from ctypes import *

# 判断你的python环境是64位还是32位
__RuntimeEnvironment = struct.calcsize("P") * 8 == 64

try:
    if __RuntimeEnvironment:
        # 如果是64位加载64位DLL,如果是 linux 或其他平台，只需要将.dll 改为.so
        lib = CDLL("./SunnyNet64.dll")
        # Go语言回调函数声明
        TcpCallback = CFUNCTYPE(None, c_int64, c_char_p, c_char_p, c_int64, c_int64, c_int64, c_int64, c_int64, c_int64)
        HttpCallback = CFUNCTYPE(None, c_int64, c_int64, c_int64, c_int64, c_char_p, c_char_p, c_char_p, c_int64)
        WsCallback = CFUNCTYPE(None, c_int64, c_int64, c_int64, c_int64, c_char_p, c_char_p, c_int64, c_int64)
        UDPCallback = CFUNCTYPE(None, c_int64, c_char_p, c_char_p, c_int64, c_int64, c_int64, c_int64)
        ScriptLogCallback = CFUNCTYPE(None, c_char_p)
        ScriptCodeCallback = CFUNCTYPE(None, c_char_p, c_int64)

    else:
        # 如果不是64位加载32位DLL
        lib = CDLL("./SunnyNet.dll")
        # Go语言回调函数声明
        TcpCallback = CFUNCTYPE(None, c_int, c_char_p, c_char_p, c_int, c_int, c_int, c_int, c_int, c_int)
        HttpCallback = CFUNCTYPE(None, c_int, c_int, c_int, c_int, c_char_p, c_char_p, c_char_p, c_int)
        WsCallback = CFUNCTYPE(None, c_int, c_int, c_int, c_int, c_char_p, c_char_p, c_int, c_int)
        UDPCallback = CFUNCTYPE(None, c_int, c_char_p, c_char_p, c_int, c_int, c_int, c_int)
        ScriptLogCallback = CFUNCTYPE(None, c_char_p)
        ScriptCodeCallback = CFUNCTYPE(None, c_char_p, c_int)


except:
    print("载入DLL失败,请检测DLL文件")
    exit(1)


# 这个类 是动态加载DLL时 设置返回值为指针
class LibSunny:
    def __getattr__(self, name):
        func = getattr(lib, name)
        func.restype = ctypes.POINTER(ctypes.c_int)
        return func


DLLSunny = LibSunny()


# 指针到字节数组 ptr=指针 skip=偏移数 num=取出几个字节
def PtrToByte(ptr, skip, num) -> bytearray | bytes:
    result_as_int = ctypes.cast(ptr, ctypes.c_void_p).value
    if result_as_int == None:
        return bytearray()
    result_as_int += skip
    new_result_ptr = ctypes.cast(result_as_int, ctypes.POINTER(ctypes.c_int))
    buffer = ctypes.create_string_buffer(num)
    ctypes.memmove(buffer, new_result_ptr, num)
    return buffer.raw


# 指针到整数
def PtrToInt(ptr) -> int:
    if isinstance(ptr, int):
        return ptr
    try:
        pp = ctypes.cast(ptr, ctypes.c_void_p)
        if pp.value is None:  # 检查值是否为 None
            return 0
        return int(pp.value)
    except:
        raise TypeError(f'module name must be str, not {type(ptr)}', ctypes.cast(ptr, ctypes.c_void_p))


# 指针到字符串
def PointerToText(ptr) -> str:
    if ptr == 0:
        return ""
    buff = b''
    i = 0
    while True:
        bs = PtrToByte(ptr, i, 1)
        i += 1
        if len(bs) == 0:
            break
        if bs[0] == 0:
            break
        buff = buff + bs

    DLLSunny.Free(ptr)  # 释放Sunny的指针,只要是Sunny返回的bytes 或 string 都需要释放指针
    try:
        return buff.decode('utf-8')
    except:
        return buff.decode('gbk')


# 字节数组到字符串
def BytesToText(buff) -> str:
    try:
        return buff.decode('utf-8')
    except:
        return buff.decode('gbk')


# 指针到字节数组 (DLL协商的前8个字节是长度)
def PointerToBytes(ptr) -> bytearray:
    if ptr == 0:
        return bytearray()
    lp = PtrToByte(ptr, 0, 8)
    if len(lp) != 8:
        return lp
    Lxp = PtrToInt(DLLSunny.BytesToInt(create_string_buffer(lp), 8))
    m = PtrToByte(ptr, 8, Lxp)
    DLLSunny.Free(ptr)  # 释放Sunny的指针,只要是Sunny返回的bytes 或 string 都需要释放指针
    return m
