@echo off
cd /d "%USERPROFILE%\Desktop\mesh-ai"  # Your MESH-AI directory

echo Unloading any previously loaded model before reloading...
lms unload <INSERT MODEL IDENTIFIER HERE>
timeout /t 2 /nobreak >nul

echo Loading defined model...
lms load <INSERT MODEL IDENTIFIER HERE>
timeout /t 5 /nobreak >nul

echo Running MESH-AI...
python mesh_ai.py

pause
