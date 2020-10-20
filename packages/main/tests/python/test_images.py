import pytest
from pathlib import Path
from RPA.Images import Images, TemplateMatcher, Region, HAS_OPENCV, to_image

IMAGES = Path(__file__).resolve().parent / ".." / "resources" / "images"

# TODO: Create new .png test data which works for pillow matching method
TEMPLATES = (
    ((26, 994, 274, 1115), "locator_Calculator_ctrl_One.jpg"),
    ((279, 994, 527, 1115), "locator_Calculator_ctrl_Two.jpg"),
    ((533, 994, 781, 1115), "locator_Calculator_ctrl_Three.jpg"),
    ((26, 868, 274, 989), "locator_Calculator_ctrl_Four.jpg"),
    ((279, 868, 527, 989), "locator_Calculator_ctrl_Five.jpg"),
    ((533, 868, 781, 989), "locator_Calculator_ctrl_Six.jpg"),
    ((26, 742, 274, 863), "locator_Calculator_ctrl_Seven.jpg"),
    ((279, 742, 527, 863), "locator_Calculator_ctrl_Eight.jpg"),
    ((533, 742, 781, 863), "locator_Calculator_ctrl_Nine.jpg"),
    ((26, 1120, 274, 1241), "locator_Calculator_ctrl_Positive_Negative.jpg"),
    ((279, 1120, 527, 1240), "locator_Calculator_ctrl_Zero.jpg"),
    ((533, 1120, 781, 1240), "locator_Calculator_ctrl_Decimal_Separator.jpg"),
    ((26, 742, 780, 1240), "locator_Calculator_ctrl_Number_pad.jpg"),
    ((786, 616, 1034, 737), "locator_Calculator_ctrl_Divide_by.jpg"),
    ((786, 742, 1034, 863), "locator_Calculator_ctrl_Multiply_by.jpg"),
    ((786, 868, 1034, 988), "locator_Calculator_ctrl_Minus.jpg"),
    ((786, 994, 1034, 1115), "locator_Calculator_ctrl_Plus.jpg"),
    ((786, 1120, 1034, 1240), "locator_Calculator_ctrl_Equals.jpg"),
    ((786, 616, 1034, 1240), "locator_Calculator_ctrl_Standard_operators.jpg"),
    ((26, 616, 274, 737), "locator_Calculator_ctrl_Reciprocal.jpg"),
    ((279, 616, 527, 737), "locator_Calculator_ctrl_Square.jpg"),
    ((533, 616, 781, 737), "locator_Calculator_ctrl_Square_root.jpg"),
    ((26, 616, 780, 737), "locator_Calculator_ctrl_Standard_functions.jpg"),
    ((27, 413, 190, 486), "locator_Calculator_ctrl_Clear_all_memory.jpg"),
    ((195, 413, 358, 486), "locator_Calculator_ctrl_Memory_Recall.jpg"),
    ((364, 413, 528, 486), "locator_Calculator_ctrl_Memory_Add.jpg"),
    ((532, 413, 695, 486), "locator_Calculator_ctrl_Memory_Subtract.jpg"),
    ((701, 413, 865, 486), "locator_Calculator_ctrl_Memory_Store.jpg"),
    ((872, 413, 1035, 486), "locator_Calculator_ctrl_Open_memory_flyout.jpg"),
    ((27, 413, 1035, 486), "locator_Calculator_ctrl_Memory_controls.jpg"),
    ((26, 490, 274, 611), "locator_Calculator_ctrl_Percent.jpg"),
    ((533, 490, 781, 611), "locator_Calculator_ctrl_Clear.jpg"),
    ((279, 490, 527, 611), "locator_Calculator_ctrl_Clear_entry.jpg"),
    ((786, 490, 1034, 611), "locator_Calculator_ctrl_Backspace.jpg"),
    ((26, 490, 1034, 611), "locator_Calculator_ctrl_Display_controls.jpg"),
    ((146, 96, 344, 163), "locator_Calculator_ctrl_Standard_Calculator_mode.jpg"),
    ((16, 81, 116, 181), "locator_Calculator_ctrl_Open_Navigation.jpg"),
    ((944, 81, 1044, 181), "locator_Calculator_ctrl_Open_history_flyout.jpg"),
    ((699, 1, 814, 81), "locator_Calculator_ctrl_Minimize_Calculator.jpg"),
    ((814, 1, 929, 81), "locator_Calculator_ctrl_Maximize_Calculator.jpg"),
    ((374, 81, 474, 181), "locator_Calculator_ctrl_Keep_on_top.jpg"),
    ((929, 1, 1044, 81), "locator_Calculator_ctrl_Close_Calculator.jpg"),
    ((61, 183, 999, 230), "locator_Calculator_ctrl_Expression_is_330__4.jpg"),
    ((16, 230, 1044, 410), "locator_Calculator_ctrl_Display_is_825.jpg"),
)


def get_test_name(param):
    return param[1].split(".")[0]


@pytest.fixture(params=TEMPLATES, ids=get_test_name)
def region_and_template(request):
    yield request.param[0], request.param[1]


@pytest.mark.skipif(not HAS_OPENCV, reason="Test requires opencv support")
def test_find_template(region_and_template):
    region, template = region_and_template
    region = Region(*region)

    library = Images()
    library.matcher = TemplateMatcher(opencv=True)

    matches = library.find_template_in_image(
        image=IMAGES / "source.png", template=IMAGES / template
    )

    assert len(matches) == 1
    match = matches[0]
    assert match.center == region.center


@pytest.mark.skipif(not HAS_OPENCV, reason="Test requires opencv support")
def test_wait_template(region_and_template):
    _, template = region_and_template
    library = Images()
    library.take_screenshot = lambda: to_image(IMAGES / "source.png")

    library.matcher = TemplateMatcher(opencv=True)
    matches = library.wait_template_on_screen(IMAGES / template, timeout=0.52)
    assert len(matches) == 1


@pytest.mark.skip(
    reason="this currently fails because the found template has some offset, at least on multi-monitor setups"
)
def test_screenshot_region_and_find_it():
    library = Images()
    region = Region(0, 0, 100, 100)
    first_capture = library.take_screenshot(region=region)
    find_result = library.find_template_on_screen(first_capture)
    assert region == find_result[0]
