"""RPA.Windows test application.

A self-contained tkinter GUI that exposes every control type exercised by
the RPA.Windows test suite:

    - Buttons (normal, disabled)
    - Checkboxes  (checked / unchecked / indeterminate tri-state)
    - Radio buttons
    - Text entry / multi-line text
    - Combobox (dropdown)
    - Listbox
    - Slider (Scale)
    - Spinner (Spinbox)
    - Labels (static and dynamic status)
    - Notebook (tabs) — useful for path: locator tests
    - Treeview table

Usage
-----
Run directly::

    python testapp.py

Or from Robot Framework test setup::

    Start Process    python    ${RESOURCES}/testapp.py    alias=testapp
    # give it time to appear
    Sleep    1s

The window title is "RPA Windows Test App" and the app stays open until
the "Quit" button or the window close button is pressed.
"""

import tkinter as tk
from tkinter import ttk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _section(parent: tk.Widget, title: str) -> ttk.LabelFrame:
    frame = ttk.LabelFrame(parent, text=title, padding=8)
    return frame


# ---------------------------------------------------------------------------
# Tab builders
# ---------------------------------------------------------------------------

def _build_tab_basic(nb: ttk.Notebook, status_var: tk.StringVar) -> None:
    """Buttons, checkboxes, radio buttons."""
    tab = ttk.Frame(nb, padding=10)
    nb.add(tab, text="Basic Controls")

    # --- Buttons ------------------------------------------------------------
    btn_frame = _section(tab, "Buttons")
    btn_frame.pack(fill="x", pady=4)

    ttk.Button(
        btn_frame,
        text="Click Me",
        name="btn_click_me",
        command=lambda: status_var.set("Button 'Click Me' pressed"),
    ).grid(row=0, column=0, padx=4, pady=4)

    ttk.Button(
        btn_frame,
        text="Action Button",
        name="btn_action",
        command=lambda: status_var.set("Button 'Action Button' pressed"),
    ).grid(row=0, column=1, padx=4, pady=4)

    disabled_btn = ttk.Button(btn_frame, text="Disabled Button", name="btn_disabled")
    disabled_btn.state(["disabled"])
    disabled_btn.grid(row=0, column=2, padx=4, pady=4)

    # --- Checkboxes ---------------------------------------------------------
    chk_frame = _section(tab, "Checkboxes")
    chk_frame.pack(fill="x", pady=4)

    chk_checked_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(
        chk_frame,
        text="Checked",
        name="chk_checked",
        variable=chk_checked_var,
        command=lambda: status_var.set(f"Checked: {chk_checked_var.get()}"),
    ).grid(row=0, column=0, sticky="w", padx=4, pady=2)

    chk_unchecked_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        chk_frame,
        text="Unchecked",
        name="chk_unchecked",
        variable=chk_unchecked_var,
        command=lambda: status_var.set(f"Unchecked: {chk_unchecked_var.get()}"),
    ).grid(row=1, column=0, sticky="w", padx=4, pady=2)

    # Tri-state / indeterminate checkbox — tkinter represents this with a
    # StringVar where "" means indeterminate, "1" = on, "0" = off.
    chk_tri_var = tk.StringVar(value="")
    chk_tri = ttk.Checkbutton(
        chk_frame,
        text="Indeterminate (tri-state)",
        name="chk_indeterminate",
        variable=chk_tri_var,
        onvalue="1",
        offvalue="0",
        command=lambda: status_var.set(f"Tri-state value: '{chk_tri_var.get()}'"),
    )
    chk_tri.state(["alternate"])  # start in indeterminate visual state
    chk_tri.grid(row=2, column=0, sticky="w", padx=4, pady=2)

    # --- Radio buttons ------------------------------------------------------
    radio_frame = _section(tab, "Radio Buttons")
    radio_frame.pack(fill="x", pady=4)

    radio_var = tk.StringVar(value="Option A")
    for col, opt in enumerate(("Option A", "Option B", "Option C")):
        ttk.Radiobutton(
            radio_frame,
            text=opt,
            name=f"radio_{opt.replace(' ', '_').lower()}",
            variable=radio_var,
            value=opt,
            command=lambda v=opt: status_var.set(f"Radio selected: {v}"),
        ).grid(row=0, column=col, padx=8)


