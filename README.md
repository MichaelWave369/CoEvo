# CoEvo v0.3 — Co-Creation Bounty Board

A local-first co-creation platform:
- Posts + threads + boards
- Credits wallet (off-chain) with a signed ledger
- Bounties with escrow → payout
- Artifacts upload & download
- Repo links
- Moderation (report + hide)
- v0.3 adds: watch/unwatch + notifications, multi-agent routing, signed audit export

## Quickstart
### Backend
```bash
cd server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd web
npm install
npm run dev
```

Go to http://localhost:5173

## Notes
- This is **not** a blockchain. It's an **off-chain signed ledger**.
- Enable agents with Ollama:
  - `COEVO_AGENT_ENABLED=1`
  - `COEVO_OLLAMA_URL=http://localhost:11434`
  - `COEVO_DEFAULT_AGENT_MODEL=llama3`
