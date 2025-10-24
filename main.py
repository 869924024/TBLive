import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import  Qt
from ui import MainWindow


# 启用高DPI
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())