"""wxPython test application for RPA.Windows UIAutomation testing.

Unlike tkinter, wxPython wraps native Win32 controls which properly expose
UIAutomation accessibility attributes (control types, names, patterns).

Controls exposed:

    - wx.CheckBox     → CheckBoxControl   + TogglePattern        (name = label text)
    - wx.RadioButton  → RadioButtonControl + SelectionItemPattern (name = label text)
    - wx.TextCtrl     → EditControl        + ValuePattern         (name = label from StaticText)
    - wx.ComboBox     → ComboBoxControl    + ValuePattern         (name = label from StaticText)
    - wx.Button       → ButtonControl      + InvokePattern        (name = label text)
    - wx.StaticText   → TextControl                               (name = label text)

Window title: "RPA Windows Test App WX"

Usage::

    python testapp_wx.py
"""

import wx


class TestFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="RPA Windows Test App WX", size=(420, 560))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # ------------------------------------------------------------------ #
        # Checkboxes
        # ------------------------------------------------------------------ #
        chk_box = wx.StaticBox(panel, label="Checkboxes")
        chk_sizer = wx.StaticBoxSizer(chk_box, wx.VERTICAL)

        self.chk_checked = wx.CheckBox(panel, label="Checked")
        self.chk_checked.SetValue(True)

        self.chk_unchecked = wx.CheckBox(panel, label="Unchecked")
        self.chk_unchecked.SetValue(False)

        # wx.CHK_3STATE enables the indeterminate (middle) state.
        # wx.CHK_ALLOW_3RD_STATE_FOR_USER lets the user cycle into it.
        self.chk_indeterminate = wx.CheckBox(
            panel,
            label="Indeterminate",
            style=wx.CHK_3STATE | wx.CHK_ALLOW_3RD_STATE_FOR_USER,
        )
        self.chk_indeterminate.Set3StateValue(wx.CHK_UNDETERMINED)

        chk_sizer.Add(self.chk_checked, 0, wx.ALL, 6)
        chk_sizer.Add(self.chk_unchecked, 0, wx.ALL, 6)
        chk_sizer.Add(self.chk_indeterminate, 0, wx.ALL, 6)
        vbox.Add(chk_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------------ #
        # Radio Buttons
        # ------------------------------------------------------------------ #
        rad_box = wx.StaticBox(panel, label="Radio Buttons")
        rad_sizer = wx.StaticBoxSizer(rad_box, wx.VERTICAL)

        # wx.RB_GROUP starts a new mutually-exclusive group.
        # "Option A" is selected by default (first in group).
        self.rad_a = wx.RadioButton(panel, label="Option A", style=wx.RB_GROUP)
        self.rad_b = wx.RadioButton(panel, label="Option B")
        self.rad_a.SetValue(True)

        rad_sizer.Add(self.rad_a, 0, wx.ALL, 6)
        rad_sizer.Add(self.rad_b, 0, wx.ALL, 6)
        vbox.Add(rad_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------------ #
        # Text Entry
        # ------------------------------------------------------------------ #
        txt_box = wx.StaticBox(panel, label="Text Entry")
        txt_sizer = wx.StaticBoxSizer(txt_box, wx.VERTICAL)

        # wx.TextCtrl → EditControl + ValuePattern in UIAutomation.
        self.txt_entry = wx.TextCtrl(panel, value="")
        txt_sizer.Add(self.txt_entry, 0, wx.EXPAND | wx.ALL, 6)
        vbox.Add(txt_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------------ #
        # Combobox
        # ------------------------------------------------------------------ #
        cmb_box = wx.StaticBox(panel, label="Combobox")
        cmb_sizer = wx.StaticBoxSizer(cmb_box, wx.VERTICAL)

        # wx.ComboBox → ComboBoxControl + ValuePattern in UIAutomation.
        self.cmb = wx.ComboBox(
            panel,
            value="Apple",
            choices=["Apple", "Banana", "Cherry"],
            style=wx.CB_READONLY,
        )
        cmb_sizer.Add(self.cmb, 0, wx.EXPAND | wx.ALL, 6)
        vbox.Add(cmb_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------------ #
        # Dynamic element (for path-locator timeout testing)
        # ------------------------------------------------------------------ #
        dyn_box = wx.StaticBox(panel, label="Dynamic Controls")
        dyn_sizer = wx.StaticBoxSizer(dyn_box, wx.VERTICAL)

        # Placeholder panel — the dynamic label is added/removed inside it.
        self._dyn_inner = wx.Panel(panel)
        self._dyn_inner_sizer = wx.BoxSizer(wx.VERTICAL)
        self._dyn_inner.SetSizer(self._dyn_inner_sizer)
        self._dynamic_label: wx.StaticText | None = None

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_show = wx.Button(panel, label="Show after 3s")
        btn_show.Bind(wx.EVT_BUTTON, lambda _: self._schedule_label(3000))
        btn_hide = wx.Button(panel, label="Hide")
        btn_hide.Bind(wx.EVT_BUTTON, lambda _: self._hide_label())
        btn_row.Add(btn_show, 0, wx.RIGHT, 6)
        btn_row.Add(btn_hide, 0)

        dyn_sizer.Add(self._dyn_inner, 0, wx.EXPAND | wx.ALL, 4)
        dyn_sizer.Add(btn_row, 0, wx.ALL, 4)
        vbox.Add(dyn_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ------------------------------------------------------------------ #
        # Quit
        # ------------------------------------------------------------------ #
        btn_quit = wx.Button(panel, label="Quit")
        btn_quit.Bind(wx.EVT_BUTTON, lambda _: self.Close())
        vbox.Add(btn_quit, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        panel.SetSizer(vbox)
        self.Centre()
        self.Show()

    # ---------------------------------------------------------------------- #
    # Dynamic label helpers
    # ---------------------------------------------------------------------- #

    def _schedule_label(self, delay_ms: int) -> None:
        self._hide_label()
        wx.CallLater(delay_ms, self._show_label)

    def _show_label(self) -> None:
        if self._dynamic_label:
            return
        # wx.StaticText is skipped by UIAutomation (non-interactive Win32 Static).
        # Use a disabled Button instead — ButtonControl is always in the a11y tree.
        self._dynamic_label = wx.Button(self._dyn_inner, label="DynamicContent")
        self._dynamic_label.Disable()
        self._dyn_inner_sizer.Add(self._dynamic_label, 0, wx.ALL, 4)
        self._dyn_inner.Layout()
        self.Layout()

    def _hide_label(self) -> None:
        if self._dynamic_label:
            self._dynamic_label.Destroy()
            self._dynamic_label = None
            self._dyn_inner.Layout()
            self.Layout()


if __name__ == "__main__":
    app = wx.App(False)
    TestFrame()
    app.MainLoop()
