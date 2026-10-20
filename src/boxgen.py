"""Finger-joint box geometry generator (MakerCase Basic Box + dividers).

Produces 2D panel outlines for a laser-cut rectangular box with finger
(box) joints, plus optional egg-crate dividers. Output is a list of
panels, each a closed polyline of (x, y) points in millimetres, which
can be exported to SVG or DXF.

Convention (outside dimensions W x D x H, material thickness t):
  - base & top panels are (W-2t) x (D-2t), MALE on all four edges
  - front/back walls are (W-2t) x (H-2t), FEMALE top/bottom, MALE sides
  - left/right walls are (D-2t) x (H-2t), FEMALE on all four edges
Mating edges always share a length, so they share a finger count and
interlock exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

Point = Tuple[float, float]

MIN_FINGERS = 3


@dataclass
class Panel:
    name: str
    points: List[Point] = field(default_factory=list)

    @property
    def width(self) -> float:
        xs = [p[0] for p in self.points]
        return max(xs) - min(xs)

    @property
    def height(self) -> float:
        ys = [p[1] for p in self.points]
        return max(ys) - min(ys)


@dataclass
class BoxParams:
    width: float = 150.0        # W (x), outside
    depth: float = 100.0        # D (y), outside
    height: float = 60.0        # H (z), outside
    thickness: float = 3.0      # material thickness t
    kerf: float = 0.0           # cut width compensation
    finger: float = 12.0        # target finger width
    open_top: bool = False      # omit the top panel
    dividers: bool = False
    cols: int = 1               # compartments along width (x)
    rows: int = 1               # compartments along depth (y)


def _odd_finger_count(length: float, target: float) -> int:
    """Pick an odd number of fingers so both ends are tabs."""
    n = max(MIN_FINGERS, int(round(length / max(target, 0.1))))
    if n % 2 == 0:
        n += 1
    return n


def _edge(p0: Point, p1: Point, normal: Point, etype: str,
          n: int, t: float, kerf: float) -> List[Point]:
    """Return points walking from p0 (exclusive) to p1 (inclusive).

    etype: 'male' (tabs protrude +t), 'female' (notches cut -t), 'flat'.
    """
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / length, dy / length
    nx, ny = normal

    pts: List[Point] = []
    cx, cy = x0, y0

    def move(along: float, out: float) -> None:
        nonlocal cx, cy
        cx += ux * along + nx * out
        cy += uy * along + ny * out
        pts.append((cx, cy))

    if etype == "flat":
        move(length, 0.0)
        return pts

    span = length - 2 * t
    fw = span / n
    move(t, 0.0)                      # corner clearance
    for i in range(n):
        engaged = (i % 2 == 0)        # ends (i=0, i=n-1) are engaged
        run = fw + (kerf if engaged else -kerf)
        if etype == "male" and engaged:
            move(0.0, t)              # push out
            move(run, 0.0)
            move(0.0, -t)             # pull back
        elif etype == "female" and engaged:
            move(0.0, -t)             # cut in
            move(run, 0.0)
            move(0.0, t)
        else:
            move(run, 0.0)            # flat gap
    move(t, 0.0)                      # corner clearance
    return pts


def _rect_panel(name: str, pw: float, ph: float, t: float, kerf: float,
                target: float, bottom: str, right: str,
                top: str, left: str) -> Panel:
    """Build a rectangular panel pw x ph with per-edge joint types.

    Edge type is one of 'male', 'female', 'flat'. Walked CCW.
    """
    nb = _odd_finger_count(pw, target)
    nr = _odd_finger_count(ph, target)
    corners = [(0.0, 0.0), (pw, 0.0), (pw, ph), (0.0, ph)]
    normals = [(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]
    types = [bottom, right, top, left]
    counts = [nb, nr, nb, nr]

    points: List[Point] = [corners[0]]
    for i in range(4):
        p0 = corners[i]
        p1 = corners[(i + 1) % 4]
        points += _edge(p0, p1, normals[i], types[i], counts[i], t, kerf)
    return Panel(name, points)


def _divider_panel(name: str, length: float, h: float, t: float,
                   crossings: int, from_top: bool) -> Panel:
    """A plain divider strip with evenly spaced half-height slots.

    Slots are cut from the top edge (from_top) or the bottom edge, so two
    sets interlock egg-crate style.
    """
    slot_depth = h / 2.0
    pts: List[Point] = [(0.0, 0.0)]
    # bottom edge left->right
    if not from_top:
        pts += _slotted_edge(length, crossings, t, slot_depth, +1)
    else:
        pts.append((length, 0.0))
    pts.append((length, h))                       # right edge up
    # top edge right->left
    if from_top:
        pts += _slotted_edge(length, crossings, t, slot_depth, -1,
                             reverse=True, y=h)
    else:
        pts.append((0.0, h))
    pts.append((0.0, 0.0))                        # left edge down
    return Panel(name, pts)


def _slotted_edge(length: float, crossings: int, t: float,
                  depth: float, direction: int, reverse: bool = False,
                  y: float = 0.0) -> List[Point]:
    """Points along a horizontal edge with `crossings` rectangular slots.

    direction +1 cuts upward (from bottom), -1 cuts downward (from top).
    """
    centers = [length * (k + 1) / (crossings + 1) for k in range(crossings)]
    pts: List[Point] = []
    xs = sorted(centers, reverse=reverse)
    cursor = length if reverse else 0.0
    for c in xs:
        a = c - t / 2.0
        b = c + t / 2.0
        if reverse:
            pts.append((b, y))
            pts.append((b, y + direction * depth))
            pts.append((a, y + direction * depth))
            pts.append((a, y))
        else:
            pts.append((a, y))
            pts.append((a, y + direction * depth))
            pts.append((b, y + direction * depth))
            pts.append((b, y))
    pts.append((0.0 if reverse else length, y))
    return pts


def generate(p: BoxParams) -> List[Panel]:
    t, k, f = p.thickness, p.kerf, p.finger
    bw, bd = p.width - 2 * t, p.depth - 2 * t     # base footprint
    wh = p.height - 2 * t                         # wall interior height

    panels: List[Panel] = [
        _rect_panel("base", bw, bd, t, k, f,
                    "male", "male", "male", "male"),
        _rect_panel("front", bw, wh, t, k, f,
                    "female", "male", "female", "male"),
        _rect_panel("back", bw, wh, t, k, f,
                    "female", "male", "female", "male"),
        _rect_panel("left", bd, wh, t, k, f,
                    "female", "female", "female", "female"),
        _rect_panel("right", bd, wh, t, k, f,
                    "female", "female", "female", "female"),
    ]
    if not p.open_top:
        panels.insert(1, _rect_panel("top", bw, bd, t, k, f,
                                     "male", "male", "male", "male"))

    if p.dividers:
        panels += _dividers(p, bw, bd, wh, t)
    return panels


def _dividers(p: BoxParams, bw: float, bd: float, wh: float,
              t: float) -> List[Panel]:
    out: List[Panel] = []
    n_along_x = p.cols - 1     # dividers spanning depth, placed along width
    n_along_y = p.rows - 1     # dividers spanning width, placed along depth
    # width-spanning dividers: slots from TOP, crossings = n_along_x
    for i in range(n_along_y):
        out.append(_divider_panel(f"div_w{i+1}", bw, wh, t,
                                   n_along_x, from_top=True))
    # depth-spanning dividers: slots from BOTTOM, crossings = n_along_y
    for i in range(n_along_x):
        out.append(_divider_panel(f"div_d{i+1}", bd, wh, t,
                                   n_along_y, from_top=False))
    return out
