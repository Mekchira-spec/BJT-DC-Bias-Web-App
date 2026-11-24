"""Pure helpers that turn simulation arrays into server-rendered SVG charts.

No JavaScript and no simulator access live here — only coordinate mapping and
tick formatting, so the result can be unit-tested and rendered by Jinja.
"""

from __future__ import annotations

import math

VIEW_W = 640
VIEW_H = 260
PLOT_LEFT = 58
PLOT_RIGHT = 624
PLOT_TOP = 16
PLOT_BOTTOM = 220


def _short(value: float) -> str:
    if value == 0:
        return "0"
    magnitude = abs(value)
    for suffix, scale in (("M", 1e6), ("k", 1e3), ("", 1.0), ("m", 1e-3), ("u", 1e-6), ("n", 1e-9)):
        if magnitude >= scale:
            scaled = value / scale
            return f"{scaled:.3g}{suffix}"
    return f"{value:.3g}"


def _domain(values: list[float]) -> tuple[float, float]:
    low, high = min(values), max(values)
    if math.isclose(low, high):
        padding = abs(low) * 0.05 or 1.0
        return low - padding, high + padding
    return low, high


def make_chart(
    title: str,
    xlabel: str,
    ylabel: str,
    series: list[dict],
    logx: bool = False,
    count: int = 6,
) -> dict:
    """Build a chart description with pixel-space polylines and ticks.

    ``series`` is a list of ``{"name", "color", "x": [...], "y": [...]}``.
    """
    if not series or not series[0]["x"]:
        raise ValueError("chart needs at least one non-empty series")
    xs = [float(value) for item in series for value in item["x"]]
    ys = [float(value) for item in series for value in item["y"]]
    if logx and any(value <= 0 for value in xs):
        raise ValueError("logx needs strictly positive x values")

    if logx:
        domain_x = [math.log10(value) for value in xs]
    else:
        domain_x = xs
    xmin, xmax = _domain(domain_x)
    ymin, ymax = _domain(ys)

    def to_px(x: float, y: float) -> tuple[float, float]:
        scaled_x = math.log10(x) if logx else x
        px = PLOT_LEFT + (scaled_x - xmin) / (xmax - xmin) * (PLOT_RIGHT - PLOT_LEFT)
        py = PLOT_BOTTOM - (y - ymin) / (ymax - ymin) * (PLOT_BOTTOM - PLOT_TOP)
        return px, py

    polylines = []
    for item in series:
        coordinates = [
            f"{px:.1f},{py:.1f}"
            for x, y in zip(item["x"], item["y"])
            for px, py in [to_px(float(x), float(y))]
        ]
        polylines.append(
            {"name": item["name"], "color": item["color"], "points": " ".join(coordinates)}
        )

    xticks = []
    yticks = []
    for index in range(count + 1):
        ratio = index / count
        raw_x = xmin + ratio * (xmax - xmin)
        value_x = 10**raw_x if logx else raw_x
        px = PLOT_LEFT + ratio * (PLOT_RIGHT - PLOT_LEFT)
        xticks.append({"x": round(px, 1), "label": _short(value_x)})

        value_y = ymin + ratio * (ymax - ymin)
        py = PLOT_BOTTOM - ratio * (PLOT_BOTTOM - PLOT_TOP)
        yticks.append({"y": round(py, 1), "label": _short(value_y)})

    return {
        "title": title,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "polylines": polylines,
        "xticks": xticks,
        "yticks": yticks,
        "plot": {
            "left": PLOT_LEFT,
            "right": PLOT_RIGHT,
            "top": PLOT_TOP,
            "bottom": PLOT_BOTTOM,
        },
        "view_w": VIEW_W,
        "view_h": VIEW_H,
    }
