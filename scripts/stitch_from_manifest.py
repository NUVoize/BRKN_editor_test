#!/usr/bin/env python3
"""
stitch_from_manifest.py
Reads OUT_DIR/manifest.json and concatenates the listed video files
into OUT_DIR/combined.mp4 using ffmpeg. Re-encodes for compatibility.
...
"""
import json, os, subprocess, sys
from pathlib import Path
TRIM_MODE = int(os.getenv("TRIM_MODE", "0"))
FFMPEG = os.getenv("FFMPEG", "ffmpeg")
def die(msg, code=2):
    sys.stderr.write(msg + "\n"); sys.exit(code)
def main():
    if len(sys.argv) < 2: die(f"Usage: {sys.argv[0]} <OUT_DIR>")
    out_dir = Path(sys.argv[1]).resolve()
    manifest = out_dir / "manifest.json"
    if not manifest.exists(): die(f"manifest.json not found in {out_dir}")
    try: items = json.load(open(manifest, "r", encoding="utf-8"))
    except Exception as e: die(f"Could not read manifest: {e}")
    if not isinstance(items, list) or not items: die("manifest.json has no items")
    def keyf(it): return (float(it.get("t0", 0.0)), float(it.get("t1", 0.0)))
    items = sorted(items, key=keyf)
    files, missing = [], []
    for it in items:
        p = it.get("path"); 
        if not p: continue
        p = str(p)
        if not os.path.exists(p): missing.append(p)
        else: files.append(p)
    if missing: die("Missing files listed in manifest:\n" + "\n".join(f"- {m}" for m in missing))
    if not files: die("No existing files in manifest paths")
    output_mp4 = out_dir / "combined.mp4"
    if TRIM_MODE == 0:
        concat_txt = out_dir / "concat.txt"
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in files:
                f.write(f"file '{p}'\n")
        cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", str(output_mp4)]
        print("Running:", " ".join(cmd))
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            print(proc.stdout); print(proc.stderr, file=sys.stderr)
            die("ffmpeg failed (concat mode)", proc.returncode)
        print(f"[OK] Wrote {output_mp4}"); sys.exit(0)
    filter_parts = []; inputs = []; idx = 0
    for it in items:
        p = it.get("path"); s = it.get("clip_start", 0.0); e = it.get("clip_end", None)
        if not p: continue
        if not os.path.exists(p): die(f"Missing file: {p}")
        inputs.extend(["-i", str(p)])
        if e is None:
            filter_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS[v{idx}];[{idx}:a]asetpts=N/SR/TB[a{idx}]")
        else:
            dur = float(e) - float(s)
            if dur <= 0: die(f"Invalid clip range for {p}: start={s} end={e}")
            filter_parts.append(
                f"[{idx}:v]trim=start={s}:duration={dur},setpts=PTS-STARTPTS[v{idx}];"
                f"[{idx}:a]atrim=start={s}:duration={dur},asetpts=N/SR/TB[a{idx}]"
            )
        idx += 1
    n = idx
    concat_inputs_v = "".join([f"[v{i}]" for i in range(n)])
    concat_inputs_a = "".join([f"[a{i}]" for i in range(n)])
    filter_full = ";".join(filter_parts) + f";{concat_inputs_v}{concat_inputs_a}concat=n={n}:v=1:a=1[v][a]"
    cmd = [FFMPEG, "-y"] + inputs + ["-filter_complex", filter_full, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", str(output_mp4)]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stdout); print(proc.stderr, file=sys.stderr)
        die("ffmpeg failed (trim mode)", proc.returncode)
    print(f"[OK] Wrote {output_mp4}"); sys.exit(0)

if __name__ == "__main__":
    main()
