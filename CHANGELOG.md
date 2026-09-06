# Changelog

All notable changes to **eli_lab Pattern Generator** are documented here.

## [Unreleased]

### Planned

- Windows installer package.
- Application icon and file associations.
- macOS and Linux release artifacts.
- Preset library and batch rendering.

## [2.2.0] - 2026-09-06

### Added

- Data-driven `pattern_app/palettes.py` registry with a curated 43-flag LGBTQIA+ baseline and compatibility aliases.
- Aggregate `LGBTQ+ / all unique colors` palette mode.
- Six organic procedural form styles: amoeba, blob, petal, cell, droplet, and leaf.
- Organic-form controls for lobes, wobble, taper, internal veins/tendrils, and selection weight.
- Pride palette browser in the desktop UI.
- Option to preserve Pride flag colors by disabling palette hue jitter.
- Tests covering the palette registry and every organic style.

### Changed

- Pattern renderer now treats organic forms as a first-class primitive family alongside blocks, circles, lines, and triangles.
- JSON presets persist all new organic and Pride-palette settings.
- Application version bumped from 2.1.0 to 2.2.0.

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
