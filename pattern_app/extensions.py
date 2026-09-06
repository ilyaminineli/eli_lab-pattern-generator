from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QLabel

from . import generator as generator_module
from .palettes import ALL_LGBTQ_COLORS, ALL_PALETTES, BUILTIN_PALETTES, PRIDE_PALETTES
from .ui import MainWindow as BaseMainWindow
from .generator import PatternRenderer as BaseRenderer, PatternConfig


# Extend the original renderer's palette dictionary in-place.  The core
# generator remains untouched, so the original pattern behavior is preserved.
generator_module.PALETTES.update({key: palette.colors for key, palette in ALL_PALETTES.items()})
generator_module.PALETTES["lgbtq-all"] = ALL_LGBTQ_COLORS


class EnhancedPatternRenderer(BaseRenderer):
    def __init__(self):
        super().__init__()
        self.organic_settings = {
            "enabled": False,
            "style": "amoeba",
            "weight": 0.8,
            "lobes": 7,
            "wobble": 0.55,
            "taper": 0.25,
            "veins": True,
        }

    def generate(self, config: PatternConfig):
        result = super().generate(config)
        settings = dict(self.organic_settings)
        if not settings.get("enabled"):
            return result

        rng = random.Random(f"{result.seed}:organic")
        noise = self._make_noise(result.seed, config)
        draw = result.image.getdraw() if hasattr(result.image, "getdraw") else None
        if draw is None:
            from PIL import ImageDraw
            draw = ImageDraw.Draw(result.image, "RGBA")

        count = max(1, min(800, int(config.grid_size ** 2 * config.density * 0.16 * max(0.25, float(settings["weight"])))))
        cell = min(config.width, config.height) / max(4, config.grid_size)
        svg_parts: list[str] = []

        for index in range(count):
            gx = rng.randrange(max(1, math.ceil(config.width / cell)))
            gy = rng.randrange(max(1, math.ceil(config.height / cell)))
            cx = min(config.width, (gx + 0.5) * cell)
            cy = min(config.height, (gy + 0.5) * cell)
            p = 0.45 + 0.55 * config.complexity
            if config.field_mode != "none":
                n = self._noise_value(cx, cy, noise, config)
                angle = self._field_angle(cx, cy, config, noise)
                drift = config.field_strength * config.jitter * cell * n
                cx += math.cos(angle) * drift
                cy += math.sin(angle) * drift
            if rng.random() > p:
                continue

            size = cell * config.shape_scale * rng.uniform(0.55, 1.05)
            size *= 1.0 - 0.18 * config.spacing
            rotation = math.radians(config.rotation) + rng.uniform(-config.rotation_jitter, config.rotation_jitter)
            if config.mutation:
                rotation += rng.uniform(-1, 1) * config.mutation * 0.65
            color = self._choose_color(rng, self._palette(rng, config), config, cx, cy)
            alpha = int(255 * rng.uniform(config.opacity_min, config.opacity_max) * 0.86)
            instances = self._symmetry_instances(cx, cy, rotation, config)
            for ix, iy, irot in instances:
                points = self._organic_points(ix, iy, size, settings, rng, irot)
                draw.polygon(points, fill=(*color, alpha))
                svg_parts.append(
                    f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" '
                    f'fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{alpha/255:.3f}"/>'
                )
                if settings.get("veins") and settings.get("style") in {"petal", "leaf", "droplet"}:
                    vein_color = (*color, max(35, int(alpha * 0.55)))
                    vein_points = self._vein_points(ix, iy, size, settings["style"], irot)
                    draw.line(vein_points, fill=vein_color, width=max(1, int(size * 0.012)), joint="curve")
                    svg_parts.append(
                        f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in vein_points)}" '
                        f'fill="none" stroke="rgb({color[0]},{color[1]},{color[2]})" stroke-opacity="{max(35, int(alpha*0.55))/255:.3f}" '
                        f'stroke-width="{max(1, int(size*0.012))}" stroke-linecap="round"/>'
                    )

        if svg_parts:
            result.svg = result.svg.rsplit("</svg>", 1)[0] + "\n" + "\n".join(svg_parts) + "\n</svg>"
        return result

    @staticmethod
    def _organic_points(cx, cy, size, settings, rng, rotation):
        style = settings["style"]
        lobes = max(3, int(settings["lobes"]))
        wobble = max(0.0, min(1.0, float(settings["wobble"])))
        taper = max(0.0, min(1.0, float(settings["taper"])))
        count = max(18, lobes * 4)
        phase = rng.uniform(0, math.tau)
        points = []
        stretch = 1.0
        if style == "leaf":
            stretch = 1.55
        elif style == "droplet":
            stretch = 1.15

        for i in range(count):
            angle = math.tau * i / count
            wave = math.sin(lobes * angle + phase)
            wave2 = math.sin((lobes + 2) * angle - phase * 0.7)
            radius = 0.82 + wobble * (0.13 * wave + 0.07 * wave2)

            if style == "amoeba":
                radius *= 1.0 + 0.18 * math.sin(3 * angle + phase * 0.5)
            elif style == "blob":
                radius *= 0.94 + 0.08 * math.sin(2 * angle + phase)
            elif style == "petal":
                radius *= 0.76 + 0.28 * (0.5 + 0.5 * math.cos(lobes * angle))
            elif style == "cell":
                radius *= 0.94 + 0.05 * math.sin(lobes * angle + phase)
            elif style == "droplet":
                radius *= 1.0 - 0.20 * math.sin(angle)
                radius *= 1.0 + taper * 0.20 * math.cos(angle)
            elif style == "leaf":
                radius *= 0.92 - taper * 0.28 * abs(math.sin(angle))

            x = math.cos(angle) * size * 0.5 * radius * stretch
            y = math.sin(angle) * size * 0.5 * radius
            if style == "leaf":
                x *= 1.0 - 0.20 * abs(math.sin(angle))
            if style == "droplet":
                y *= 1.0 + 0.12 * math.sin(angle)

            ca, sa = math.cos(rotation), math.sin(rotation)
            points.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        return points

    @staticmethod
    def _vein_points(cx, cy, size, style, rotation):
        if style == "leaf":
            local = [(-size * 0.72, 0), (size * 0.0, 0), (size * 0.72, 0)]
        else:
            local = [(0, size * 0.40), (0, 0), (0, -size * 0.40)]
        ca, sa = math.cos(rotation), math.sin(rotation)
        return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in local]


