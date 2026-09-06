from pattern_app.generator import PatternConfig, PatternRenderer, hex_to_rgba
from pattern_app.palettes import ALL_PALETTES, ALL_LGBTQ_COLORS, DATA


def test_hex_to_rgba():
    assert hex_to_rgba('#abc') == (170, 187, 204, 255)
    assert hex_to_rgba('112233') == (17, 34, 51, 255)


def test_config_normalization():
    config = PatternConfig(width=1, height=90000, grid_size=100, density=-1, blur=20, field_strength=9, palette_size=99, layer_count=99, organic_lobes=99).normalized()
    assert config.width == 64
    assert config.height == 8192
    assert config.grid_size == 48
    assert config.density == 0.02
    assert config.blur == 12
    assert config.field_strength == 1.5
    assert config.palette_size == 16
    assert config.layer_count == 8
    assert config.organic_lobes == 18


def test_pride_palette_catalogue():
    assert len(DATA) == 43
    assert 'nonbinary' in ALL_PALETTES
    assert 'intersex' in ALL_PALETTES
    assert 'progress' in ALL_PALETTES
    assert len(ALL_LGBTQ_COLORS) > 20


def test_seeded_generation_is_deterministic():
    renderer = PatternRenderer()
    config = PatternConfig(width=320, height=180, seed='12345', grid_size=8)
    first = renderer.generate(config)
    second = renderer.generate(config)
    assert first.seed == second.seed == '12345'
    assert first.image.tobytes() == second.image.tobytes()
    assert '<svg' in first.svg
    assert '<polygon' in first.svg or '<polyline' in first.svg or '<circle' in first.svg


def test_organic_styles_are_renderable():
    renderer = PatternRenderer()
    for style in ('amoeba', 'blob', 'petal', 'cell', 'droplet', 'leaf'):
        config = PatternConfig(width=180, height=120, seed='organic', grid_size=7, use_blocks=False, use_circles=False, use_lines=False, use_triangles=False, use_organic=True, organic_style=style)
        result = renderer.generate(config)
        assert result.image.size == (180, 120)
        assert '<polygon' in result.svg


def test_behavior_profiles_are_renderable():
    renderer = PatternRenderer()
    base = PatternConfig(width=180, height=120, seed='behavior-test', grid_size=7)
    for behavior in ('calm', 'organic', 'architectural', 'chaotic', 'ritual'):
        result = renderer.generate(PatternConfig(**{**base.to_dict(), 'behavior': behavior}))
        assert result.image.size == (180, 120)
        assert result.seed == 'behavior-test'
        assert result.svg.endswith('</svg>')


def test_symmetry_is_reproducible():
    renderer = PatternRenderer()
    for symmetry in ('none', 'mirror', 'grid', 'radial'):
        config = PatternConfig(width=220, height=140, seed='symmetry', grid_size=6, symmetry=symmetry)
        first = renderer.generate(config)
        second = renderer.generate(config)
        assert first.image.tobytes() == second.image.tobytes()
