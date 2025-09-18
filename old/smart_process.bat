@echo off
:: 1) Clean old meta + manifest
del /q E:\n8n-docker\data\meta\*.json 2>nul
del /q E:\n8n-docker\videos_out\manifest.json 2>nul
del /q E:\n8n-docker\videos_out\smart_manifest.json 2>nul

:: 2) AI analyze each clip
echo Starting AI analysis of clips...
for %%f in (E:\n8n-docker\videos_in\*.mp4) do (
    echo Analyzing %%~nxf
    py -3 "E:\n8n-docker\scripts\analyze_clip.py" "%%f"
)

:: 3) Smart sequencing (if smart_sequence_clips.py exists)
if exist "E:\n8n-docker\scripts\smart_sequence_clips.py" (
    echo Creating smart sequence...
    py -3 "E:\n8n-docker\scripts\smart_sequence_clips.py" "E:\n8n-docker\data\meta" "E:\n8n-docker\videos_out"
) else (
    echo Smart sequencer not found, using fallback...
    py -3 "E:\n8n-docker\scripts\sequence_and_assemble_verbose.py" "E:\n8n-docker\data\meta" "E:\n8n-docker\videos_out"
)

:: 4) Stitch
echo Stitching...
py -3 "E:\n8n-docker\scripts\stitch_from_manifest.py" "E:\n8n-docker\videos_out"