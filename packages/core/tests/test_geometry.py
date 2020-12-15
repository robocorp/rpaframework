import pytest
from RPA.core import geometry


def test_str_to_point():
    point = geometry.to_point("13,37")
    assert isinstance(point, geometry.Point)
    assert point.x == 13
    assert point.y == 37


def test_tuple_to_point():
    point = geometry.to_point((11, 233))
    assert isinstance(point, geometry.Point)
    assert point.x == 11
    assert point.y == 233


def test_point_to_point():
    before = geometry.Point(10, 10)
    after = geometry.to_point(before)
    assert before == after


def test_point_tuple():
    point = geometry.Point(1, 2)
    assert point.as_tuple() == (1, 2)


def test_point_iterable():
    point = geometry.Point(10, 20)
    values = [i for i in point]
    assert values == [10, 20]


def test_point_move():
    first = geometry.Point(0, 0)
    second = first.move(10, 10)
    third = second.move(-5, -5)

    assert first.as_tuple() == (0, 0)
    assert second.as_tuple() == (10, 10)
    assert third.as_tuple() == (5, 5)


def test_point_string():
    point = geometry.Point(200, -20)
    assert str(point) == "point:200,-20"


def test_str_to_region():
    region = geometry.to_region("10,20,30,40")
    assert isinstance(region, geometry.Region)
    assert region.left == 10
    assert region.top == 20
    assert region.right == 30
    assert region.bottom == 40


def test_tuple_to_region():
    region = geometry.to_region((11, 233, 56, 320))
    assert isinstance(region, geometry.Region)
    assert region.left == 11
    assert region.top == 233
    assert region.right == 56
    assert region.bottom == 320


def test_region_to_region():
    before = geometry.Region(10, 10, 20, 20)
    after = geometry.to_region(before)
    assert before == after


def test_region_invalid():
    with pytest.raises(ValueError):
        geometry.Region(10, 10, 5, 20)

    with pytest.raises(ValueError):
        geometry.Region(10, 10, 20, 5)


def test_region_iterable():
    region = geometry.Region(1, 2, 3, 4)
    values = [i for i in region]
    assert values == [1, 2, 3, 4]


def test_region_from_size():
    region = geometry.Region.from_size(50, 50, 100, 200)
    assert region.left == 50
    assert region.top == 50
    assert region.right == 150
    assert region.bottom == 250


def test_region_merge():
    first = geometry.Region(10, 10, 20, 20)
    second = geometry.Region(10, 5, 25, 19)

    merged = geometry.Region.merge((first, second))
    assert merged.left == 10
    assert merged.top == 5
    assert merged.right == 25
    assert merged.bottom == 20


def test_region_width():
    assert geometry.Region(10, 5, 25, 10).width == 15


def test_region_width_setter():
    region = geometry.Region(10, 5, 30, 15)
    assert region.width == 20
    assert region.height == 10
    assert region.center == geometry.Point(20, 10)

    region.width = 30
    assert region.width == 30
    assert region.height == 10
    assert region.center == geometry.Point(20, 10)


def test_region_height():
    assert geometry.Region(10, 5, 25, 10).height == 5


def test_region_height_setter():
    region = geometry.Region(10, 5, 30, 15)
    assert region.width == 20
    assert region.height == 10
    assert region.center == geometry.Point(20, 10)

    region.height = 30
    assert region.width == 20
    assert region.height == 30
    assert region.center == geometry.Point(20, 10)


def test_region_area():
    assert geometry.Region(10, 5, 25, 10).area == 75


def test_region_center():
    assert geometry.Region(10, 5, 25, 10).center == geometry.Point(17, 7)


def test_region_scale():
    region = geometry.Region(5, 5, 10, 10)

    scaled = region.scale(2)
    assert scaled.left == 10
    assert scaled.top == 10
    assert scaled.right == 20
    assert scaled.bottom == 20


def test_region_rezise():
    region = geometry.Region(20, 40, 30, 60)

    resized = region.resize(5)
    assert resized.left == 15
    assert resized.top == 35
    assert resized.right == 35
    assert resized.bottom == 65

    resized = region.resize(-2)
    assert resized.left == 22
    assert resized.top == 42
    assert resized.right == 28
    assert resized.bottom == 58

    with pytest.raises(ValueError):
        region.resize(-5)


def test_region_resize_varargs():
    region = geometry.Region(20, 40, 30, 60)

    resized = region.resize(5, 10)
    assert resized.left == 15
    assert resized.top == 30
    assert resized.right == 35
    assert resized.bottom == 70

    resized = region.resize(5, 10, 15)
    assert resized.left == 15
    assert resized.top == 30
    assert resized.right == 45
    assert resized.bottom == 70

    resized = region.resize(5, 10, 15, 20)
    assert resized.left == 15
    assert resized.top == 30
    assert resized.right == 45
    assert resized.bottom == 80

    with pytest.raises(ValueError):
        region.resize(1, 2, 3, 4, 5)


def test_region_move():
    region = geometry.Region(5, 5, 10, 10)

    moved = region.move(-8, 700)
    assert moved.left == -3
    assert moved.top == 705
    assert moved.right == 2
    assert moved.bottom == 710


def test_region_contains():
    region = geometry.Region(-10, 15, 255, 137)

    assert region.contains(geometry.Point(15, 90))
    assert region.contains(geometry.Point(-10, 90))
    assert region.contains(geometry.Point(255, 15))
    assert not region.contains(geometry.Point(-11, 90))
    assert not region.contains(geometry.Point(100, 9000))

    assert region.contains(geometry.Region(15, 90, 100, 100))
    assert region.contains(geometry.Region(-10, 15, -5, 16))
    assert region.contains(geometry.Region(-10, 15, 255, 137))
    assert not region.contains(geometry.Region(-11, 15, 137, 137))
    assert not region.contains(geometry.Region(15, 90, 100, 10000))


def test_region_clamp():
    region = geometry.Region(200, -20, 600, 75)
    bounds = geometry.Region(200, 0, 500, 80)

    clamped = region.clamp(bounds)
    assert clamped.left == 200
    assert clamped.top == 0
    assert clamped.right == 500
    assert clamped.bottom == 75

    region = geometry.Region(0, 0, 100, 100)
    bounds = geometry.Region(200, 250, 500, 500)

    with pytest.raises(ValueError):
        region.clamp(bounds)


def test_region_string():
    region = geometry.Region(200, -20, 600, 75)
    assert str(region) == "region:200,-20,600,75"
