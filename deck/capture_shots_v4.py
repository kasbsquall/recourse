"""Capture fresh 6-agent product screenshots for deck v4 (non-destructive — no debate run).
Marcus Reyes is the CLOSED showcase (approved, with Quinn), so his page already has the full
6-agent transcript + a signed resolution to screenshot without changing any state.

Run:  uv run --with playwright python deck/capture_shots_v4.py
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://recourseband.duckdns.org"
OUT = Path(__file__).parent / "shots"
OUT.mkdir(parents=True, exist_ok=True)


def shot_ancestor(pg, text, name):
    """Screenshot the nearest .brut ancestor of an element found by text."""
    try:
        el = pg.get_by_text(text, exact=False).first
        el.scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        box = el.locator("xpath=ancestor-or-self::div[contains(@class,'brut')][1]")
        box.screenshot(path=str(OUT / name))
        print("captured", name)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"{name} skipped:", e)
        return False


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
    pg = ctx.new_page()

    # 1) dashboard — 6-agent standing panel + 3-case docket + judge banner
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_selector("text=Adversarial", timeout=30000)
    pg.wait_for_timeout(1400)
    pg.screenshot(path=str(OUT / "dashboard_v4.png"))
    print("dashboard_v4 captured")

    # 2) Marcus Reyes — the closed showcase (6 agents incl. Quinn, signed resolution)
    marcus = pg.locator('a[href^="/claims/"]').filter(has_text="Marcus Reyes").first
    marcus.click()
    pg.wait_for_selector("text=Adjudication Room", timeout=30000)
    pg.wait_for_timeout(1600)

    shot_ancestor(pg, "Supporting Documents", "evidence_v4.png")
    shot_ancestor(pg, "Resolution · Legal Record", "resolution_v4.png")

    # 3) Quinn's SIU message in the transcript (the dynamic-recruitment payoff)
    try:
        q = pg.get_by_text("Special Investigations Unit", exact=False).first
        q.scroll_into_view_if_needed()
        pg.wait_for_timeout(500)
        box = q.locator("xpath=ancestor::div[contains(@class,'brut')][1]")
        box.screenshot(path=str(OUT / "quinn_msg_v4.png"))
        print("quinn_msg_v4 captured")
    except Exception as e:  # noqa: BLE001
        print("quinn_msg_v4 skipped:", e)

    b.close()

print("shots ->", OUT)
