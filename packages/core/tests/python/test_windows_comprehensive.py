"""Comprehensive tests for Windows automation modules to increase coverage."""

import base64
import platform
from io import BytesIO
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from PIL import Image

from RPA.core.windows.action import ActionMethods, ActionNotPossible
from RPA.core.windows.context import (
    ElementNotFound,
    WindowsContext,
    WindowControlError,
    with_timeout,
)
from RPA.core.windows.elements import ElementMethods
from RPA.core.windows.helpers import IS_WINDOWS, get_process_list
from RPA.core.windows.window import WindowMethods

# Create a mock COMError class for testing
class MockCOMError(Exception):
    """Mock COMError for testing."""
    pass


@pytest.fixture
def mock_ctx():
    """Create a mock context object."""
    ctx = Mock()
    ctx.logger = Mock()
    ctx.logger.debug = Mock()
    ctx.logger.info = Mock()
    ctx.logger.warning = Mock()
    ctx.list_processes = True
    ctx.global_timeout = 5.0
    ctx.anchor_element = None
    ctx.window_element = None
    return ctx


@pytest.fixture
def windows_context(mock_ctx):
    """Create a WindowsContext instance."""
    return WindowsContext(mock_ctx)


@pytest.fixture
def window_methods(mock_ctx):
    """Create a WindowMethods instance."""
    return WindowMethods(mock_ctx)


@pytest.fixture
def element_methods(mock_ctx):
    """Create an ElementMethods instance."""
    return ElementMethods(mock_ctx)


