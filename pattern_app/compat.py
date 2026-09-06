from __future__ import annotations

import math

from PySide6.QtGui import QFontDatabase

from . import extensions
from .generator import PatternRenderer as BaseRenderer, _rotate


def _compatible_shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha):
    """Compatibility layer for the base renderer's RNG-aware _shape hook."""
    settings = getattr(self, "perspective_settings", {})
    if not settings.get("enabled", False) or settings.get("strength", 0) <= 0:
        return BaseRenderer._shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha)

    vx = cfg.width * float(settings.get("vanishing_x", 0.5))
    vy = cfg.height * float(settings.get("vanishing_y", 0.42))
    dx = cx - vx
    dy = cy - vy
    distance = max(1.0, math.hypot(dx, dy))
    strength = float(settings.get("strength", 0.18))
    depth = size * strength * (0.65 + 0.35 * min(1.0, distance / max(cfg.width, cfg.height)))
    ox = dx / distance * depth
    oy = dy / distance * depth
    shadow = tuple(max(0, int(c * 0.42)) for c in color)
    shadow_alpha = max(24, int(alpha * 0.42))

    if shape in {"block", "tri"}:
        half = size * 0.5
        if shape == "tri":
            front = _rotate(
                [(cx, cy - half), (cx - half, cy + half), (cx + half, cy + half)],
                rotation, cx, cy,
            )
        else:
            front = _rotate(
                [(cx - half, cy - half), (cx + half, cy - half),
                 (cx + half, cy + half), (cx - half, cy + half)],
                rotation, cx, cy,
            )
        back = [(x + ox, y + oy) for x, y in front]
        face_alpha = max(18, int(alpha * 0.30))
        for i in range(len(front)):
            a, b = front[i], front[(i + 1) % len(front)]
            bi, bj = back[i], back[(i + 1) % len(back)]
            draw.polygon([a, b, bj, bi], fill=(*shadow, face_alpha))
            svg.append(
                f'<polygon points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} '
                f'{bj[0]:.1f},{bj[1]:.1f} {bi[0]:.1f},{bi[1]:.1f}" '
                f'fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{face_alpha/255:.3f}"/>'
            )
        draw.polygon(back, fill=(*shadow, shadow_alpha))
        svg.append(
            f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in back)}" '
            f'fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{shadow_alpha/255:.3f}"/>'
        )
    elif shape == "circle":
        r = size * 0.5
        draw.ellipse(
            (cx - r + ox, cy - r + oy, cx + r + ox, cy + r + oy),
            fill=(*shadow, shadow_alpha),
        )
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
            front.append(
                (cx - half + t * size,
                 cy + math.sin(t * math.pi * 2 + rotation) * size * 0.25)
            )
        front = _rotate(front, rotation, cx, cy)
        back = [(x + ox, y + oy) for x, y in front]
        width = max(1, int((1 + cfg.depth * 5) * size / 120))
        draw.line(back, fill=(*shadow, shadow_alpha), width=width, joint="curve")
        svg.append(
            f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in back)}" fill="none" '
            f'stroke="rgb({shadow[0]},{shadow[1]},{shadow[2]})" stroke-opacity="{shadow_alpha/255:.3f}" '
            f'stroke-width="{width}" stroke-linecap="round"/>'
        )

    # Draw the canonical foreground primitive through the unchanged renderer.
    BaseRenderer._shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha)

    edge_light = float(settings.get("edge_light", 0.28))
    if edge_light > 0 and shape in {"block", "tri", "circle"}:
        hi = tuple(min(255, int(c + (255 - c) * edge_light)) for c in color)
        ha = max(12, int(alpha * 0.20))
        r = size * 0.5
        draw.ellipse(
            (cx - r * 0.48, cy - r * 0.76, cx - r * 0.20, cy - r * 0.48),
            fill=(*hi, ha),
        )
        svg.append(
            f'<ellipse cx="{cx-r*0.34:.1f}" cy="{cy-r*0.62:.1f}" '
            f'rx="{r*0.14:.1f}" ry="{r*0.14:.1f}" '
            f'fill="rgb({hi[0]},{hi[1]},{hi[2]})" fill-opacity="{ha/255:.3f}"/>'
        )


