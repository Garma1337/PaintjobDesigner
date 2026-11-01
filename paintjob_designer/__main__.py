# coding: utf-8

import sys

from PySide6.QtWidgets import QApplication

from paintjob_designer.gui.main_window import MainWindow
from paintjob_designer.services import container


def main() -> int:
    app = QApplication(sys.argv)
    app.setWindowIcon(container.resolve("app_icon").load())

    window = MainWindow(container)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
