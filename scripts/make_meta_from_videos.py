#!/usr/bin/env python3
"""
make_meta_from_videos.py
Scans VIDEOS_IN for video files and creates simple meta JSONs in META_DIR.
- Uses sequential fallback timing with DEFAULT_CLIP_SECS per clip (default 2.0s).
- Won't overwrite existing JSONs unless --force is passed.
Usage:
  py -3 make_meta_from_videos.py E:\n8n-docker\videos_in E:\n8n-docker\data\meta 2.5
"""
import sys, os
from pathlib import Path
import json

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <VIDEOS_IN> <META_DIR> [DEFAULT_CLIP_SECS]", file=sys.stderr)
        sys.exit(2)
    videos_in = Path(sys.argv[1]).resolve()
    meta_dir  = Path(sys.argv[2]).resolve()
    dur = float(sys.argv[3]) if len(sys.argv) >= 4 else 2.0
    force = any(arg == "--force" for arg in sys.argv[4:])

    meta_dir.mkdir(parents=True, exist_ok=True)
    if not videos_in.exists():
        print(f"ERROR: VIDEOS_IN not found: {videos_in}", file=sys.stderr); sys.exit(3)

    exts = {".mp4",".mov",".mkv",".avi",".webm"}
    paths = sorted([p for p in videos_in.iterdir() if p.suffix.lower() in exts and p.is_file()])
    if not paths:
        print(f"No videos found in {videos_in}", file=sys.stderr); sys.exit(4)

    t = 0.0
    count = 0
    for p in paths:
        name = p.stem
        jp = meta_dir / f"{name}.json"
        if jp.exists() and not force:
            # skip existing to avoid destroying your annotations
            continue
        obj = {
            "file": p.name,
            "start": {"seconds": t},
            "end":   {"seconds": t + dur},
            "base": name
        }
        with open(jp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        t += dur
        count += 1
    print(f"[OK] wrote {count} meta files to {meta_dir} (dur={dur}s per clip)")

if __name__ == "__main__":
    main()
