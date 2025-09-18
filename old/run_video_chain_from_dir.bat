@echo off
setlocal
set "ROOT=%~dp0"
set "OUT=%ROOT%videos_out"
set "SCRIPTS=%ROOT%scripts"
mkdir "%OUT%" 2>nul

echo [1/2] Build concat list from videos_in
py -3 "%SCRIPTS%\make_concat_from_dir.py" || goto :fail

echo [2/2] Stitch (try stream copy first)
ffmpeg -y -f concat -safe 0 -i "%OUT%\concat.txt" -c copy "%OUT%\joined_final.mp4" && goto :done

echo Stream copy failed or unreadable — re-encoding (CFR 30fps)...
ffmpeg -y -f concat -safe 0 -i "%OUT%\concat.txt" -fflags +genpts -vf fps=30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a 192k "%OUT%\joined_final.mp4" && goto :done

echo No audio track; video-only re-encode...
ffmpeg -y -f concat -safe 0 -i "%OUT%\concat.txt" -fflags +genpts -vf fps=30 -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -movflags +faststart -an "%OUT%\joined_final.mp4" || goto :fail

:done
echo DONE -> "%OUT%\joined_final.mp4"
exit /b 0

:fail
echo FAILED. See messages above.
exit /b 1
