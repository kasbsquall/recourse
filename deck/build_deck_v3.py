"""Build deck_v3.pdf from deck_v3.html (legible conversation + verdict crops).
Leaves the v1 deck.pdf untouched. Also writes per-slide PNGs to deck/preview_v3/
and reports any slide that overflows 1280x720.

Run:  uv run --with playwright python deck/build_deck_v3.py
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

html = (HERE / "deck_v3.html").read_text(encoding="utf-8").replace("<!--LOGO_LIGHT-->", svg_light)
built = HERE / "deck_v3_built.html"
built.write_text(html, encoding="utf-8")

prev = HERE / "preview_v3"
prev.mkdir(exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(device_scale_factor=2).new_page()
    pg.goto(built.as_uri(), wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(700)

    slides = pg.locator("section.slide")
    n = slides.count()
    overflow = pg.evaluate(
        """() => [...document.querySelectorAll('section.slide')].map((s,i)=>(
            {i:i+1, w:s.scrollWidth, h:s.scrollHeight}
        )).filter(o => o.w>1280 || o.h>720)"""
    )
    for i in range(n):
        slides.nth(i).screenshot(path=str(prev / f"slide_{i + 1}.png"))

    pg.pdf(path=str(HERE / "deck_v3.pdf"), width="1280px", height="720px",
           print_background=True, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()

print(f"deck_v3.pdf + {n} preview PNGs -> {HERE}")
print("OVERFLOW:", overflow if overflow else "none — all slides fit 1280x720")
