"""Assemble the Recourse demo from the raw Playwright capture.

Stage 1 (now): cut + speed-ramp the product footage into product_cut.mp4 (no audio) so the
walkthrough reads in ~35s — the long Alex turn is time-lapsed.

Stage 2 (once assets land in video/assets/): prepend the stock intro clips, lay the ElevenLabs
voiceover (voiceover.mp3) + ducked music (music.mp3), burn subtitles (subs.srt), export final.mp4.

Run: ffmpeg must be on PATH.  python video/build_video.py
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).parent
RAW = OUT / "raw" / "demo_raw.webm"

# (start_s, end_s, speed) slices of the raw capture, from timestamps.json milestones.
# The raw take had a ~70s gap waiting for Alex (Featherless) — we JUMP-CUT over that dead air
# and only show each agent the moment it posts, so the debate reads tight.
SEGMENTS = [
    (5.0, 9.0, 1.0),      # dashboard — the standing panel + 2 pending cases
    (10.3, 12.8, 1.0),    # case file — David Chen, crash photos
    (13.5, 28.0, 2.4),    # panel convenes → Blake + Morgan debate (sped)
    (94.5, 100.5, 1.5),   # >>> jump-cut over the wait <<< Alex's challenge lands
    (100.5, 108.5, 1.3),  # Coordinator routes to Sam → APPROVED $12,000 resolution
    (108.8, 112.3, 1.0),  # hover Approve & sign off / Override & deny
    (112.3, 114.0, 1.0),  # the tamper-evident sha256 hash
]


def build_product_cut() -> Path:
    filters, labels = [], []
    for i, (s, e, sp) in enumerate(SEGMENTS):
        filters.append(
            f"[0:v]trim=start={s}:end={e},setpts=(PTS-STARTPTS)/{sp},fps=30,"
            f"scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
        )
        labels.append(f"[v{i}]")
    fc = ";".join(filters) + ";" + "".join(labels) + f"concat=n={len(SEGMENTS)}:v=1:a=0[outv]"
    out = OUT / "product_cut.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", str(RAW),
        "-filter_complex", fc, "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


if __name__ == "__main__":
    if not RAW.exists():
        raise SystemExit(f"missing raw capture: {RAW} — run record_demo.py first")
    out = build_product_cut()
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True,
    ).stdout.strip()
    print(f"product_cut.mp4 -> {out} ({dur}s, {out.stat().st_size // 1024} KB)")
