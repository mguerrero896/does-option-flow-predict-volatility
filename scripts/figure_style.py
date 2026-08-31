"""The project's figure system: one palette, one type scale, one drawing grammar.

Every figure in `docs/figures/` is generated from this module, so the set reads as one
system rather than a pile of pictures made at different times by different tools.

The palette is not invented. It was extracted from this repository's archived predecessor
by counting colour usage across its committed figures: research navy carried the text and
strokes, slate the secondary type, a hairline grey the borders, and a signal amber
appeared only on sealed or focal elements. That last constraint is the important one and
it is kept here — amber marks at most two things per figure, so it still means something.

Drawing rules follow the diagram-design system: a 4-pixel grid, orthogonal connectors with
rounded corners rather than diagonals, every connector label masked and held clear of its
own stroke, and the legend as a strip below the drawing rather than floating inside it.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field

# --- palette -----------------------------------------------------------------------
INK = "#1a2332"
INK_SOFT = "#243044"
MUTED = "#5a6570"
SOFT = "#7a8593"
RULE = "#e1e6ea"
RULE_STRONG = "#c9d2da"
PAPER = "#ffffff"
PAPER_2 = "#f5f7f9"
ACCENT = "#e8a33d"
ACCENT_TINT = "#fdf6ea"
ACCENT_RULE = "#ecd9b6"
LINK = "#123c69"
LINK_TINT = "#eef5fb"

SANS = "'Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'Cascadia Mono','SF Mono',Consolas,monospace"

# --- type scale (4px grid) ---------------------------------------------------------
T_TITLE = 24
T_SUBTITLE = 14
T_NODE = 15
T_SUB = 12
T_TAG = 10
T_EDGE = 11
T_LEGEND = 11


def esc(text: str) -> str:
    return html.escape(text, quote=False)


@dataclass
class Canvas:
    """Accumulates SVG in paint order: rules, then connectors, then nodes, then type."""

    width: int
    height: int
    title: str
    description: str
    slug: str
    under: list[str] = field(default_factory=list)
    over: list[str] = field(default_factory=list)

    def back(self, markup: str) -> None:
        """Painted first: hairlines, plane boundaries, connectors."""
        self.under.append(markup)

    def front(self, markup: str) -> None:
        """Painted last: node boxes and their type."""
        self.over.append(markup)

    def render(self) -> str:
        return "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
                f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
                f'role="img" aria-labelledby="{self.slug}-title {self.slug}-desc">',
                f'<title id="{self.slug}-title">{esc(self.title)}</title>',
                f'<desc id="{self.slug}-desc">{esc(self.description)}</desc>',
                _markers(),
                f'<rect width="100%" height="100%" fill="{PAPER}"/>',
                *self.under,
                *self.over,
                "</svg>",
            ]
        )


def _markers() -> str:
    heads = (("head", MUTED), ("head-accent", ACCENT), ("head-link", LINK))
    out = ["<defs>"]
    for name, colour in heads:
        out.append(
            f'<marker id="{name}" markerWidth="8" markerHeight="6" refX="7" refY="3" '
            f'orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{colour}"/></marker>'
        )
    out.append("</defs>")
    return "".join(out)


def header(canvas: Canvas, eyebrow: str, title: str, subtitle: str, x: int = 32) -> None:
    canvas.front(
        f'<text x="{x}" y="30" fill="{SOFT}" font-family="{MONO}" font-size="{T_TAG}" '
        f'letter-spacing="0.14em">{esc(eyebrow.upper())}</text>'
        f'<text x="{x}" y="62" fill="{INK}" font-family="{SANS}" font-size="{T_TITLE}" '
        f'font-weight="600">{esc(title)}</text>'
        f'<text x="{x}" y="88" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="{T_SUBTITLE}">{esc(subtitle)}</text>'
    )


def node(
    canvas: Canvas,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    sublabel: str = "",
    tag: str = "",
    focal: bool = False,
    quiet: bool = False,
) -> None:
    """One idea, one box. `focal` spends the amber; at most two per figure."""
    if focal:
        fill, stroke, ink = ACCENT_TINT, ACCENT, INK
    elif quiet:
        fill, stroke, ink = PAPER_2, RULE_STRONG, MUTED
    else:
        fill, stroke, ink = PAPER, INK, INK

    cx = x + w // 2
    baseline = y + h // 2 + (0 if not sublabel else -4)
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PAPER}"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.2"/>',
        f'<text x="{cx}" y="{baseline}" fill="{ink}" font-family="{SANS}" '
        f'font-size="{T_NODE}" font-weight="600" text-anchor="middle">{esc(label)}</text>',
    ]
    if sublabel:
        parts.append(
            f'<text x="{cx}" y="{baseline + 20}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="{T_SUB}" text-anchor="middle">{esc(sublabel)}</text>'
        )
    if tag:
        parts.append(
            f'<text x="{x + 12}" y="{y + 18}" fill="{SOFT}" font-family="{MONO}" '
            f'font-size="{T_TAG}" letter-spacing="0.1em">{esc(tag.upper())}</text>'
        )
    canvas.front("".join(parts))


def plane(canvas: Canvas, x: int, y: int, w: int, h: int, label: str, amber: bool = False) -> None:
    """A dashed container marking where something is allowed to exist."""
    stroke = ACCENT if amber else RULE_STRONG
    text = ACCENT if amber else SOFT
    canvas.back(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" '
        f'stroke="{stroke}" stroke-width="1.2" stroke-dasharray="6,5"/>'
        f'<rect x="{x + 16}" y="{y - 8}" width="{8 * len(label) + 16}" height="16" '
        f'fill="{PAPER}"/>'
        f'<text x="{x + 24}" y="{y + 4}" fill="{text}" font-family="{MONO}" '
        f'font-size="{T_TAG}" letter-spacing="0.1em">{esc(label.upper())}</text>'
    )


def arrow_down(
    canvas: Canvas, x: int, y1: int, y2: int, label: str = "", accent: bool = False
) -> None:
    """A vertical connector. Its label sits beside the stroke, never on it."""
    colour = ACCENT if accent else MUTED
    marker = "head-accent" if accent else "head"
    canvas.back(
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{colour}" '
        f'stroke-width="1.6" marker-end="url(#{marker})"/>'
    )
    if label:
        mid = (y1 + y2) // 2
        width = int(6.2 * len(label)) + 16
        canvas.back(
            f'<rect x="{x + 12}" y="{mid - 9}" width="{width}" height="18" rx="3" '
            f'fill="{PAPER}"/>'
            f'<text x="{x + 20}" y="{mid + 4}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="{T_EDGE}">{esc(label)}</text>'
        )


def arrow_right(
    canvas: Canvas, x1: int, x2: int, y: int, label: str = "", accent: bool = False
) -> None:
    colour = ACCENT if accent else MUTED
    marker = "head-accent" if accent else "head"
    canvas.back(
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{colour}" '
        f'stroke-width="1.6" marker-end="url(#{marker})"/>'
    )
    if label:
        mid = (x1 + x2) // 2
        width = int(6.2 * len(label)) + 16
        canvas.back(
            f'<rect x="{mid - width // 2}" y="{y - 28}" width="{width}" height="18" '
            f'rx="3" fill="{PAPER}"/>'
            f'<text x="{mid}" y="{y - 15}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="{T_EDGE}" text-anchor="middle">{esc(label)}</text>'
        )


def legend(canvas: Canvas, y: int, items: list[tuple[str, str]], x: int = 32) -> None:
    """A strip under the drawing. Never floating inside it."""
    canvas.front(
        f'<line x1="{x}" y1="{y - 20}" x2="{canvas.width - x}" y2="{y - 20}" '
        f'stroke="{RULE}" stroke-width="1"/>'
    )
    cursor = x
    for colour, text in items:
        canvas.front(
            f'<rect x="{cursor}" y="{y - 8}" width="12" height="12" rx="3" '
            f'fill="{colour}" stroke="none"/>'
            f'<text x="{cursor + 20}" y="{y + 2}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="{T_LEGEND}">{esc(text)}</text>'
        )
        cursor += 28 + int(6.4 * len(text))


def footnote(canvas: Canvas, y: int, text: str, x: int = 32) -> None:
    canvas.front(
        f'<text x="{x}" y="{y}" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="{T_SUBTITLE}">{esc(text)}</text>'
    )
