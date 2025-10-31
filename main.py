import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui import MainWindow
from loguru import logger

# 配置日志输出到文件
if not os.path.exists('logs'):
    os.makedirs('logs')

# 移除默认的控制台输出
logger.remove()

# 添加控制台输出（带颜色）
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 添加文件输出（按日期轮转）
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天0点轮转
    retention="7 days",  # 保留7天
    compression="zip",  # 压缩旧日志
    encoding="utf-8",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# 添加错误日志单独保存
logger.add(
    "logs/error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",  # 错误日志保留30天
    compression="zip",
    encoding="utf-8",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

logger.info("=" * 60)
logger.info("🚀 程序启动")
logger.info("=" * 60)

# 启用高DPI
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

app = QApplication(sys.argv)
window = MainWindow()
window.show()

logger.info("✅ 主窗口已显示")

try:
    exit_code = app.exec_()
    logger.info("=" * 60)
    logger.info(f"🛑 程序正常退出 (exit_code={exit_code})")
    logger.info("=" * 60)
    sys.exit(exit_code)
except Exception as e:
    logger.error("=" * 60)
    logger.error(f"❌ 程序异常退出: {e}")
    logger.error("=" * 60)
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)