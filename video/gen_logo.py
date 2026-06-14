"""Render the REAL Recourse wordmark (from frontend/components/RecourseLogo.tsx) to a
transparent PNG, so the video end-card uses the brand logo instead of a placeholder.

Run:  uv run --with playwright python video/gen_logo.py
"""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TSX = ROOT / "frontend" / "components" / "RecourseLogo.tsx"
OUT = Path(__file__).parent / "assets" / "logo.png"

# Pull every <path .../> out of the component and rebuild a clean standalone SVG.
paths = re.findall(r"<path\b[^>]*/>", TSX.read_text(encoding="utf-8"))
# Dark letters use currentColor -> render them white for the dark end-card.
paths = [p.replace('fill="currentColor"', 'fill="#f5f5f7"') for p in paths]

WIDTH = 1480
svg = (
    f'<svg viewBox="0 0 4597 488" width="{WIDTH}" '
    f'xmlns="http://www.w3.org/2000/svg">{"".join(paths)}</svg>'
)
html = f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}'\
       f'#w{{display:inline-block}}</style><div id="w">{svg}</div>'

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(device_scale_factor=2).new_page()
    pg.set_content(html)
    pg.locator("#w").screenshot(path=str(OUT), omit_background=True)
    b.close()

print("logo ->", OUT, f"({len(paths)} paths)")
