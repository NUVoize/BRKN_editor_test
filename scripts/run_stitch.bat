@echo off
set OUT_DIR=E:\n8n-docker\videos_out
py -3 "%~dp0stitch_from_manifest.py" "%OUT_DIR%"
pause
