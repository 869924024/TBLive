#!/bin/bash

echo "========================================"
echo "淘宝直播刷量客户端 - 打包脚本"
echo "========================================"
echo

echo "[1/4] 检查依赖..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3！请先安装 Python3。"
    exit 1
fi

python3 --version

if ! python3 -c "import pyinstaller" 2>/dev/null; then
    echo "⚠️  未找到 PyInstaller，正在安装..."
    pip3 install pyinstaller
    if [ $? -ne 0 ]; then
        echo "❌ PyInstaller 安装失败！"
        exit 1
    fi
fi

echo "✓ 依赖检查完成"
echo

echo "[2/4] 清理旧的打包文件..."
rm -rf build dist *.spec
echo "✓ 清理完成"
echo

echo "[3/4] 开始打包（这可能需要几分钟）..."
pyinstaller --name="淘宝直播刷量客户端" \
    --onefile \
    --windowed \
    --add-data "model:model" \
    --hidden-import PyQt5 \
    --hidden-import qfluentwidgets \
    --hidden-import to_requests \
    --hidden-import database \
    --hidden-import tools \
    --hidden-import model.user \
    --hidden-import model.device \
    --hidden-import taobao \
    --hidden-import proxy_manager \
    --exclude-module generate_device \
    --exclude-module mumu \
    --exclude-module SunnyNet \
    --exclude-module api_server \
    --exclude-module import_data_to_db \
    ui_client.py

if [ $? -ne 0 ]; then
    echo
    echo "❌ 打包失败！请检查错误信息。"
    echo
    echo "常见问题："
    echo "1. 检查是否安装了所有依赖: pip3 install -r requirements.txt"
    echo "2. 检查 PyInstaller 版本: pip3 install --upgrade pyinstaller"
    echo "3. 尝试使用 --console 模式查看详细错误"
    exit 1
fi

echo
echo "[4/4] 打包完成！"
echo
echo "========================================"
echo "打包成功！"
echo "========================================"
echo
echo "📦 可执行文件位置: dist/淘宝直播刷量客户端"
echo
chmod +x dist/淘宝直播刷量客户端

echo "📝 注意事项："
echo "1. 首次运行会自动创建配置文件（client_config.json）"
echo "2. 日志文件会自动保存在 logs/ 目录"
echo "3. 确保有网络连接（用于拉取资源和执行任务）"
echo
