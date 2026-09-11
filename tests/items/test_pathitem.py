from PyQt6 import QtCore, QtGui

from beeref.fileio.export import SceneToSVGExporter
from beeref.items import BeePathItem, item_registry


def mark(tool='pen', style='solid', start=(0, 0), end=(40, 30)):
    return {
        'tool': tool,
        'style': style,
        'color': [255, 80, 60, 255],
        'base_size': 6,
        'points': [
            {'x': start[0], 'y': start[1], 'pressure': 1.0},
            {'x': end[0], 'y': end[1], 'pressure': 0.8},
        ],
    }


def test_path_item_registered(qapp):
    assert item_registry['path'] is BeePathItem


def test_path_item_roundtrip_and_copy(qapp):
    strokes = [mark('rectangle'), mark('line', 'arrow')]
    item = BeePathItem.create_from_data(data={'strokes': strokes})
    duplicate = item.create_copy()

    assert item.get_extra_save_data() == {'strokes': strokes}
    assert duplicate.strokes == strokes
    assert duplicate.strokes is not item.strokes
    assert item.bounding_rect_unselected().width() > 40


def test_all_drawing_tools_render(qapp):
    strokes = [
        mark('pen'),
        mark('line', 'dotted', (5, 35), (50, 35)),
        mark('rectangle', 'solid', (55, 0), (95, 30)),
        mark('ellipse', 'solid', (55, 35), (95, 75)),
        mark('line', 'arrow', (0, 80), (50, 80)),
    ]
    item = BeePathItem(strokes)
    item._update_bounding_rect()
    image, rect = item.render_to_image()

    assert not image.isNull()
    assert rect.width() > 95
    assert any(
        QtGui.QColor(image.pixel(x, y)).alpha() > 0
        for x in range(image.width())
        for y in range(image.height()))


def test_eraser_removes_intersecting_mark(qapp):
    item = BeePathItem([
        mark('line', start=(0, 0), end=(40, 0)),
        mark('line', start=(0, 40), end=(40, 40)),
    ])
    item._update_bounding_rect()

    assert item.erase_at(QtCore.QPointF(20, 0), 5) is True
    assert len(item.strokes) == 1
    assert item.erase_at(QtCore.QPointF(200, 200), 5) is False


def test_eraser_preview_fades_without_mutating_until_commit(qapp):
    item = BeePathItem([
        mark('line', start=(0, 0), end=(40, 0)),
        mark('line', start=(0, 40), end=(40, 40)),
    ])
    item._update_bounding_rect()
    item.set_erase_preview({0})

    assert item.erase_preview_indexes == {0}
    assert len(item.strokes) == 2
    assert item.erase_indexes({0}) is True
    assert len(item.strokes) == 1
    assert item.erase_preview_indexes == set()


def test_freehand_path_uses_cubic_smoothing(qapp):
    stroke = mark('pen')
    stroke['points'].insert(1, {'x': 12, 'y': 18, 'pressure': 1.0})
    stroke['points'].insert(2, {'x': 27, 'y': 12, 'pressure': 1.0})
    path = BeePathItem()._stroke_path(stroke)

    types = [
        path.elementAt(index).type for index in range(path.elementCount())]
    assert QtGui.QPainterPath.ElementType.CurveToElement in types


def test_backward_compatible_freehand_data(qapp):
    old_stroke = {
        'color': [1, 2, 3, 255],
        'base_size': 10,
        'points': [{'x': 1, 'y': 2}, {'x': 5, 'y': 6}],
    }
    item = BeePathItem.create_from_data(data={'strokes': [old_stroke]})
    assert item._stroke_path(old_stroke).elementCount() >= 2


def test_drawing_is_included_in_svg_export(view):
    item = BeePathItem([mark('line', 'arrow')])
    item._update_bounding_rect()
    view.scene.addItem(item)
    exporter = SceneToSVGExporter(view.scene)
    exporter.get_user_input(view)

    svg = exporter.render_to_svg()
    image = svg.find('{http://www.w3.org/2000/svg}image')
    if image is None:
        image = svg.find('image')
    assert image is not None
    href = (image.get('{http://www.w3.org/1999/xlink}href')
            or image.get('xlink:href'))
    assert href.startswith('data:image/png;base64,')
