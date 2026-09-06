from __future__ import annotations

import html
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
)

from . import generator as generator_module
from .generator import PatternConfig, PatternRenderer as BaseRenderer, _rotate
from .palettes import ALL_LGBTQ_COLORS, ALL_PALETTES, BUILTIN_PALETTES, PRIDE_PALETTES
from .ui import MainWindow as BaseMainWindow


# Extend the original palette registry without replacing the composition engine.
generator_module.PALETTES.update({key: palette.colors for key, palette in ALL_PALETTES.items()})
generator_module.PALETTES["lgbtq-all"] = ALL_LGBTQ_COLORS


def _system_font_family() -> str:
    """Prefer Bahnschrift when Windows has it installed; otherwise use Qt's UI font."""
    try:
        families = set(QFontDatabase.families())
    except Exception:
        families = set()
    return "Bahnschrift" if "Bahnschrift" in families else QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()


class EnhancedPatternRenderer(BaseRenderer):
    """Additive renderer extensions: perspective geometry, organic linework, and text."""

    def __init__(self):
        super().__init__()
        self.organic_settings = {
            "enabled": False,
            "style": "amoeba",
            "weight": 0.8,
            "lobes": 7,
            "wobble": 0.55,
            "taper": 0.25,
            "line_mode": "mixed",
            "veins": True,
            "vein_count": 3,
            "vein_wobble": 0.55,
            "strand_count": 8,
            "strand_length": 26,
            "strand_wander": 0.45,
            "strand_width": 1.5,
        }
        self.perspective_settings = {
            "enabled": True,
            "strength": 0.18,
            "vanishing_x": 0.5,
            "vanishing_y": 0.42,
            "edge_light": 0.28,
        }
        self.text_settings = {
            "enabled": False,
            "text": "",
            "mode": "flow",
            "font_family": _system_font_family(),
            "font_size": 72,
            "opacity": 0.82,
            "tracking": 2.0,
            "line_spacing": 1.18,
            "radius": 0.33,
            "wave": 0.12,
            "rotation": 0.0,
        }

    def generate(self, config: PatternConfig):
        result = super().generate(config)
        if self.organic_settings["enabled"]:
            self._draw_organic_extension(result, config)
        if self.text_settings["enabled"] and self.text_settings["text"].strip():
            self._draw_text_extension(result, config)
        return result

    # ------------------------------------------------------------------
    # Perspective / dimensional geometry
    # ------------------------------------------------------------------

    def _shape(self, draw, svg, cfg, shape, cx, cy, size, rotation, color, alpha):
        settings = self.perspective_settings
        if not settings["enabled"] or settings["strength"] <= 0:
            return super()._shape(draw, svg, cfg, shape, cx, cy, size, rotation, color, alpha)

        vx = cfg.width * settings["vanishing_x"]
        vy = cfg.height * settings["vanishing_y"]
        dx = cx - vx
        dy = cy - vy
        distance = max(1.0, math.hypot(dx, dy))
        depth = size * settings["strength"] * (0.65 + 0.35 * min(1.0, distance / max(cfg.width, cfg.height)))
        ox = dx / distance * depth
        oy = dy / distance * depth
        shadow = tuple(max(0, int(c * 0.42)) for c in color)
        shadow_alpha = max(24, int(alpha * 0.52))

        if shape in {"block", "tri"}:
            half = size * 0.5
            if shape == "tri":
                front = _rotate([(cx, cy - half), (cx - half, cy + half), (cx + half, cy + half)], rotation, cx, cy)
            else:
                front = _rotate([(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)], rotation, cx, cy)
            back = [(x + ox, y + oy) for x, y in front]
            draw.polygon(back, fill=(*shadow, shadow_alpha))
            # Side faces add a simple extruded / perspective reading without changing the front primitive.
            face_alpha = max(18, int(alpha * 0.38))
            for i in range(len(front)):
                a, b = front[i], front[(i + 1) % len(front)]
                draw.polygon([a, b, back[(i + 1) % len(front)], back[i]], fill=(*shadow, face_alpha))
                svg.append(
                    f'<polygon points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} '
                    f'{back[(i + 1) % len(front)][0]:.1f},{back[(i + 1) % len(front)][1]:.1f} '
                    f'{back[i][0]:.1f},{back[i][1]:.1f}" fill="rgb{shadow}" fill-opacity="{face_alpha/255:.3f}"/>'
                )
            svg.append(
                f'<polygon points="{" ".join(f"{x+ox:.1f},{y+oy:.1f}" for x,y in front)}" '
                f'fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{shadow_alpha/255:.3f}"/>'
            )
        elif shape == "circle":
            r = size * 0.5
            draw.ellipse((cx - r + ox, cy - r + oy, cx + r + ox, cy + r + oy), fill=(*shadow, shadow_alpha))
            svg.append(
                f'<ellipse cx="{cx+ox:.1f}" cy="{cy+oy:.1f}" rx="{r:.1f}" ry="{r:.1f}" '
                f'fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{shadow_alpha/255:.3f}"/>'
            )
        elif shape == "line":
            half = size * 0.5
            count = 3 + int(cfg.line_complexity * 6)
            front = []
            for i in range(count):
                t = i / max(1, count - 1)
                front.append((cx - half + t * size, cy + math.sin(t * math.pi * 2 + rotation) * size * 0.25))
            front = _rotate(front, rotation, cx, cy)
            back = [(x + ox, y + oy) for x, y in front]
            draw.line(back, fill=(*shadow, shadow_alpha), width=max(1, int((1 + cfg.depth * 5) * size / 120)), joint="curve")
            svg.append(
                f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in back)}" fill="none" '
                f'stroke="rgb({shadow[0]},{shadow[1]},{shadow[2]})" stroke-opacity="{shadow_alpha/255:.3f}" '
                f'stroke-width="{max(1, int((1 + cfg.depth * 5) * size / 120))}" stroke-linecap="round"/>'
            )

        # Let the legacy front-face renderer draw exactly as before.
        super()._shape(draw, svg, cfg, shape, cx, cy, size, rotation, color, alpha)

        # Small edge highlight on dimensional geometric primitives.
        if settings["edge_light"] > 0 and shape in {"block", "tri", "circle"}:
            hi = tuple(min(255, int(c + (255 - c) * settings["edge_light"])) for c in color)
            ha = max(12, int(alpha * 0.28))
            r = size * 0.5
            draw.ellipse((cx - r * 0.52, cy - r * 0.76, cx - r * 0.22, cy - r * 0.46), fill=(*hi, ha))
            svg.append(
                f'<ellipse cx="{cx-r*0.37:.1f}" cy="{cy-r*0.61:.1f}" rx="{r*0.15:.1f}" ry="{r*0.15:.1f}" '
                f'fill="rgb({hi[0]},{hi[1]},{hi[2]})" fill-opacity="{ha/255:.3f}"/>'
            )

    # ------------------------------------------------------------------
    # Organic silhouettes + smooth stochastic linework
    # ------------------------------------------------------------------

    def _draw_organic_extension(self, result, config):
        settings = self.organic_settings
        rng = random.Random(f"{result.seed}:organic")
        noise = self._make_noise(result.seed, config)
        palette = self._palette(rng, config)
        draw = ImageDraw.Draw(result.image, "RGBA")
        cell = min(config.width, config.height) / max(4, config.grid_size)
        cols = max(1, math.ceil(config.width / cell)); rows = max(1, math.ceil(config.height / cell))
        count = max(1, min(600, int(config.grid_size ** 2 * config.density * 0.20 * max(0.25, settings["weight"]))))
        svg_parts: list[str] = []

        for _ in range(count):
            gx = rng.randrange(cols); gy = rng.randrange(rows)
            cx = (gx + 0.5) * cell; cy = (gy + 0.5) * cell
            if config.field_mode != "none":
                n = self._noise_value(cx, cy, noise, config)
                angle = self._field_angle(cx, cy, config, noise)
                drift = config.field_strength * config.jitter * cell * n
                cx += math.cos(angle) * drift; cy += math.sin(angle) * drift
            if rng.random() > 0.45 + 0.55 * config.complexity:
                continue

            size = cell * config.shape_scale * rng.uniform(0.50, 0.98) * (1.0 - 0.15 * config.spacing)
            rotation = math.radians(config.rotation) + rng.uniform(-config.rotation_jitter, config.rotation_jitter)
            color = self._choose_color(rng, palette, config, cx, cy)
            alpha = int(255 * rng.uniform(config.opacity_min, config.opacity_max) * 0.84)

            for ix, iy, irot in self._symmetry_instances(cx, cy, rotation, config):
                points = self._points(ix, iy, size, settings, rng, irot)
                draw.polygon(points, fill=(*color, alpha))
                svg_parts.append(
                    f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" '
                    f'fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{alpha/255:.3f}"/>'
                )

                if settings["line_mode"] != "none":
                    for vein_index in range(max(1, int(settings["vein_count"]))):
                        if settings["line_mode"] == "veins" and vein_index % 2:
                            continue
                        vein = self._organic_curve(ix, iy, size, settings, rng, irot, vein_index)
                        va = max(24, int(alpha * 0.46))
                        vw = max(1, int(settings["strand_width"] * max(0.7, size / 90)))
                        draw.line(vein, fill=(*color, va), width=vw, joint="curve")
                        svg_parts.append(
                            f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in vein)}" fill="none" '
                            f'stroke="rgb({color[0]},{color[1]},{color[2]})" stroke-opacity="{va/255:.3f}" '
                            f'stroke-width="{vw}" stroke-linecap="round" stroke-linejoin="round"/>'
                        )

        # Long field-guided strands form an independent organic nervous-system layer.
        for _ in range(max(0, int(settings["strand_count"]))):
            x = rng.uniform(0, config.width); y = rng.uniform(0, config.height)
            points = [(x, y)]
            steps = max(6, int(settings["strand_length"]))
            for step in range(steps):
                angle = self._field_angle(x, y, config, noise) if config.field_mode != "none" else math.sin(step * 0.31) * math.pi
                angle += rng.uniform(-1.0, 1.0) * settings["strand_wander"] * 0.22
                stride = max(2.0, min(config.width, config.height) / 90)
                x += math.cos(angle) * stride
                y += math.sin(angle) * stride
                if not (-stride <= x <= config.width + stride and -stride <= y <= config.height + stride):
                    break
                points.append((x, y))
            if len(points) < 4:
                continue
            color = self._choose_color(rng, palette, config, points[0][0], points[0][1])
            a = max(18, int(255 * rng.uniform(config.opacity_min, config.opacity_max) * 0.33))
            w = max(1, int(settings["strand_width"] * max(0.75, min(config.width, config.height) / 850)))
            draw.line(points, fill=(*color, a), width=w, joint="curve")
            svg_parts.append(
                f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in points)}" fill="none" '
                f'stroke="rgb({color[0]},{color[1]},{color[2]})" stroke-opacity="{a/255:.3f}" '
                f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
            )

        if svg_parts:
            result.svg = result.svg.rsplit("</svg>", 1)[0] + "\n" + "\n".join(svg_parts) + "\n</svg>"

    @staticmethod
    def _points(cx, cy, size, settings, rng, rotation):
        style = settings["style"]
        lobes = max(3, int(settings["lobes"]))
        wobble = max(0.0, min(1.0, float(settings["wobble"])))
        taper = max(0.0, min(1.0, float(settings["taper"])))
        count = max(20, lobes * 5)
        phase = rng.uniform(0, math.tau)
        stretch = 1.55 if style == "leaf" else 1.18 if style == "droplet" else 1.0
        pts = []
        for i in range(count):
            a = math.tau * i / count
            r = 0.82 + wobble * (0.13 * math.sin(lobes * a + phase) + 0.07 * math.sin((lobes + 2) * a - phase * 0.7))
            if style == "amoeba":
                r *= 1 + 0.18 * math.sin(3 * a + phase * 0.5)
            elif style == "blob":
                r *= 0.94 + 0.08 * math.sin(2 * a + phase)
            elif style == "petal":
                r *= 0.76 + 0.28 * (0.5 + 0.5 * math.cos(lobes * a))
            elif style == "cell":
                r *= 0.95 + 0.05 * math.sin(lobes * a + phase)
            elif style == "droplet":
                r *= (1 - 0.20 * math.sin(a)) * (1 + 0.20 * taper * math.cos(a))
            elif style == "leaf":
                r *= 0.92 - 0.28 * taper * abs(math.sin(a))
            elif style == "shell":
                r *= 0.72 + 0.22 * (i / max(1, count - 1)) + 0.12 * math.sin(3 * a + phase)
            elif style == "seed":
                r *= 0.78 + 0.32 * (0.5 + 0.5 * math.cos(a))
            x = math.cos(a) * size * 0.5 * r * stretch
            y = math.sin(a) * size * 0.5 * r
            if style == "leaf":
                x *= 1 - 0.20 * abs(math.sin(a))
            ca, sa = math.cos(rotation), math.sin(rotation)
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        return pts

    @staticmethod
    def _organic_curve(cx, cy, size, settings, rng, rotation, index):
        wobble = float(settings["vein_wobble"])
        angle = rotation + (index - max(0, settings["vein_count"] - 1) / 2) * 0.42 + rng.uniform(-0.14, 0.14)
        length = size * rng.uniform(0.30, 0.66)
        start = rng.uniform(-0.15, 0.15) * size
        local = []
        samples = 18
        for i in range(samples):
            t = i / max(1, samples - 1)
            along = (t - 0.5) * length
            bend = math.sin(t * math.pi) * math.sin(index * 1.7 + t * math.tau) * wobble * size * 0.07
            lateral = (start * (1 - t) * 0.35) + bend
            local.append((lateral, along))
        ca, sa = math.cos(angle), math.sin(angle)
        return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in local]

    # ------------------------------------------------------------------
    # Unicode-friendly text compositor
    # ------------------------------------------------------------------

    def _draw_text_extension(self, result, config):
        settings = self.text_settings
        text = settings["text"].replace("\r\n", "\n")
        if not text.strip():
            return

        qimage = QImage(config.width, config.height, QImage.Format_ARGB32_Premultiplied)
        qimage.fill(Qt.transparent)
        painter = QPainter(qimage)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        font = QFont(settings["font_family"], int(settings["font_size"]))
        font.setKerning(True)
        try:
            font.setLetterSpacing(QFont.AbsoluteSpacing, float(settings["tracking"]))
        except Exception:
            pass
        painter.setFont(font)

        palette_rng = random.Random(f"{result.seed}:text-color")
        palette = self._palette(palette_rng, config)
        base_alpha = max(1, min(255, int(255 * settings["opacity"])))
        metrics = painter.fontMetrics()
        line_height = metrics.height() * float(settings["line_spacing"])
        chars = [c for c in text if c != "\n"]
        svg_parts: list[str] = []

        def paint_char(char: str, x: float, y: float, rotation: float, index: int):
            color = self._choose_color(palette_rng, palette, config, x, y)
            qcolor = QColor(*color, base_alpha)
            painter.save()
            painter.translate(x, y)
            painter.rotate(rotation)
            painter.setPen(QPen(qcolor))
            painter.drawText(QPointF(-metrics.horizontalAdvance(char) / 2, metrics.ascent() * -0.02), char)
            painter.restore()
            svg_parts.append(
                f'<text x="{x:.1f}" y="{y:.1f}" transform="rotate({rotation:.2f} {x:.1f} {y:.1f})" '
                f'font-family="{html.escape(settings["font_family"])}" font-size="{int(settings["font_size"])}" '
                f'fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{base_alpha/255:.3f}" '
                f'text-anchor="middle" dominant-baseline="middle" xml:space="preserve">{html.escape(char)}</text>'
            )

        mode = settings["mode"]
        if mode == "grid":
            cols = max(1, int(config.width / max(20, settings["font_size"] * 1.35)))
            col = row = 0
            for char in text:
                if char == "\n" or col >= cols:
                    row += 1; col = 0
                    if char == "\n":
                        continue
                x = settings["font_size"] * 0.75 + col * settings["font_size"] * 1.15
                y = settings["font_size"] * 1.05 + row * line_height
                if y < config.height:
                    paint_char(char, x, y, settings["rotation"], col + row * cols)
                col += 1
        elif mode == "arc":
            radius = min(config.width, config.height) * settings["radius"]
            center_x, center_y = config.width * 0.5, config.height * 0.57
            step = max(0.012, (settings["font_size"] + settings["tracking"]) / max(1, radius))
            start = -step * (len(chars) - 1) * 0.5
            for i, char in enumerate(chars):
                a = start + i * step
                x = center_x + math.cos(a) * radius
                y = center_y + math.sin(a) * radius
                paint_char(char, x, y, math.degrees(a) + 90 + settings["rotation"], i)
        elif mode == "spiral":
            cx, cy = config.width * 0.5, config.height * 0.5
            angle_step = max(0.13, (settings["font_size"] + settings["tracking"]) / 90)
            for i, char in enumerate(chars):
                a = i * angle_step
                r = min(config.width, config.height) * (0.05 + 0.0036 * i)
                x = cx + math.cos(a) * r
                y = cy + math.sin(a) * r
                paint_char(char, x, y, math.degrees(a) + 90 + settings["rotation"], i)
        elif mode == "scatter":
            for i, char in enumerate(chars):
                x = palette_rng.uniform(0.06, 0.94) * config.width
                y = palette_rng.uniform(0.08, 0.92) * config.height
                paint_char(char, x, y, palette_rng.uniform(-24, 24) + settings["rotation"], i)
        elif mode == "wave":
            x = settings["font_size"]
            baseline = config.height * 0.5
            i = 0
            for char in chars:
                if x >= config.width - settings["font_size"]:
                    x = settings["font_size"]
                    baseline += line_height * 1.4
                y = baseline + math.sin(i * 0.34) * config.height * settings["wave"]
                paint_char(char, x, y, math.cos(i * 0.34) * 12 + settings["rotation"], i)
                x += metrics.horizontalAdvance(char) + settings["tracking"]
                i += 1
        else:  # flow
            x, y = config.width * 0.12, config.height * 0.28
            for i, char in enumerate(chars):
                angle = self._field_angle(x, y, config, self._make_noise(result.seed, config))
                paint_char(char, x, y, math.degrees(angle) + settings["rotation"], i)
                step = metrics.horizontalAdvance(char) + settings["tracking"]
                x += math.cos(angle) * step
                y += math.sin(angle) * step
                if not (20 < x < config.width - 20 and 20 < y < config.height - 20):
                    x = config.width * 0.12 + (i % 5) * metrics.height() * 1.2
                    y = config.height * (0.25 + ((i // 5) % 5) * 0.12)

        painter.end()
        raw = qimage.bits().tobytes()
        text_image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), raw, "raw", "BGRA")
        result.image = Image.alpha_composite(result.image.convert("RGBA"), text_image)
        if svg_parts:
            result.svg = result.svg.rsplit("</svg>", 1)[0] + "\n" + "\n".join(svg_parts) + "\n</svg>"


class MainWindow(BaseMainWindow):
    """Stable dark UI with additive organic, perspective, text, and palette controls."""

    def __init__(self):
        app = __import__("PySide6.QtWidgets", fromlist=["QApplication"]).QApplication.instance()
        if app is not None:
            app.setFont(QFont(_system_font_family(), 9))
        super().__init__()
        self.renderer = EnhancedPatternRenderer()
        self.generate()

    def _build_ui(self):
        super()._build_ui()
        tabs = self.findChild(QTabWidget)
        if tabs is not None:
            organic_index = tabs.addTab(self._organic_tab(), "Organic")
            self._add_perspective_controls(tabs)
            tabs.addTab(self._text_tab(), "Text")
            export_index = tabs.indexOf(next((tabs.widget(i) for i in range(tabs.count()) if tabs.tabText(i) == "Export"), None))
            if export_index >= 0 and export_index != tabs.count() - 1:
                widget = tabs.widget(export_index)
                title = tabs.tabText(export_index)
                tabs.removeTab(export_index)
                tabs.addTab(widget, title)

        self._extend_palette_selector()
        self._add_palette_lock()
        self._wire_extensions()

    def _organic_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box = QGroupBox("Organic forms"); form = QFormLayout(box)
        self.use_organic = QCheckBox("Enable organic forms"); self.use_organic.setChecked(False)
        self.organic_style = QComboBox(); self.organic_style.addItems(["amoeba", "blob", "petal", "cell", "droplet", "leaf", "shell", "seed"])
        self.organic_weight = QDoubleSpinBox(); self.organic_weight.setRange(0, 4); self.organic_weight.setValue(0.8); self.organic_weight.setSingleStep(0.1)
        self.organic_lobes = QSpinBox(); self.organic_lobes.setRange(3, 18); self.organic_lobes.setValue(7)
        self.organic_wobble = QDoubleSpinBox(); self.organic_wobble.setRange(0, 1); self.organic_wobble.setValue(0.55); self.organic_wobble.setSingleStep(0.05)
        self.organic_taper = QDoubleSpinBox(); self.organic_taper.setRange(0, 1); self.organic_taper.setValue(0.25); self.organic_taper.setSingleStep(0.05)
        self.organic_line_mode = QComboBox(); self.organic_line_mode.addItems(["none", "veins", "tendrils", "mixed"])
        self.organic_vein_count = QSpinBox(); self.organic_vein_count.setRange(1, 9); self.organic_vein_count.setValue(3)
        self.organic_vein_wobble = QDoubleSpinBox(); self.organic_vein_wobble.setRange(0, 1); self.organic_vein_wobble.setValue(0.55); self.organic_vein_wobble.setSingleStep(0.05)
        self.organic_strand_count = QSpinBox(); self.organic_strand_count.setRange(0, 80); self.organic_strand_count.setValue(8)
        self.organic_strand_length = QSpinBox(); self.organic_strand_length.setRange(6, 140); self.organic_strand_length.setValue(26)
        self.organic_strand_wander = QDoubleSpinBox(); self.organic_strand_wander.setRange(0, 1); self.organic_strand_wander.setValue(0.45); self.organic_strand_wander.setSingleStep(0.05)
        self.organic_strand_width = QDoubleSpinBox(); self.organic_strand_width.setRange(0.4, 6); self.organic_strand_width.setValue(1.5); self.organic_strand_width.setSingleStep(0.2)
        for label, widget in [
            ("Enable", self.use_organic), ("Style", self.organic_style), ("Weight", self.organic_weight),
            ("Lobes", self.organic_lobes), ("Wobble", self.organic_wobble), ("Taper", self.organic_taper),
            ("Linework", self.organic_line_mode), ("Vein count", self.organic_vein_count), ("Vein wobble", self.organic_vein_wobble),
            ("Long strands", self.organic_strand_count), ("Strand length", self.organic_strand_length),
            ("Strand wander", self.organic_strand_wander), ("Strand width", self.organic_strand_width),
        ]: form.addRow(label, widget)
        layout.addWidget(box)
        hint = QLabel("Organic linework uses smooth stochastic curves and field-guided strands. It stays deterministic with the main seed.")
        hint.setWordWrap(True); layout.addWidget(hint); layout.addStretch(1)
        return page

    def _add_perspective_controls(self, tabs):
        geometry = next((tabs.widget(i) for i in range(tabs.count()) if tabs.tabText(i) == "Geometry"), None)
        if geometry is None:
            return
        box = QGroupBox("Perspective & depth"); form = QFormLayout(box)
        self.perspective_enabled = QCheckBox("Enable dimensional depth"); self.perspective_enabled.setChecked(True)
        self.perspective_strength = QDoubleSpinBox(); self.perspective_strength.setRange(0, 0.9); self.perspective_strength.setValue(0.18); self.perspective_strength.setSingleStep(0.02)
        self.vanishing_x = QDoubleSpinBox(); self.vanishing_x.setRange(0, 1); self.vanishing_x.setValue(0.50); self.vanishing_x.setSingleStep(0.02)
        self.vanishing_y = QDoubleSpinBox(); self.vanishing_y.setRange(0, 1); self.vanishing_y.setValue(0.42); self.vanishing_y.setSingleStep(0.02)
        self.edge_light = QDoubleSpinBox(); self.edge_light.setRange(0, 1); self.edge_light.setValue(0.28); self.edge_light.setSingleStep(0.02)
        for label, widget in [("Enable", self.perspective_enabled), ("Depth", self.perspective_strength), ("Vanishing X", self.vanishing_x), ("Vanishing Y", self.vanishing_y), ("Edge light", self.edge_light)]:
            form.addRow(label, widget)
        layout = geometry.layout()
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(max(0, layout.count() - 1), box)

    def _text_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box = QGroupBox("Text / Unicode overlay"); form = QFormLayout(box)
        self.use_text = QCheckBox("Enable text")
        self.text_input = QPlainTextEdit(); self.text_input.setPlaceholderText("Enter a word, sentence, multiline text, hiragana, katakana, kanji, symbols…")
        self.text_input.setMinimumHeight(120)
        self.text_mode = QComboBox(); self.text_mode.addItems(["flow", "wave", "arc", "spiral", "grid", "scatter"])
        self.text_font = QComboBox(); self.text_font.addItems([_system_font_family(), "Sans Serif"])
        self.text_font.setCurrentText(_system_font_family())
        self.text_font_size = QSpinBox(); self.text_font_size.setRange(10, 420); self.text_font_size.setValue(72)
        self.text_opacity = QDoubleSpinBox(); self.text_opacity.setRange(0.05, 1); self.text_opacity.setValue(0.82); self.text_opacity.setSingleStep(0.05)
        self.text_tracking = QDoubleSpinBox(); self.text_tracking.setRange(-20, 40); self.text_tracking.setValue(2); self.text_tracking.setSingleStep(0.5)
        self.text_line_spacing = QDoubleSpinBox(); self.text_line_spacing.setRange(0.7, 2.4); self.text_line_spacing.setValue(1.18); self.text_line_spacing.setSingleStep(0.05)
        self.text_radius = QDoubleSpinBox(); self.text_radius.setRange(0.08, 0.8); self.text_radius.setValue(0.33); self.text_radius.setSingleStep(0.02)
        self.text_wave = QDoubleSpinBox(); self.text_wave.setRange(0, 0.35); self.text_wave.setValue(0.12); self.text_wave.setSingleStep(0.02)
        self.text_rotation = QDoubleSpinBox(); self.text_rotation.setRange(-180, 180); self.text_rotation.setValue(0); self.text_rotation.setSingleStep(5)
        form.addRow("Enable", self.use_text); form.addRow("Text", self.text_input); form.addRow("Arrangement", self.text_mode); form.addRow("Font", self.text_font)
        form.addRow("Size", self.text_font_size); form.addRow("Opacity", self.text_opacity); form.addRow("Tracking", self.text_tracking); form.addRow("Line spacing", self.text_line_spacing)
        form.addRow("Arc / spiral radius", self.text_radius); form.addRow("Wave amount", self.text_wave); form.addRow("Rotation", self.text_rotation)
        layout.addWidget(box)
        layout.addWidget(QLabel("Text is drawn with Qt so Japanese and other Unicode scripts can use the operating system's fallback fonts automatically. Bahnschrift is preferred for Latin text when installed."))
        layout.addStretch(1)
        return page

    def _extend_palette_selector(self):
        combo = self.palette_mode; combo.blockSignals(True); combo.clear()
        combo.addItem("random", "random"); combo.addItem("pastel", "pastel"); combo.insertSeparator(combo.count())
        for key, palette in BUILTIN_PALETTES.items(): combo.addItem(palette.name, key)
        combo.addItem("LGBTQ+ / all unique colors", "lgbtq-all"); combo.insertSeparator(combo.count())
        for key, palette in PRIDE_PALETTES.items(): combo.addItem(palette.name, key)
        combo.setCurrentIndex(0); combo.blockSignals(False)

    def _add_palette_lock(self):
        self.preserve_palette = QCheckBox("Preserve exact Pride palette colors"); self.preserve_palette.setChecked(True)
        for box in self.findChildren(QGroupBox):
            if box.title() == "Color behavior" and isinstance(box.layout(), QFormLayout):
                box.layout().addRow("", self.preserve_palette); return

    def _wire_extensions(self):
        controls = [
            self.use_organic, self.organic_style, self.organic_weight, self.organic_lobes, self.organic_wobble,
            self.organic_taper, self.organic_line_mode, self.organic_vein_count, self.organic_vein_wobble,
            self.organic_strand_count, self.organic_strand_length, self.organic_strand_wander, self.organic_strand_width,
            self.preserve_palette, self.perspective_enabled, self.perspective_strength, self.vanishing_x,
            self.vanishing_y, self.edge_light, self.use_text, self.text_input, self.text_mode, self.text_font,
            self.text_font_size, self.text_opacity, self.text_tracking, self.text_line_spacing, self.text_radius,
            self.text_wave, self.text_rotation,
        ]
        for control in controls:
            if isinstance(control, QComboBox): control.currentTextChanged.connect(self._request)
            elif isinstance(control, QCheckBox): control.toggled.connect(self._request)
            elif isinstance(control, QPlainTextEdit): control.textChanged.connect(self._request)
            else: control.valueChanged.connect(self._request)

    def _config(self):
        cfg = super()._config(); values = cfg.to_dict()
        key = self.palette_mode.currentData() or self.palette_mode.currentText()
        values["palette_mode"] = key if key in generator_module.PALETTES else "random"
        if self.preserve_palette.isChecked() and values["palette_mode"] not in {"random", "pastel"}:
            values.update(hue_jitter=0.0, saturation=1.0, contrast=0.0)
        self.renderer.organic_settings = {
            "enabled": self.use_organic.isChecked(), "style": self.organic_style.currentText(), "weight": self.organic_weight.value(),
            "lobes": self.organic_lobes.value(), "wobble": self.organic_wobble.value(), "taper": self.organic_taper.value(),
            "line_mode": self.organic_line_mode.currentText(), "veins": self.organic_line_mode.currentText() != "none",
            "vein_count": self.organic_vein_count.value(), "vein_wobble": self.organic_vein_wobble.value(),
            "strand_count": self.organic_strand_count.value(), "strand_length": self.organic_strand_length.value(),
            "strand_wander": self.organic_strand_wander.value(), "strand_width": self.organic_strand_width.value(),
        }
        self.renderer.perspective_settings = {
            "enabled": self.perspective_enabled.isChecked(), "strength": self.perspective_strength.value(),
            "vanishing_x": self.vanishing_x.value(), "vanishing_y": self.vanishing_y.value(), "edge_light": self.edge_light.value(),
        }
        self.renderer.text_settings = {
            "enabled": self.use_text.isChecked(), "text": self.text_input.toPlainText(), "mode": self.text_mode.currentText(),
            "font_family": self.text_font.currentText(), "font_size": self.text_font_size.value(), "opacity": self.text_opacity.value(),
            "tracking": self.text_tracking.value(), "line_spacing": self.text_line_spacing.value(), "radius": self.text_radius.value(),
            "wave": self.text_wave.value(), "rotation": self.text_rotation.value(),
        }
        return PatternConfig(**values)

    def save_preset(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save preset", "pattern-preset.json", "JSON (*.json)")
        if not path:
            return
        data = self._config().to_dict()
        data["_eli_lab_extensions"] = {
            "organic": self.renderer.organic_settings,
            "perspective": self.renderer.perspective_settings,
            "text": self.renderer.text_settings,
            "preserve_palette": self.preserve_palette.isChecked(),
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_preset(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load preset", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            ext = data.pop("_eli_lab_extensions", {})
            cfg = PatternConfig(**data).normalized()
            self._loading_preset = True
            self.width.setValue(cfg.width); self.height.setValue(cfg.height); self.seed.setText(cfg.seed); self.background.setText(cfg.background)
            self.aspect.setCurrentText("custom"); self.symmetry.setCurrentText(cfg.symmetry)
            idx = self.palette_mode.findData(cfg.palette_mode); self.palette_mode.setCurrentIndex(max(0, idx))
            self.composition_mode.setCurrentText(cfg.composition_mode); self.focal_x.setValue(cfg.focal_x); self.focal_y.setValue(cfg.focal_y); self.focal_strength.setValue(cfg.focal_strength)
            self.edge_bias.setValue(cfg.edge_bias); self.cluster_count.setValue(cfg.cluster_count); self.cluster_strength.setValue(cfg.cluster_strength); self.spacing.setValue(cfg.spacing); self.jitter.setValue(cfg.jitter)
            self.field_mode.setCurrentText(cfg.field_mode); self.field_strength.setValue(cfg.field_strength); self.field_scale.setValue(cfg.field_scale); self.field_curvature.setValue(cfg.field_curvature); self.field_steps.setValue(cfg.field_steps); self.field_step_size.setValue(cfg.field_step_size); self.noise_octaves.setValue(cfg.noise_octaves)
            self.grid_size.setValue(cfg.grid_size); self.shape_scale.setValue(cfg.shape_scale); self.scale_variance.setValue(cfg.scale_variance); self.rotation.setValue(cfg.rotation); self.rotation_jitter.setValue(cfg.rotation_jitter); self.corner_roundness.setValue(cfg.corner_roundness); self.line_complexity.setValue(cfg.line_complexity); self.overlap.setValue(cfg.overlap)
            self.use_blocks.setChecked(cfg.use_blocks); self.use_circles.setChecked(cfg.use_circles); self.use_lines.setChecked(cfg.use_lines); self.use_triangles.setChecked(cfg.use_triangles); self.block_weight.setValue(cfg.block_weight); self.circle_weight.setValue(cfg.circle_weight); self.line_weight.setValue(cfg.line_weight); self.triangle_weight.setValue(cfg.triangle_weight)
            self.palette_size.setValue(cfg.palette_size); self.saturation.setValue(cfg.saturation); self.contrast.setValue(cfg.contrast); self.hue_jitter.setValue(cfg.hue_jitter); self.opacity_min.setValue(cfg.opacity_min); self.opacity_max.setValue(cfg.opacity_max); self.color_coherence.setValue(cfg.color_coherence)
            self.layer_count.setValue(cfg.layer_count); self.depth.setValue(cfg.depth); self.accent_density.setValue(cfg.accent_density); self.gradient.setChecked(cfg.gradient); self.blur.setValue(cfg.blur); self.behavior.setCurrentText(cfg.behavior); self.mutation.setValue(cfg.mutation); self.asymmetry.setValue(cfg.asymmetry)
            organic = ext.get("organic", {})
            if organic:
                self.use_organic.setChecked(bool(organic.get("enabled", False))); self.organic_style.setCurrentText(organic.get("style", "amoeba")); self.organic_weight.setValue(float(organic.get("weight", 0.8))); self.organic_lobes.setValue(int(organic.get("lobes", 7))); self.organic_wobble.setValue(float(organic.get("wobble", 0.55))); self.organic_taper.setValue(float(organic.get("taper", 0.25))); self.organic_line_mode.setCurrentText(organic.get("line_mode", "mixed")); self.organic_vein_count.setValue(int(organic.get("vein_count", 3))); self.organic_vein_wobble.setValue(float(organic.get("vein_wobble", 0.55))); self.organic_strand_count.setValue(int(organic.get("strand_count", 8))); self.organic_strand_length.setValue(int(organic.get("strand_length", 26))); self.organic_strand_wander.setValue(float(organic.get("strand_wander", 0.45))); self.organic_strand_width.setValue(float(organic.get("strand_width", 1.5)))
            perspective = ext.get("perspective", {})
            if perspective:
                self.perspective_enabled.setChecked(bool(perspective.get("enabled", True))); self.perspective_strength.setValue(float(perspective.get("strength", 0.18))); self.vanishing_x.setValue(float(perspective.get("vanishing_x", 0.5))); self.vanishing_y.setValue(float(perspective.get("vanishing_y", 0.42))); self.edge_light.setValue(float(perspective.get("edge_light", 0.28)))
            text = ext.get("text", {})
            if text:
                self.use_text.setChecked(bool(text.get("enabled", False))); self.text_input.setPlainText(text.get("text", "")); self.text_mode.setCurrentText(text.get("mode", "flow")); self.text_font.setCurrentText(text.get("font_family", _system_font_family())); self.text_font_size.setValue(int(text.get("font_size", 72))); self.text_opacity.setValue(float(text.get("opacity", 0.82))); self.text_tracking.setValue(float(text.get("tracking", 2.0))); self.text_line_spacing.setValue(float(text.get("line_spacing", 1.18))); self.text_radius.setValue(float(text.get("radius", 0.33))); self.text_wave.setValue(float(text.get("wave", 0.12))); self.text_rotation.setValue(float(text.get("rotation", 0)))
            if "preserve_palette" in ext:
                self.preserve_palette.setChecked(bool(ext["preserve_palette"]))
        except Exception as exc:
            QMessageBox.critical(self, "Load preset", f"Could not load preset:\n{exc}")
        finally:
            self._loading_preset = False
        self.generate()


__all__ = ["MainWindow", "EnhancedPatternRenderer"]
