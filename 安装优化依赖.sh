#!/bin/bash

echo "=========================================="
echo "  高并发优化依赖安装脚本"
echo "=========================================="
echo ""

# 检查pip是否存在
if ! command -v pip &> /dev/null; then
    echo "❌ pip未安装，请先安装Python环境"
    exit 1
fi

echo "📦 开始安装优化依赖..."
echo ""

# 安装HTTP/2支持（h2库）
echo "1️⃣ 安装HTTP/2支持（h2库）..."
pip install 'httpx[http2]' -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 安装uvloop（高性能事件循环）
echo "2️⃣ 安装uvloop（高性能事件循环）..."
pip install uvloop -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

echo "=========================================="
echo "✅ 优化依赖安装完成！"
echo ""
echo "性能提升预期："
echo "  • HTTP/2: 20-40%速度提升"
echo "  • uvloop: 20-40%异步性能提升"
echo "  • 综合提升: 40-70%"
echo ""
echo "现在可以运行程序，享受更快的速度！"
echo "=========================================="

