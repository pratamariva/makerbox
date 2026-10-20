# Build MakerBox.exe on Windows. Run from the makercase-box folder:
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
# Produces dist\MakerBox.exe
pip install pyinstaller
pyinstaller --onefile --windowed --name MakerBox src\app.py
Write-Host "Done -> dist\MakerBox.exe"
