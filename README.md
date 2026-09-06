# eli_lab Pattern Generator

A procedural graphics workstation for generating abstract images and SVG compositions from a deterministic seed.

**Author / creative project:** Ilya Minin (Eli) — **eli_lab**

> The project is **eli_lab**. It is not named “ELI LAB”.

## What it does

The generator builds compositions from interacting systems instead of a single randomness slider. A pattern is the result of spatial composition, a shared vector field, weighted primitive families, color behavior, layered depth, controlled mutation, optional organic structures, perspective, and text.

The desktop application uses **PySide6** for the UI, **Pillow** for raster output, and OpenSimplex when available for noise-driven fields.

### Core capabilities

- Deterministic seed-based generation.
- PNG and procedural SVG export.
- Responsive background rendering through a Qt worker pool.
- JSON preset save/load.
- Persistent window geometry.
- Blocks, circles, lines, and triangles with independent probability weights.
- Optional organic forms: amoeba, blob, petal, cell, droplet, leaf, shell, and seed.
- Smooth stochastic veins, tendrils, and field-guided organic strands.
- Optional perspective extrusion for geometric primitives with a configurable vanishing point and edge light.
- `none`, `mirror`, `radial`, and `grid` symmetry.
- Multiple spatial composition modes and explicit focal-point control.
- Noise, swirl, vortex, waves, and radial vector fields.
- Palette families: random, pastel, neon, earth, monochrome, ice, ritual, and the curated LGBTQIA+ catalogue.
- LGBTQ+ aggregate mode using the unique colors in the catalogue.
- Unicode text overlay for sentences, multiline text, hiragana, katakana, kanji, and symbols.
- Text arrangements: flow, wave, arc, spiral, grid, and scatter.
- System-font integration with **Bahnschrift** preferred when installed, while Qt handles fallback glyphs for scripts Bahnschrift does not contain.
- Aspect-aware geometry for square, portrait, landscape, ultrawide, and custom canvases.
- **Export remains the final UI section.**

## Pride palette catalogue

The palette registry lives in `pattern_app/palettes.py` and is data-driven so additional flags can be added without changing the renderer. The current curated baseline contains the project's 43 named Pride/LGBTQIA+ palettes and an aggregate unique-color mode.

This is intentionally a curated baseline rather than a claim that there is one finite or universally authoritative list of every Pride flag ever created. The ecosystem includes alternate, regional, historical, and community-specific designs.

## Text and typography

The Text tab accepts ordinary sentences as well as Unicode writing systems. Text can be organised spatially as a flow, waveform, arc, spiral, grid, or scattered composition rather than only as a conventional caption.

The application prefers the **Bahnschrift** system font when it is installed. It is not bundled into the repository; Qt's normal font fallback remains available for Japanese and other glyphs that Bahnschrift does not cover.

## Requirements

Python **3.10+** and a desktop environment supported by Qt 6.

Runtime dependencies are listed in `pyproject.toml` and `requirements.txt`:

- `PySide6>=6.10`
- `Pillow>=11.0`
- `opensimplex>=0.4`

Development and release dependencies are listed in `requirements-dev.txt` and include PyInstaller.

## Install

```bash
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# Linux / macOS
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt
```

For editable development:

```bash
python -m pip install -e .
```

## Run

Recommended from the repository root:

```bash
python run.py
```

Other supported forms:

```bash
python -m pattern_app.main
```

```bash
eli-pattern-generator
```

## Build the Windows application

The repository contains a dedicated PyInstaller setup in `release/` for producing a **single-file Windows x64 executable**. The tracked application icon is `Icon/favicon.ico`.

### One-command build

From the repository root, with the project `.venv` available:

```powershell
powershell -ExecutionPolicy Bypass -File .\\release\\build-windows.ps1
```

The executable will be at:

```text
dist\\eli_lab-pattern-generator.exe
```

Do not commit `build/`, `dist/`, or generated release artifacts.

## Release process

1. Update the version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run `release/build-windows.ps1` and launch the resulting `.exe` to test it on Windows.
4. Create a Git tag matching the package version, for example:

```powershell
git tag v2.3.0
git push origin v2.3.0
```

5. Upload `dist/eli_lab-pattern-generator.exe` to the GitHub Release.

## Presets

Presets are ordinary JSON files containing the full `PatternConfig` plus extension settings for organic structures, perspective, text, and palette preservation. They are intended to be portable, diffable, and version-controllable. Older presets without extension fields remain loadable with defaults.

## Architecture

```text
pattern_app/
├── __init__.py
├── generator.py        # Stable procedural renderer + SVG generator
├── palettes.py         # Pride palette registry + aggregate colors
├── extensions.py       # Additive organic/perspective/text layer
├── main.py             # Stable application entry point
└── ui.py               # Original dark PySide6 UI

run.py
requirements.txt
requirements-dev.txt
pyproject.toml
release/
├── eli_lab_pattern_generator.spec
└── build-windows.ps1
scripts/
└── build-release.ps1
Icon/
└── favicon.ico

tests/
└── test_generator.py
```

The renderer remains independent of Qt. The original generator is kept as the base composition engine, while `extensions.py` adds the newer creative systems without rewriting the established dark UI or the original spatial logic.

## Development

Run the test suite with:

```bash
python -m pytest
```

The tests cover color parsing, normalization bounds, deterministic generation, SVG output, aspect-aware geometry, and representative behavior profiles. The Windows GUI should additionally be launched manually after changes affecting `extensions.py` or Qt typography.

## Historical versions

`Versions/v_1`, `Versions/v_2`, and `Versions/v_3` remain as a development archive. The current application is the PySide6 implementation under `pattern_app/`.

## Roadmap

Future work can build on the current model with palette harmony modes, masks, layer blend modes, batch generation, seed browsing, animation-ready parameter interpolation, richer SVG primitives, a preset library, a Windows installer, and additional platform-specific release bundles.
