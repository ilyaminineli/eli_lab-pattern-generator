from __future__ import annotations

import math
import random

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLabel, QSpinBox, QTabWidget, QVBoxLayout, QWidget

from . import generator as generator_module
from .generator import PatternConfig, PatternRenderer as BaseRenderer
from .palettes import ALL_LGBTQ_COLORS, ALL_PALETTES, BUILTIN_PALETTES, PRIDE_PALETTES
from .ui import MainWindow as BaseMainWindow


# Add palette data to the original renderer without rewriting its composition
# engine. Legacy palettes and seeded behavior therefore remain unchanged.
generator_module.PALETTES.update({key: palette.colors for key, palette in ALL_PALETTES.items()})
generator_module.PALETTES["lgbtq-all"] = ALL_LGBTQ_COLORS


class EnhancedPatternRenderer(BaseRenderer):
    def __init__(self):
        super().__init__()
        self.organic_settings = {"enabled": False, "style": "amoeba", "weight": 0.8, "lobes": 7, "wobble": 0.55, "taper": 0.25, "veins": True}

    def generate(self, config: PatternConfig):
        result = super().generate(config)
        if not self.organic_settings["enabled"]:
            return result

        from PIL import ImageDraw
        rng = random.Random(f"{result.seed}:organic")
        noise = self._make_noise(result.seed, config)
        palette = self._palette(rng, config)
        draw = ImageDraw.Draw(result.image, "RGBA")
        settings = self.organic_settings
        cell = min(config.width, config.height) / max(4, config.grid_size)
        cols = max(1, math.ceil(config.width / cell)); rows = max(1, math.ceil(config.height / cell))
        count = max(1, min(500, int(config.grid_size ** 2 * config.density * 0.18 * max(0.25, settings["weight"]))))
        svg_parts = []

        for _ in range(count):
            gx = rng.randrange(cols); gy = rng.randrange(rows)
            cx = (gx + 0.5) * cell; cy = (gy + 0.5) * cell
            if config.field_mode != "none":
                n = self._noise_value(cx, cy, noise, config); angle = self._field_angle(cx, cy, config, noise)
                drift = config.field_strength * config.jitter * cell * n
                cx += math.cos(angle) * drift; cy += math.sin(angle) * drift
            if rng.random() > 0.45 + 0.55 * config.complexity:
                continue
            size = cell * config.shape_scale * rng.uniform(0.50, 0.95) * (1.0 - 0.15 * config.spacing)
            rotation = math.radians(config.rotation) + rng.uniform(-config.rotation_jitter, config.rotation_jitter)
            color = self._choose_color(rng, palette, config, cx, cy)
            alpha = int(255 * rng.uniform(config.opacity_min, config.opacity_max) * 0.84)
            for ix, iy, irot in self._symmetry_instances(cx, cy, rotation, config):
                points = self._points(ix, iy, size, settings, rng, irot)
                draw.polygon(points, fill=(*color, alpha))
                svg_parts.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{alpha/255:.3f}"/>')
                if settings["veins"] and settings["style"] in {"leaf", "petal", "droplet"}:
                    vein = self._vein(ix, iy, size, settings["style"], irot)
                    va = max(30, int(alpha * 0.52)); vw = max(1, int(size * 0.012))
                    draw.line(vein, fill=(*color, va), width=vw, joint="curve")
                    svg_parts.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in vein)}" fill="none" stroke="rgb({color[0]},{color[1]},{color[2]})" stroke-opacity="{va/255:.3f}" stroke-width="{vw}" stroke-linecap="round"/>')

        if svg_parts:
            result.svg = result.svg.rsplit("</svg>", 1)[0] + "\n" + "\n".join(svg_parts) + "\n</svg>"
        return result

    @staticmethod
    def _points(cx, cy, size, settings, rng, rotation):
        style = settings["style"]; lobes = max(3, int(settings["lobes"])); wobble = max(0.0, min(1.0, float(settings["wobble"]))); taper = max(0.0, min(1.0, float(settings["taper"])))
        count = max(18, lobes * 4); phase = rng.uniform(0, math.tau); stretch = 1.55 if style == "leaf" else 1.18 if style == "droplet" else 1.0
        pts = []
        for i in range(count):
            a = math.tau * i / count; r = 0.82 + wobble * (0.13 * math.sin(lobes*a + phase) + 0.07 * math.sin((lobes+2)*a - phase*0.7))
            if style == "amoeba": r *= 1 + 0.18 * math.sin(3*a + phase*0.5)
            elif style == "blob": r *= 0.94 + 0.08 * math.sin(2*a + phase)
            elif style == "petal": r *= 0.76 + 0.28 * (0.5 + 0.5 * math.cos(lobes*a))
            elif style == "cell": r *= 0.95 + 0.05 * math.sin(lobes*a + phase)
            elif style == "droplet": r *= (1 - 0.20*math.sin(a)) * (1 + 0.20*taper*math.cos(a))
            elif style == "leaf": r *= 0.92 - 0.28*taper*abs(math.sin(a))
            x = math.cos(a) * size * 0.5 * r * stretch; y = math.sin(a) * size * 0.5 * r
            if style == "leaf": x *= 1 - 0.20*abs(math.sin(a))
            ca, sa = math.cos(rotation), math.sin(rotation)
            pts.append((cx + x*ca - y*sa, cy + x*sa + y*ca))
        return pts

    @staticmethod
    def _vein(cx, cy, size, style, rotation):
        local = [(-size*0.72, 0), (0, 0), (size*0.72, 0)] if style == "leaf" else [(0, size*0.40), (0, 0), (0, -size*0.40)]
        ca, sa = math.cos(rotation), math.sin(rotation)
        return [(cx + x*ca - y*sa, cy + x*sa + y*ca) for x,y in local]


