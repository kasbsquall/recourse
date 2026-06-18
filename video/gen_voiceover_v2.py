"""Generate the Recourse commercial v2 voiceover via ElevenLabs (per-character timestamps),
then derive per-line start/end times + a burned-in SRT. Outputs are _v2-suffixed so the original
commercial assets stay intact. Reads the key from ELEVEN_KEY (kept in the gitignored .env).

Run:  ELEVEN_KEY=... uv run --with requests python video/gen_voiceover_v2.py
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

# v2 script — adds the dynamic-recruitment (6th agent) act.
LINES = [
    "Every day, another denied claim lands on someone's desk.",
    "A dispute. An appeal. A person who feels unheard,",
    "and a judgment call that falls on one reviewer, alone.",
    "Too often, fraud is flagged on a hunch, and a claim is denied on suspicion.",
    "Meet Recourse.",
    "A panel of A.I. specialists puts every disputed claim on trial.",
    "One builds the case for the insured. One maps the fine print, clause by clause.",
    "And one fights to deny it, so no weakness goes unexamined.",
    "They argue in the open, until the case is settled.",
    "And the moment fraud is alleged, the panel does something different.",
    "It recruits a sixth specialist, live, a special investigator.",
    "Quinn weighs the accusation against the evidence on the record,",
    "so no one is denied on suspicion alone.",
    "Every word becomes a tamper-evident audit trail.",
    "A signed record a regulator can file,",
    "and a machine can verify.",
    "You stay in command. Approve, or override.",
    "The final word is always yours.",
    "Faster decisions. Reasoning you can defend.",
    "Recourse. Every claim deserves a fair fight.",
]
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
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()

    (OUT / "voiceover_v2.mp3").write_bytes(base64.b64decode(data["audio_base64"]))

    align = data["alignment"]
    starts = align["character_start_times_seconds"]
    ends = align["character_end_times_seconds"]

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
    (OUT / "subs_v2.srt").write_text("\n".join(srt), encoding="utf-8")

    total = ends[-1]
    print(f"voiceover_v2.mp3 + subs_v2.srt -> {OUT}  (total {total:.2f}s)\n")
    for line, s, e in cuts:
        print(f"  [{s:6.2f} -> {e:6.2f}]  {line}")
    (OUT / "timings_v2.json").write_text(
        json.dumps([{"line": l, "start": s, "end": e} for l, s, e in cuts], indent=2)
    )


if __name__ == "__main__":
    main()
