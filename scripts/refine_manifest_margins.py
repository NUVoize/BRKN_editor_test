#!/usr/bin/env python3
"""
refine_manifest_margins.py
Apply strict margins to manifest.json:
- Reads <OUT_DIR>/manifest.json
- Adds clip_start/clip_end = [t0+LEAD, t1-TAIL]
- Drops clips where (clip_end - clip_start) < MIN_DUR
- Writes back to <OUT_DIR>/manifest.json (in-place), and also writes <OUT_DIR>/manifest_raw.json as backup

Env vars (defaults):
  SAFE_LEAD_SEC=0.30
  SAFE_TAIL_SEC=0.30
  MIN_DUR_SEC=1.00

Usage:
  py -3 refine_manifest_margins.py E:\n8n-docker\videos_out_strict
"""
import os, sys, json
from pathlib import Path

def die(msg, code=2):
    sys.stderr.write(msg + "\n"); sys.exit(code)

def main():
    if len(sys.argv) < 2:
        die(f"Usage: {sys.argv[0]} <OUT_DIR>")

    out_dir = Path(sys.argv[1]).resolve()
    manifest = out_dir / "manifest.json"
    if not manifest.exists():
        die(f"manifest.json not found in {out_dir}")

    LEAD = float(os.getenv("SAFE_LEAD_SEC", "0.30"))
    TAIL = float(os.getenv("SAFE_TAIL_SEC", "0.30"))
    MIN_DUR = float(os.getenv("MIN_DUR_SEC", "1.00"))

    try:
        items = json.load(open(manifest, "r", encoding="utf-8"))
    except Exception as e:
        die(f"Could not read manifest: {e}")

    # backup original
    backup = out_dir / "manifest_raw.json"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    refined = []
    for it in items:
        t0 = it.get("t0"); t1 = it.get("t1")
        if t0 is None or t1 is None:
            continue
        start = float(t0) + LEAD
        end   = float(t1) - TAIL
        if end - start >= MIN_DUR:
            it["clip_start"] = start
            it["clip_end"]   = end
            refined.append(it)

    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(refined, f, indent=2)

    print(f"[OK] Refined {len(refined)} clips (lead={LEAD}s, tail={TAIL}s, min_dur={MIN_DUR}s)")
    print(f"Backup of original manifest: {backup}")

if __name__ == "__main__":
    main()
