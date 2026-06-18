"""Assemble the Recourse commercial v2 (~82s): stock pain -> the 6-agent product run incl. the
dynamic SIU recruitment (Quinn) -> signed record + JSON -> brand close. Beats are synced to the
v2 voiceover line timings (assets/timings_v2.json), with ducked music + burned subs.

Pass 1: cut/stretch each visual beat to its VO-line slot, concat -> commercial_v2_silent.mp4
Pass 2: mix VO + sidechain-ducked music -> mixed_v2.m4a, burn subs_v2.srt -> commercial_v2.mp4

Run:  python video/assemble_commercial_v2.py    (ffmpeg on PATH; run gen_voiceover_v2.py first)
"""
import json
import subprocess
from pathlib import Path

V = Path(__file__).parent
A = V / "assets"
STOCK = Path(r"C:/Users/User/Downloads/generado/6")

CLIP1 = STOCK / "9813c5a4-706d-4ba4-879a-7d136834c71b.mp4"   # denial letter
CLIP2 = STOCK / "774cd7a1-1b29-4ec5-a7ab-0219b052ed52.mp4"   # overwhelmed officer
CLIP3 = STOCK / "d5603924-cb38-454c-a325-c153843d52d1.mp4"   # scale of justice
RAW = V / "raw" / "lisa_raw.webm"                            # 6-agent product run (Quinn live)
RECORD = A / "record_shot.png"                               # signed record still
JSONS = A / "json_shot.png"                                  # JSON export still
ENDCARD = A / "endcard.png"

TIM = json.loads((A / "timings_v2.json").read_text())
starts = [t["start"] for t in TIM]
endL = TIM[-1]["end"]
TAIL = 0.6
# beat duration = gap to the next line's start (last line runs to its end + tail)
durs = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)] + [endL - starts[-1] + TAIL]

# still inputs (index >= 4) need their length known up front
REC_I, JSON_I, END_I = 4, 5, 6
rec_dur, json_dur, end_dur = durs[14], durs[15], durs[19]

# (src_idx, s, e, fade_in, fade_out)   s=None -> still (use full beat duration)
STORY = [
    (0, 0.3, 5.5, 0.40, 0.00),    # 1  denial letter
    (1, 0.5, 6.0, 0.00, 0.00),    # 2  officer
    (1, 4.0, 9.0, 0.00, 0.25),    # 3  officer (closer)
    (2, 0.3, 6.0, 0.30, 0.00),    # 4  scale — fraud on a hunch
    (3, 4.6, 6.3, 0.30, 0.00),    # 5  Meet Recourse — dashboard
    (3, 5.5, 10.0, 0.00, 0.00),   # 6  the 6-agent panel
    (3, 22.0, 28.5, 0.00, 0.00),  # 7  Blake / Morgan
    (3, 37.5, 43.0, 0.00, 0.00),  # 8  Alex
    (3, 43.5, 47.5, 0.00, 0.00),  # 9  argue in the open
    (3, 47.0, 51.2, 0.00, 0.00),  # 10 fraud alleged — Coordinator recruits
    (3, 51.0, 56.5, 0.00, 0.00),  # 11 Quinn joins, live
    (3, 55.0, 58.5, 0.00, 0.00),  # 12 Quinn weighs the evidence
    (3, 56.5, 59.0, 0.00, 0.00),  # 13 not denied on suspicion
    (3, 67.5, 70.5, 0.00, 0.00),  # 14 tamper-evident hash
    (REC_I, None, None, 0.30, 0.00),   # 15 signed record (still)
    (JSON_I, None, None, 0.00, 0.00),  # 16 JSON export (still)
    (3, 65.0, 69.0, 0.00, 0.00),  # 17 approve / override
    (3, 61.5, 64.5, 0.00, 0.00),  # 18 the verdict appears — final word
    (2, 4.0, 8.5, 0.30, 0.00),    # 19 scale — faster, defensible
    (END_I, None, None, 0.40, 0.50),   # 20 end card (still)
]


def pass1() -> Path:
    parts, labels = [], []
    for i, (idx, s, e, fin, fout) in enumerate(STORY):
        dur = durs[i]
        if s is None:  # still: already `dur` long via -loop -t; trim exact, no stretch
            f = f"[{idx}:v]trim=0:{dur:.3f},setpts=PTS-STARTPTS,fps=30,scale=1920:1080:flags=lanczos,setsar=1"
        else:          # video: cut [s,e] and stretch to the line slot
            f = (
                f"[{idx}:v]trim=start={s}:end={e},"
                f"setpts=(PTS-STARTPTS)*{dur}/{e - s},fps=30,"
                f"scale=1920:1080:flags=lanczos,setsar=1"
            )
        if fin:
            f += f",fade=t=in:st=0:d={fin}"
        if fout:
            f += f",fade=t=out:st={dur - fout:.2f}:d={fout}"
        f += f"[v{i}]"
        parts.append(f)
        labels.append(f"[v{i}]")
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(STORY)}:v=1:a=0[outv]"

    out = V / "commercial_v2_silent.mp4"
    cmd = ["ffmpeg", "-y",
           "-i", str(CLIP1), "-i", str(CLIP2), "-i", str(CLIP3), "-i", str(RAW),
           "-loop", "1", "-t", f"{rec_dur + 0.3:.2f}", "-i", str(RECORD),
           "-loop", "1", "-t", f"{json_dur + 0.3:.2f}", "-i", str(JSONS),
           "-loop", "1", "-t", f"{end_dur + 0.3:.2f}", "-i", str(ENDCARD),
           "-filter_complex", fc, "-map", "[outv]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium", str(out)]
    subprocess.run(cmd, check=True)
    return out


def pass2(silent: Path) -> Path:
    total = sum(durs)
    mixed = V / "mixed_v2.m4a"
    amix = (
        "[1:a]asplit=2[k0][v0];"
        "[k0]apad=pad_dur=4[key];"
        f"[2:a]volume=0.20,afade=t=in:st=0:d=1.5,afade=t=out:st={total - 2.4:.2f}:d=2.4[mus0];"
        "[mus0][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=350[mus];"
        "[v0]volume=1.12[vo];"
        "[vo][mus]amix=inputs=2:normalize=0:duration=longest[a]"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(silent), "-i", str(A / "voiceover_v2.mp3"),
        "-stream_loop", "-1", "-i", str(A / "music.mp3"),
        "-filter_complex", amix, "-map", "[a]",
        "-c:a", "aac", "-b:a", "192k", str(mixed),
    ], check=True)

    style = (
        "Fontname=Arial\\,Fontsize=15\\,Bold=1\\,PrimaryColour=&H00FFFFFF&\\,"
        "OutlineColour=&H00141414&\\,BorderStyle=1\\,Outline=2\\,Shadow=1\\,"
        "MarginV=46\\,Alignment=2"
    )
    out = V / "commercial_v2.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(mixed),
        "-vf", f"subtitles=assets/subs_v2.srt:force_style='{style}'",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-shortest", str(out),
    ], check=True, cwd=str(V))
    return out


if __name__ == "__main__":
    sv = pass1()
    print("pass1 ->", sv)
    fv = pass2(sv)
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(fv)], capture_output=True, text=True).stdout.strip()
    print(f"commercial_v2.mp4 -> {fv}  ({dur}s, {fv.stat().st_size // 1024} KB)")
