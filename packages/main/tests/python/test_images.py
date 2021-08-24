import pytest
from pathlib import Path
from RPA.Images import Images, TemplateMatcher, Region, to_image, HAS_RECOGNITION

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
)


def get_test_name(param):
    return param[1].split(".")[0]


@pytest.fixture(params=TEMPLATES, ids=get_test_name)
def region_and_template(request):
    yield request.param[0], request.param[1]


@pytest.mark.skipif(not HAS_RECOGNITION, reason="Test requires recognition")
def test_find_template(region_and_template):
    region, template = region_and_template
    region = Region(*region)

    library = Images()
    matches = library.find_template_in_image(
        image=IMAGES / "source.png",
        template=IMAGES / template,
        tolerance=0.8,
    )

    assert len(matches) == 1
    match = matches[0]
    assert match.center == region.center
