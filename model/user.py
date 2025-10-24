import tools

class User:
    def __init__(self, cookies):
        self.cookies = cookies

        # 获取昵称，依次尝试三个 Cookie 键
        nickname = tools.get_cookie_item_value(cookies, "tracknick")
        if nickname is None:
            nickname = tools.get_cookie_item_value(cookies, "lgc")
        if nickname is None:
            nickname = tools.get_cookie_item_value(cookies, "_nk_")


        self.nickname = nickname
        self.sid = tools.get_cookie_item_value(cookies, "cookie2")
        self.uid = tools.get_cookie_item_value(cookies, "unb")