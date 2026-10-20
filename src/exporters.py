"""Export box panels to SVG and DXF, tiled into a single sheet."""

from __future__ import annotations

from typing import List, Tuple

from boxgen import Panel

MARGIN = 10.0   # gap between panels (mm)
STROKE = 0.2    # cut-line width in SVG (mm)


def _bounds(panel: Panel) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in panel.points]
    ys = [p[1] for p in panel.points]
    return min(xs), min(ys), max(xs), max(ys)


def _layout(panels: List[Panel]) -> Tuple[List[Tuple[Panel, float, float]], float, float]:
    """Pack panels left-to-right in rows; return placements + sheet size."""
    placements: List[Tuple[Panel, float, float]] = []
    x_cursor = MARGIN
    y_cursor = MARGIN
    row_h = 0.0
    sheet_w = 0.0
    max_row_w = 800.0
    for panel in panels:
        minx, miny, maxx, maxy = _bounds(panel)
        w, h = maxx - minx, maxy - miny
        if x_cursor + w > max_row_w and x_cursor > MARGIN:
            x_cursor = MARGIN
            y_cursor += row_h + MARGIN
            row_h = 0.0
        placements.append((panel, x_cursor - minx, y_cursor - miny))
        x_cursor += w + MARGIN
        row_h = max(row_h, h)
        sheet_w = max(sheet_w, x_cursor)
    sheet_h = y_cursor + row_h + MARGIN
    return placements, sheet_w, sheet_h


def to_svg(panels: List[Panel]) -> str:
    placements, w, h = _layout(panels)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.2f}mm" height="{h:.2f}mm" '
        f'viewBox="0 0 {w:.2f} {h:.2f}">',
        f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" fill="white"/>',
    ]
    for panel, ox, oy in placements:
        pts = " ".join(f"{x + ox:.3f},{y + oy:.3f}" for x, y in panel.points)
        parts.append(
            f'<polygon points="{pts}" fill="none" '
            f'stroke="#d00" stroke-width="{STROKE}"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def to_dxf(panels: List[Panel]) -> str:
    """Minimal DXF with one LWPOLYLINE per panel (R12-compatible)."""
    placements, _, _ = _layout(panels)
    out: List[str] = ["0", "SECTION", "2", "ENTITIES"]
    for panel, ox, oy in placements:
        out += ["0", "LWPOLYLINE", "8", "CUT", "90",
                str(len(panel.points)), "70", "1"]
        for x, y in panel.points:
            out += ["10", f"{x + ox:.4f}", "20", f"{y + oy:.4f}"]
    out += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(out) + "\n"
