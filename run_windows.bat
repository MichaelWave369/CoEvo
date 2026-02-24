\
@echo off
setlocal
echo Starting CoEvo backend...
cd server
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
start "" uvicorn app.main:app --reload --port 8000

echo Starting CoEvo web...
cd ..\web
if not exist node_modules (
  npm install
)
start "" npm run dev

echo Done. Open http://localhost:5173
endlocal
