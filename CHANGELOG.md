# Changelog

All notable changes to **eli_lab Pattern Generator** are documented here.

## [Unreleased]

### Planned

- Windows installer package.
- Application icon and file associations.
- macOS and Linux release artifacts.
- Preset library and batch rendering.

## [2.3.0] - 2026-09-06

### Added

- Expanded organic forms with shell and seed silhouettes.
- Smooth stochastic organic veins and field-guided strands / tendrils.
- Optional perspective extrusion for blocks, triangles, circles, and lines.
- Configurable vanishing point and subtle dimensional edge lighting.
- Unicode text layer supporting sentences, multiline input, hiragana, katakana, kanji, and symbols.
- Text arrangements: flow, wave, arc, spiral, grid, and scatter.
- System-font detection with **Bahnschrift** preferred when installed, with Qt font fallback for unsupported glyphs.
- Organic, perspective, and text extension settings are stored in JSON presets.

### Changed

- Export is kept as the final UI tab.
- New features remain additive in `pattern_app/extensions.py`; the established renderer and dark UI are not replaced.

## [2.1.0] - 2026-08-30

### Added

- Generative parameter system organized around composition, field dynamics, geometry, color, layers, and controlled behavior.
- Multiple field modes and weighted primitive selection.
- Aspect-aware geometry and composition controls.
- PNG, SVG, and JSON preset export/import.
- PySide6 desktop UI.
- Windows portable release build configuration.

### Changed

- Project identity standardized as **eli_lab**.
- Renderer separated from the GUI.
- Seeded generation remains deterministic.
