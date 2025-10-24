def json_cookie_to_string(json_cookie):
    """
    将 JSON 格式的 cookie 转换成字符串格式

    参数:
        json_cookie: dict 或 list
                    - 如果是 dict: {"key1": "value1", "key2": "value2"}
                    - 如果是 list: [{"name": "key1", "value": "value1"}, ...]

    返回:
        str: cookie 字符串，格式为 "key1=value1; key2=value2"

    示例:
        >>> json_cookie_to_string({"session": "abc123", "user": "john"})
        'session=abc123; user=john'

        >>> json_cookie_to_string([{"name": "session", "value": "abc123"}])
        'session=abc123'
    """
    if isinstance(json_cookie, dict):
        # 处理字典格式
        cookie_pairs = [f"{key}={value}" for key, value in json_cookie.items()]
        return "; ".join(cookie_pairs)

    elif isinstance(json_cookie, list):
        # 处理列表格式（通常来自浏览器开发工具）
        cookie_pairs = []
        for item in json_cookie:
            if isinstance(item, dict):
                # 支持 {"name": "key", "value": "val"} 格式
                if "name" in item and "value" in item:
                    cookie_pairs.append(f"{item['name']}={item['value']}")
                # 也支持直接的 {"key": "value"} 格式
                else:
                    for key, value in item.items():
                        cookie_pairs.append(f"{key}={value}")
        return "; ".join(cookie_pairs)

    else:
        raise TypeError("json_cookie 必须是 dict 或 list 类型")


# 使用示例
if __name__ == "__main__":
    # 示例 1: 字典格式
    cookie_dict = {
        "session_id": "abc123xyz",
        "user_token": "token_value",
        "theme": "dark"
    }
    print("字典格式转换:")
    print(json_cookie_to_string(cookie_dict))
    print()

    # 示例 2: 列表格式（类似浏览器开发工具导出的格式）
    cookie_list = [
        {"name": "session_id", "value": "abc123xyz"},
        {"name": "user_token", "value": "token_value"},
        {"name": "theme", "value": "dark"}
    ]
    print("列表格式转换:")
    print(json_cookie_to_string(cookie_list))
    print()

    # 示例 3: 从 JSON 字符串解析
    import json

    json_string = '{"session_id": "abc123", "user": "john"}'
    cookie_obj = json.loads(json_string)
    print("从 JSON 字符串解析后转换:")
    print(json_cookie_to_string(cookie_obj))