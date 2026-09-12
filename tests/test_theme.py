from beeref.theme import (
    available_themes,
    canvas_colors,
    canvas_decoration,
)


def test_theme_catalog_contains_color_forward_variants():
    themes = dict(available_themes())

    assert themes['sakura'] == 'Sakura'
    assert themes['sakura-night'] == 'Sakura Night'
    assert themes['citrus'] == 'Citrus Dusk'
    assert themes['lavender'] == 'Lavender Haze'
    assert len(themes) == 10


def test_decorations_are_limited_to_selected_expressive_themes():
    assert canvas_decoration('sakura')[0] == 'petals'
    assert canvas_decoration('citrus')[0] == 'rings'
    assert canvas_decoration('graphite') is None
    assert canvas_decoration('paper') is None


def test_sakura_night_preserves_the_previous_canvas_palette():
    assert canvas_colors('sakura-night') == ('#151015', '#211820')
    assert canvas_colors('sakura') != canvas_colors('sakura-night')
