import os, json, glob

ROOT = r"E:\n8n_docker_strick"
IN_DIR = os.path.join(ROOT, "videos_in")
OUT_DIR = os.path.join(ROOT, "videos_out")
MF = os.path.join(OUT_DIR, "manifest.json")

# 1) collect files (absolute paths)
files = []
for ext in ("*.mp4","*.mov","*.mkv","*.m4v","*.avi"):
    files.extend(glob.glob(os.path.join(IN_DIR, ext)))
files = sorted(os.path.abspath(p) for p in files if os.path.exists(p))

# 2) build a dict-based item with t0/t1 for refine script
items = [{"path": p, "t0": 0.0, "t1": -1.0} for p in files]

# 3) write a manifest that covers multiple expected shapes
data = {
    "items": items,
    "clips": items,
    "segments": items,
    "paths": [it["path"] for it in items],
    "files": [it["path"] for it in items]
}

os.makedirs(OUT_DIR, exist_ok=True)
with open(MF, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Rewrote manifest with {len(items)} items -> {MF}")
