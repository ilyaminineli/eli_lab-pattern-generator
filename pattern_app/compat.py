from __future__ import annotations

import math

from . import extensions
from .generator import PatternRenderer as BaseRenderer, _rotate


def _compatible_shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha):
    """Compatibility layer for the base renderer's RNG-aware _shape hook.

    The stable PatternRenderer calls _shape with ``rng``.  The extension
    override predates that signature, so normalize the call here while keeping
    the original generator implementation untouched.
    """
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


# Override only the broken extension hook. No changes to generator.py/ui.py.
extensions.EnhancedPatternRenderer._shape = _compatible_shape

MainWindow = extensions.MainWindow
EnhancedPatternRenderer = extensions.EnhancedPatternRenderer

__all__ = ["MainWindow", "EnhancedPatternRenderer"]
