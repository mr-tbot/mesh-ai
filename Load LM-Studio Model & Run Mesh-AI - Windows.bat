@echo off
cd /d "%USERPROFILE%\Desktop\meshtastic-ai"  # Your Meshtastic-AI directory

echo Unloading any previously loaded model before reloading...
lms unload <INSERT MODEL IDENTIFIER HERE>
timeout /t 2 /nobreak >nul

echo Loading defined model...
lms load <INSERT MODEL IDENTIFIER HERE>
timeout /t 5 /nobreak >nul

echo Running Meshtastic-AI...
python meshtastic_ai.py

pause
