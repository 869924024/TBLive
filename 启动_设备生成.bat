@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title 设备参数生成工具

echo ============================================================
echo               设备参数批量生成工具
echo ============================================================
echo.
echo 请选择运行模式：
echo.
echo 1. 生成指定数量（快速模式）
echo 2. 生成指定数量（多窗口并发）
echo 3. 无限循环生成
echo 4. 自定义参数
echo.
set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" (
    set /p num="请输入要生成的数量: "
    echo.
    echo 启动中...
    python generate_device.py -n !num! -w 1
    goto end
)

if "%choice%"=="2" (
    set /p num="请输入要生成的数量: "
    set /p windows="请输入并发窗口数 (1-10): "
    echo.
    echo 启动中...
    python generate_device.py -n !num! -w !windows!
    goto end
)

if "%choice%"=="3" (
    set /p windows="请输入并发窗口数 (1-10): "
    echo.
    echo 启动中...
    python generate_device.py -w !windows!
    goto end
)

if "%choice%"=="4" (
    echo.
    echo 命令格式: python generate_device.py -n [数量] -w [窗口数]
    echo 示例: python generate_device.py -n 100 -w 3
    echo.
    set /p cmd="请输入完整命令: "
    !cmd!
    goto end
)

echo 无效的选项！
pause
goto end

:end
echo.
echo ============================================================
echo 程序已结束
echo ============================================================
pause
