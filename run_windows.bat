@echo off
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 7860
pause