class MainWindow(BaseMainWindow):
    """Stable dark UI with additive palettes and an optional Organic tab."""

    def __init__(self):
        super().__init__()
        self.renderer = EnhancedPatternRenderer()
        self.generate()

    def _build_ui(self):
        super()._build_ui()
        tabs = self.findChild(QTabWidget)
        if tabs is not None:
            tabs.addTab(self._organic_tab(), "Organic")
        self._extend_palette_selector()
        self._add_palette_lock()
        self._wire_extensions()

    def _organic_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); box = QWidget(); form = QFormLayout(box)
        self.use_organic = QCheckBox("Enable organic forms"); self.use_organic.setChecked(False)
        self.organic_style = QComboBox(); self.organic_style.addItems(["amoeba", "blob", "petal", "cell", "droplet", "leaf"])
        self.organic_weight = QDoubleSpinBox(); self.organic_weight.setRange(0,4); self.organic_weight.setValue(0.8); self.organic_weight.setSingleStep(0.1)
        self.organic_lobes = QSpinBox(); self.organic_lobes.setRange(3,18); self.organic_lobes.setValue(7)
        self.organic_wobble = QDoubleSpinBox(); self.organic_wobble.setRange(0,1); self.organic_wobble.setValue(0.55); self.organic_wobble.setSingleStep(0.05)
        self.organic_taper = QDoubleSpinBox(); self.organic_taper.setRange(0,1); self.organic_taper.setValue(0.25); self.organic_taper.setSingleStep(0.05)
        self.organic_veins = QCheckBox("Internal veins / tendrils"); self.organic_veins.setChecked(True)
        for label, widget in [("Enable",self.use_organic),("Style",self.organic_style),("Weight",self.organic_weight),("Lobes",self.organic_lobes),("Wobble",self.organic_wobble),("Taper",self.organic_taper),("",self.organic_veins)]: form.addRow(label, widget)
        layout.addWidget(QLabel("A separate organic layer: amoeba, blob, petal, cell, droplet and leaf. Off = original composition.")); layout.addWidget(box); layout.addStretch(1); return page

    def _extend_palette_selector(self):
        combo = self.palette_mode
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("random", "random")
        combo.addItem("pastel", "pastel")
        combo.insertSeparator(combo.count())
        for key, palette in BUILTIN_PALETTES.items():
            combo.addItem(palette.name, key)
        combo.addItem("LGBTQ+ / all unique colors", "lgbtq-all")
        combo.insertSeparator(combo.count())
        for key, palette in PRIDE_PALETTES.items():
            combo.addItem(palette.name, key)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _add_palette_lock(self):
        self.preserve_palette = QCheckBox("Preserve exact Pride palette colors"); self.preserve_palette.setChecked(True)
        for box in self.findChildren(QWidget):
            if hasattr(box, "title") and box.title() == "Color behavior" and isinstance(box.layout(), QFormLayout):
                box.layout().addRow("", self.preserve_palette); return

    def _wire_extensions(self):
        for control in [self.use_organic, self.organic_style, self.organic_weight, self.organic_lobes, self.organic_wobble, self.organic_taper, self.organic_veins, self.preserve_palette]:
            if isinstance(control, QComboBox): control.currentTextChanged.connect(self._request)
            elif isinstance(control, QCheckBox): control.toggled.connect(self._request)
            else: control.valueChanged.connect(self._request)

    def _config(self):
        cfg = super()._config(); values = cfg.to_dict(); key = self.palette_mode.currentData() or self.palette_mode.currentText(); values["palette_mode"] = key if key in generator_module.PALETTES else "random"
        if self.preserve_palette.isChecked() and values["palette_mode"] not in {"random", "pastel"}: values.update(hue_jitter=0.0, saturation=1.0, contrast=0.0)
        self.renderer.organic_settings = {"enabled": self.use_organic.isChecked(), "style": self.organic_style.currentText(), "weight": self.organic_weight.value(), "lobes": self.organic_lobes.value(), "wobble": self.organic_wobble.value(), "taper": self.organic_taper.value(), "veins": self.organic_veins.isChecked()}
        return PatternConfig(**values)
