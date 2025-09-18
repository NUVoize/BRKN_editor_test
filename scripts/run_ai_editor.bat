@echo off
REM AI Video Editor - Multi-Angle Scene Builder
REM Reads original videos from videos_in with natural audio

echo ========================================
echo AI Video Editor - Multi-Angle Scenes
echo ========================================

REM Set your paths - CORRECTED
set META_DIR=E:\n8n_docker_strick\data\meta
set VIDEOS_IN=E:\n8n_docker_strick\videos_in
set OUTPUT_DIR=E:\n8n_docker_strick\videos_out
set SCRIPTS_DIR=E:\n8n_docker_strick\scripts

echo.
echo Input videos: %VIDEOS_IN%
echo Output folder: %OUTPUT_DIR%
echo Meta data: %META_DIR%
echo.

REM Check if directories exist
if not exist "%VIDEOS_IN%" (
    echo [ERROR] Videos input directory not found: %VIDEOS_IN%
    pause
    exit /b 1
)

if not exist "%META_DIR%" (
    echo [ERROR] Meta directory not found: %META_DIR%
    pause
    exit /b 1
)

REM Create output directory if needed
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    echo Created output directory: %OUTPUT_DIR%
)

REM Run AI Video Editor
echo Starting AI Video Editor...
echo.
cd "%SCRIPTS_DIR%"
python ai_video_editor.py "%META_DIR%" "%VIDEOS_IN%" "%OUTPUT_DIR%"

echo.
echo ========================================
echo AI Video Editor Complete!
echo ========================================
echo.
echo Check output folder for:
echo - scene_*.mp4 (multi-angle scenes)
echo - loop_*.mp4 (seamless loops)
echo.

REM Show created files
echo Files created:
dir /b "%OUTPUT_DIR%\scene_*.mp4" 2>nul
dir /b "%OUTPUT_DIR%\loop_*.mp4" 2>nul

echo.
echo Would you like to:
echo 1. Open output folder
echo 2. Play latest scene
echo 3. Exit
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    explorer "%OUTPUT_DIR%"
) else if "%choice%"=="2" (
    for /f %%i in ('dir /b /o:d "%OUTPUT_DIR%\scene_*.mp4" 2^>nul') do set latest=%%i
    if defined latest (
        start "" "%OUTPUT_DIR%\%latest%"
    ) else (
        echo No scene files found.
    )
)

pause