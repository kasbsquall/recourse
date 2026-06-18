"""Build the trimmed LIVE walkthrough from the Lisa Park raw recording (6 agents, incl. Quinn/SIU).

Keeps the real production run but cuts the ~67s dead-air (Alex waiting on Featherless) down to a
short 'deliberating' beat, burns brand caption chips per phase — including the dynamic SIU
recruitment beat — and bookends it with a title + end card over a soft music bed.

Run:  uv run --with pillow python video/build_walkthrough_lisa.py
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
RAW = HERE / "raw" / "lisa_raw.webm"
ASSETS = HERE / "assets"
WT = HERE / "_wt_lisa"
WT.mkdir(exist_ok=True)
OUT = HERE / "walkthrough_lisa.mp4"

W, H = 1920, 1080
BG = (11, 11, 12)
WHITE = (245, 245, 247)
GRAY = (161, 161, 170)
YELLOW = (245, 217, 10)
CYAN = (34, 211, 238)
AMBER = (245, 158, 11)

F = "C:/Windows/Fonts"
f_disp = ImageFont.truetype(f"{F}/arialbd.ttf", 42)
f_mono = ImageFont.truetype(f"{F}/consolab.ttf", 26)
f_mono_sm = ImageFont.truetype(f"{F}/consola.ttf", 24)
f_eyebrow = ImageFont.truetype(f"{F}/consolab.ttf", 30)
f_sub = ImageFont.truetype(f"{F}/arial.ttf", 38)


def center(d, text, font, y, fill, tracking=0):
    if tracking:
        widths = [d.textlength(c, font=font) for c in text]
        total = sum(widths) + tracking * (len(text) - 1)
        x = (W - total) / 2
        for c, w in zip(text, widths):
            d.text((x, y), c, font=font, fill=fill)
            x += w + tracking
    else:
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=fill)


# --- title card -------------------------------------------------------------
def make_title():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for gy in range(120, H - 120, 46):
        for gx in range(160, W - 160, 46):
            d.point((gx, gy), fill=(28, 28, 32))
    center(d, "LIVE WALKTHROUGH", f_eyebrow, 360, CYAN, tracking=8)
    logo = Image.open(ASSETS / "logo.png").convert("RGBA")
    lw = 980
    lh = round(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    img.paste(logo, ((W - lw) // 2, 426), logo)
    by = 426 + lh + 54
    d.rectangle([(W - 300) / 2, by, (W + 300) / 2, by + 16], fill=YELLOW)
    center(d, "Six agents put a claim on trial — one recruited the moment fraud is alleged.",
           f_sub, by + 60, GRAY)
    center(d, "A real production run, lightly trimmed.", f_sub, by + 110, GRAY)
    p = WT / "title.png"
    img.save(p)
    return p


# --- caption chips (transparent, lower-third) -------------------------------
BAR_TOP, BAR_BOT = 958, 1060


def make_caption(idx, total, tag, text, mono=False, accent=YELLOW):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, BAR_TOP, W, BAR_BOT], fill=(8, 8, 9, 214))
    d.rectangle([0, BAR_TOP, 12, BAR_BOT], fill=accent)
    d.text((48, BAR_TOP + 14), tag, font=f_mono, fill=accent)
    font = f_mono if mono else f_disp
    yoff = BAR_TOP + 44 if not mono else BAR_TOP + 48
    d.text((48, yoff), text, font=font, fill=WHITE)
    ix = f"{idx:02d} / {total:02d}"
    iw = d.textlength(ix, font=f_mono_sm)
    d.text((W - 48 - iw, BAR_TOP + 14), ix, font=f_mono_sm, fill=GRAY)
    p = WT / f"cap_{idx}.png"
    img.save(p)
    return p


# (tag, main text, mono?, accent)
CAPS = [
    ("THE CLAIM", "Lisa Park · $4,200 theft — denied as alleged commercial use", False, YELLOW),
    ("THE EVIDENCE", "Clickable evidence — police report, scene photos, adjuster note", False, YELLOW),
    ("THE ROOM", "Open the adjudication room — agents convene in one Band room", False, YELLOW),
    ("ARGUE", "Blake argues for the insured — theft is covered under §5.2", False, YELLOW),
    ("POLICY · RAG", "Morgan cites the governing clauses — §5.2, §7.4", False, YELLOW),
    ("DELIBERATING", ">>  Adversarial review in progress…", True, GRAY),
    ("CHALLENGE", "Alex attacks the denial — no rideshare records on file", False, YELLOW),
    ("RECRUIT · SIU", "Fraud alleged → Quinn (SIU) recruited live · finds it unproven", False, AMBER),
    ("NOTARIZE", "Sam compiles the signed, reasoned resolution", False, YELLOW),
    ("THE VERDICT", "APPROVED — the human officer has the final word", False, YELLOW),
]
# body-time window boundaries (seconds) — 10 windows
WIN = [0.0, 8.0, 15.5, 24.0, 28.5, 32.5, 34.5, 41.5, 47.5, 51.0, 59.5]

title_png = make_title()
cap_pngs = [make_caption(i + 1, len(CAPS), t, txt, m, a) for i, (t, txt, m, a) in enumerate(CAPS)]

# hold frame for the deliberating beat (mid dead-air, Alex pending)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "65", "-i", str(RAW),
                "-frames:v", "1", str(WT / "hold_delib.png")], check=True)

# ---- PASS A: body segments + captions -------------------------------------
# A = trim 0.5:33.0 (32.5)   B = hold 2.0   C = trim 96.0:121.0 (25.0)  -> 59.5
inputs_a = [
    "-i", str(RAW),                                                  # 0
    "-loop", "1", "-t", "2.0", "-i", str(WT / "hold_delib.png"),     # 1
]
for p in cap_pngs:                                                   # 2..11
    inputs_a += ["-i", str(p)]

norm = "fps=30,scale=1920:1080,setsar=1"
fc = (
    f"[0:v]trim=0.5:33.0,setpts=PTS-STARTPTS,{norm}[a];"
    f"[1:v]{norm},setpts=PTS-STARTPTS[b];"
    f"[0:v]trim=96.0:121.0,setpts=PTS-STARTPTS,{norm}[c];"
    f"[a][b][c]concat=n=3:v=1:a=0[body]"
)
prev = "body"
for i in range(len(cap_pngs)):
    s, e = WIN[i], WIN[i + 1]
    inp = i + 2
    out = f"o{i}"
    fc += f";[{prev}][{inp}:v]overlay=0:0:enable='between(t,{s},{e})'[{out}]"
    prev = out
fc += f";[{prev}]format=yuv420p[bc]"

body_mp4 = WT / "body_cap.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs_a, "-filter_complex", fc,
                "-map", "[bc]", "-r", "30", "-c:v", "libx264", "-crf", "18",
                "-preset", "medium", str(body_mp4)], check=True)
print("pass A done ->", body_mp4)

# ---- PASS B: title + body + endcard + music -------------------------------
TITLE_D, END_D = 3.0, 2.5
total = TITLE_D + 59.5 + END_D  # 65.0

inputs_b = [
    "-loop", "1", "-t", str(TITLE_D), "-i", str(title_png),             # 0
    "-i", str(body_mp4),                                                # 1
    "-loop", "1", "-t", str(END_D), "-i", str(ASSETS / "endcard.png"),  # 2
    "-stream_loop", "-1", "-i", str(ASSETS / "music.mp3"),              # 3
]
fc2 = (
    f"[0:v]{norm},setpts=PTS-STARTPTS[t];"
    f"[1:v]{norm},setpts=PTS-STARTPTS[m];"
    f"[2:v]{norm},setpts=PTS-STARTPTS[e];"
    f"[t][m][e]concat=n=3:v=1:a=0,format=yuv420p[v];"
    f"[3:a]volume=0.16,afade=t=in:st=0:d=1.2,"
    f"afade=t=out:st={total-1.6}:d=1.6,atrim=0:{total}[au]"
)
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs_b, "-filter_complex", fc2,
                "-map", "[v]", "-map", "[au]", "-r", "30",
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)], check=True)
print("walkthrough ->", OUT, f"(~{total:.0f}s)")
