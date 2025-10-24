from ctypes import create_string_buffer
from typing import Callable, Any, Type, Tuple
import inspect

from SunnyNet import SunnyDLL


def check_function_signature(func: Callable, param_types: Tuple[Type, ...], return_type: Type) -> bool:
    """ 检查给定函数的参数类型和返回值类型是否与指定类型一致 """
    if not callable(func):
        return False

    # 获取函数的参数签名
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # 检查参数个数
    if len(params) != len(param_types):
        return False

    # 检查每个参数的类型
    for param, expected_type in zip(params, param_types):
        if param.annotation is not expected_type and param.annotation is not inspect._empty:
            return False

    # 检查返回值类型
    if sig.return_annotation is not return_type and sig.return_annotation is not inspect._empty:
        return False

    return True


def BrCompress(bin: bytes) -> bytes:
    """ brotli Br压缩 """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.BrCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def BrUnCompress(bin: bytes) -> bytes:
    """ brotli 解压缩 """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.BrUnCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def DeflateCompress(bin: bytes) -> bytes:
    """ (可能等同于zlib压缩) """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.DeflateCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def DeflateUnCompress(bin: bytes) -> bytes:
    """ (可能等同于zlib解压缩) """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.DeflateUnCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def ZSTDCompress(bin: bytes) -> bytes:
    """ (可能等同于zlib压缩) """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.ZSTDCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def ZSTDUnCompress(bin: bytes) -> bytes:
    """ (可能等同于zlib解压缩) """
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.ZSTDDecompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def GzipCompress(bin: bytes) -> bytes:
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.GzipCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def GzipUnCompress(bin: bytes) -> bytes:
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.GzipUnCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def ZlibCompress(bin: bytes) -> bytes:
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.ZlibCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def ZlibUnCompress(bin: bytes) -> bytes:
    if not isinstance(bin, bytes):
        return bytearray()
    Ptr = SunnyDLL.DLLSunny.ZlibUnCompress(create_string_buffer(bin), len(bin))
    return SunnyDLL.PointerToBytes(Ptr)


def PbToJson(pbData: bytes) -> str:
    if not isinstance(pbData, bytes):
        return ""
    return SunnyDLL.DLLSunny.PbToJson(create_string_buffer(pbData), len(pbData))


def JsonToPB(jsonString: str) -> bytes:
    if not isinstance(jsonString, str):
        return bytearray()
    try:
        d = jsonString.encode("gbk")
    except:
        try:
            d = jsonString.encode("utf-8")
        except:
            return bytearray()
    return SunnyDLL.PointerToBytes(SunnyDLL.DLLSunny.JsonToPB(create_string_buffer(d), len(d)))


HTTP2_fp_Config_Firefox = "{\"ConnectionFlow\":12517377,\"HeaderPriority\":{\"StreamDep\":13,\"Exclusive\":false,\"Weight\":41},\"Priorities\":[{\"PriorityParam\":{\"StreamDep\":0,\"Exclusive\":false,\"Weight\":200},\"StreamID\":3},{\"PriorityParam\":{\"StreamDep\":0,\"Exclusive\":false,\"Weight\":100},\"StreamID\":5},{\"PriorityParam\":{\"StreamDep\":0,\"Exclusive\":false,\"Weight\":0},\"StreamID\":7},{\"PriorityParam\":{\"StreamDep\":7,\"Exclusive\":false,\"Weight\":0},\"StreamID\":9},{\"PriorityParam\":{\"StreamDep\":3,\"Exclusive\":false,\"Weight\":0},\"StreamID\":11},{\"PriorityParam\":{\"StreamDep\":0,\"Exclusive\":false,\"Weight\":240},\"StreamID\":13}],\"PseudoHeaderOrder\":[\":method\",\":path\",\":authority\",\":scheme\"],\"Settings\":{\"1\":65536,\"4\":131072,\"5\":16384},\"SettingsOrder\":[1,4,5]}"
HTTP2_fp_Config_Opera = "{\"ConnectionFlow\":15663105,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":authority\",\":scheme\",\":path\"],\"Settings\":{\"1\":65536,\"3\":1000,\"4\":6291456,\"6\":262144},\"SettingsOrder\":[1,3,4,6]}"
HTTP2_fp_Config_Safari_IOS_17_0 = "{\"ConnectionFlow\":10485760,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":scheme\",\":path\",\":authority\"],\"Settings\":{\"2\":0,\"3\":100,\"4\":2097152},\"SettingsOrder\":[2,4,3]}"
HTTP2_fp_Config_Safari_IOS_16_0 = "{\"ConnectionFlow\":10485760,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":scheme\",\":path\",\":authority\"],\"Settings\":{\"3\":100,\"4\":2097152},\"SettingsOrder\":[4,3]}"
HTTP2_fp_Config_Safari = "{\"ConnectionFlow\":10485760,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":scheme\",\":path\",\":authority\"],\"Settings\":{\"3\":100,\"4\":4194304},\"SettingsOrder\":[4,3]}"
HTTP2_fp_Config_Chrome_117_120_124 = "{\"ConnectionFlow\":15663105,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":authority\",\":scheme\",\":path\"],\"Settings\":{\"1\":65536,\"2\":0,\"4\":6291456,\"6\":262144},\"SettingsOrder\":[1,2,4,6]}"
HTTP2_fp_Config_Chrome_106_116 = "{\"ConnectionFlow\":15663105,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":authority\",\":scheme\",\":path\"],\"Settings\":{\"1\":65536,\"2\":0,\"3\":1000,\"4\":6291456,\"6\":262144},\"SettingsOrder\":[1,2,3,4,6]}"
HTTP2_fp_Config_Chrome_103_105 = "{\"ConnectionFlow\":15663105,\"HeaderPriority\":null,\"Priorities\":null,\"PseudoHeaderOrder\":[\":method\",\":authority\",\":scheme\",\":path\"],\"Settings\":{\"1\":65536,\"3\":1000,\"4\":6291456,\"6\":262144},\"SettingsOrder\":[1,3,4,6]}"
