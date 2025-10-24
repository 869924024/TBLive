#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据格式转换脚本
将shebei.txt转换为设备.txt的格式，删除指定列
"""

def convert_shebei_to_shebei_format():
    """
    转换shebei.txt的数据格式，删除第4列（36274712679450@tmall_android_13.12.2）
    并将分隔符从----改为制表符
    注意：此脚本采用追加模式，不会覆盖现有数据
    """
    input_file = 'shebei.txt'
    output_file = '../设备.txt'

    converted_lines = []

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue

            # 按----分割数据
            parts = line.split('----')

            # 检查数据格式是否正确
            if len(parts) != 6:
                print(f"警告：第{line_num}行数据格式不正确，共有{len(parts)}个部分")
                print(f"数据内容：{line}")
                continue

            # 删除第4列（索引为3），即36274712679450@tmall_android_13.12.2
            # 保留：第1列, 第2列, 第3列, 第5列, 第6列
            converted_parts = [parts[0], parts[1], parts[2], parts[4], parts[5]]

            # 用制表符连接
            converted_line = '\t'.join(converted_parts)
            converted_lines.append(converted_line)

        # 追加到输出文件（不覆盖现有数据）
        with open(output_file, 'a', encoding='utf-8') as f:
            for line in converted_lines:
                f.write(line + '\n')

        print(f"转换完成！")
        print(f"输入文件：{input_file}")
        print(f"输出文件：{output_file} (追加模式)")
        print(f"总共转换了 {len(converted_lines)} 行数据")
        print(f"数据已追加到文件末尾，原有数据保留")

        # 显示转换示例
        if converted_lines:
            print("\n转换示例（前3行）：")
            for i, line in enumerate(converted_lines[:3], 1):
                print(f"{i}. {line}")

    except FileNotFoundError:
        print(f"错误：找不到输入文件 {input_file}")
    except Exception as e:
        print(f"转换过程中发生错误：{str(e)}")

if __name__ == "__main__":
    convert_shebei_to_shebei_format()