"""Convenient PyCharm-friendly launcher for the eli_lab Pattern Generator."""

from pattern_app.main import MainWindow, main as app_main


def _wire_auto_preview_safely(self):
    """Connect each control through its actual Qt signal type."""
    widgets = [
        self.width,
        self.height,
        self.seed,
        self.background,
        self.palette,
        self.symmetry,
        self.use_blocks,
        self.use_circles,
        self.use_lines,
        self.use_triangles,
        self.use_noise,
        self.noise_octaves,
        self.gradient,
        self.use_accents,
    ]
    for widget in widgets:
        if hasattr(widget, "textChanged"):
            widget.textChanged.connect(self._request_preview)
        elif hasattr(widget, "currentTextChanged"):
            widget.currentTextChanged.connect(self._request_preview)
        elif hasattr(widget, "toggled"):
            widget.toggled.connect(self._request_preview)
        elif hasattr(widget, "valueChanged"):
            widget.valueChanged.connect(self._request_preview)

    for slider in (
            self.density,
            self.complexity,
            self.grid,
            self.noise_scale,
            self.noise_amplitude,
            self.blur,
    ):
        slider.valueChanged.connect(lambda _value: self._request_preview())


# PyCharm commonly runs this file directly. Install the safe signal wiring
# before MainWindow.__init__ is invoked by pattern_app.main.main().
MainWindow._wire_auto_preview = _wire_auto_preview_safely

if __name__ == "__main__":
    raise SystemExit(app_main())
