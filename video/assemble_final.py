"""Assemble the Recourse commercial: stock pain -> live product (beat-synced to the VO) ->
brand close, with ducked music and burned subtitles. All beats are timed to assets/timings.json.

Pass 1: cut every visual beat from its source, stretch to its exact slot, concat -> final_video.mp4
Pass 2: mix VO + sidechain-ducked music -> mixed.m4a, then burn subs.srt -> final.mp4

Run:  python video/assemble_final.py   (ffmpeg on PATH; assets/ already generated)
"""
import subprocess
from pathlib import Path

V = Path(__file__).parent
A = V / "assets"
STOCK = Path(r"C:/Users/User/Downloads/generado/6")  # watermark-free re-renders

CLIP1 = STOCK / "9813c5a4-706d-4ba4-879a-7d136834c71b.mp4"  # denial letter
CLIP2 = STOCK / "774cd7a1-1b29-4ec5-a7ab-0219b052ed52.mp4"  # overwhelmed officer
CLIP3 = STOCK / "d5603924-cb38-454c-a325-c153843d52d1.mp4"  # scale of justice
RAW = V / "raw" / "demo_raw.webm"
ENDCARD = A / "endcard.png"

# input order -> ffmpeg -i index
INPUTS = [CLIP1, CLIP2, CLIP3, RAW]  # endcard added as a looped image input (index 4)

# Each beat: (input_idx, src_start, src_end, out_dur, fade_in, fade_out)
# out_dur slots are derived from the VO line timings (assets/timings.json).
BEATS = [
    (0,  0.3,   6.0,   5.60, 0.40, 0.00),  # "Every day, another disputed claim..."  denial letter
    (1,  1.5,   8.0,   5.67, 0.00, 0.30),  # "A denial. An appeal... falls on you alone."  officer
    (3,  4.8,  12.8,   5.14, 0.30, 0.00),  # "Meet Recourse. Five AI specialists..."  dashboard+case
    (3, 19.0,  27.5,   3.75, 0.00, 0.00),  # "One argues the merits. One maps the fine print."  Blake+Morgan
    (3, 94.5, 100.3,   3.77, 0.00, 0.00),  # "And one fights to deny it..."  Alex
    (3,100.5, 106.0,   3.67, 0.00, 0.00),  # "They debate in the open, until the case is settled."  verdict
    (3,111.7, 113.6,   3.49, 0.00, 0.00),  # "Every word becomes a tamper-evident audit trail."  hash
    (3,108.6, 112.2,   4.16, 0.00, 0.00),  # "You stay in command. Approve, or override,"  hover
    (3,109.0, 111.2,   2.81, 0.00, 0.30),  # "the final word is always yours."  approve focus
    (2,  0.4,   5.0,   3.94, 0.30, 0.00),  # "Faster decisions. Reasoning you can defend."  scale
    (4,  0.0,   5.5,   5.50, 0.40, 0.50),  # "Recourse. Every claim deserves a fair fight."  end card
]


def pass1() -> Path:
    parts, labels = [], []
    for i, (idx, s, e, dur, fin, fout) in enumerate(BEATS):
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
    fc = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(BEATS)}:v=1:a=0[outv]"

    out = V / "final_video.mp4"
    cmd = ["ffmpeg", "-y"]
    for p in INPUTS:
        cmd += ["-i", str(p)]
    cmd += ["-loop", "1", "-t", "6", "-i", str(ENDCARD)]  # input 4
    cmd += [
        "-filter_complex", fc, "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def pass2(silent: Path) -> Path:
    mixed = V / "mixed.m4a"
    # asplit the VO: one copy keys the sidechain (padded so it never truncates the music),
    # the other is the actual voice in the mix.
    amix = (
        "[1:a]asplit=2[k0][v0];"
        "[k0]apad=pad_dur=4[key];"
        "[2:a]volume=0.20,afade=t=in:st=0:d=1.5,afade=t=out:st=44.8:d=2.2[mus0];"
        "[mus0][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=350[mus];"
        "[v0]volume=1.12[vo];"
        "[vo][mus]amix=inputs=2:normalize=0:duration=longest[a]"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(silent), "-i", str(A / "voiceover.mp3"), "-i", str(A / "music.mp3"),
        "-filter_complex", amix, "-map", "[a]",
        "-c:a", "aac", "-b:a", "192k", str(mixed),
    ], check=True)

    style = (
        "Fontname=Arial\\,Fontsize=15\\,Bold=1\\,PrimaryColour=&H00FFFFFF&\\,"
        "OutlineColour=&H00141414&\\,BorderStyle=1\\,Outline=2\\,Shadow=1\\,"
        "MarginV=46\\,Alignment=2"
    )
    out = V / "final.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(mixed),
        "-vf", f"subtitles=assets/subs.srt:force_style='{style}'",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",  # normalize to web commercial loudness
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
    print(f"final.mp4 -> {fv}  ({dur}s, {fv.stat().st_size // 1024} KB)")
