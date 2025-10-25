from __future__ import annotations

import re
from urllib.parse import unquote
import random
import string

def get_cookie_item_value(cookies: str, name: str) -> str | None:
    """
    从 Cookie 字符串中获取指定名称的值
    """
    # 正则匹配 Cookie 项
    match = re.search(rf"(?:\s|;|^){re.escape(name)}=([^;]+)(?=;|$)", cookies)
    if match:
        # URL 解码 + 转义字符处理
        return unquote(match.group(1))
    return None

def replace_cookie_item(cookies: str, name: str, value: str | None) -> str:
    """
    替换或添加 Cookie 项
    """
    if value is None or value.strip() == "":
        # 删除 Cookie 项
        items = cookies.split(";")
        new_items = []
        for item in items:
            if not item.strip():
                continue
            key_value = item.strip().split("=", 1)
            key = key_value[0]
            if key != name:
                new_items.append(item.strip())
        return ";".join(new_items)

    # 检查是否已存在该 Cookie
    current_value = get_cookie_item_value(cookies, name)
    if current_value is None:
        # 添加新 Cookie
        if cookies and cookies.strip().endswith(";"):
            return f"{cookies}{name}={value}"
        return f"{cookies};{name}={value}"

    # 替换现有 Cookie
    return cookies.replace(f"{name}={current_value}", f"{name}={value}")

def get_random_string(length: int = 11, is_number: bool = False) -> str:
    """
    生成指定长度的随机字符串
    """
    if is_number:
        characters = string.digits
    else:
        characters = string.digits + string.ascii_uppercase
    return "".join(random.choice(characters) for _ in range(length))