@pytest.fixture
def action_methods(mock_ctx):
    """Create an ActionMethods instance."""
    return ActionMethods(mock_ctx)


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific tests")
class TestWindowsContext:
    """Test WindowsContext class."""

    def test_init(self, mock_ctx):
        """Test WindowsContext initialization."""
        ctx = WindowsContext(mock_ctx)
        assert ctx.ctx == mock_ctx

    def test_logger_property(self, windows_context, mock_ctx):
        """Test logger property."""
        assert windows_context.logger == mock_ctx.logger

    @patch("RPA.core.windows.context.auto")
    def test_current_timeout(self, mock_auto, windows_context):
        """Test current_timeout property."""
        mock_auto.uiautomation.TIME_OUT_SECOND = 10.0
        assert windows_context.current_timeout == 10.0

    def test_window_or_none_with_valid_window(self, windows_context):
        """Test _window_or_none with valid window."""
        mock_window = Mock()
        mock_window.item = Mock()
        mock_window.item.BoundingRectangle = Mock()

        result = windows_context._window_or_none(mock_window)
        assert result == mock_window

    def test_window_or_none_with_com_error(self, windows_context):
        """Test _window_or_none with COMError."""
        mock_window = Mock()
        mock_item = Mock()
        # Use PropertyMock to make BoundingRectangle raise exception when accessed
        type(mock_item).BoundingRectangle = PropertyMock(side_effect=MockCOMError())
        mock_window.item = mock_item

        # Patch COMError in the context module
        with patch("RPA.core.windows.context.COMError", MockCOMError):
            result = windows_context._window_or_none(mock_window)
            assert result is None

    def test_window_or_none_with_none_window(self, windows_context):
        """Test _window_or_none with None window."""
        result = windows_context._window_or_none(None)
        assert result is None

    def test_window_or_none_with_none_item(self, windows_context):
        """Test _window_or_none with window that has None item."""
        mock_window = Mock()
        mock_window.item = None

        result = windows_context._window_or_none(mock_window)
        assert result is None

    def test_anchor_property(self, windows_context, mock_ctx):
        """Test anchor property."""
        mock_anchor = Mock()
        mock_anchor.item = Mock()
        mock_anchor.item.BoundingRectangle = Mock()
        mock_ctx.anchor_element = mock_anchor

        assert windows_context.anchor == mock_anchor

    def test_window_property(self, windows_context, mock_ctx):
        """Test window property."""
        mock_window = Mock()
        mock_window.item = Mock()
        mock_window.item.BoundingRectangle = Mock()
        mock_ctx.window_element = mock_window

        assert windows_context.window == mock_window

    @patch("RPA.core.windows.context.auto")
    def test_set_timeout_context_manager(self, mock_auto, windows_context, mock_ctx):
        """Test set_timeout context manager."""
        mock_ctx.global_timeout = 5.0
        mock_auto.uiautomation.TIME_OUT_SECOND = 5.0

        with windows_context.set_timeout(10.0):
            mock_auto.SetGlobalSearchTimeout.assert_called_with(10.0)

        mock_auto.SetGlobalSearchTimeout.assert_called_with(5.0)

    @patch("RPA.core.windows.context.auto")
    def test_set_timeout_with_none(self, mock_auto, windows_context):
        """Test set_timeout with None timeout."""
        with windows_context.set_timeout(None):
            pass

        mock_auto.SetGlobalSearchTimeout.assert_not_called()

    def test_anchor_property_with_invalid_window(self, windows_context, mock_ctx):
        """Test anchor property with invalid window."""
        mock_anchor = Mock()
        mock_item = Mock()
        # Use PropertyMock to make BoundingRectangle raise exception when accessed
        type(mock_item).BoundingRectangle = PropertyMock(side_effect=MockCOMError())
        mock_anchor.item = mock_item
        mock_ctx.anchor_element = mock_anchor

        # Patch COMError in the context module
        with patch("RPA.core.windows.context.COMError", MockCOMError):
            result = windows_context.anchor
            assert result is None

    def test_window_property_with_invalid_window(self, windows_context, mock_ctx):
        """Test window property with invalid window."""
        mock_window = Mock()
        mock_item = Mock()
        # Use PropertyMock to make BoundingRectangle raise exception when accessed
        type(mock_item).BoundingRectangle = PropertyMock(side_effect=MockCOMError())
        mock_window.item = mock_item
        mock_ctx.window_element = mock_window

        # Patch COMError in the context module
        with patch("RPA.core.windows.context.COMError", MockCOMError):
            result = windows_context.window
            assert result is None

    @patch("RPA.core.windows.context.auto")
    def test_set_timeout_logs(self, mock_auto, windows_context, mock_ctx):
        """Test set_timeout logs messages."""
        mock_ctx.global_timeout = 5.0
        mock_auto.uiautomation.TIME_OUT_SECOND = 5.0

        with windows_context.set_timeout(10.0):
            mock_ctx.logger.info.assert_called()

        mock_ctx.logger.debug.assert_called()

    @patch("RPA.core.windows.context.auto")
    def test_with_timeout_decorator(self, mock_auto, windows_context, mock_ctx):
        """Test with_timeout decorator."""
        mock_ctx.global_timeout = 5.0
        mock_auto.uiautomation.TIME_OUT_SECOND = 5.0

        @with_timeout
        def test_method(self, value):
            return value * 2

        result = test_method(windows_context, 5, timeout=10.0)
        assert result == 10
        mock_auto.SetGlobalSearchTimeout.assert_called()

    @patch("RPA.core.windows.context.auto")
    def test_with_timeout_decorator_no_timeout(self, mock_auto, windows_context):
        """Test with_timeout decorator without timeout parameter."""
        @with_timeout
        def test_method(self, value):
            return value * 2

        result = test_method(windows_context, 5)
        assert result == 10
        # Should not call SetGlobalSearchTimeout when timeout is not provided
        mock_auto.SetGlobalSearchTimeout.assert_not_called()

    def test_exception_classes(self):
        """Test exception classes can be instantiated."""
        action_error = ActionNotPossible("Test error")
        assert isinstance(action_error, ValueError)
        assert str(action_error) == "Test error"

        element_error = ElementNotFound("Element not found")
        assert isinstance(element_error, ValueError)
        assert str(element_error) == "Element not found"

        window_error = WindowControlError("Window not found")
        assert isinstance(window_error, ValueError)
        assert str(window_error) == "Window not found"


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific tests")
class TestWindowMethods:
    """Test WindowMethods class."""

    @patch("RPA.core.windows.window.win32gui")
    @patch("RPA.core.windows.window.win32ui")
    @patch("RPA.core.windows.window.win32api")
    @patch("RPA.core.windows.window.win32con")
    @patch("RPA.core.windows.window.Image")
    @patch("RPA.core.windows.window.base64")
    def test_get_icon_success(
        self, mock_base64, mock_image, mock_win32con, mock_win32api, mock_win32ui, mock_win32gui, tmp_path
    ):
        """Test get_icon with successful icon extraction."""
        # Setup mocks
        mock_icon = Mock()
        mock_small_icon = Mock()
        mock_win32gui.ExtractIconEx.return_value = ([mock_small_icon], [mock_icon])
        mock_win32gui.GetDC.return_value = 0
        mock_win32api.GetSystemMetrics.side_effect = [32, 32]

        mock_hdc = Mock()
        mock_compatible_dc = Mock()
        mock_hdc.CreateCompatibleDC.return_value = mock_compatible_dc
        mock_win32ui.CreateDCFromHandle.return_value = mock_hdc

        mock_hbmp = Mock()
        mock_win32ui.CreateBitmap.return_value = mock_hbmp

        # Create a temporary file for icon
        icon_file = tmp_path / "test.exe"
        icon_file.write_bytes(b"fake exe data")

        # Create the BMP file that will be "saved"
        icon_bmp = tmp_path / "icon_test.exe.bmp"

        # Mock Image.open
        mock_img = Mock()
        mock_image.open.return_value.__enter__.return_value = mock_img
        mock_buffered = BytesIO()
        mock_buffered.write(b"fake image data")
        mock_img.save = Mock()

        # Mock base64 encoding
        mock_encoded = Mock()
        mock_encoded.decode.return_value = "base64string"
        mock_base64.b64encode.return_value = mock_encoded

        # Mock SaveBitmapFile to create the file
        def save_bitmap_side_effect(hdc, path):
            Path(path).write_bytes(b"fake bmp")
        mock_hbmp.SaveBitmapFile = Mock(side_effect=save_bitmap_side_effect)

        result = WindowMethods.get_icon(str(icon_file), str(tmp_path))

        assert result is not None
        assert isinstance(result, str)  # Base64 string
        assert result == "base64string"

    def test_get_icon_no_filepath(self):
        """Test get_icon with no filepath."""
        result = WindowMethods.get_icon(None)
        assert result is None

    @patch("RPA.core.windows.window.win32gui")
    def test_get_icon_no_icons(self, mock_win32gui):
        """Test get_icon when no icons are found."""
        mock_win32gui.ExtractIconEx.return_value = ([], [])

        result = WindowMethods.get_icon("test.exe")
        assert result is None

    @patch("RPA.core.windows.window.win32process")
    @patch("RPA.core.windows.window.win32api")
    @patch("RPA.core.windows.window.win32con")
    def test_get_fullpath(self, mock_win32con, mock_win32api, mock_win32process):
        """Test get_fullpath method."""
        mock_handle = Mock()
        mock_win32api.OpenProcess.return_value = mock_handle
        mock_win32process.GetModuleFileNameEx.return_value = "C:\\test\\app.exe"

        result = WindowMethods.get_fullpath(1234)
        assert result == "C:\\test\\app.exe"
        mock_win32api.OpenProcess.assert_called_once()

    def test_get_window_rectangle_success(self, window_methods):
        """Test _get_window_rectangle with successful access."""
        mock_win = Mock()
        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win.BoundingRectangle = mock_rect

        result = window_methods._get_window_rectangle(mock_win, 1234)
        assert result == [10, 20, 100, 200]

    def test_get_window_rectangle_com_error(self, window_methods):
        """Test _get_window_rectangle with COMError."""
        mock_win = Mock()
        # Use PropertyMock to make BoundingRectangle raise exception when accessed
        type(mock_win).BoundingRectangle = PropertyMock(side_effect=MockCOMError())

        # Patch COMError in the window module
        with patch("RPA.core.windows.window.COMError", MockCOMError):
            result = window_methods._get_window_rectangle(mock_win, 1234)
            assert result is None

    def test_get_window_rectangle_none_rect(self, window_methods):
        """Test _get_window_rectangle with None rectangle."""
        mock_win = Mock()
        mock_win.BoundingRectangle = None

        result = window_methods._get_window_rectangle(mock_win, 1234)
        assert result == [None, None, None, None]

    def test_get_window_name_from_process_list(self, window_methods):
        """Test _get_window_name from process list."""
        process_list = {1234: "test.exe"}
        result = window_methods._get_window_name(1234, None, process_list)
        assert result == "test.exe"

    def test_get_window_name_from_fullpath(self, window_methods):
        """Test _get_window_name from fullpath."""
        process_list = {}
        result = window_methods._get_window_name(1234, "C:\\test\\app.exe", process_list)
        assert result == "app.exe"

    def test_get_window_name_none(self, window_methods):
        """Test _get_window_name with no name available."""
        process_list = {}
        result = window_methods._get_window_name(1234, None, process_list)
        assert result is None

    @patch.object(WindowMethods, "get_icon")
    def test_get_window_icon_success(self, mock_get_icon, window_methods):
        """Test _get_window_icon with successful icon retrieval."""
        mock_get_icon.return_value = "base64_icon_string"

        result = window_methods._get_window_icon("C:\\test.exe", None, 1234)
        assert result == "base64_icon_string"

    @patch.object(WindowMethods, "get_icon")
    def test_get_window_icon_failure(self, mock_get_icon, window_methods):
        """Test _get_window_icon with icon retrieval failure."""
        mock_get_icon.side_effect = Exception("Icon error")

        result = window_methods._get_window_icon("C:\\test.exe", None, 1234)
        assert result is None

    @patch("RPA.core.windows.window.auto")
    def test_build_window_info_success(self, mock_auto, window_methods):
        """Test _build_window_info with successful build."""
        mock_win = Mock()
        mock_win.Name = "Test Window"
        mock_win.AutomationId = "test-id"
        mock_win.ControlTypeName = "Window"
        mock_win.ClassName = "TestClass"
        mock_win.HasKeyboardFocus = True

        mock_auto.GetForegroundWindow.return_value = 12345

        result = window_methods._build_window_info(
            mock_win, 1234, "test.exe", "C:\\test.exe", 12345, "icon", [10, 20, 100, 200]
        )

        assert result is not None
        assert result["title"] == "Test Window"
        assert result["pid"] == 1234
        assert result["name"] == "test.exe"
        assert result["handle"] == 12345
        assert result["is_active"] is True

    def test_build_window_info_com_error(self, window_methods):
        """Test _build_window_info with COMError."""
        mock_win = Mock()
        # Use PropertyMock to make Name raise exception when accessed
        type(mock_win).Name = PropertyMock(side_effect=MockCOMError())

        # Patch COMError in the window module
        with patch("RPA.core.windows.window.COMError", MockCOMError):
            result = window_methods._build_window_info(
                mock_win, 1234, "test.exe", "C:\\test.exe", 12345, "icon", [10, 20, 100, 200]
            )
            assert result is None

    def test_process_single_window_success(self, window_methods):
        """Test _process_single_window with successful processing."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        mock_win.NativeWindowHandle = 12345
        mock_win.Name = "Test Window"
        mock_win.AutomationId = "test-id"
        mock_win.ControlTypeName = "Window"
        mock_win.ClassName = "TestClass"
        mock_win.HasKeyboardFocus = True

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win.BoundingRectangle = mock_rect

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_icon", return_value="icon"):
                with patch("RPA.core.windows.window.auto") as mock_auto:
                    mock_auto.GetForegroundWindow.return_value = 12345

                    result = window_methods._process_single_window(
                        mock_win, False, None, {1234: "test.exe"}
                    )

                    assert result is not None
                    assert result["pid"] == 1234

    def test_process_single_window_com_error_process_id(self, window_methods):
        """Test _process_single_window with COMError accessing ProcessId."""
        mock_win = Mock()
        # Use PropertyMock to make ProcessId raise exception when accessed
        type(mock_win).ProcessId = PropertyMock(side_effect=MockCOMError())

        # Patch COMError in the window module
        with patch("RPA.core.windows.window.COMError", MockCOMError):
            result = window_methods._process_single_window(mock_win, False, None, {})
            assert result is None

    def test_process_single_window_com_error_handle(self, window_methods):
        """Test _process_single_window with COMError accessing NativeWindowHandle."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        # Use PropertyMock to make NativeWindowHandle raise exception when accessed
        type(mock_win).NativeWindowHandle = PropertyMock(side_effect=MockCOMError())

        # Patch COMError in the window module
        with patch("RPA.core.windows.window.COMError", MockCOMError):
            with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
                result = window_methods._process_single_window(mock_win, False, None, {})
                assert result is None

    @patch("RPA.core.windows.window.auto")
    @patch("RPA.core.windows.window.get_process_list")
    def test_list_windows_success(self, mock_get_process_list, mock_auto, window_methods):
        """Test list_windows with successful window listing."""
        mock_root = Mock()
        mock_win1 = Mock()
        mock_win1.ProcessId = 1234
        mock_win1.NativeWindowHandle = 12345
        mock_win1.Name = "Window 1"
        mock_win1.AutomationId = "id1"
        mock_win1.ControlTypeName = "Window"
        mock_win1.ClassName = "Class1"
        mock_win1.HasKeyboardFocus = False

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win1.BoundingRectangle = mock_rect

        mock_root.GetChildren.return_value = [mock_win1]
        mock_auto.GetRootControl.return_value = mock_root
        mock_auto.GetForegroundWindow.return_value = 99999
        mock_get_process_list.return_value = {1234: "test.exe"}

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            result = window_methods.list_windows(icons=False)

            assert isinstance(result, list)
            assert len(result) == 1

    @patch("RPA.core.windows.window.auto")
    def test_list_windows_com_error(self, mock_auto, window_methods):
        """Test list_windows with COMError getting root control."""
        mock_auto.GetRootControl.return_value.GetChildren.side_effect = MockCOMError()

        with patch("RPA.core.windows.window.COMError", MockCOMError):
            result = window_methods.list_windows()
            assert result == []

    @patch("RPA.core.windows.window.auto")
    @patch("RPA.core.windows.window.get_process_list")
    def test_list_windows_with_icons(self, mock_get_process_list, mock_auto, window_methods, tmp_path):
        """Test list_windows with icons enabled."""
        mock_root = Mock()
        mock_win1 = Mock()
        mock_win1.ProcessId = 1234
        mock_win1.NativeWindowHandle = 12345
        mock_win1.Name = "Window 1"
        mock_win1.AutomationId = "id1"
        mock_win1.ControlTypeName = "Window"
        mock_win1.ClassName = "Class1"
        mock_win1.HasKeyboardFocus = False

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win1.BoundingRectangle = mock_rect

        mock_root.GetChildren.return_value = [mock_win1]
        mock_auto.GetRootControl.return_value = mock_root
        mock_auto.GetForegroundWindow.return_value = 99999
        mock_get_process_list.return_value = {1234: "test.exe"}

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_icon", return_value="icon_string"):
                result = window_methods.list_windows(icons=True, icon_save_directory=str(tmp_path))

                assert isinstance(result, list)

    @patch("RPA.core.windows.window.auto")
    @patch("RPA.core.windows.window.get_process_list")
    def test_list_windows_with_empty_icon(self, mock_get_process_list, mock_auto, window_methods):
        """Test list_windows when icon is empty."""
        mock_root = Mock()
        mock_win1 = Mock()
        mock_win1.ProcessId = 1234
        mock_win1.NativeWindowHandle = 12345
        mock_win1.Name = "Window 1"
        mock_win1.AutomationId = "id1"
        mock_win1.ControlTypeName = "Window"
        mock_win1.ClassName = "Class1"
        mock_win1.HasKeyboardFocus = False

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win1.BoundingRectangle = mock_rect

        mock_root.GetChildren.return_value = [mock_win1]
        mock_auto.GetRootControl.return_value = mock_root
        mock_auto.GetForegroundWindow.return_value = 99999
        mock_get_process_list.return_value = {1234: "test.exe"}

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_icon", return_value=None):
                result = window_methods.list_windows(icons=True)

                assert isinstance(result, list)
                window_methods.logger.info.assert_called()

    @patch("RPA.core.windows.window.auto")
    @patch("RPA.core.windows.window.get_process_list")
    def test_list_windows_iteration_error(self, mock_get_process_list, mock_auto, window_methods):
        """Test list_windows with error during iteration."""
        mock_root = Mock()
        mock_win1 = Mock()
        mock_win1.ProcessId = 1234
        mock_win1.NativeWindowHandle = 12345
        mock_win1.Name = "Window 1"
        mock_win1.AutomationId = "id1"
        mock_win1.ControlTypeName = "Window"
        mock_win1.ClassName = "Class1"
        mock_win1.HasKeyboardFocus = False

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win1.BoundingRectangle = mock_rect

        mock_root.GetChildren.return_value = [mock_win1]
        mock_auto.GetRootControl.return_value = mock_root
        mock_get_process_list.return_value = {1234: "test.exe"}

        # Make iteration raise an error
        def side_effect(*args, **kwargs):
            raise COMError()

        with patch.object(window_methods, "_process_single_window", side_effect=side_effect):
            result = window_methods.list_windows()

            assert isinstance(result, list)
            window_methods.logger.warning.assert_called()

    def test_process_single_window_no_fullpath(self, window_methods):
        """Test _process_single_window when get_fullpath fails."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        mock_win.NativeWindowHandle = 12345
        mock_win.Name = "Test Window"
        mock_win.AutomationId = "test-id"
        mock_win.ControlTypeName = "Window"
        mock_win.ClassName = "TestClass"
        mock_win.HasKeyboardFocus = True

        mock_rect = Mock()
        mock_rect.left = 10
        mock_rect.top = 20
        mock_rect.right = 100
        mock_rect.bottom = 200
        mock_win.BoundingRectangle = mock_rect

        with patch.object(window_methods, "get_fullpath", side_effect=Exception("Access denied")):
            with patch.object(window_methods, "_get_window_icon", return_value=None):
                with patch("RPA.core.windows.window.auto") as mock_auto:
                    mock_auto.GetForegroundWindow.return_value = 99999

                    result = window_methods._process_single_window(
                        mock_win, False, None, {1234: "test.exe"}
                    )

                    assert result is not None
                    window_methods.logger.info.assert_called()

    def test_process_single_window_rectangle_none(self, window_methods):
        """Test _process_single_window when rectangle is None."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        mock_win.NativeWindowHandle = 12345

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_rectangle", return_value=None):
                result = window_methods._process_single_window(mock_win, False, None, {})
                assert result is None

    def test_process_single_window_info_none(self, window_methods):
        """Test _process_single_window when _build_window_info returns None."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        mock_win.NativeWindowHandle = 12345

        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_rectangle", return_value=[10, 20, 100, 200]):
                with patch.object(window_methods, "_build_window_info", return_value=None):
                    result = window_methods._process_single_window(mock_win, False, None, {})
                    assert result is None

    def test_process_single_window_general_exception(self, window_methods):
        """Test _process_single_window with general exception."""
        mock_win = Mock()
        mock_win.ProcessId = 1234
        mock_win.NativeWindowHandle = 12345

        # Make something in the processing fail with a general exception
        # We'll make _build_window_info raise an exception
        with patch.object(window_methods, "get_fullpath", return_value="C:\\test.exe"):
            with patch.object(window_methods, "_get_window_rectangle", return_value=[10, 20, 100, 200]):
                with patch.object(window_methods, "_build_window_info", side_effect=Exception("General error")):
                    with patch("RPA.core.windows.window.COMError", MockCOMError):
                        result = window_methods._process_single_window(mock_win, False, None, {})
                        # Should return None due to exception being caught
                        assert result is None
                        window_methods.logger.debug.assert_called()


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific tests")
class TestElementMethods:
    """Test ElementMethods class."""

    def test_add_child_to_tree_with_locator_and_path(self, element_methods):
        """Test _add_child_to_tree with both locator and path."""
        mock_control = Mock()
        structure = {}

        ElementMethods._add_child_to_tree(
            mock_control, structure, locator="parent", depth=1, path="1|2"
        )

        assert 1 in structure
        assert len(structure[1]) == 1

    def test_add_child_to_tree_with_path_only(self, element_methods):
        """Test _add_child_to_tree with path only."""
        mock_control = Mock()
        structure = {}

        ElementMethods._add_child_to_tree(
            mock_control, structure, locator=None, depth=2, path="1|2|3"
        )

        assert 2 in structure
        assert len(structure[2]) == 1

    def test_add_child_to_tree_with_locator_only(self, element_methods):
        """Test _add_child_to_tree with locator only."""
        mock_control = Mock()
        structure = {}

        ElementMethods._add_child_to_tree(
            mock_control, structure, locator="parent", depth=0, path=""
        )

        assert 0 in structure
        assert len(structure[0]) == 1

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_basic(self, mock_auto, element_methods, mock_ctx):
        """Test print_tree basic functionality."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "WindowControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            # Mock WalkTree to return a single control
            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            result = element_methods.print_tree(locator="test", max_depth=1, return_structure=False)
            assert result is None

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_with_structure(self, mock_auto, element_methods, mock_ctx):
        """Test print_tree with return_structure=True."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "WindowControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            result = element_methods.print_tree(locator="test", max_depth=1, return_structure=True)
            assert isinstance(result, dict)

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_with_image_capture(self, mock_auto, element_methods, mock_ctx, tmp_path):
        """Test print_tree with image capture."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "ButtonControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            with patch.object(element_methods.ctx, "screenshot"):
                result = element_methods.print_tree(
                    locator="test",
                    max_depth=1,
                    capture_image_folder=str(tmp_path),
                    return_structure=False
                )
                assert result is None

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_image_capture_error(self, mock_auto, element_methods, mock_ctx, tmp_path):
        """Test print_tree with image capture error."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "ButtonControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            with patch.object(element_methods.ctx, "screenshot", side_effect=Exception("Capture error")):
                result = element_methods.print_tree(
                    locator="test",
                    max_depth=1,
                    capture_image_folder=str(tmp_path),
                    return_structure=False
                )
                assert result is None

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_with_warnings(self, mock_auto, element_methods, mock_ctx):
        """Test print_tree with log_as_warnings=True."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "WindowControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            result = element_methods.print_tree(
                locator="test",
                max_depth=1,
                log_as_warnings=True,
                return_structure=False
            )
            assert result is None
            mock_ctx.logger.warning.assert_called()

    @patch("RPA.core.windows.elements.auto")
    def test_print_tree_with_debug(self, mock_auto, element_methods, mock_ctx):
        """Test print_tree with log_as_warnings=None (debug mode)."""
        mock_control = Mock()
        mock_control.GetChildren.return_value = []
        mock_control.ControlType = "WindowControl"

        mock_element = Mock()
        mock_element.item = mock_control
        mock_ctx.get_element.return_value = mock_element

        with patch("RPA.core.windows.elements.WindowsElement") as mock_we:
            mock_we.norm_locator.return_value = "test_locator"

            mock_auto.WalkTree.return_value = [
                (mock_control, 0, 1)
            ]

            result = element_methods.print_tree(
                locator="test",
                max_depth=1,
                log_as_warnings=None,
                return_structure=False
            )
            assert result is None
            mock_ctx.logger.debug.assert_called()

    def test_add_child_to_tree_multiple_depths(self, element_methods):
        """Test _add_child_to_tree with multiple depths."""
        mock_control1 = Mock()
        mock_control2 = Mock()
        structure = {}

        ElementMethods._add_child_to_tree(
            mock_control1, structure, locator="parent", depth=0, path=""
        )
        ElementMethods._add_child_to_tree(
            mock_control2, structure, locator="parent", depth=1, path="0"
        )

        assert 0 in structure
        assert 1 in structure
        assert len(structure[0]) == 1
        assert len(structure[1]) == 1


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific tests")
class TestActionMethods:
    """Test ActionMethods class."""

    def test_screenshot_success(self, action_methods, mock_ctx, tmp_path):
        """Test screenshot with successful capture."""
        mock_item = Mock()
        mock_item.CaptureToImage = Mock()
        mock_item.SetFocus = Mock()

        mock_element = Mock()
        mock_element.item = mock_item
        mock_ctx.get_element.return_value = mock_element

        screenshot_path = tmp_path / "screenshot.png"
        result = action_methods.screenshot("test_locator", str(screenshot_path))

        assert result == str(screenshot_path.resolve())
        mock_item.SetFocus.assert_called_once()
        mock_item.CaptureToImage.assert_called_once()

    def test_screenshot_no_capture_method(self, action_methods, mock_ctx):
        """Test screenshot when element doesn't have CaptureToImage."""
        mock_item = Mock()
        mock_item.CaptureToImage = None

        mock_element = Mock()
        mock_element.item = mock_item
        mock_ctx.get_element.return_value = mock_element

        with pytest.raises(ActionNotPossible):
            action_methods.screenshot("test_locator", "test.png")

    def test_screenshot_with_path_object(self, action_methods, mock_ctx, tmp_path):
        """Test screenshot with Path object."""
        mock_item = Mock()
        mock_item.CaptureToImage = Mock()
        mock_item.SetFocus = Mock()

        mock_element = Mock()
        mock_element.item = mock_item
        mock_ctx.get_element.return_value = mock_element

        screenshot_path = tmp_path / "screenshot.png"
        result = action_methods.screenshot("test_locator", screenshot_path)

        assert result == str(screenshot_path.resolve())

    def test_screenshot_with_tilde_path(self, action_methods, mock_ctx, tmp_path):
        """Test screenshot with tilde-expanded path."""
        mock_item = Mock()
        mock_item.CaptureToImage = Mock()
        mock_item.SetFocus = Mock()

        mock_element = Mock()
        mock_element.item = mock_item
        mock_ctx.get_element.return_value = mock_element

        # Use a path that would be expanded
        result = action_methods.screenshot("test_locator", str(tmp_path / "test.png"))

        assert "test.png" in result


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-specific tests")
class TestHelpers:
    """Test helper functions."""

    @patch("RPA.core.windows.helpers.psutil")
    def test_get_process_list(self, mock_psutil):
        """Test get_process_list function."""
        mock_proc1 = Mock()
        mock_proc1.pid = 1234
        mock_proc1.name.return_value = "test.exe"

        mock_proc2 = Mock()
        mock_proc2.pid = 5678
        mock_proc2.name.return_value = "app.exe"

        mock_psutil.process_iter.return_value = [mock_proc1, mock_proc2]

        result = get_process_list()

        assert result == {1234: "test.exe", 5678: "app.exe"}

