# Migration from robocorp-flet to Official Flet

## Overview

The `rpaframework-assistant` package was migrated from `robocorp-flet==0.4.2.3` (an outdated fork of flet 0.4.2) to the official `flet>=0.82.0,<1.0.0` package. This was necessary because the fork was no longer maintained and fell far behind upstream flet, which has undergone major breaking changes — most notably the [v0.80 "1.0 Alpha" overhaul](https://flet.dev/blog/flet-v0-80-release-announcement) that merged `flet_core` into `flet` and redesigned many APIs.

## Reason for Migration

- **`robocorp-flet` is unmaintained** — pinned to a fork of flet 0.4.2 with no further updates.
- **Security and compatibility** — staying on an outdated fork blocks Python version upgrades and misses upstream fixes.
- **`flet_core` was removed** — flet 0.80+ merged `flet_core` into `flet`, making the old import paths (`from flet_core import ...`) invalid.

## Python Version Requirement

`requires-python` was bumped from `>=3.9.1` to `>=3.10` because flet 0.82+ requires Python 3.10 at minimum.

## Major Changes by File

### `background_flet.py` — Full Rewrite

**Why:** The old code relied on private flet internals that were completely removed:
- `ft.__connect_internal_sync` — internal connection setup
- `ft.open_flet_view` / `ft.close_flet_view` — subprocess-based window management
- `flet_core.page.Connection` — internal connection class

**New approach:**
- Runs `ft.app(target=...)` in a daemon `threading.Thread`
- Patches `signal.signal` to no-op in the thread (signal handlers can't be registered outside the main thread)
- Uses `threading.Event` for close detection (replaces `subprocess.Popen.poll()`)
- `close_flet_view()` calls `page.window.destroy()` via `asyncio.run_coroutine_threadsafe` instead of subprocess termination
- `start_flet_view()` has a 30-second timeout on page readiness to prevent indefinite hangs if flet fails to start
- `poll()` returns `None` (still open) or `0` (closed), preserving the existing interface

**Reference:** [Flet Page Window events](https://flet.dev/docs/controls/page#window)

### `flet_client.py` — Window API and Service Changes

**Window properties renamed** (flet 0.80+ change):

| Old (0.4.x) | New (0.82+) |
|---|---|
| `page.window_height` | `page.window.height` |
| `page.window_width` | `page.window.width` |
| `page.window_always_on_top` | `page.window.always_on_top` |
| `page.window_center()` | `page.window.center()` |
| `page.window_left` | `page.window.left` |
| `page.window_top` | `page.window.top` |
| `page.window_destroy()` | `page.window.destroy()` |

**Reference:** [Flet Window properties migration](https://flet.dev/docs/controls/page#window)

**FilePicker moved from overlay to services:**
`FilePicker` is now a `Service` subclass. Invisible elements that are services are added to `page.services` instead of `page.overlay`.

**Reference:** [Flet Services](https://flet.dev/docs/controls/filepicker)

**Dropdown `on_change` renamed to `on_select`:**
The `Dropdown` control no longer has `on_change`. The equivalent event handler is `on_select`. Other controls (`TextField`, `Checkbox`, `Slider`, `RadioGroup`) still use `on_change`.

**Thread-safe `page.update()` via `flet_update()`:**
In flet 0.82+, calling `page.update()` from a thread other than the flet event loop thread corrupts flet's internal state and prevents `window.destroy()` from closing the app. The `flet_update()` method now detects whether it's being called from the flet thread or not, and routes cross-thread calls through `loop.call_soon_threadsafe(page.update)`. This is critical for button callbacks, which are queued as `pending_operation` and executed on the main thread.

**AppBar.actions defaults to None:**
In the old flet, `AppBar.actions` was initialized as an empty list. In 0.82+, it defaults to `None` and must be initialized before appending.

### `library.py` — API Renames

**Renamed modules:**

| Old | New |
|---|---|
| `from flet_core import ...` | `from flet import ...` |
| `from flet_core.control_event import ControlEvent` | `from flet import ControlEvent` |
| `from flet_core.dropdown import Option` | `from flet import DropdownOption` |
| `colors` (module) | `Colors` (enum) |
| `icons` (module) | `Icons` (enum) |

**Icon constructor:**
`flet.Icon(name=...)` changed to `flet.Icon(icon=...)`.

**Icon names must use `Icons` enum:**
In flet 0.82+, passing icon names as lowercase strings (e.g. `"check_circle_rounded"`) no longer renders correctly — the icon appears as a blank white area. String names must be converted to the `Icons` enum via `getattr(Icons, icon.upper(), icon)`. The `add_icon` method already used `Icons` enum constants; `add_flet_icon` was updated to convert user-provided strings.

**FilePicker API change:**
The old callback-based `FilePicker(on_result=callback)` pattern was replaced. In flet 0.82+, `pick_files()` is async and returns a list of `FilePickerFile` directly. The `FilePickerResultEvent` class was removed. The click handler must be `async def` and `await` the `pick_files()` call.

**FilePicker service registration:**
`page.services.append()` is a plain list that doesn't mount controls. Must use `page._services.register_service()` to properly register services like FilePicker so they get a page reference.

**`page.launch_url()` is now async:**
In flet 0.82+, `page.launch_url()` is a coroutine. Event handlers that call it must wrap it with `asyncio.ensure_future()` to schedule it on the event loop.

**Reference:** [Flet FilePicker](https://flet.dev/docs/controls/filepicker)

### `types.py` — Alignment Constants Removed

The convenience constants `alignment.center`, `alignment.top_left`, etc. were removed. Replaced with explicit `Alignment(x, y)` values:

| Old constant | New value |
|---|---|
| `alignment.top_left` | `Alignment(-1, -1)` |
| `alignment.top_center` | `Alignment(0, -1)` |
| `alignment.top_right` | `Alignment(1, -1)` |
| `alignment.center_left` | `Alignment(-1, 0)` |
| `alignment.center` | `Alignment(0, 0)` |
| `alignment.center_right` | `Alignment(1, 0)` |
| `alignment.bottom_left` | `Alignment(-1, 1)` |
| `alignment.bottom_center` | `Alignment(0, 1)` |
| `alignment.bottom_right` | `Alignment(1, 1)` |

**Reference:** [Flet Alignment](https://flet.dev/docs/controls/container#alignment)

### `library.py` — State Cleanup Between Dialogs

After each `run_dialog` / `ask_user` call, the following state is now cleared to prevent leaks between sequential dialogs:
- `results` — user input values
- `date_inputs` — names of date fields (for string→date conversion)
- `_required_fields` — names of required fields
- `_open_layouting` — layout stack (Row/Column/Stack/Container/AppBar)
- `validation_errors` — validation error messages

**Date input empty value handling:**
`_get_results()` now returns `None` for empty date fields instead of crashing with `ValueError: Invalid isoformat string: ''`.

### `callback_runner.py` — Import Path Only

Changed `from flet_core import ControlEvent` to `from flet import ControlEvent`. No logic changes.

## Files Modified

| File | Change scope |
|---|---|
| `packages/assistant/pyproject.toml` | Dependency + Python version |
| `packages/assistant/src/RPA/Assistant/background_flet.py` | Full rewrite, startup timeout |
| `packages/assistant/src/RPA/Assistant/callback_runner.py` | Import path |
| `packages/assistant/src/RPA/Assistant/flet_client.py` | Window API, services, Dropdown event, thread-safe update |
| `packages/assistant/src/RPA/Assistant/library.py` | Renames, FilePicker (async), Icon enum, launch_url async, state cleanup, date input empty handling |
| `packages/assistant/src/RPA/Assistant/types.py` | Import path, alignment constants |

## Future Considerations

### Improve window close error handling

`close_flet_view()` in `background_flet.py` uses a broad `except Exception: pass` that silently swallows all errors from `window.destroy()`. This can mask real failures and make the dialog appear closed when the native window is still open. A future improvement would be to log the error instead of silently ignoring it, and ensure `_closed_event` is only set after the close operation actually succeeds or a real close/disconnect event is observed. Note that `close_flet_view` also serves as an `atexit` handler, so error propagation must be handled carefully.

### Replace private flet service internals with public API

`flet_client.py` uses `page._services.register_service()` and `page._services.unregister_services()` — private flet internals that may change without notice. This was necessary because the public `page.services.append()` does not properly mount controls (the `FilePicker` fails with "Control must be added to the page first"). If a future flet version provides a public service registration API, these calls should be migrated. Until then, this is documented tech debt.

### Expose additional flet layout properties

The Assistant library keywords expose only a subset of the underlying flet control properties. The following are available in flet 0.82+ and would be useful additions:

**Quick wins — high impact, easy to add:**

| Keyword | Property | Description |
|---|---|---|
| `open_row` | [`alignment`](https://flet.dev/docs/controls/row#alignment) | Position children along main axis (START, END, CENTER, SPACE_BETWEEN) |
| `open_row` | [`vertical_alignment`](https://flet.dev/docs/controls/row#vertical_alignment) | Align items vertically within the row |
| `open_row` | [`spacing`](https://flet.dev/docs/controls/row#spacing) | Gap between children (default 10) |
| `open_column` | [`horizontal_alignment`](https://flet.dev/docs/controls/column#horizontal_alignment) | Left/center/right align content |
| `open_column` | [`alignment`](https://flet.dev/docs/controls/column#alignment) | Vertical distribution of children |
| `open_column` | [`spacing`](https://flet.dev/docs/controls/column#spacing) | Gap between children |
| `open_container` | [`alignment`](https://flet.dev/docs/controls/container#alignment) | Position content within container |
| `open_navbar` | [`bgcolor`](https://flet.dev/docs/controls/appbar#bgcolor) | Navbar background color |

**Medium priority:**

| Keyword | Property | Description |
|---|---|---|
| `open_row` / `open_column` | [`wrap`](https://flet.dev/docs/controls/row#wrap) | Wrap children to next line when out of space |
| `open_container` | [`border_radius`](https://flet.dev/docs/controls/container#border_radius) | Rounded corners |
| `open_container` | [`border`](https://flet.dev/docs/controls/container#border) | Border styling (color, width) |
| `open_container` | [`shadow`](https://flet.dev/docs/controls/container#shadow) | Drop shadow effect |
| `open_navbar` | [`center_title`](https://flet.dev/docs/controls/appbar#center_title) | Center the title text |
| `open_navbar` | [`leading`](https://flet.dev/docs/controls/appbar#leading) | Back button or menu icon |
| `open_stack` | [`alignment`](https://flet.dev/docs/controls/stack#alignment) | Default position for non-positioned children |
| `add_submit_buttons` | [`icon`](https://flet.dev/docs/controls/elevatedbutton#icon) | Icons on buttons |

**Advanced:**

| Keyword | Property | Description |
|---|---|---|
| `open_container` | [`gradient`](https://flet.dev/docs/controls/container#gradient), [`image`](https://flet.dev/docs/controls/container#image) | Background gradient or image |
| `open_stack` | [`fit`](https://flet.dev/docs/controls/stack#fit), [`clip_behavior`](https://flet.dev/docs/controls/stack#clip_behavior) | Child sizing strategy, overflow clipping |
| `add_submit_buttons` | [`style`](https://flet.dev/docs/controls/elevatedbutton#style) | Per-button colors, elevation, shape |

## External References

- [Flet 0.80 Release Announcement](https://flet.dev/blog/flet-v0-80-release-announcement) — breaking changes overview
- [Flet Documentation](https://flet.dev/docs/) — official docs
- [Flet Page / Window API](https://flet.dev/docs/controls/page#window) — window property changes
- [Flet FilePicker](https://flet.dev/docs/controls/filepicker) — new FilePicker API
- [Flet PyPI](https://pypi.org/project/flet/) — package versions
