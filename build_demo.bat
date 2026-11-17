@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --name SkyCityDemo --add-data "generated_assets;generated_assets" game.py
echo.
echo Build complete: dist\SkyCityDemo\SkyCityDemo.exe
pause
