@echo off
echo Installing Python dependencies...
pip install pyinstaller mss Pillow websocket-client

echo.
echo Building screenshare-client.exe ...
pyinstaller --onefile --name screenshare-client client.py

echo.
echo Done! Your exe is at:  dist\screenshare-client.exe
echo.
echo Before running, open client.py and set:
echo   SERVER_URL = "ws://your-deployed-server"
echo   SECRET = "your-secret"
echo.
pause
