from contextlib import nullcontext
from unittest import mock

import pytest

from RPA.core.windows.context import ElementNotFound, WindowControlError
from RPA.core.windows.locators import LocatorMethods, MatchObject


class TestMatchObject:
    """Test locator resolver."""

    @pytest.mark.parametrize(
        "locator, locators",
        [
            ("Robocorp", [("Name", "Robocorp", 0)]),
            ("Robocorp Window", [("Name", "Robocorp Window", 0)]),
            ("name:Robocorp Window", [("Name", "Robocorp", 0), ("Name", "Window", 0)]),
            ('name:"Robocorp Window"', [("Name", "Robocorp Window", 0)]),
            ('name:"Robocorp\'s Window"', [("Name", "Robocorp's Window", 0)]),
            (
                'name:"Robocorp\'s Window" class:"My Class"',
                [("Name", "Robocorp's Window", 0), ("ClassName", "My Class", 0)],
            ),
            (
                "Robocorp > File",
                [("Name", "Robocorp", 0), ("Name", "File", 1)],
            ),  # this isn't currently used in end-to-end logic
            (
                '"Robocorp Window93" subname:Robocorp and class:"My Class" Test regex:Robo.+',
                [
                    ("Name", "Robocorp Window93", 0),
                    ("SubName", "Robocorp", 0),
                    ("ClassName", "My Class", 0),
                    ("Name", "Test", 0),
                    ("RegexName", "Robo.+", 0),
                ],
            ),
            ("Robocorp:Window", [("Name", "Robocorp:Window", 0)]),
            ("name:Robocorp:Window", [("Name", "Robocorp:Window", 0)]),
            (
                "Robocorp:Window class:Class",
                [("Name", "Robocorp:Window", 0), ("ClassName", "Class", 0)],
            ),
            (
                "Robocorp'Window Test1 class:Class classx:Classx Test2",
                [
                    ("Name", "Robocorp'Window Test1", 0),
                    ("ClassName", "Class", 0),
                    ("Name", "classx:Classx Test2", 0),
                ],
            ),
            ("'Robocorp Window'", [("Name", "Robocorp Window", 0)]),
            (
                "name:'Robocorp Window'",
                [("Name", "Robocorp Window", 0)],
            ),  # single quotes work as delimiters, same as double quotes
            ('Robocorp" Window', [("Name", 'Robocorp" Window', 0)]),
            (
                'name:Robocorp" Window class:"My Class"',
                [("Name", 'Robocorp" Window class:', 0), ("Name", "My Class", 0)],
            ),  # enclosing quotes have to be closed properly
            (
                'name:"Robocorp" Window" class:"My Class"',
                [("Name", 'Robocorp" Window', 0), ("ClassName", "My Class", 0)],
            ),  # lucky capture
            (
                'name:"Robocorp " Window" class:"My Class"',
                [("Name", "Robocorp", 0), ("Name", 'Window" class:" My Class', 0)],
            ),  # can't capture same quote in enclosing ones
            ("", []),
            (
                "Robo and Corp or Window desktop",
                [("desktop", "desktop", 0), ("Name", "Robo Corp Window", 0)],
            ),
            (
                "id:123-456 depth:10 subname:Robo offset:100 executable:my.exe",
                [
                    ("AutomationId", "123-456", 0),
                    ("searchDepth", 10, 0),
                    ("SubName", "Robo", 0),
                    ("offset", "100", 0),
                    ("executable", "my.exe", 0),
                ],
            ),
            (
                'type:Group and name:"Number pad" > type:Button and index:4',
                [
                    ("ControlType", "GroupControl", 0),
                    ("Name", "Number pad", 0),
                    ("ControlType", "ButtonControl", 1),
                    ("foundIndex", 4, 1),
                ],
            ),
            (
                "Calculator > path:2|3|2|8|2",
                [("Name", "Calculator", 0), ("path", [2, 3, 2, 8, 2], 1)],
            ),
            (
                "locator='executable:AsdfConfigurator.exe",
                [("executable", "AsdfConfigurator.exe", 0)],
            ),  # stray `locator=` keyword-arg prefix + unmatched quote (issue #1323)
            (
                "LOCATOR=\"executable:AsdfConfigurator.exe",
                [("executable", "AsdfConfigurator.exe", 0)],
            ),  # case-insensitive, double-quote variant
        ],
    )
    def test_match_object(self, locator, locators):
        match_object = MatchObject.parse_locator(locator)
        assert match_object.locators == locators


class TestLocatorMethods:
    """Test element/control retrieval based on the resolved locator."""

    @pytest.fixture
    def library(self):
        yield LocatorMethods(mock.Mock())

    @pytest.mark.parametrize(
        "search_params,should_raise",
        [
            ({"path": [1, 2]}, nullcontext()),
            ({"path": [1, 3]}, pytest.raises(ElementNotFound)),
        ],
    )
    def test_get_control_from_path(self, library, search_params, should_raise):
        child21, child22 = mock.Mock(), mock.Mock()
        child1 = mock.Mock()
        child1.GetChildren.return_value = [child21, child22]
        root_control = mock.Mock()
        root_control.GetChildren.return_value = [child1]
        with should_raise:
            leaf = library._get_control_from_path(search_params, root_control)
            assert leaf == child22

    @pytest.mark.parametrize(
        "locator_value, listed_name, should_match",
        [
            # Windows file names are case-insensitive, so the case a user writes
            # must not decide whether the window is found. Windows 11 lists
            # Notepad as "Notepad.exe" while everyone writes "notepad.exe".
            ("notepad.exe", "Notepad.exe", True),
            ("Notepad.exe", "notepad.exe", True),
            ("NOTEPAD.EXE", "Notepad.exe", True),
            ("notepad.exe", "notepad.exe", True),
            # Different executables must still not match each other.
            ("notepad.exe", "wordpad.exe", False),
        ],
    )
    def test_executable_match_is_case_insensitive(
        self, library, locator_value, listed_name, should_match
    ):
        library.ctx.list_windows.return_value = [
            {"name": listed_name, "title": "Untitled - Notepad", "handle": 1}
        ]

        should_raise = (
            nullcontext() if should_match else pytest.raises(WindowControlError)
        )
        with should_raise, mock.patch.object(
            library, "_get_control_from_params"
        ) as get_control:
            library._get_control_from_listed_windows(
                {"executable": locator_value}, param_type="executable", win_type="name"
            )
            # The window title of the matched process is what gets searched for.
            assert get_control.call_args[0][0]["Name"] == "Untitled - Notepad"

    def test_handle_match_stays_exact(self, library):
        """Only `executable` is folded - `handle` is numeric and must not be."""
        library.ctx.list_windows.return_value = [
            {"name": "notepad.exe", "title": "Untitled - Notepad", "handle": 12345}
        ]

        with mock.patch.object(library, "_get_control_from_params") as get_control:
            library._get_control_from_listed_windows(
                {"handle": 12345}, param_type="handle", win_type="handle"
            )
            assert get_control.call_args[0][0]["Name"] == "Untitled - Notepad"

        with pytest.raises(WindowControlError):
            library._get_control_from_listed_windows(
                {"handle": 99999}, param_type="handle", win_type="handle"
            )

