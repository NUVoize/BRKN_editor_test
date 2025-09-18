#!/usr/bin/env python3
import os, sys, glob, json
from pathlib import Path
import numpy as np
def coerce_float(v, f=None):
    if v is None: return f
    if isinstance(v,(int,float)): return float(v)
    if isinstance(v,str):
        try: return float(v.strip())
        except: return f
    if isinstance(v,list) and v: return coerce_float(v[0], f)
    if isinstance(v,dict):
        for k in ("value","val","sec","secs","second","seconds","s","start","end"):
            if k in v: 
                out = coerce_float(v[k], f)
                if out is not None: return out
        if len(v)==1: return coerce_float(next(iter(v.values())), f)
    return f
def coerce_int(v, f=None):
    x = coerce_float(v, None)
    return int(round(x)) if x is not None else f
def norm_key(k:str)->str:
    k=k.replace("-","_").replace(" ","_"); kl=k.lower()
    if kl in {"emb_end","embend","end_emb","end"}: return "emb_end"
    if kl in {"emb_start","embstart","start_emb","start","t0"}: return "emb_start"
    if kl in {"fps","frame_rate","framerate"}: return "fps"
    if kl in {"frames","n_frames","frame_count"}: return "frames"
    if kl in {"duration","duration_s","secs","seconds"}: return "duration"
    if kl in {"path","file","filepath","file_path"}: return "path"
    return kl
def load_meta_files(meta_dir: Path):
    items=[]; problems=[]
    jps=sorted(glob.glob(str(meta_dir/"*.json")))
    if not jps: raise SystemExit(f"No .json files found in {meta_dir}")
    for jp in jps:
        try:
            raw=json.load(open(jp,"r",encoding="utf-8"))
        except Exception as e:
            problems.append((jp,f"json error: {e}")); continue
        norm={norm_key(k):v for k,v in raw.items()}
        path=norm.get("path"); emb_start=norm.get("emb_start"); emb_end=norm.get("emb_end")
        fps=norm.get("fps"); frames=norm.get("frames"); duration=norm.get("duration")
        path_str=str(path) if path is not None else None
        t0=coerce_float(emb_start); t1=coerce_float(emb_end)
        fps_f=coerce_float(fps); frames_i=coerce_int(frames); dur_f=coerce_float(duration)
        if t1 is None:
            if dur_f is not None and t0 is not None: t1=t0+dur_f
            elif frames_i is not None and fps_f and t0 is not None: t1=t0+(frames_i/fps_f) if fps_f else None
        miss=[]
        if path_str is None: miss.append("path")
        if t0 is None: miss.append("emb_start")
        if t1 is None: miss.append("emb_end (or frames+fps/duration)")
        if miss:
            problems.append((jp, f"missing/invalid: {', '.join(miss)}; keys: {list(norm.keys())}")); continue
        items.append({"path":path_str,"emb_start":float(t0),"emb_end":float(t1),
                      "fps":float(fps_f) if fps_f is not None else None,
                      "frames":int(frames_i) if frames_i is not None else None,
                      "duration":float(dur_f) if dur_f is not None else None})
    if problems:
        lines=["Metadata problems detected:"]+[f"- {p}: {why}" for p,why in problems[:12]]
        if len(problems)>12: lines.append(f"(and {len(problems)-12} more ...)")
        raise SystemExit("\n".join(lines))
    if not items: raise SystemExit(f"All metadata invalid in {meta_dir}")
    return items
if len(sys.argv)<3:
    sys.stderr.write(f"Usage: {sys.argv[0]} <META_DIR> <OUT_DIR>\n")
    sys.exit(2)
META_DIR=Path(sys.argv[1]).resolve(); OUT_DIR=Path(sys.argv[2]).resolve(); OUT_DIR.mkdir(parents=True, exist_ok=True)
items=load_meta_files(META_DIR)
S=np.array([i["emb_start"] for i in items],dtype=np.float32)
E=np.array([i["emb_end"] for i in items],dtype=np.float32)
print(f"[OK] Loaded {len(items)} items from {META_DIR}")
print("First 5 starts:", S[:5]); print("First 5 ends:  ", E[:5])