def _build_tab_input(nb: ttk.Notebook, status_var: tk.StringVar) -> None:
    """Entry, combobox, slider, spinbox."""
    tab = ttk.Frame(nb, padding=10)
    nb.add(tab, text="Input Controls")

    # --- Text entry ---------------------------------------------------------
    entry_frame = _section(tab, "Text Entry")
    entry_frame.pack(fill="x", pady=4)

    ttk.Label(entry_frame, text="Single-line:").grid(row=0, column=0, sticky="w", padx=4)
    entry_single = ttk.Entry(entry_frame, name="entry_single", width=30)
    entry_single.insert(0, "Hello RPA")
    entry_single.grid(row=0, column=1, padx=4, pady=2)

    ttk.Label(entry_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=4)
    entry_pwd = ttk.Entry(entry_frame, name="entry_password", show="*", width=30)
    entry_pwd.grid(row=1, column=1, padx=4, pady=2)

    ttk.Label(entry_frame, text="Multi-line:").grid(row=2, column=0, sticky="nw", padx=4)
    text_multi = tk.Text(entry_frame, name="text_multiline", width=30, height=4)
    text_multi.insert("1.0", "Line 1\nLine 2\n")
    text_multi.grid(row=2, column=1, padx=4, pady=2)

    # --- Combobox -----------------------------------------------------------
    combo_frame = _section(tab, "Combobox")
    combo_frame.pack(fill="x", pady=4)

    ttk.Label(combo_frame, text="Select fruit:").grid(row=0, column=0, sticky="w", padx=4)
    combo = ttk.Combobox(
        combo_frame,
        name="combo_fruit",
        values=["Apple", "Banana", "Cherry", "Date", "Elderberry"],
        state="readonly",
        width=20,
    )
    combo.set("Apple")
    combo.grid(row=0, column=1, padx=4, pady=4)
    combo.bind(
        "<<ComboboxSelected>>",
        lambda e: status_var.set(f"Combo selected: {combo.get()}"),
    )

    # --- Slider -------------------------------------------------------------
    slider_frame = _section(tab, "Slider")
    slider_frame.pack(fill="x", pady=4)

    slider_var = tk.IntVar(value=50)
    ttk.Label(slider_frame, text="Volume:").grid(row=0, column=0, sticky="w", padx=4)
    slider = ttk.Scale(
        slider_frame,
        name="slider_volume",
        from_=0,
        to=100,
        orient="horizontal",
        variable=slider_var,
        length=200,
        command=lambda v: status_var.set(f"Slider: {int(float(v))}"),
    )
    slider.grid(row=0, column=1, padx=4, pady=4)
    slider_label = ttk.Label(slider_frame, textvariable=slider_var, width=4)
    slider_label.grid(row=0, column=2, padx=4)

    # --- Spinbox ------------------------------------------------------------
    spin_frame = _section(tab, "Spinbox")
    spin_frame.pack(fill="x", pady=4)

    ttk.Label(spin_frame, text="Quantity:").grid(row=0, column=0, sticky="w", padx=4)
    spin = ttk.Spinbox(
        spin_frame,
        name="spin_quantity",
        from_=0,
        to=99,
        width=8,
        command=lambda: status_var.set(f"Spinbox: {spin.get()}"),
    )
    spin.set(5)
    spin.grid(row=0, column=1, padx=4, pady=4)


