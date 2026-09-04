# LLM WebApp (LLM-Experiments)

Local LLM cockpit: Next.js UI + FastAPI backend, **MLX inference on Apple Silicon**, RAG, optional Google search, multi-model “agent” (HRM) pipeline, and LoRA training hooks.

This is a personal research stack, not a hosted product. Models are **not** in git. You need a Mac with enough unified memory and a Hugging Face token for gated weights.

## What it does

- **Chat / General / Code** modes with per-mode default models
- **Agent / reasoning (HRM)**: planner → executor → synthesizer, swapping MLX models in one process
- **Search controller**: a small Qwen-3B model decides whether to hit Google CSE, then the main model answers
- **RAG**: upload docs; in-memory FAISS + `all-MiniLM-L6-v2`
- **Sessions, memory, refinement** (accept / correct a turn)
- **Admin** (`/admin`): memory, model convert-to-MLX, training panel, system monitor

Use the app in **`frontend/`**. Root `src/` is an older “cockpit” landing page.

## Hardware (short)

| | |
| --- | --- |
| OS / chip | macOS, Apple Silicon |
| RAM | 32 GB unified for the full model map; 16 GB only for TinyLlama / 3B |
| Disk | tens of GB under `backend/models/` |
| Inference | MLX / Metal |
| Training demos | MLX LoRA **or** PyTorch MPS (TinyLlama) **or** CUDA QLoRA script |

Details, exact Hub folders, and RAM ballparks: [docs/HARDWARE_AND_MODELS.md](docs/HARDWARE_AND_MODELS.md).

## Quick start

```bash
git clone https://github.com/Xavierree/LLM-Experiments.git
cd LLM-Experiments

# secrets — never commit the real file
cp .env.example backend/.env
# edit backend/.env  (at least HF_TOKEN)

# backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# frontend
cd frontend
npm install
cd ..

# both processes
chmod +x start-app.sh
./start-app.sh
```

- UI: http://localhost:3000  
- API: http://localhost:8000  (`GET /` → `{"status":"running"}`)  
- Admin: http://localhost:3000/admin  

The UI talks to `localhost:8000` (HTTP + WebSocket). There is no `NEXT_PUBLIC_*` env yet.

## Environment

See [.env.example](.env.example). Copy it to **`backend/.env`** (`load_dotenv()` runs with cwd = `backend`).

| Variable | Required? | Used for |
| --- | --- | --- |
| `HF_TOKEN` | Yes for gated Hub models | Downloads and `snapshot_download` |
| `GOOGLE_API_KEY` | No | Custom Search |
| `GOOGLE_CSE_ID` | No | Custom Search engine id |
| `GROQ_API_KEY` / `CLOUD_API_KEY` | No | Unused in current code; listed for older local `.env` files |

`.gitignore` ignores `.env*`. `.env.example` is the only env file that should be in git.

## Models (defaults)

From `backend/app/core/models.py`:

| Mode / role | Model |
| --- | --- |
| Search controller | Qwen2.5-3B Instruct (MLX) |
| Chat / planner | Qwen2.5-7B Instruct bf16 |
| General / executor | Qwen2.5-14B Instruct 8-bit |
| Code / synthesis | Qwen3-32B MLX 4-bit |
| Code (direct) | DeepSeek Coder 6.7B Instruct (MLX) |

Put MLX snapshots in `backend/models/` (that directory is `HF_HOME`). Convert HF checkpoints from the admin Model Converter or `python -m mlx_lm.convert`.

Do **not** run `backend/download_*.py` without reading them — their Hub IDs lag the registry. `backend/download_dataset.py` still has a hardcoded `/Volumes/WD-SN850X/...` path.

## Layout

```
frontend/          Next.js 16 UI (the real app)
backend/           FastAPI, MLX loader, RAG, HRM, training scripts
  app/core/        models.py, rag.py, memory.py, logger.py
  app/services/    chat, search, hrm, refinement, ingestion, convert
  scripts/         LoRA (CUDA), gated downloads
  training/        MLX LoRA helper, TinyLlama DPO-on-MPS demo
src/               leftover Next pages
start-app.sh       backend :8000 + frontend :3000
docs/              hardware and model notes
```

## Training

- Mac / MLX: `backend/training/training-mlx.py` or `mlx_lm.lora`
- Mac / PyTorch MPS: `backend/training/training-demo.py` (TinyLlama DPO, batch sized for M1 Max 32 GB)
- NVIDIA: `backend/scripts/training_lora.py` + `backend/requirements-qlora.txt` (`bitsandbytes`)

Datasets and adapters are gitignored.

## Sharing this repo

Safe to share: source, README, `.env.example`, this docs folder.  
Not safe: `backend/.env`, Hub tokens, `backend/models/`, session logs, uploaded RAG files.

If something fails, it is usually (1) no `backend/.env`, (2) missing MLX snapshot, (3) not Apple Silicon, or (4) RAM too small for 14B/32B.
