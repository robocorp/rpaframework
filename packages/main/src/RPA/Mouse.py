import platform
import logging

from RPA.core.helpers import delay
from RPA.Images import Images

if platform.system() == "Windows":
    from RPA.Desktop.Windows import Windows


class Mouse:
    """Mouse interaction keywords."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def find_element(self, *args, **kwargs):
        if platform.system() == "Windows":
            return Windows().find_element(*args, **kwargs)
        else:
            raise NotImplementedError(
                "Find element not yet implmented for non-windows OS"
            )

    def get_element_center(self, *args, **kwargs):
        if platform.system() == "Windows":
            return Windows().get_element_center(*args, **kwargs)
        else:
            raise NotImplementedError(
                "Get Element Center not yet implmented for non-windows OS"
            )

    def mouse_click(
        self,
        locator: str = None,
        x: int = 0,
        y: int = 0,
        off_x: int = 0,
        off_y: int = 0,
        image: str = None,
        method: str = "locator",
        ctype: str = "click",
        **kwargs,
    ) -> None:
        # pylint: disable=C0301
        """Mouse click `locator`, `coordinates`, or `image`

        When using method `locator`,`image` or `ocr` mouse is clicked by default at
        center coordinates.

        Click types are:

        - `click` normal left button mouse click
        - `double`
        - `right`

        :param locator: element locator on active window
        :param x: coordinate x on desktop
        :param y: coordinate y on desktop
        :param off_x: offset x (used for locator and image clicks)
        :param off_y: offset y (used for locator and image clicks)
        :param image: image to click on desktop
        :param method: one of the available methods to mouse click, default "locator"
        :param ctype: type of mouse click
        :param **kwargs: these keyword arguments can be used to pass arguments
         to underlying `Images` library to finetune image template matching,
         for example. `tolerance=0.5` would adjust image tolerance for the image
         matching

        Example:

        .. code-block:: robotframework

            Mouse Click  method=coordinates  100   100
            Mouse Click  CalculatorResults
            Mouse Click  method=image  image=myimage.png  off_x=10  off_y=10  ctype=right
            Mouse Click  method=image  image=myimage.png  tolerance=0.8

        """  # noqa: E501
        self.logger.info("Mouse click: %s", locator)

        if method == "locator":
            element, _ = self.find_element(locator)
            if element and len(element) == 1:
                x, y = self.get_element_center(element[0])
                self.click_type(x + off_x, y + off_y, ctype)
            else:
                raise ValueError(f"Could not find unique element for '{locator}'")
        elif method == "coordinates":
            self.mouse_click_coords(x, y, ctype)
        elif method == "image":
            self.mouse_click_image(image, off_x, off_y, ctype, **kwargs)

    def mouse_click_image(
        self,
        template: str,
        off_x: int = 0,
        off_y: int = 0,
        ctype: str = "click",
        **kwargs,
    ) -> None:
        """Click at template image on desktop

        :param image: image to click on desktop
        :param off_x: horizontal offset from top left corner to click on
        :param off_y: vertical offset from top left corner to click on
        :param ctype: type of mouse click
        :param **kwargs: these keyword arguments can be used to pass arguments
         to underlying `Images` library to finetune image template matching,
         for example. `tolerance=0.5` would adjust image tolerance for the image
         matching

        Example:

        .. code-block:: robotframework

            Mouse Click  image=myimage.png  off_x=10  off_y=10  ctype=right
            Mouse Click  image=myimage.png  tolerance=0.8

        """
        matches = Images().find_template_on_screen(template, limit=1, **kwargs)

        center_x = matches[0].center.x + int(off_x)
        center_y = matches[0].center.y + int(off_y)

        self.click_type(center_x, center_y, ctype)

    def mouse_click_coords(
        self, x: int, y: int, ctype: str = "click", delay_time: float = None
    ) -> None:
        """Click at coordinates on desktop

        :param x: horizontal coordinate on the windows to click
        :param y: vertical coordinate on the windows to click
        :param ctype: click type "click", "right" or "double", defaults to "click"
        :param delay: delay in seconds after, default is no delay

        Example:

        .. code-block:: robotframework

            Mouse Click Coords  x=450  y=100
            Mouse Click Coords  x=300  y=300  ctype=right
            Mouse Click Coords  x=450  y=100  delay=5.0

        """
        self.click_type(x, y, ctype)
        if delay_time:
            delay(delay_time)

    def click_type(
        self, x: int = None, y: int = None, click_type: str = "click"
    ) -> None:
        """Mouse click on coordinates x and y.

        Default click type is `click` meaning `left`

        :param x: horizontal coordinate for click, defaults to None
        :param y: vertical coordinate for click, defaults to None
        :param click_type: "click", "right" or "double", defaults to "click"
        :raises ValueError: if coordinates are not valid

        Example:

        .. code-block:: robotframework

            Click Type  x=450  y=100
            Click Type  x=450  y=100  click_type=right
            Click Type  x=450  y=100  click_type=double

        """
        self.logger.info("Click type '%s' at (%s, %s)", click_type, x, y)
        if (x is None or y is None) or (x < 0 or y < 0):
            raise ValueError(f"Can't click on given coordinates: ({x}, {y})")
        if platform.system() == "Windows":
            Windows().windows_click_type(x, y, click_type)
        else:
            raise NotImplementedError
