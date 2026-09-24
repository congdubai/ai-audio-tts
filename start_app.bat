@echo off
chcp 65001 > nul
echo ===================================================
echo   KHOI DONG HE THONG KOKORO VIETNAMESE TTS
echo   (React Frontend + FastAPI Backend)
echo ===================================================
echo.

echo [1/2] Dang khoi dong FastAPI Backend tai http://127.0.0.1:8000 ...
start "Kokoro TTS - Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Dang khoi dong React Frontend tai http://localhost:5173 ...
start "Kokoro TTS - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ===================================================
echo   He thong dang khoi chay!
echo   Hay mo trinh duyet tai: http://localhost:5173
echo ===================================================
timeout /t 5
start http://localhost:5173
