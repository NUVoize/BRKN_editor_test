@echo off
cd /d E:\n8n_docker_strick\scripts
for %%f in (E:\n8n_docker_strick\videos_in\*.mp4) do (
    echo Analyzing %%~nxf
    python analyze_clip.py "%%f"
)
echo Done analyzing all clips