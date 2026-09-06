"""Application entry point for the eli_lab Pattern Generator."""

try:
    from .compat import MainWindow
    from .ui import build_app
except ImportError:  # pragma: no cover - direct execution compatibility
    from compat import MainWindow
    from ui import build_app


def main() -> int:
    app = build_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
