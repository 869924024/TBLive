#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2024/7/29 下午2:40
# @Author : wlkjyy
# @File : Core.py
# @Software: PyCharm
import json
import warnings
from typing import Union


class Info:

    def __init__(self, utils):
        self.utils = utils

    def get_info(self) -> dict:
        """
            创建模拟器
        :param number: 创建数量
        :return:
        """

        self.utils.set_operate("info")
        ret_code, retval = self.utils.run_command([])
        if ret_code != 0:
            raise RuntimeError(retval)
        data = json.loads(retval)
        return data
    def info_all(self) -> dict:
        """
            创建模拟器
        :param number: 创建数量
        :return:
        """

        self.utils.set_operate("info")
        ret_code, retval = self.utils.run_command(["all"])
        if ret_code != 0:
            raise RuntimeError(retval)
        data = json.loads(retval)
        return data