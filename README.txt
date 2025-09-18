
N8N GUARD PACK
==============

What this is
------------
A *drop-in* guard that prevents the "undefined" path bug from reaching your analyzer.
It requires **zero** edits to your existing Python analyzer. You only swap your n8n
Execute Command to call the guard `.cmd` instead.

Files
-----
- analyze_clip_guard.py   (cross-platform Python guard)
- analyze_clip_guard.cmd  (Windows-friendly wrapper that calls the Python guard)

Minimal usage in n8n
--------------------
In your Execute Command node, change your Command to:

    cmd /V:ON /C "E:\n8n-docker\scripts\analyze_clip_guard.cmd {$json.filePath || $json.clipPath || $json.path || $binary.data.filePath}"

(use the one JSON field that *actually* contains your written-to-disk path; the rest are fallbacks shown here)

Behavior
--------
- Exits with code 2 when input path is missing or 'undefined'.
- Exits with code 3 when the file does not exist on disk.
- Proxies stdout/stderr and exit code from your existing analyzer after validation.
- Sets LM Studio env vars so your analyzer can read them:
  - LMSTUDIO_MODEL=llama3-llava-next-8b:2
  - LMSTUDIO_URL=http://localhost:1234/v1/chat/completions
  - META_DIR=E:\n8n-docker\data\meta
  - TMP_DIR=E:\n8n-docker\data\tmp

Overriding the analyzer path
----------------------------
If your analyzer lives somewhere else, either:
- Set env var: ANALYZER_PY=E:\path\to\analyze_clip.py
- Or edit the `.cmd` and uncomment the line:
    set "ANALYZER_PY=E:\n8n-docker\scripts\analyze_clip.py"

Local test (here in the pack)
-----------------------------
You can simulate the guard’s validation in any Python environment:

    python analyze_clip_guard.py undefined        -> exit 2
    python analyze_clip_guard.py ""               -> exit 2
    python analyze_clip_guard.py C:\nope.mp4     -> exit 3

Place these two files in: E:\n8n-docker\scripts (on your Windows host).
Then point your Execute Command to the `.cmd` file above.