def _build_tab_list(nb: ttk.Notebook, status_var: tk.StringVar) -> None:
    """Listbox and treeview table."""
    tab = ttk.Frame(nb, padding=10)
    nb.add(tab, text="List & Table")

    # --- Listbox ------------------------------------------------------------
    list_frame = _section(tab, "Listbox")
    list_frame.pack(fill="x", pady=4)

    listbox = tk.Listbox(list_frame, name="listbox_items", height=5, selectmode="single")
    for item in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon"):
        listbox.insert(tk.END, item)
    listbox.select_set(0)
    listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
    listbox.bind(
        "<<ListboxSelect>>",
        lambda e: status_var.set(
            f"Listbox: {listbox.get(listbox.curselection()[0])}"
            if listbox.curselection()
            else ""
        ),
    )

    sb = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
    listbox.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")

    # --- Treeview table -----------------------------------------------------
    tree_frame = _section(tab, "Table (Treeview)")
    tree_frame.pack(fill="both", expand=True, pady=4)

    columns = ("name", "department", "salary")
    tree = ttk.Treeview(
        tree_frame,
        name="tree_employees",
        columns=columns,
        show="headings",
        height=5,
    )
    for col, heading in zip(columns, ("Name", "Department", "Salary")):
        tree.heading(col, text=heading)
        tree.column(col, width=120)

    rows = [
        ("Alice", "Engineering", "90000"),
        ("Bob", "Marketing", "75000"),
        ("Carol", "Engineering", "95000"),
        ("Dave", "HR", "65000"),
        ("Eve", "Engineering", "88000"),
    ]
    for row in rows:
        tree.insert("", tk.END, values=row)

    tree.pack(fill="both", expand=True, padx=4, pady=4)
    tree.bind(
        "<<TreeviewSelect>>",
        lambda e: status_var.set(
            f"Table row: {tree.item(tree.focus(), 'values')}"
        ),
    )


def _build_tab_dynamic(nb: ttk.Notebook, status_var: tk.StringVar) -> None:
    """Controls that appear/disappear on demand — useful for testing timeout."""
    tab = ttk.Frame(nb, padding=10)
    nb.add(tab, text="Dynamic Controls")

    dyn_frame = _section(tab, "Delayed Element")
    dyn_frame.pack(fill="x", pady=4)

    placeholder = ttk.Frame(dyn_frame, name="dynamic_placeholder", height=40)
    placeholder.pack(fill="x", padx=4, pady=4)

    _hidden_label: list[ttk.Label] = []

    def _show_label(delay_ms: int) -> None:
        if _hidden_label:
            _hidden_label[0].destroy()
            _hidden_label.clear()
        status_var.set(f"Label will appear in {delay_ms // 1000}s...")

        def _create() -> None:
            lbl = ttk.Label(
                placeholder,
                name="dynamic_label",
                text="I appeared after the delay!",
            )
            lbl.pack()
            _hidden_label.append(lbl)
            status_var.set("Dynamic label is now visible.")

        tab.after(delay_ms, _create)

    def _hide_label() -> None:
        if _hidden_label:
            _hidden_label[0].destroy()
            _hidden_label.clear()
            status_var.set("Dynamic label hidden.")

    btn_row = ttk.Frame(dyn_frame)
    btn_row.pack(padx=4, pady=4)
    ttk.Button(btn_row, text="Show after 1s",
               command=lambda: _show_label(1000)).pack(side="left", padx=4)
    ttk.Button(btn_row, text="Show after 3s",
               command=lambda: _show_label(3000)).pack(side="left", padx=4)
    ttk.Button(btn_row, text="Hide",
               command=_hide_label).pack(side="left", padx=4)

    info = ttk.Label(
        dyn_frame,
        text=(
            "Use 'Show after Xs' then locate 'name:dynamic_label' with a matching\n"
            "timeout to exercise the path: timeout fix (issue #1125)."
        ),
        foreground="gray",
    )
    info.pack(padx=4, pady=4)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

def build_app() -> tk.Tk:
    root = tk.Tk()
    root.title("RPA Windows Test App")
    root.resizable(True, True)
    root.minsize(520, 440)

    # Main notebook
    nb = ttk.Notebook(root, name="notebook_main")
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    # Status bar
    status_var = tk.StringVar(value="Ready")
    status_bar = ttk.Label(
        root,
        name="lbl_status",
        textvariable=status_var,
        relief="sunken",
        anchor="w",
        padding=(4, 2),
    )
    status_bar.pack(fill="x", side="bottom")

    # Build tabs
    _build_tab_basic(nb, status_var)
    _build_tab_input(nb, status_var)
    _build_tab_list(nb, status_var)
    _build_tab_dynamic(nb, status_var)

    # Quit button
    ttk.Button(
        root,
        text="Quit",
        name="btn_quit",
        command=root.destroy,
    ).pack(side="bottom", pady=4)

    return root


if __name__ == "__main__":
    app = build_app()
    app.mainloop()
