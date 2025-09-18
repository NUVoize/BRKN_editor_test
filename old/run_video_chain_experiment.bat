@echo off
setlocal EnableDelayedExpansion

rem === paths ===
set "ROOT=E:\n8n-docker"
set "IN=%ROOT%\videos_in"
set "OUT=%ROOT%\videos_out"
set "SCRIPTS=%ROOT%\scripts"

rem === refine parameters ===
set SAFE_LEAD_SEC=0.50
set SAFE_TAIL_SEC=0.50
set MIN_DUR_SEC=1.50

if not exist "%OUT%" mkdir "%OUT%"

echo [1/4] Build manifest
py -3 "%SCRIPTS%\gen_manifest.py" "%IN%" "%OUT%" || goto :err

echo [1.5/4] Validate manifest has items
py -3 -c "import json,sys; m=json.load(open(r'%OUT%\manifest.json','r',encoding='utf-8')); n=len(m.get('items',[])); print('  items =',n); sys.exit(0 if n else 1)" || goto :err

echo [2/4] Stitch (pre)
py -3 "%SCRIPTS%\stitch_from_manifest.py" "%OUT%" || goto :err

echo [3/4] Refine
py -3 "%SCRIPTS%\refine_manifest_margins.py" "%OUT%" || goto :err

echo [4/4] Restitch (refined)
py -3 "%SCRIPTS%\stitch_from_manifest.py" "%OUT%" || goto :err

echo Done. Output: %OUT%
exit /b 0
:err
echo FAILED. Check manifest and paths.
exit /b 1
