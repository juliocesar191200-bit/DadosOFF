@echo off
title DadosOFF - Gerando EXE
cd /d "%~dp0"
REM Requer Python 3.10+ no PATH e a pasta "ffmpeg" (ffmpeg.exe + ffprobe.exe) ao lado deste arquivo.
python -m pip install flask pyinstaller werkzeug --quiet
python -m PyInstaller --noconfirm DadosOFF.spec
if exist "ffmpeg" xcopy /e /i /y "ffmpeg" "dist\ffmpeg" >nul
echo Pronto: dist\DadosOFF.exe
pause
