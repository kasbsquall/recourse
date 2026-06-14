"""Generate the Recourse commercial voiceover via ElevenLabs (with per-character timestamps),
then derive per-line start/end times and a burned-in SRT. Outputs land in video/assets/.

Run:  uv run --with requests python video/gen_voiceover.py
"""
import base64
import json
import os
from pathlib import Path

import requests

KEY = os.environ["ELEVEN_KEY"]
VOICE = "pqHfZKP75CvOlQylNhV4"  # Bill — Wise, Mature, Balanced (advertisement)
MODEL = "eleven_multilingual_v2"

OUT = Path(__file__).parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# Each line is one subtitle beat. Punctuation drives the pacing/pauses.
LINES = [
    "Every day, another disputed claim lands on your desk.",
    "A denial. An appeal. A person who feels unheard,",
    "and a decision that falls on you alone.",
    "Meet Recourse.",
    "Five A.I. specialists put every claim on trial.",
    "One argues the merits. One maps the fine print.",
    "And one fights to deny it, so nothing is missed.",
    "They debate in the open, until the case is settled.",
    "Every word becomes a tamper-evident audit trail.",
    "You stay in command. Approve, or override,",
    "the final word is always yours.",
    "Faster decisions. Reasoning you can defend.",
    "Recourse. Every claim deserves a fair fight.",
]
# Two spaces between lines so each beat keeps a small breath.
TEXT = "  ".join(LINES)


def srt_ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def main() -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps",
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
        json={
            "text": TEXT,
            "model_id": MODEL,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.25,
                "use_speaker_boost": True,
            },
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()

    (OUT / "voiceover.mp3").write_bytes(base64.b64decode(data["audio_base64"]))

    align = data["alignment"]
    chars = align["characters"]
    starts = align["character_start_times_seconds"]
    ends = align["character_end_times_seconds"]

    # Walk the original TEXT, mapping each LINE to its char span -> time span.
    cuts, pos = [], 0
    for line in LINES:
        idx = TEXT.index(line, pos)
        start = starts[idx]
        end = ends[min(idx + len(line) - 1, len(ends) - 1)]
        cuts.append((line, start, end))
        pos = idx + len(line)

    srt = []
    for i, (line, s, e) in enumerate(cuts, 1):
        srt.append(f"{i}\n{srt_ts(s)} --> {srt_ts(e)}\n{line}\n")
    (OUT / "subs.srt").write_text("\n".join(srt), encoding="utf-8")

    total = ends[-1]
    print(f"voiceover.mp3 + subs.srt -> {OUT}  (total {total:.2f}s)\n")
    for line, s, e in cuts:
        print(f"  [{s:6.2f} -> {e:6.2f}]  {line}")
    (OUT / "timings.json").write_text(
        json.dumps([{"line": l, "start": s, "end": e} for l, s, e in cuts], indent=2)
    )


if __name__ == "__main__":
    main()
