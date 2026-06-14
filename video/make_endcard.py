"""Render the Recourse brand end-card (1920x1080) to assets/endcard.png.
Neo-brutalist 'Verdict' look: near-black field, heavy wordmark, signal-yellow bar, mono URL.

Run:  uv run --with pillow python video/make_endcard.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent / "assets" / "endcard.png"
W, H = 1920, 1080

BG = (11, 11, 12)
WHITE = (245, 245, 247)
GRAY = (161, 161, 170)
YELLOW = (245, 217, 10)
CYAN = (34, 211, 238)

F = "C:/Windows/Fonts"
eyebrow = ImageFont.truetype(f"{F}/arialbd.ttf", 30)
tagline = ImageFont.truetype(f"{F}/arial.ttf", 50)
url_font = ImageFont.truetype(f"{F}/consolab.ttf", 40)

LOGO = Path(__file__).parent / "assets" / "logo.png"


def center(draw, text, font, y, fill, tracking=0):
    if tracking:
        widths = [draw.textlength(c, font=font) for c in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = (W - total) / 2
        for c, w in zip(text, widths):
            draw.text((x, y), c, font=font, fill=fill)
            x += w + tracking
    else:
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # faint dot-grid texture (brand background)
    for gy in range(120, H - 120, 46):
        for gx in range(160, W - 160, 46):
            d.point((gx, gy), fill=(28, 28, 32))

    center(d, "AI ADJUDICATION, ON THE RECORD", eyebrow, 360, GRAY, tracking=10)

    # real brand wordmark (rendered from RecourseLogo.tsx -> assets/logo.png)
    logo = Image.open(LOGO).convert("RGBA")
    lw = 1040
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, ((W - lw) // 2, 432), logo)

    bar_w = 300
    bar_y = 432 + lh + 56
    d.rectangle([(W - bar_w) / 2, bar_y, (W + bar_w) / 2, bar_y + 16], fill=YELLOW)

    center(d, "Every claim deserves a fair fight.", tagline, bar_y + 64, GRAY)

    url = "recourseband.duckdns.org"
    uw = d.textlength(url, font=url_font)
    pad_x, pad_y = 34, 18
    url_y = bar_y + 138
    bx0, by0 = (W - uw) / 2 - pad_x, url_y
    bx1, by1 = (W + uw) / 2 + pad_x, url_y + 40 + pad_y * 2
    d.rectangle([bx0, by0, bx1, by1], outline=CYAN, width=3)
    d.text(((W - uw) / 2, by0 + pad_y - 2), url, font=url_font, fill=CYAN)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print("endcard ->", OUT)


if __name__ == "__main__":
    main()
