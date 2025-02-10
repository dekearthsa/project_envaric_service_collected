@echo off
:start
echo Running app.py...
python3 app.py
echo App crashed or closed. Restarting...
timeout /t 5 /nobreak
goto start