class MainWindow(BaseMainWindow):
    """The original dark UI plus additive palette and organic-form controls."""

    def __init__(self):
        self.renderer = EnhancedPatternRenderer()
        super().__init__()

    def _build_ui(self):
        super()._build_ui()
        tabs = self.findChild(QTabWidget)
        if tabs is not None:
            tabs.addTab(self._organic_tab(), "Organic")
        self._extend_palette_selector()
        self._add_palette_lock()
        self._wire_extensions()

    def _organic_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        box = QWidget()
        form = QFormLayout(box)
        self.use_organic = QCheckBox("Enable organic forms")
        self.use_organic.setChecked(False)
        self.organic_style = QComboBox()
        self.organic_style.addItems(["amoeba", "blob", "petal", "cell", "droplet", "leaf"])
        self.organic_weight = QDoubleSpinBox(); self.organic_weight.setRange(0, 4); self.organic_weight.setValue(0.8); self.organic_weight.setSingleStep(0.1)
        self.organic_lobes = QSpinBox(); self.organic_lobes.setRange(3, 18); self.organic_lobes.setValue(7)
        self.organic_wobble = QDoubleSpinBox(); self.organic_wobble.setRange(0, 1); self.organic_wobble.setValue(0.55); self.organic_wobble.setSingleStep(0.05)
        self.organic_taper = QDoubleSpinBox(); self.organic_taper.setRange(0, 1); self.organic_taper.setValue(0.25); self.organic_taper.setSingleStep(0.05)
        self.organic_veins = QCheckBox("Internal veins / tendrils"); self.organic_veins.setChecked(True)
        form.addRow("Enable", self.use_organic); form.addRow("Style", self.organic_style); form.addRow("Weight", self.organic_weight)
        form.addRow("Lobes", self.organic_lobes); form.addRow("Wobble", self.organic_wobble); form.addRow("Taper", self.organic_taper); form.addRow("", self.organic_veins)
        layout.addWidget(QLabel("Organic silhouettes are layered over the original renderer, so disabling them returns the legacy composition exactly."))
        layout.addWidget(box); layout.addStretch(1)
        return page

    def _extend_palette_selector(self):
        combo = self.palette_mode
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("random", "random")
        combo.addItem("pastel", "pastel")
        combo.addSeparator()
        for key, palette in BUILTIN_PALETTES.items():
            combo.addItem(palette.name, key)
        combo.addItem("LGBTQ+ / all unique colors", "lgbtq-all")
        combo.addSeparator()
        for key, palette in PRIDE_PALETTES.items():
            combo.addItem(palette.name, key)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _add_palette_lock(self):
        # Locate the existing Color behavior group and add the preserve switch
        # without replacing the original dark stylesheet or control layout.
        self.preserve_palette = QCheckBox("Preserve exact Pride palette colors")
        self.preserve_palette.setChecked(True)
        for box in self.findChildren(QWidget):
            if hasattr(box, "title") and box.title() == "Color behavior":
                layout = box.layout()
                if isinstance(layout, QFormLayout):
                    layout.addRow("", self.preserve_palette)
                    break

    def _wire_extensions(self):
        controls = [self.use_organic, self.organic_style, self.organic_weight, self.organic_lobes, self.organic_wobble, self.organic_taper, self.organic_veins, self.preserve_palette]
        for control in controls:
            if isinstance(control, QComboBox):
                control.currentTextChanged.connect(self._request)
            elif isinstance(control, QCheckBox):
                control.toggled.connect(self._request)
            else:
                control.valueChanged.connect(self._request)

    def _config(self):
        cfg = super()._config()
        palette_key = self.palette_mode.currentData() or self.palette_mode.currentText()
        if palette_key not in generator_module.PALETTES:
            palette_key = "random"
        if getattr(self, "preserve_palette", None) is not None and self.preserve_palette.isChecked() and palette_key not in {"random", "pastel"}:
            values = cfg.to_dict()
            values["palette_mode"] = palette_key
            values["hue_jitter"] = 0.0
            values["saturation"] = 1.0
            values["contrast"] = 0.0
            cfg = PatternConfig(**values)
        else:
            values = cfg.to_dict(); values["palette_mode"] = palette_key; cfg = PatternConfig(**values)

        self.renderer.organic_settings = {
            "enabled": self.use_organic.isChecked(),
            "style": self.organic_style.currentText(),
            "weight": self.organic_weight.value(),
            "lobes": self.organic_lobes.value(),
            "wobble": self.organic_wobble.value(),
            "taper": self.organic_taper.value(),
            "veins": self.organic_veins.isChecked(),
        }
        return cfg

    def save_preset(self):
        path, _ = self._save_preset_path()
        if not path:
            return
        data = self._config().to_dict()
        data["_eli_lab_extensions"] = {"organic": dict(self.renderer.organic_settings), "preserve_palette": self.preserve_palette.isChecked()}
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _save_preset_path(self):
        from PySide6.QtWidgets import QFileDialog
        return QFileDialog.getSaveFileName(self, "Save preset", "pattern-preset.json", "JSON (*.json)")

    def load_preset(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            extensions = data.pop("_eli_lab_extensions", {})
            organic = extensions.get("organic", {})
            # Use the original loader for all legacy PatternConfig fields by
            # applying them directly; this also keeps older presets loadable.
            c = PatternConfig(**data).normalized()
            self._loading_preset = True
            self.width.setValue(c.width); self.height.setValue(c.height); self.seed.setText(c.seed); self.background.setText(c.background); self.aspect.setCurrentText("custom"); self.symmetry.setCurrentText(c.symmetry); self.palette_mode.setCurrentIndex(max(0, self.palette_mode.findData(c.palette_mode)))
            self.composition_mode.setCurrentText(c.composition_mode); self.focal_x.setValue(c.focal_x); self.focal_y.setValue(c.focal_y); self.focal_strength.setValue(c.focal_strength); self.edge_bias.setValue(c.edge_bias); self.cluster_count.setValue(c.cluster_count); self.cluster_strength.setValue(c.cluster_strength); self.spacing.setValue(c.spacing); self.jitter.setValue(c.jitter)
            self.field_mode.setCurrentText(c.field_mode); self.field_strength.setValue(c.field_strength); self.field_scale.setValue(c.field_scale); self.field_curvature.setValue(c.field_curvature); self.field_steps.setValue(c.field_steps); self.field_step_size.setValue(c.field_step_size); self.noise_octaves.setValue(c.noise_octaves)
            self.grid_size.setValue(c.grid_size); self.shape_scale.setValue(c.shape_scale); self.scale_variance.setValue(c.scale_variance); self.rotation.setValue(c.rotation); self.rotation_jitter.setValue(c.rotation_jitter); self.corner_roundness.setValue(c.corner_roundness); self.line_complexity.setValue(c.line_complexity); self.overlap.setValue(c.overlap)
            self.use_blocks.setChecked(c.use_blocks); self.use_circles.setChecked(c.use_circles); self.use_lines.setChecked(c.use_lines); self.use_triangles.setChecked(c.use_triangles); self.block_weight.setValue(c.block_weight); self.circle_weight.setValue(c.circle_weight); self.line_weight.setValue(c.line_weight); self.triangle_weight.setValue(c.triangle_weight)
            self.palette_size.setValue(c.palette_size); self.saturation.setValue(c.saturation); self.contrast.setValue(c.contrast); self.hue_jitter.setValue(c.hue_jitter); self.opacity_min.setValue(c.opacity_min); self.opacity_max.setValue(c.opacity_max); self.color_coherence.setValue(c.color_coherence)
            self.layer_count.setValue(c.layer_count); self.depth.setValue(c.depth); self.accent_density.setValue(c.accent_density); self.gradient.setChecked(c.gradient); self.blur.setValue(c.blur); self.behavior.setCurrentText(c.behavior); self.mutation.setValue(c.mutation); self.asymmetry.setValue(c.asymmetry)
            self.use_organic.setChecked(bool(organic.get("enabled", False))); self.organic_style.setCurrentText(organic.get("style", "amoeba")); self.organic_weight.setValue(float(organic.get("weight", .8))); self.organic_lobes.setValue(int(organic.get("lobes", 7))); self.organic_wobble.setValue(float(organic.get("wobble", .55))); self.organic_taper.setValue(float(organic.get("taper", .25))); self.organic_veins.setChecked(bool(organic.get("veins", True))); self.preserve_palette.setChecked(bool(extensions.get("preserve_palette", True)))
        except Exception as exc:
            QMessageBox.critical(self, self.APP_NAME, f"Could not load preset:\n{exc}")
        finally:
            self._loading_preset = False
        self.generate()
