import json, os, glob, subprocess as sp

def probe_dur(p):
    try:
        out = sp.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nokey=1:noprint_wrappers=1','--', p],
                              stderr=sp.DEVNULL, universal_newlines=True).strip()
        return max(0.0, round(float(out), 3))
    except Exception:
        return 0.0

def main():
    import sys
    in_dir  = sys.argv[1] if len(sys.argv)>1 else r'E:\n8n-docker\videos_in'
    out_dir = sys.argv[2] if len(sys.argv)>2 else r'E:\n8n-docker\videos_out'
    files = sorted(glob.glob(os.path.join(in_dir, '*.mp4')))
    items = []
    for p in files:
        d = probe_dur(p)
        t1 = d if d > 0 else 9_999_999.0   # fallback if ffprobe is missing
        items.append({'path': p, 't0': 0, 't1': t1})
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'version': 1, 'items': items}, f, ensure_ascii=False, indent=2)
    print(f"[gen_manifest] wrote {len(items)} items -> {os.path.join(out_dir,'manifest.json')}")

if __name__ == '__main__':
    main()
