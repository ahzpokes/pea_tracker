# PEA Dual Momentum

Suivi personnel de stratégie PEA ETF Dual Momentum.

## Phase 1 — MVP données et interface

Cette phase fournit :
- CRUD des instruments (ETF / benchmarks)
- Import CSV manuel des prix
- Dashboard statique
- Frontend Vite + Tailwind CSS v4

## Démarrage

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows : .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000