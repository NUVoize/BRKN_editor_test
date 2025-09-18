@echo off
setlocal
set "ROOT=%~dp0"
set "OUT_DIR=%ROOT%videos_out"
set "SCRIPTS=%ROOT%scripts"

mkdir "%OUT_DIR%" 2>nul

echo [1/3] Normalize (ok to skip if you like)
py -3 "%SCRIPTS%\normalize_manifest.py" || echo (normalize skipped)

echo [2/3] Refine (ok if it no-ops)
py -3 "%SCRIPTS%\refine_manifest_margins.py" "%OUT_DIR%" || echo (refine skipped)

echo [2.5/3] Build concat list from videos_in
py -3 "%SCRIPTS%\make_concat_from_dir.py" || goto :fail

echo [3/3] Stitch with ffmpeg
ffmpeg -y -f concat -safe 0 -i "%OUT_DIR%\concat.txt" -c copy "%OUT_DIR%\joined_final.mp4" || goto :reencode

echo DONE -> "%OUT_DIR%\joined_final.mp4"
exit /b 0

:reencode
echo Streams differ; re-encoding...
ffmpeg -y -f concat -safe 0 -i "%OUT_DIR%\concat.txt" -c:v libx264 -preset veryfast -crf 18 -c:a aac -b:a 192k "%OUT_DIR%\joined_final.mp4" || goto :fail
echo DONE -> "%OUT_DIR%\joined_final.mp4"
exit /b 0

:fail
echo FAILED. See messages above.
exit /b 1
