"""Inject the real Recourse wordmark into deck.html and render it to deck.pdf (9x 16:9 pages).
Also writes per-slide PNGs to deck/preview/ for visual QA.

Run:  uv run --with playwright python deck/build_deck.py
"""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
ROOT = HERE.parent
TSX = ROOT / "frontend" / "components" / "RecourseLogo.tsx"

paths = re.findall(r"<path\b[^>]*/>", TSX.read_text(encoding="utf-8"))
white = [p.replace('fill="currentColor"', 'fill="#f5f5f7"') for p in paths]
svg_light = (
    '<svg viewBox="0 0 4597 488" width="100%" '
    'xmlns="http://www.w3.org/2000/svg">' + "".join(white) + "</svg>"
)

html = (HERE / "deck.html").read_text(encoding="utf-8").replace("<!--LOGO_LIGHT-->", svg_light)
built = HERE / "deck_built.html"
built.write_text(html, encoding="utf-8")

prev = HERE / "preview"
prev.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(device_scale_factor=2).new_page()
    pg.goto(built.as_uri(), wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(700)

    slides = pg.locator("section.slide")
    n = slides.count()
    for i in range(n):
        slides.nth(i).screenshot(path=str(prev / f"slide_{i + 1}.png"))

    pg.pdf(path=str(HERE / "deck.pdf"), width="1280px", height="720px",
           print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()

print(f"deck.pdf + {n} preview PNGs -> {HERE}")
