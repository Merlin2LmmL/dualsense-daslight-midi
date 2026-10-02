@echo off
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name dualsense-daslight-midi --hidden-import mido.backends.rtmidi app.py
echo Done: dist\dualsense-daslight-midi.exe
pause
