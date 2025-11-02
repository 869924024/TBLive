@echo off
chcp 65001 >nul
echo ========================================
echo 淘宝直播刷量客户端 - 打包脚本
echo ========================================
echo.

echo [1/4] 检查依赖...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python！请先安装 Python。
    pause
    exit /b 1
)

pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ 未找到 PyInstaller，正在安装...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ❌ PyInstaller 安装失败！
        pause
        exit /b 1
    )
)

echo ✓ 依赖检查完成
echo.

echo [2/4] 清理旧的打包文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "淘宝直播刷量客户端.spec" del "淘宝直播刷量客户端.spec"
echo ✓ 清理完成
echo.

echo [3/4] 开始打包（这可能需要几分钟）...
pyinstaller --name="淘宝直播刷量客户端" ^
    --onefile ^
    --windowed ^
    --add-data "model;model" ^
    --collect-all PyQt5 ^
    --collect-all qfluentwidgets ^
    --hidden-import PyQt5 ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import PyQt5.sip ^
    --hidden-import qfluentwidgets ^
    --hidden-import qfluentwidgets.common ^
    --hidden-import qfluentwidgets.components ^
    --hidden-import to_requests ^
    --hidden-import database ^
    --hidden-import tools ^
    --hidden-import model.user ^
    --hidden-import model.device ^
    --hidden-import taobao ^
    --hidden-import proxy_manager ^
    --hidden-import requests ^
    --hidden-import httpx ^
    --hidden-import asyncio ^
    --exclude-module generate_device ^
    --exclude-module mumu ^
    --exclude-module SunnyNet ^
    --exclude-module api_server ^
    --exclude-module import_data_to_db ^
    ui_client.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ 打包失败！请检查错误信息。
    echo.
    echo 常见问题：
    echo 1. 检查是否安装了所有依赖: pip install -r requirements.txt
    echo 2. 检查 PyInstaller 版本: pip install --upgrade pyinstaller
    echo 3. 尝试使用 --console 模式查看详细错误
    echo 4. 如果遇到 DLL 加载失败，尝试使用 --onedir 模式
    pause
    exit /b 1
)

echo.
echo [可选] 如果遇到 DLL 加载失败，可以尝试使用 --onedir 模式打包：
echo pyinstaller --name="淘宝直播刷量客户端" --onedir --windowed --add-data "model;model" --collect-all PyQt5 --collect-all qfluentwidgets --hidden-import PyQt5 --hidden-import PyQt5.QtCore --hidden-import PyQt5.QtGui --hidden-import PyQt5.QtWidgets ui_client.py

echo.
echo [4/4] 打包完成！
echo.
echo ========================================
echo 打包成功！
echo ========================================
echo.
echo 📦 可执行文件位置: dist\淘宝直播刷量客户端.exe
echo.
echo 📝 注意事项：
echo 1. 首次运行会自动创建配置文件（client_config.json）
echo 2. 日志文件会自动保存在 logs\ 目录
echo 3. 确保有网络连接（用于拉取资源和执行任务）
echo.
echo 按任意键退出...
pause >nul
