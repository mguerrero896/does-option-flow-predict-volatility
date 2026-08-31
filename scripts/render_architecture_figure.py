"""Render the README architecture figure from the delivered Archify artifact.

The diagram is authored as `docs/figures/architecture.json` and delivered by Archify as a
self-contained interactive page. That page is built for a browser: it carries a viewer
chrome, a background, and a theme that follows the reader. A README needs the opposite —
one static image, cropped to its own content, in a fixed theme.

This extracts the inline SVG and the stylesheet it depends on, mounts them in the viewer's
own embed mode (which drops the background and padding), and screenshots the result at 2x.
Keeping it as a script rather than a shell incantation is the point: the published PNG is
regenerable from the committed specification instead of being a hand-made artefact nobody
can reproduce.

    uv run python scripts/render_architecture_figure.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "figures" / "architecture.html"
TARGET = REPO / "docs" / "figures" / "architecture.png"

#: Chrome renders the page; Archify already requires it for its own visual check.
CHROME_CANDIDATES = (
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
)

#: Device scale. The README displays the image near 880 CSS pixels; rendering at 2x keeps
#: the text crisp on high-density screens without inflating the file beyond ~100 kB.
SCALE = 2

#: Breathing room around the drawing, in SVG units.
MARGIN = 8


def _chrome() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.is_file():
            return candidate
    found = shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return Path(found)
    raise SystemExit("RENDER_CHROME_MISSING: no Chrome or Chromium executable was found")


def _extract(html: str) -> tuple[str, str, int, int]:
    style = re.search(r"<style[^>]*>(.*?)</style>", html, re.DOTALL)
    svg = re.search(r"<svg\b.*?</svg>", html, re.DOTALL)
    if not style or not svg:
        raise SystemExit("RENDER_SOURCE_UNPARSEABLE: the delivered page has no inline SVG")
    box = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg.group(0))
    if not box:
        raise SystemExit("RENDER_VIEWBOX_MISSING: the SVG declares no origin viewBox")
    return style.group(1), svg.group(0), int(box.group(1)), int(box.group(2))


def _page(style: str, svg: str, width: int, height: int) -> str:
    """Mount the drawing alone.

    `data-embed="true"` is the viewer's own switch for this: it removes the page
    background and padding, so the capture is the diagram and nothing else. The theme is
    pinned to light because a PNG cannot follow the reader's preference.
    """
    return (
        '<!doctype html><html lang="en" data-theme="light" data-preset="classic" '
        'data-embed="true"><head><meta charset="utf-8">'
        f"<style>{style}</style>"
        "<style>html,body{margin:0;padding:0;background:#fff;background-image:none}"
        f"svg{{display:block;width:{width}px;height:{height}px}}</style>"
        f"</head><body>{svg}</body></html>"
    )


def main() -> int:
    if not SOURCE.is_file():
        raise SystemExit(f"RENDER_SOURCE_MISSING: {SOURCE.relative_to(REPO).as_posix()}")

    style, svg, width, height = _extract(SOURCE.read_text(encoding="utf-8"))

    # The viewer paints a grid behind the drawing for orientation while panning. A static
    # image has nothing to pan, so the grid is only noise competing with the labels.
    svg = re.sub(r'<rect width="100%" height="100%" fill="url\(#grid\)"\s*/>', "", svg, count=1)

    # Trim the authored padding so the image is the drawing, not a frame around it.
    cropped = re.sub(
        r'viewBox="0 0 \d+ \d+"',
        f'viewBox="{MARGIN} {MARGIN} {width - 2 * MARGIN} {height - 2 * MARGIN}"',
        svg,
        count=1,
    )
    view_width, view_height = width - 2 * MARGIN, height - 2 * MARGIN

    with tempfile.TemporaryDirectory() as directory:
        page = Path(directory) / "figure.html"
        page.write_text(_page(style, cropped, view_width, view_height), encoding="utf-8")
        result = subprocess.run(
            [
                str(_chrome()),
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--force-device-scale-factor={SCALE}",
                f"--window-size={view_width},{view_height}",
                "--default-background-color=ffffffff",
                f"--screenshot={TARGET}",
                page.as_uri(),
            ],
            capture_output=True,
            text=True,
        )

    if result.returncode or not TARGET.is_file():
        sys.stderr.write(result.stderr)
        raise SystemExit(f"RENDER_FAILED: chrome exited {result.returncode}")

    print(
        f"[figure] {TARGET.relative_to(REPO).as_posix()} "
        f"{view_width}x{view_height} at {SCALE}x, {TARGET.stat().st_size} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
