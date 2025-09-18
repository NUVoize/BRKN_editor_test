#!/usr/bin/env python3
"""
sequence_and_assemble_verbose.py  (v5)
- Reads meta JSONs that may NOT contain numeric times (start/end as descriptive dicts)
- If numeric times are unavailable, assigns times sequentially by filename with a default duration
- Prefixes relative file names with VIDEOS_IN
- Prints summary and writes manifest.json
"""

import os, sys, glob, json, re
from pathlib import Path

VIDEOS_IN = r"E:\n8n-docker\videos_in"
DEFAULT_DUR = float(os.getenv("DEFAULT_CLIP_SECS", "2.0"))  # fallback per-clip duration when no times are parseable

TIME_RE = re.compile(r"^(?:(\d+):)?(?:(\d{1,2}):)?(\d+(?:\.\d+)?)$")

def parse_time(v):
    if v is None: return None
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s.endswith("ms"):
            try: return float(s[:-2]) / 1000.0
            except: return None
        if s.endswith("s"):
            try: return float(s[:-1])
            except: pass
        try: return float(s)
        except: pass
        m = TIME_RE.match(s)
        if m:
            h, m_, s_ = m.groups()
            secs = float(s_)
            if m_: secs += 60.0 * float(m_)
            if h:  secs += 3600.0 * float(h)
            return secs
        return None
    if isinstance(v, dict):
        for k in ("value","val","sec","secs","second","seconds","s","ms","start","end","t0","t1","time","timestamp","duration"):
            out = parse_time(v.get(k))
            if out is not None: return out
        if len(v)==1:
            return parse_time(next(iter(v.values())))
        for vv in v.values():
            out = parse_time(vv)
            if out is not None: return out
    if isinstance(v, list) and v:
        return parse_time(v[0])
    return None

def norm_key(k:str)->str:
    return k.replace("-","_").replace(" ","_").lower()

NESTED_HINT_KEYS = ("base","timing","meta","embedding","range","clip")

def resolve_path(norm):
    p = norm.get("path")
    if p is None and "file" in norm: p = norm.get("file")
    if p is None: return None
    p = str(p)
    if (len(p)>2 and p[1]==":") or p.startswith("\\\\"): return p
    return str(Path(VIDEOS_IN)/p)

def pull_time_any(raw, norm, which):
    alt = "t0" if which=="emb_start" else "t1"
    literal = "start" if which=="emb_start" else "end"
    for label, v in (("top:"+which, norm.get(which)),
                     ("top:"+alt,   norm.get(alt)),
                     ("top:"+literal, raw.get(literal))):
        t = parse_time(v)
        if t is not None: return t, label
    for cont_key in NESTED_HINT_KEYS:
        cont = raw.get(cont_key)
        if isinstance(cont, dict):
            for k in (which, alt, literal, "start", "end", "time", "timestamp"):
                t = parse_time(cont.get(k))
                if t is not None: return t, f"nested:{cont_key}.{k}"
            for ck, cv in cont.items():
                t = parse_time(cv)
                if t is not None: return t, f"nested:{cont_key}.{ck}"
    for ck, cv in raw.items():
        t = parse_time(cv)
        if t is not None: return t, f"scan_top:{ck}"
    return None, "missing"

def load_items(meta_dir: Path):
    raw_items = []
    problems = []
    paths = sorted(glob.glob(str(meta_dir / "*.json")))
    if not paths:
        problems.append(("*", f"No .json files found in {meta_dir}"))
        return [], problems
    for jp in paths:
        try:
            raw = json.load(open(jp, "r", encoding="utf-8"))
        except Exception as e:
            problems.append((jp, f"json error: {e}"))
            continue
        norm = {norm_key(k): v for k, v in raw.items()}
        resolved_path = resolve_path(norm)
        t0, src0 = pull_time_any(raw, norm, "emb_start")
        t1, src1 = pull_time_any(raw, norm, "emb_end")
        raw_items.append({"meta": jp, "path": resolved_path, "t0": t0, "t1": t1, "src0": src0, "src1": src1})
    return raw_items, problems

def apply_sequential_fallback(items):
    """If any item lacks numeric t0/t1, assign sequential slots sorted by filename with DEFAULT_DUR."""
    need_fallback = any(i["t0"] is None or i["t1"] is None for i in items)
    if not need_fallback: return items, False
    # Sort by video filename to get a stable order
    items_sorted = sorted(items, key=lambda i: (Path(i["path"]).name if i["path"] else i["meta"]))
    t = 0.0
    for it in items_sorted:
        it["t0"] = float(t)
        it["t1"] = float(t + DEFAULT_DUR)
        it["src0"] = it.get("src0","fallback:sequential")
        it["src1"] = it.get("src1","fallback:sequential")
        t += DEFAULT_DUR
    return items_sorted, True

def analyze(items):
    items = sorted(items, key=lambda x: (x["t0"], x["t1"]))
    gaps, overlaps = [], []
    if not items: return items, gaps, overlaps
    prev_end = items[0]["t0"]
    for i, it in enumerate(items):
        if i>0:
            if it["t0"] > prev_end:
                gaps.append((items[i-1]["meta"], it["meta"], items[i-1]["t1"], it["t0"], it["t0"]-items[i-1]["t1"]))
            elif it["t0"] < prev_end:
                overlaps.append((items[i-1]["meta"], it["meta"], it["t0"]-prev_end))
        prev_end = max(prev_end, it["t1"])
    return items, gaps, overlaps

def main():
    if len(sys.argv) < 3:
        sys.stderr.write(f"Usage: {sys.argv[0]} <META_DIR> <OUT_DIR>\n")
        sys.exit(2)
    meta_dir = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_items, problems = load_items(meta_dir)
    if problems:
        for p, why in problems: print(f"Problem: {p}: {why}")

    # If any lack times, assign sequential fallback
    items, used_fallback = apply_sequential_fallback(raw_items)

    # Validate presence of path
    missing_path = [it for it in items if not it["path"]]
    if missing_path:
        print("Metadata problems detected: missing file path in:")
        for it in missing_path[:10]:
            print(f"- {it['meta']}")
        if len(missing_path) > 10:
            print(f"(and {len(missing_path)-10} more ...)")
        sys.exit(3)

    items, gaps, overlaps = analyze(items)

    print(f"[OK] {len(items)} items  (sequential_fallback={'YES' if used_fallback else 'NO'}, default_dur={DEFAULT_DUR}s)")
    print(f"First start: {items[0]['t0']:.3f}  Last end: {items[-1]['t1']:.3f}")
    print(f"Gaps: {len(gaps)}  Overlaps: {len(overlaps)}")

    print("\nItems (first 20):")
    for it in items[:20]:
        print(f"- {Path(it['meta']).name}: t0={it['t0']:.3f} ({it['src0']})  t1={it['t1']:.3f} ({it['src1']})  path={Path(it['path']).name}")

    manifest = out_dir / "manifest.json"
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"\nWrote manifest: {manifest}")
    sys.exit(0)

if __name__ == "__main__":
    main()
