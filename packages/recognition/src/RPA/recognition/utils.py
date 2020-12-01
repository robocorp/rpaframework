import base64
import io
import math
from typing import Any

from PIL import Image


def to_image(obj: Any) -> Image.Image:
    """Convert `obj` to instance of Pillow's Image class."""
    if obj is None or isinstance(obj, Image.Image):
        return obj
    return Image.open(obj)


def image_to_base64(image: Image.Image) -> str:
    """Convert Image object to base64 string."""
    stream = io.BytesIO()
    image.save(stream)
    data = stream.getvalue()
    text = base64.b64encode(data).decode()
    return text


def base64_to_image(text: str) -> Image.Image:
    """Convert image in base64 string to Image object."""
    data = base64.b64decode(text)
    stream = io.BytesIO(data)
    image = Image.open(stream)
    return image


def clamp(minimum: float, value: float, maximum: float) -> float:
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


def log2lin(minimum: float, value: float, maximum: float) -> float:
    """Maps logarithmic scale to linear scale of same range."""
    assert value >= minimum
    assert value <= maximum
    return (maximum - minimum) * (math.log(value) - math.log(minimum)) / (
        math.log(maximum) - math.log(minimum)
    ) + minimum
