@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Compile Blue Mesa for Counter-Strike 1.6
where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
echo Python 3 is required for this compile helper.
echo You can also compile the MAP directly in Hammer or J.A.C.K.
echo Read README.md for the editor configuration and four compiler stages.
pause
exit /b 1
:use_py
py -3 "%~dp0compile_map.py" %*
goto finished
:use_python
python "%~dp0compile_map.py" %*
:finished
set "build_result=%errorlevel%"
pause
exit /b %build_result%
