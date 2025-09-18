@echo off
echo AI Video Workflow with Enhanced Audio - Keep under 15 clips for best results
echo.

:: Clean previous results
echo Cleaning previous results...
del /q E:\n8n_docker_strick\data\meta\*.json 2>nul
del /q E:\n8n_docker_strick\videos_out\*.json 2>nul
del /q E:\n8n_docker_strick\videos_out\*.mp4 2>nul
del /q E:\n8n_docker_strick\videos_out\*.wav 2>nul

:: Count clips
for /f %%i in ('dir /b E:\n8n_docker_strick\videos_in\*.mp4 2^>nul ^| find /c /v ""') do set clip_count=%%i
echo Found %clip_count% video clips

if %clip_count% GTR 15 (
    echo WARNING: %clip_count% clips found. Recommend 15 or fewer for best results.
    pause
)

:: Step 1: AI Analysis
echo.
echo Step 1: Running AI analysis on each clip...
cd /d E:\n8n_docker_strick\scripts
for %%f in (E:\n8n_docker_strick\videos_in\*.mp4) do (
    echo Analyzing %%~nxf
    python analyze_clip.py "%%f"
)

:: Copy metadata to correct location if needed
if exist "E:\n8n-docker\data\meta\*.json" (
    echo Copying metadata to correct location...
    copy "E:\n8n-docker\data\meta\*.json" "E:\n8n_docker_strick\data\meta\" >nul
)

:: Step 2: Smart Sequencing
echo.
echo Step 2: Finding optimal sequence...
python smart_sequence_clips.py E:\n8n_docker_strick\data\meta E:\n8n_docker_strick\videos_out

:: Step 3: Loop Detection and Trimming
echo.
echo Step 3: Removing AI loop resets for smoother flow...
python smart_loop_trimmer.py E:\n8n_docker_strick\videos_out

:: Step 4: Final Video Generation (fallback if audio fails)
echo.
echo Step 5: Creating fallback video (video-only)...
python video_only_stitcher.py E:\n8n_docker_strick\videos_out

echo.
echo Workflow complete! 
echo Check these outputs:
echo - combined_smooth_loops.mp4 (video only, loop-trimmed)
echo - enhanced_audio.wav (procedural audio track)
echo - combined_smooth_loops_enhanced_audio.mp4 (FINAL VIDEO WITH AUDIO)
echo.
pause