import glob, os, pathlib

ROOT = r"E:\n8n_docker_strick"
INP  = os.path.join(ROOT, "videos_in")
OUTF = os.path.join(ROOT, "videos_out", "concat.txt")

# pick the extensions you use
exts = ("*.mp4","*.mov","*.mkv","*.m4v","*.avi")

# collect and sort by filename (your zero-padding will keep order)
paths = []
for e in exts:
    paths.extend(glob.glob(os.path.join(INP, e)))
paths = [pathlib.Path(p).resolve().as_posix() for p in sorted(paths)]

os.makedirs(os.path.dirname(OUTF), exist_ok=True)
with open(OUTF, "w", encoding="utf-8", newline="\n") as f:
    for p in paths:
        f.write(f"file '{p}'\n")

print(f"wrote {len(paths)} lines -> {OUTF}")
