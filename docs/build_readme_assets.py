"""Build fresh README visuals: a 6-agent dashboard hero, a rendered architecture diagram (no ASCII),
and tidy screenshot crops for a 'See it in action' grid.

Run:  uv run --with playwright --with pillow python docs/build_readme_assets.py
"""
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
ROOT = HERE.parent
URL = "https://recourseband.duckdns.org"

ARCH_HTML = """<!doctype html><html><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;800;900&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet"/>
<style>
  :root{--bg:#e9e6dd;--ink:#0e0e0e;--paper:#fff;--muted:#6b6a63;--signal:#f5d90a;
    --coord:#0e7490;--blake:#2d5bff;--morgan:#7c3aed;--alex:#dc2626;--sam:#15803d;--quinn:#b45309;
    --shadow-sm:3px 3px 0 var(--ink);--mono:"Space Mono",monospace;--display:"Archivo",sans-serif;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{width:1360px;background:var(--bg);background-image:radial-gradient(var(--ink) .6px,transparent .6px);
    background-size:22px 22px;font-family:var(--display);padding:46px 54px}
  .hd{font-family:var(--mono);font-weight:700;text-transform:uppercase;letter-spacing:.14em;font-size:15px;color:var(--coord)}
  h2{font-size:34px;font-weight:900;letter-spacing:-.02em;margin:6px 0 26px}
  .archv{display:flex;flex-direction:column;gap:8px}
  .tier{background:var(--paper);border:2.5px solid var(--ink);border-left:11px solid var(--c);
    box-shadow:var(--shadow-sm);padding:13px 20px;display:flex;align-items:center;gap:20px}
  .tlab{font-family:var(--mono);font-weight:700;font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--c);flex:0 0 128px}
  .tmain{flex:1}
  .tmain b{font-size:18px;font-weight:900;display:block;line-height:1.1}
  .tmain .desc{font-family:var(--mono);font-size:12.5px;color:var(--muted);display:block;margin-top:3px;line-height:1.3}
  .flowc{display:flex;justify-content:center;height:15px;align-items:center}
  .flowc span{font-family:var(--mono);font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.05em;background:var(--bg);padding:0 14px;text-transform:uppercase}
  .dots{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}
  .dot{font-family:var(--mono);font-size:12px;font-weight:700;color:#fff;padding:3px 11px}
  .dot.dim{background:transparent;color:var(--quinn);border:2px solid var(--quinn)}
  .row{display:flex;gap:8px}.grow{flex:1}
</style></head><body>
  <div class="hd">Architecture</div>
  <h2>One room. A streaming spine. A durable record.</h2>
  <div class="archv">
    <div class="tier" style="--c:var(--blake)"><span class="tlab">Client</span>
      <div class="tmain"><b>Next.js 14 · App Router</b><span class="desc">Dashboard · live debate room · resolution panel · signed-record / JSON export</span></div></div>
    <div class="flowc"><span>&uarr; SSE live stream (un-buffered) &nbsp;&middot;&nbsp; &darr; user actions</span></div>
    <div class="tier" style="--c:var(--coord)"><span class="tlab">Orchestration</span>
      <div class="tmain"><b>FastAPI &middot; Coordinator-driven turn engine</b><span class="desc">async SQLAlchemy &middot; streams each turn over SSE &middot; drives every handoff</span></div></div>
    <div class="flowc"><span>Band Agent API &nbsp;&middot;&nbsp; @mention routing &nbsp;&middot;&nbsp; add_participant</span></div>
    <div class="tier" style="--c:var(--quinn)"><span class="tlab">Band room</span>
      <div class="tmain"><b>One Band room &mdash; agents assembled per case</b>
        <div class="dots">
          <span class="dot" style="background:var(--coord)">Coordinator</span>
          <span class="dot" style="background:var(--blake)">Blake</span>
          <span class="dot" style="background:var(--morgan)">Morgan</span>
          <span class="dot" style="background:var(--alex)">Alex</span>
          <span class="dot" style="background:var(--sam)">Sam</span>
          <span class="dot dim">&#9673; Quinn &middot; recruited on demand</span>
        </div></div></div>
    <div class="row" style="margin-top:0">
      <div class="tier grow" style="--c:var(--morgan)"><span class="tlab">Data &middot; RAG</span>
        <div class="tmain"><b>PostgreSQL + pgvector</b><span class="desc">claims &middot; transcript &middot; clause embeddings &mdash; MiniLM 384-dim, cosine</span></div></div>
      <div class="tier grow" style="--c:var(--sam)"><span class="tlab">Models</span>
        <div class="tmain"><b>AI/ML GPT-4o &middot; Featherless Hermes-2-Pro</b><span class="desc">GPT-4o: Blake &middot; Morgan &middot; Sam &middot; Quinn &nbsp;|&nbsp; Hermes-2-Pro: Alex</span></div></div>
    </div>
  </div>
</body></html>"""


def crop_to(src: Path, dst: Path, width: int):
    im = Image.open(src).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(dst, "PNG")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1600, "height": 980}, device_scale_factor=2)
    pg = ctx.new_page()

    # fresh 6-agent dashboard hero
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("text=Adversarial", timeout=30000)
    pg.wait_for_timeout(1400)
    pg.screenshot(path=str(HERE / "dashboard.png"))
    print("dashboard.png (fresh 6-agent hero)")

    # rendered architecture diagram
    arch = HERE / "_arch.html"
    arch.write_text(ARCH_HTML, encoding="utf-8")
    pg.goto(arch.as_uri(), wait_until="networkidle")
    pg.wait_for_timeout(700)
    body = pg.locator("body")
    body.screenshot(path=str(HERE / "architecture.png"))
    print("architecture.png (rendered diagram)")
    b.close()

# tidy screenshot crops for the grid (reuse the deck/video assets)
SHOTS = ROOT / "deck" / "shots"
crop_to(SHOTS / "quinn_msg_v4.png", HERE / "shot-recruit.png", 900)
crop_to(SHOTS / "resolution_v4.png", HERE / "shot-verdict.png", 900)
crop_to(ROOT / "video" / "assets" / "record_shot.png", HERE / "shot-record.png", 900)
crop_to(ROOT / "video" / "assets" / "json_shot.png", HERE / "shot-json.png", 900)
crop_to(SHOTS / "evidence_v4.png", HERE / "shot-evidence.png", 700)
print("screenshot crops -> docs/")
