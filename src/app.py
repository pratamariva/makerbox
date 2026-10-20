"""MakerBox — a MakerCase-style finger-joint box generator (desktop GUI).

Enter outside dimensions, material thickness and joint settings; preview
the flat panel layout live; export a laser-ready SVG or DXF. Supports an
open-top box and egg-crate dividers.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from boxgen import BoxParams, generate
from exporters import to_dxf, to_svg, _layout

PREVIEW_W = 640
PREVIEW_H = 360
PAD = 8


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MakerBox — Finger-Joint Box Generator")
        self.resizable(True, True)
        self.vars: dict[str, tk.Variable] = {}
        self._build_controls()
        self._build_preview()
        self.refresh()

    # ---- UI construction -------------------------------------------------
    def _build_controls(self) -> None:
        frm = ttk.Frame(self, padding=PAD)
        frm.grid(row=0, column=0, sticky="ns")

        def add_num(label: str, key: str, default: float, row: int) -> None:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=default)
            self.vars[key] = var
            ent = ttk.Entry(frm, textvariable=var, width=10)
            ent.grid(row=row, column=1, sticky="e", pady=1)
            var.trace_add("write", lambda *_: self.refresh())

        r = 0
        ttk.Label(frm, text="Outside dimensions (mm)",
                  font=("", 10, "bold")).grid(row=r, column=0, columnspan=2,
                                              sticky="w", pady=(0, 2))
        r += 1
        for lbl, key, dv in (("Width (W)", "width", 150.0),
                             ("Depth (D)", "depth", 100.0),
                             ("Height (H)", "height", 60.0)):
            add_num(lbl, key, dv, r); r += 1

        ttk.Separator(frm, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r += 1
        ttk.Label(frm, text="Material & joints",
                  font=("", 10, "bold")).grid(row=r, column=0, columnspan=2,
                                              sticky="w"); r += 1
        for lbl, key, dv in (("Thickness (t)", "thickness", 3.0),
                             ("Kerf", "kerf", 0.1),
                             ("Finger width", "finger", 12.0)):
            add_num(lbl, key, dv, r); r += 1

        self.vars["open_top"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Open top (no lid)",
                        variable=self.vars["open_top"],
                        command=self.refresh).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(4, 0)); r += 1

        ttk.Separator(frm, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r += 1
        self.vars["dividers"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text="Add dividers",
                        variable=self.vars["dividers"],
                        command=self.refresh).grid(
            row=r, column=0, columnspan=2, sticky="w"); r += 1
        for lbl, key, dv in (("Columns (W)", "cols", 2),
                             ("Rows (D)", "rows", 2)):
            ttk.Label(frm, text=lbl).grid(row=r, column=0, sticky="w")
            var = tk.IntVar(value=dv)
            self.vars[key] = var
            ttk.Spinbox(frm, from_=1, to=20, textvariable=var, width=8,
                        command=self.refresh).grid(row=r, column=1,
                                                   sticky="e", pady=1)
            var.trace_add("write", lambda *_: self.refresh())
            r += 1

        ttk.Separator(frm, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6); r += 1
        ttk.Button(frm, text="Export SVG…",
                   command=self.export_svg).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=2); r += 1
        ttk.Button(frm, text="Export DXF…",
                   command=self.export_dxf).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=2); r += 1

        self.status = ttk.Label(frm, text="", foreground="#555",
                                wraplength=180)
        self.status.grid(row=r, column=0, columnspan=2, sticky="w",
                         pady=(8, 0))

    def _build_preview(self) -> None:
        self.canvas = tk.Canvas(self, width=PREVIEW_W, height=PREVIEW_H,
                                bg="white", highlightthickness=1,
                                highlightbackground="#ccc")
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=PAD, pady=PAD)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas.bind("<Configure>", lambda _e: self.refresh())

    # ---- logic -----------------------------------------------------------
    def _params(self) -> BoxParams | None:
        try:
            p = BoxParams(
                width=float(self.vars["width"].get()),
                depth=float(self.vars["depth"].get()),
                height=float(self.vars["height"].get()),
                thickness=float(self.vars["thickness"].get()),
                kerf=float(self.vars["kerf"].get()),
                finger=float(self.vars["finger"].get()),
                open_top=bool(self.vars["open_top"].get()),
                dividers=bool(self.vars["dividers"].get()),
                cols=int(self.vars["cols"].get()),
                rows=int(self.vars["rows"].get()),
            )
        except (tk.TclError, ValueError):
            return None
        t = p.thickness
        if min(p.width, p.depth, p.height) <= 2 * t or t <= 0:
            return None
        return p

    def refresh(self) -> None:
        if not hasattr(self, "canvas"):
            return
        p = self._params()
        self.canvas.delete("all")
        if p is None:
            self.status.config(text="Enter valid dimensions (each > 2×t).")
            return
        placements, w, h = _layout(generate(p))
        cw = max(self.canvas.winfo_width(), 50)
        ch = max(self.canvas.winfo_height(), 50)
        scale = min((cw - 20) / w, (ch - 20) / h)
        ox = (cw - w * scale) / 2
        oy = (ch - h * scale) / 2
        for panel, px, py in placements:
            pts = []
            for x, y in panel.points:
                pts += [ox + (x + px) * scale, oy + (y + py) * scale]
            self.canvas.create_polygon(pts, outline="#d00", fill="",
                                       width=1)
        n = len(placements)
        self.status.config(
            text=f"{n} panels · sheet {w:.0f}×{h:.0f} mm")

    def _export(self, kind: str) -> None:
        p = self._params()
        if p is None:
            messagebox.showerror("MakerBox", "Fix the dimensions first.")
            return
        ext = ".svg" if kind == "svg" else ".dxf"
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(kind.upper(), f"*{ext}")],
            initialfile=f"box_{int(p.width)}x{int(p.depth)}x{int(p.height)}{ext}",
        )
        if not path:
            return
        data = to_svg(generate(p)) if kind == "svg" else to_dxf(generate(p))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(data)
        self.status.config(text=f"Saved {path.split('/')[-1]}")

    def export_svg(self) -> None:
        self._export("svg")

    def export_dxf(self) -> None:
        self._export("dxf")


if __name__ == "__main__":
    App().mainloop()
