import json, os, sys

MF   = r"E:\n8n_docker_strick\videos_out\manifest.json"
OUTF = r"E:\n8n_docker_strick\videos_out\concat.txt"

def coerce_to_paths(m):
    if isinstance(m, list):
        if m and isinstance(m[0], dict) and 'path' in m[0]:
            return [it['path'] for it in m]
        return [str(x) for x in m]
    if isinstance(m, dict):
        for key in ('items','clips','segments','paths','files'):
            if key in m:
                v = m[key]
                if isinstance(v, list):
                    if v and isinstance(v[0], dict) and 'path' in v[0]:
                        return [it['path'] for it in v]
                    return [str(x) for x in v]
    return []

with open(MF, "r", encoding="utf-8") as f:
    m = json.load(f)

paths = coerce_to_paths(m)

lines = []
for p in paths:
    if not os.path.isabs(p):
        p = os.path.abspath(p)
    lines.append(f'file "{p}"\n')

os.makedirs(os.path.dirname(OUTF), exist_ok=True)
with open(OUTF, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(lines)

print(f"wrote {len(lines)} lines -> {OUTF}")
if not lines:
    sys.exit(1)
