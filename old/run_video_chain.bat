@echo off
setlocal

REM === Resolve this folder (with trailing backslash) ===
set "ROOT=%~dp0"

REM === Standardized paths (all relative to this copy) ===
set "IN_DIR=%ROOT%videos_in"
set "OUT_DIR=%ROOT%videos_out"
set "META_DIR=%ROOT%data\meta"
set "TMP_DIR=%ROOT%data\tmp"
set "SCRIPTS=%ROOT%scripts"

REM === Ensure folders exist ===
mkdir "%OUT_DIR%" 2>nul
mkdir "%META_DIR%" 2>nul
mkdir "%TMP_DIR%" 2>nul

echo [0/4] Sanity: inputs present?
dir /b "%IN_DIR%\*.mp4" "%IN_DIR%\*.mov" "%IN_DIR%\*.mkv" "%IN_DIR%\*.m4v" "%IN_DIR%\*.avi" >nul 2>&1
if errorlevel 1 (
  echo No input videos found in "%IN_DIR%".
  echo Put files in videos_in and re-run.
  exit /b 1
)

echo [1/4] Build manifest
py -3 "%SCRIPTS%\gen_manifest.py" "%IN_DIR%" "%OUT_DIR%"
if errorlevel 1 goto :fail

echo [1.5/4] Validate manifest has items (inline)
py -3 -c "import json,sys,os; p=r'%OUT_DIR%\manifest.json'; d=json.load(open(p,'r',encoding='utf-8')); n=len(d.get('items', d)); print('items=',n); sys.exit(0 if n else 1)"
if errorlevel 1 (
  echo manifest has 0 items. Check file types in "%IN_DIR%".
  goto :fail
)

echo [2/4] Stitch (pre)
py -3 "%SCRIPTS%\stitch_from_manifest.py" "%OUT_DIR%"
if errorlevel 1 goto :fail

echo [3/4] Refine margins
set "SAFE_LEAD_SEC=0.5"
set "SAFE_TAIL_SEC=0.5"
set "MIN_DUR_SEC=1.5"
py -3 "%SCRIPTS%\refine_manifest_margins.py" "%OUT_DIR%"
if errorlevel 1 goto :fail

echo [4/4] Stitch (final)
py -3 "%SCRIPTS%\stitch_from_manifest.py" "%OUT_DIR%"
if errorlevel 1 goto :fail

echo DONE. Outputs in: "%OUT_DIR%"
goto :eof

:fail
echo FAILED. Check errors above. Ensure inputs are in "%IN_DIR%".
exit /b 1
