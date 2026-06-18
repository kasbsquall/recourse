"""New 16:9 submission cover featuring the SIX agents — with Quinn (SIU) highlighted as the
one the panel dynamically recruits when fraud is alleged. Neo-brutalist 'Verdict' look.

Run:  uv run --with pillow python video/gen_cover_hero.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ROOT = HERE.parent
ASSETS = HERE / "assets"
PORTRAITS = ROOT / "frontend" / "public" / "agents"
OUT = ROOT / "covers"
OUT.mkdir(exist_ok=True)

W, H = 1920, 1080
BG = (11, 11, 12)
WHITE = (245, 245, 247)
GRAY = (161, 161, 170)
MUTED = (120, 120, 128)
YELLOW = (245, 217, 10)
CYAN = (34, 211, 238)
AMBER = (180, 83, 9)

F = "C:/Windows/Fonts"


def font(name, size):
    return ImageFont.truetype(f"{F}/{name}", size)


def center(d, text, fnt, y, fill, tracking=0, cx=W // 2):
    if tracking:
        ws = [d.textlength(c, font=fnt) for c in text]
        total = sum(ws) + tracking * (len(text) - 1)
        x = cx - total / 2
        for c, w in zip(text, ws):
            d.text((x, y), c, font=fnt, fill=fill)
            x += w + tracking
    else:
        w = d.textlength(text, font=fnt)
        d.text((cx - w / 2, y), text, font=fnt, fill=fill)


def text_centered(d, text, fnt, y, fill, cx):
    w = d.textlength(text, font=fnt)
    d.text((cx - w / 2, y), text, font=fnt, fill=fill)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# dot grid texture
for gy in range(110, H - 90, 46):
    for gx in range(150, W - 150, 46):
        d.point((gx, gy), fill=(28, 28, 32))

# eyebrow
center(d, "BAND OF AGENTS HACKATHON   ·   TRACK 3 — REGULATED & HIGH-STAKES",
       font("consolab.ttf", 25), 96, CYAN, tracking=5)

# logo
logo = Image.open(ASSETS / "logo.png").convert("RGBA")
lw = 720
lh = round(lw * logo.height / logo.width)
logo = logo.resize((lw, lh), Image.LANCZOS)
img.paste(logo, ((W - lw) // 2, 150), logo)

# tagline
ty = 150 + lh + 36
center(d, "A panel of AI agents debates every denied insurance claim —",
       font("arial.ttf", 40), ty, GRAY)
center(d, "and recruits a 6th investigator the moment fraud is alleged.",
       font("arialbd.ttf", 40), ty + 52, WHITE)

# yellow divider
dy = ty + 128
d.rectangle([(W - 300) / 2, dy, (W + 300) / 2, dy + 12], fill=YELLOW)

# ---- six agents row ----
AGENTS = [
    ("coordinator.png", "Coordinator", "Orchestrator", (150, 150, 158)),
    ("blake.png", "Blake", "Claims Evaluator", (14, 116, 144)),
    ("morgan.png", "Morgan", "Policy Analyst", (45, 91, 255)),
    ("alex.png", "Alex", "Devil's Advocate", (220, 38, 38)),
    ("sam.png", "Sam", "Resolution Notary", (21, 128, 61)),
    ("quinn.png", "Quinn", "SIU · on-call", AMBER),
]
S = 184          # portrait size
GAP = 36
n = len(AGENTS)
row_w = n * S + (n - 1) * GAP
x0 = (W - row_w) // 2
py = dy + 56     # portrait top

name_f = font("arialbd.ttf", 27)
role_f = font("consola.ttf", 19)
chip_f = font("consolab.ttf", 17)

for i, (file, name, role, color) in enumerate(AGENTS):
    x = x0 + i * (S + GAP)
    cx = x + S // 2
    is_quinn = name == "Quinn"
    ring = AMBER if is_quinn else color
    bw = 6 if is_quinn else 4
    # colored ring + frame
    d.rectangle([x - bw, py - bw, x + S + bw, py + S + bw], fill=ring)
    d.rectangle([x - bw - 3, py - bw - 3, x + S + bw + 3, py + S + bw + 3], outline=(40, 40, 44), width=2)
    por = Image.open(PORTRAITS / file).convert("RGB").resize((S, S), Image.LANCZOS)
    img.paste(por, (x, py))
    # name + role
    text_centered(d, name, name_f, py + S + 18, WHITE if not is_quinn else YELLOW, cx)
    text_centered(d, role, role_f, py + S + 52, GRAY if not is_quinn else AMBER, cx)
    # 'recruited' chip above Quinn
    if is_quinn:
        chip = "◉ RECRUITED ON FRAUD"
        cw = d.textlength(chip, font=chip_f)
        d.rectangle([cx - cw / 2 - 12, py - bw - 40, cx + cw / 2 + 12, py - bw - 12], fill=AMBER)
        d.text((cx - cw / 2, py - bw - 38), chip, font=chip_f, fill=(12, 12, 12))

# ---- url chip ----
url = "recourseband.duckdns.org"
uf = font("consolab.ttf", 34)
uw = d.textlength(url, font=uf)
uy = py + S + 110
d.rectangle([(W - uw) / 2 - 28, uy, (W + uw) / 2 + 28, uy + 64], outline=CYAN, width=3)
d.text(((W - uw) / 2, uy + 15), url, font=uf, fill=CYAN)

out = OUT / "cover_hero_6agents.png"
img.save(out)
print("cover ->", out, f"({out.stat().st_size // 1024} KB)")
