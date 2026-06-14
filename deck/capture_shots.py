"""Capture real product screenshots for the deck + README.
Non-destructive: only navigates the live site (no debate run, no state change).

Run:  uv run --with playwright python deck/capture_shots.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://recourseband.duckdns.org"
OUT = Path(__file__).parent / "shots"
OUT.mkdir(parents=True, exist_ok=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    pg = ctx.new_page()

    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("text=Adversarial", timeout=30000)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "dashboard.png"))
    pg.screenshot(path=str(OUT / "dashboard_full.png"), full_page=True)
    print("dashboard captured")

    dc = pg.locator('a[href^="/claims/"]').filter(has_text="David Chen").first
    dc.click()
    pg.wait_for_selector("text=Adjudication Room", timeout=30000)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / "casefile.png"))
    pg.screenshot(path=str(OUT / "casefile_full.png"), full_page=True)
    print("casefile captured")

    b.close()

print("shots ->", OUT)
