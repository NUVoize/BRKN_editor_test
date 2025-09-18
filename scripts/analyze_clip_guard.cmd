@echo off
py -3 "%~dp0analyze_clip_guard.py" %*
exit /b %ERRORLEVEL%
