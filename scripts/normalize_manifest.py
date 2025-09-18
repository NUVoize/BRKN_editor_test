import os, json, glob

ROOT = r"E:\n8n_docker_strick"
IN_DIR  = os.path.join(ROOT, "videos_in")
OUT_DIR = os.path.join(ROOT, "videos_out")
MF      = os.path.join(OUT_DIR, "manifest.json")

# collect absolute paths
files = []
for ext in ("*.mp4","*.mov","*.mkv","*.m4v","*.avi"):
    files.extend(glob.glob(os.path.join(IN_DIR, ext)))
files = sorted(os.path.abspath(p) for p in files if os.path.exists(p))

# write a single, simple shape: top-level list of dicts (path,t0,t1)
items = [{"path": p, "t0": 0.0, "t1": -1.0} for p in files]

os.makedirs(OUT_DIR, exist_ok=True)
with open(MF, "w", encoding="utf-8") as f:
    json.dump(items, f, indent=2)
print(f"Normalized manifest with {len(items)} items -> {MF}")

