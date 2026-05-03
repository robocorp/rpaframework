"""Tests for RPA.Desktop keyboard and mouse keyword utilities."""
from unittest.mock import MagicMock, patch

import pytest


# --- to_key ---


def test_to_key_special_keys():
    pytest.importorskip("pynput")
    from pynput.keyboard import Key

    from RPA.Desktop.keywords.keyboard import to_key

    assert to_key("ctrl") == Key.ctrl
    assert to_key("shift") == Key.shift
    assert to_key("enter") == Key.enter
    assert to_key("alt") == Key.alt
    assert to_key("tab") == Key.tab
    assert to_key("delete") == Key.delete
    assert to_key("f4") == Key.f4
    assert to_key("space") == Key.space


def test_to_key_single_character():
    pytest.importorskip("pynput")
    from pynput.keyboard import KeyCode

    from RPA.Desktop.keywords.keyboard import to_key

    assert isinstance(to_key("a"), KeyCode)
    assert isinstance(to_key("z"), KeyCode)
    assert isinstance(to_key("1"), KeyCode)


def test_to_key_case_insensitive():
    pytest.importorskip("pynput")
    from pynput.keyboard import Key

    from RPA.Desktop.keywords.keyboard import to_key

    assert to_key("CTRL") == Key.ctrl
    assert to_key("Enter") == Key.enter
    assert to_key("SHIFT") == Key.shift


def test_to_key_passthrough():
    pytest.importorskip("pynput")
    from pynput.keyboard import Key, KeyCode

    from RPA.Desktop.keywords.keyboard import to_key

    assert to_key(Key.ctrl) is Key.ctrl
    kc = KeyCode.from_char("a")
    assert to_key(kc) is kc


def test_to_key_invalid_raises():
    pytest.importorskip("pynput")
    from RPA.Desktop.keywords.keyboard import to_key

    with pytest.raises(ValueError, match="Invalid key"):
        to_key("notakey")

    with pytest.raises(ValueError, match="Invalid key"):
        to_key("ab")


# --- to_action ---


def test_to_action_valid():
    from RPA.Desktop.keywords.mouse import Action, to_action

    assert to_action("click") == Action.click
    assert to_action("double_click") == Action.double_click
    assert to_action("right_click") == Action.right_click
    assert to_action("triple_click") == Action.triple_click
    assert to_action("double click") == Action.double_click


def test_to_action_passthrough():
    from RPA.Desktop.keywords.mouse import Action, to_action

    assert to_action(Action.click) is Action.click


def test_to_action_invalid_raises():
    from RPA.Desktop.keywords.mouse import to_action

    with pytest.raises(ValueError, match="Unknown mouse action"):
        to_action("spin_click")


# --- to_button ---


def test_to_button_valid():
    pytest.importorskip("pynput")
    from pynput.mouse import Button

    from RPA.Desktop.keywords.mouse import to_button

    assert to_button("left") == Button.left
    assert to_button("right") == Button.right
    assert to_button("middle") == Button.middle


def test_to_button_passthrough():
    pytest.importorskip("pynput")
    from pynput.mouse import Button

    from RPA.Desktop.keywords.mouse import to_button

    assert to_button(Button.left) is Button.left


def test_to_button_invalid_raises():
    pytest.importorskip("pynput")
    from RPA.Desktop.keywords.mouse import to_button

    with pytest.raises(ValueError, match="Unknown mouse button"):
        to_button("side")


# --- KeyboardKeywords ---


def _make_keyboard_keywords():
    """Create KeyboardKeywords with a mocked pynput Controller and ctx."""
    mock_controller = MagicMock()
    ctx = MagicMock()

    with patch("pynput.keyboard.Controller", return_value=mock_controller):
        from RPA.Desktop.keywords.keyboard import KeyboardKeywords

        kb = KeyboardKeywords(ctx)

    return kb, mock_controller


def test_press_keys_special():
    pytest.importorskip("pynput")
    from pynput.keyboard import Key

    kb, ctrl = _make_keyboard_keywords()
    kb.press_keys("enter")

    ctrl.press.assert_called_once_with(Key.enter)
    ctrl.release.assert_called_once_with(Key.enter)


def test_press_keys_character():
    pytest.importorskip("pynput")
    from pynput.keyboard import KeyCode

    kb, ctrl = _make_keyboard_keywords()
    kb.press_keys("a")

    pressed = ctrl.press.call_args[0][0]
    assert isinstance(pressed, KeyCode)


def test_press_keys_combination_order():
    """ctrl+a: ctrl pressed first, released last."""
    pytest.importorskip("pynput")
    from pynput.keyboard import Key, KeyCode

    kb, ctrl = _make_keyboard_keywords()
    kb.press_keys("ctrl", "a")

    press_calls = [c[0][0] for c in ctrl.press.call_args_list]
    release_calls = [c[0][0] for c in ctrl.release.call_args_list]

    assert press_calls[0] == Key.ctrl
    assert isinstance(press_calls[1], KeyCode)
    assert isinstance(release_calls[0], KeyCode)
    assert release_calls[1] == Key.ctrl


def test_type_text():
    pytest.importorskip("pynput")
    kb, ctrl = _make_keyboard_keywords()
    kb.type_text("hello")

    ctrl.type.assert_called_once_with("hello")