# Keep the core renderer untouched; only normalize the extension hook.
extensions.EnhancedPatternRenderer._shape = _compatible_shape


def _font_families() -> list[str]:
    """Build a useful, deterministic system-font list for Latin + Japanese text."""
    try:
        db = QFontDatabase()
        all_families = set(db.families())
        try:
            japanese = set(db.families(QFontDatabase.WritingSystem.Japanese))
        except Exception:
            japanese = set()
    except Exception:
        all_families = set()
        japanese = set()

    preferred = [
        # Japanese / CJK serif
        "Yu Mincho", "YuMincho", "MS Mincho", "MS PMincho", "BIZ UDPMincho", "BIZ UDMincho",
        "Noto Serif CJK JP", "Noto Serif JP", "Source Han Serif", "Source Han Serif JP",
        "Hiragino Mincho ProN", "Hiragino Mincho Pro", "IPAexMincho", "IPAMincho",
        # Japanese / CJK sans
        "Yu Gothic", "YuGothic", "Meiryo", "Meiryo UI", "MS Gothic", "MS PGothic",
        "BIZ UDPGothic", "BIZ UD Gothic", "Noto Sans CJK JP", "Noto Sans JP", "Source Han Sans",
        "Source Han Sans JP", "Hiragino Kaku Gothic ProN", "IPAexGothic", "IPAGothic",
        # Latin / display / technical
        "Bahnschrift", "Bahnschrift SemiBold", "Segoe UI", "Segoe UI Variable", "Segoe UI Light",
        "Aptos", "Aptos Display", "Arial", "Arial Narrow", "Helvetica Neue", "Futura",
        "Gill Sans", "Garamond", "Book Antiqua", "Century Gothic", "Impact", "Trebuchet MS",
        "Consolas", "Cascadia Code", "Cascadia Mono", "JetBrains Mono", "IBM Plex Sans",
        "IBM Plex Serif", "Inter", "Montserrat", "Roboto", "Roboto Condensed",
    ]

    ordered: list[str] = []
    seen: set[str] = set()

    # Put known Japanese-capable families first, preserving useful distinctions.
    for family in preferred:
        if family in all_families and family not in seen:
            ordered.append(family)
            seen.add(family)

    for family in sorted(japanese, key=str.casefold):
        if family not in seen:
            ordered.append(family)
            seen.add(family)

    # Add interesting installed families even if they are not Japanese-capable.
    keywords = (
        "display", "condensed", "mono", "serif", "gothic", "mincho", "script", "slab",
        "hand", "sans", "headline", "black", "light", "variable", "retro", "pixel",
    )
    for family in sorted(all_families, key=str.casefold):
        low = family.casefold()
        if family not in seen and any(word in low for word in keywords):
            ordered.append(family)
            seen.add(family)

    return ordered


class MainWindow(extensions.MainWindow):
    """Final compatibility wrapper: stable rendering + richer system fonts."""

    def _connect_auto_preview(self):
        # Keep all of the original auto-preview controls, but choosing a palette
        # merely changes the pending configuration. It must not trigger a render.
        super()._connect_auto_preview()
        try:
            self.palette_mode.currentTextChanged.disconnect(self._request)
        except (TypeError, RuntimeError):
            pass

    def __init__(self):
        super().__init__()
        self._populate_text_fonts()

    def _populate_text_fonts(self):
        combo = getattr(self, "text_font", None)
        if combo is None:
            return
        current = combo.currentText()
        families = _font_families()
        if not families:
            families = [current or "Sans Serif"]
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(families)
        if current in families:
            combo.setCurrentText(current)
        elif "Bahnschrift" in families:
            combo.setCurrentText("Bahnschrift")
        else:
            combo.setCurrentIndex(0)
        combo.setEditable(True)
        combo.setInsertPolicy(combo.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(18)
        combo.blockSignals(False)


EnhancedPatternRenderer = extensions.EnhancedPatternRenderer

__all__ = ["MainWindow", "EnhancedPatternRenderer"]
