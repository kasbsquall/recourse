"""Two YouTube thumbnails (1280x720) — walkthrough + commercial. Big, high-contrast, legible small.

Run:  uv run --with pillow python video/gen_thumbnails.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
PORTRAITS = ROOT / "frontend" / "public" / "agents"
OUT = ROOT / "covers"
OUT.mkdir(exist_ok=True)

W, H = 1280, 720
BG = (11, 11, 12)
WHITE = (245, 245, 247)
GRAY = (165, 165, 174)
YELLOW = (245, 217, 10)
CYAN = (34, 211, 238)
AMBER = (217, 119, 6)

F = "C:/Windows/Fonts"


def font(name, size):
    return ImageFont.truetype(f"{F}/{name}", size)


def dotgrid(d, color, step=34, x0=40, y0=40, x1=W - 40, y1=H - 40):
    for gy in range(y0, y1, step):
        for gx in range(x0, x1, step):
            d.point((gx, gy), fill=color)


def tracked(d, text, fnt, x, y, fill, tracking):
    for c in text:
        d.text((x, y), c, font=fnt, fill=fill)
        x += d.textlength(c, font=fnt) + tracking


def agent_row(img, d, cx, y, size):
    files = [("coordinator.png", False), ("blake.png", False), ("morgan.png", False),
             ("alex.png", False), ("sam.png", False), ("quinn.png", True)]
    gap = 16
    total = len(files) * size + (len(files) - 1) * gap
    x = cx - total // 2
    for f, siu in files:
        ring = AMBER if siu else (60, 60, 66)
        bw = 5 if siu else 3
        d.rectangle([x - bw, y - bw, x + size + bw, y + size + bw], fill=ring)
        por = Image.open(PORTRAITS / f).convert("RGB").resize((size, size), Image.LANCZOS)
        img.paste(por, (x, y))
        x += size + gap


# ---------------- THUMB A · WALKTHROUGH ----------------
def thumb_walkthrough():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    dotgrid(d, (30, 30, 34))
    d.polygon([(60, 52), (60, 80), (86, 66)], fill=CYAN)  # play triangle
    tracked(d, "LIVE WALKTHROUGH", font("consolab.ttf", 30), 104, 54, CYAN, 6)
    # headline
    hf = font("arialbd.ttf", 104)
    d.text((58, 116), "AI agents put a", font=hf, fill=WHITE)
    d.text((58, 224), "claim ", font=hf, fill=WHITE)
    w = d.textlength("claim ", font=hf)
    d.text((58 + w, 224), "ON TRIAL", font=hf, fill=YELLOW)
    # amber sub-hook
    sf = font("arialbd.ttf", 38)
    d.text((60, 350), "+ a 6th investigator, recruited live when fraud is alleged",
           font=sf, fill=AMBER)
    # agent row
    agent_row(img, d, W // 2, 470, 150)
    # logo bottom-left small
    logo = Image.open(ASSETS / "logo.png").convert("RGBA")
    lw = 300
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, (58, H - lh - 36), logo)
    d.text((W - 360, H - 56), "recourseband.duckdns.org", font=font("consolab.ttf", 24), fill=CYAN)
    img.save(OUT / "thumb_walkthrough.png")
    print("thumb_walkthrough.png")


# ---------------- THUMB B · COMMERCIAL ----------------
def thumb_commercial():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    dotgrid(d, (30, 30, 34))
    # logo centered-top
    logo = Image.open(ASSETS / "logo.png").convert("RGBA")
    lw = 560
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, ((W - lw) // 2, 78), logo)
    # huge tagline
    hf = font("arialbd.ttf", 92)

    def cline(text, y, fill):
        wt = d.textlength(text, font=hf)
        d.text(((W - wt) / 2, y), text, font=hf, fill=fill)

    cline("EVERY CLAIM DESERVES", 210, WHITE)
    # second line "A FAIR FIGHT." — "A " white, "FAIR FIGHT." yellow, centered as one unit
    wt = d.textlength("A FAIR FIGHT.", font=hf)
    x = (W - wt) / 2
    d.text((x, 312), "A ", font=hf, fill=WHITE)
    x += d.textlength("A ", font=hf)
    d.text((x, 312), "FAIR FIGHT.", font=hf, fill=YELLOW)
    # yellow rule
    d.rectangle([(W - 240) / 2, 432, (W + 240) / 2, 446], fill=YELLOW)
    # sub
    sf = font("arial.ttf", 34)
    sub = "Adversarial AI claims adjudication — six agents, one recruited on demand."
    ws = d.textlength(sub, font=sf)
    d.text(((W - ws) / 2, 472), sub, font=sf, fill=GRAY)
    # agent color bar
    cols = [(14, 116, 144), (45, 91, 255), (124, 58, 237), (220, 38, 38), (21, 128, 61), (180, 83, 9)]
    bw = 150
    bx = (W - (len(cols) * bw + (len(cols) - 1) * 10)) // 2
    for c in cols:
        d.rectangle([bx, 560, bx + bw, 576], fill=c)
        bx += bw + 10
    d.text((W // 2 - 130, 612), "recourseband.duckdns.org", font=font("consolab.ttf", 26), fill=CYAN)
    img.save(OUT / "thumb_commercial.png")
    print("thumb_commercial.png")


thumb_walkthrough()
thumb_commercial()
print("thumbnails ->", OUT)
