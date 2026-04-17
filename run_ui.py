import sys

from PyQt6.QtWidgets import QApplication

from src.petcare_ui.app import PetCareApp


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pet Care Management")

    ui = PetCareApp()
    ui.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

