"""Record the Recourse product walkthrough as 1920x1080 video via Playwright, driving the LIVE
site through the real adjudication flow and saving milestone timestamps for the ffmpeg edit.

Run:  uv run --with playwright python video/record_demo.py
(needs `playwright install chromium` once)
"""
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://recourseband.duckdns.org"
OUT = Path(__file__).parent
RAW = OUT / "raw"
RAW.mkdir(parents=True, exist_ok=True)

marks: dict[str, float] = {}


def mark(name: str, t0: float) -> None:
    marks[name] = round(time.time() - t0, 2)
    print(f"  [{marks[name]:7.2f}s] {name}", flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(RAW),
        record_video_size={"width": 1920, "height": 1080},
    )
    page = ctx.new_page()
    video = page.video
    t0 = time.time()

    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("text=Adversarial", timeout=30000)
    page.wait_for_timeout(800)  # let avatars paint
    mark("dashboard", t0)
    page.wait_for_timeout(3500)

    # Open David Chen's case
    dc = page.locator('a[href^="/claims/"]').filter(has_text="David Chen").first
    dc.scroll_into_view_if_needed()
    dc.click()
    page.wait_for_selector("text=Adjudication Room", timeout=30000)
    page.wait_for_timeout(1200)
    mark("casefile", t0)
    page.wait_for_timeout(2800)

    # Convene the panel
    page.get_by_role("button", name=re.compile("Open Adjudication Room")).click()
    mark("debate_start", t0)

    # Poll for each agent + the verdict
    roles = {
        "Claims Evaluator": "blake",
        "Policy Analyst": "morgan",
        "Devil's Advocate": "alex",
        "Resolution Notary": "sam",
    }
    seen: set[str] = set()
    deadline = time.time() + 210
    while time.time() < deadline:
        for label, slug in roles.items():
            if slug not in seen and page.get_by_text(label, exact=True).count() > 0:
                seen.add(slug)
                mark(slug, t0)
        if page.get_by_role("button", name=re.compile("Approve & sign off")).count() > 0:
            mark("verdict", t0)
            break
        page.wait_for_timeout(800)
    page.wait_for_timeout(2500)

    # Hover the human-decision actions
    try:
        approve = page.get_by_role("button", name=re.compile("Approve & sign off"))
        approve.scroll_into_view_if_needed()
        approve.hover()
        page.wait_for_timeout(1600)
        page.get_by_role("button", name=re.compile("Override")).hover()
        page.wait_for_timeout(1600)
        mark("actions", t0)
    except Exception as e:  # noqa: BLE001
        print("actions hover skipped:", e)

    # Reveal the tamper-evident hash
    try:
        page.get_by_text(re.compile("tamper-evident")).scroll_into_view_if_needed()
        page.wait_for_timeout(2800)
        mark("hash", t0)
    except Exception as e:  # noqa: BLE001
        print("hash scroll skipped:", e)

    page.wait_for_timeout(1500)
    mark("end", t0)
    ctx.close()
    src = Path(video.path())  # must read the path while the Playwright loop is still alive
    browser.close()

final = RAW / "demo_raw.webm"
src.replace(final)
(OUT / "timestamps.json").write_text(json.dumps(marks, indent=2))
print("\nVIDEO :", final, f"({final.stat().st_size // 1024} KB)")
print("MARKS :", json.dumps(marks))
