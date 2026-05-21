import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEvent
from ui.main_window import MainWindow


class ForexApp(QApplication):
    def event(self, event):
        if event.type() == QEvent.Type.ApplicationActivate:
            for w in self.topLevelWindows():
                if not w.isVisible():
                    w.showNormal()
                    w.raise_()
                    w.activateWindow()
        return super().event(event)


def main():
    app = ForexApp(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("实时外汇监控系统")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
