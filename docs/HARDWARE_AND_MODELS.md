# Hardware, models, and local layout

This stack is built for **Apple Silicon + unified memory**, not a discrete NVIDIA box. Inference uses **MLX** (`mlx` / `mlx-lm`). PyTorch is still in the tree for LoRA/QLoRA scripts and Mac MPS experiments.

## Target machine (as coded)

Comments and defaults in the training scripts assume something in this class:

| Item | What the repo is written for |
| --- | --- |
| Chip | Apple Silicon (M1 Max called out; M2/M3+ also fine) |
| RAM | **32 GB unified memory minimum** for the full model set. 16 GB can run TinyLlama / Qwen 3B 4-bit only. |
| GPU API | Metal via MLX for inference. PyTorch **MPS** for some training demos (`PYTORCH_ENABLE_MPS_FALLBACK=1`). |
| Disk | Fast local SSD. Original dataset path on the author machine was an external **WD SN850X** (`/Volumes/WD-SN850X/...`). Weights are large; budget **50–80 GB** if you download everything. |
| OS | macOS. Linux/CUDA is not the inference path (`app/core/models.py` imports `mlx.core`). |

M1 does **not** get BF16 acceleration in the PyTorch DPO demo (`bf16=False`; `fp16` is also off because MPS is unstable with it). M2/M3 can enable BF16 for those PyTorch scripts. MLX inference is separate and is the production path.

## What runs where

```
browser  -->  Next.js :3000 (frontend/)  --HTTP/WS-->  FastAPI :8000 (backend/)
                                                      |
                                                      +-- MLX models in backend/models  (HF_HOME)
                                                      +-- FAISS + MiniLM RAG (in-memory)
                                                      +-- Google CSE (optional)
                                                      +-- sessions.json, logs, LoRA adapters
```

`start-app.sh` starts both processes. The frontend hardcodes `http://localhost:8000` and `ws://localhost:8000/api/ws/chat`.

There is also a leftover Next app at repo root / `src/` (“Neural Orchestrator” cockpit). The UI you actually want is **`frontend/`**.

## Model registry (inference)

Defined in `backend/app/core/models.py`. Role names are what chat/HRM request; folders are Hugging Face cache layout under `backend/models/` (and `backend/models/hub/`).

| Role / alias | Local folder (HF cache name) | Typical weights | Notes |
| --- | --- | --- | --- |
| `qwen-3b` (controller) | `models--mlx-community--converted--Qwen2.5-3B-Instruct-mlx-bf16` | ~6 GB bf16; 4-bit fallback is `mlx-community/Qwen2.5-3B-Instruct-4bit` | Search-decision JSON. Loaded/unloaded around calls unless HRM keeps it. |
| `chat`, `planner`, `qwen` | `models--mlx-community--Qwen2.5-7B-Instruct-bf16` | ~14 GB | Default chat. |
| `general`, `executioner`, `mistral` | `models--mlx-community--Qwen2.5-14B-Instruct-8bit` | ~15 GB | `mistral` is an alias; Mistral weights are **not** required. |
| `synthesis` | `models--mlx-community--converted--Qwen3-32B-mlx-4bit` | ~18 GB 4-bit | Code-mode default; HRM final synthesizer. Needs the 32 GB class machine. |
| `code` | `models--mlx-community--conikeec-deepseek-coder-6.7b-instruct` | ~13 GB-ish | Coding mode. |
| (available, not default) | `models--mlx-community--Meta-Llama-3-8B-Instruct` | ~16 GB | Gated; needs `HF_TOKEN` + license accept. |
| (available) | `models--mlx-community--converted--TinyLlama-1.1B-Chat-v1.0-mlx-4bit` | <1 GB | Training demo / smoke test. |
| (available) | `models--Fmuaddib--Qwen2.5-14B-Instruct-Uncensored-mlx-fp16` | ~28 GB | Optional; heavy. |
| RAG / memory embedder | downloaded by sentence-transformers | ~90 MB | `sentence-transformers/all-MiniLM-L6-v2` |

HRM (“agent” / “reasoning”) **swaps models in one process**: planner (`chat` 7B) → executioner (14B 8-bit) → synthesis (32B 4-bit), with `mx.clear_cache()` between stages. That is why unified memory size matters more than a second GPU.

If a mapped folder is missing, `load()` falls back to Hub download (controller explicitly uses `mlx-community/Qwen2.5-3B-Instruct-4bit`).

## Download scripts (do not run blindly)

These lists are **out of date vs the registry above**. Prefer downloading the MLX repos in the table, or convert with the admin Model Converter (`mlx_lm.convert`).

| Script | What it currently pulls |
| --- | --- |
| `backend/download_inference.py` | Qwen2.5-7B-Instruct, Qwen2.5-3B, Qwen3-32B, Flan-T5-XL. **Requires `HF_TOKEN`.** |
| `backend/download_inference_mlx.py` | TinyLlama, Qwen2.5-7B, Llama-3-8B (mlx-community + NousResearch). |
| `backend/download_models.py` | Qwen2.5-3B-Instruct, Mistral-7B, DeepSeek Coder 6.7B, Llama-2-7B-chat, CodeLlama-7B. Several are gated. |
| `backend/scripts/download_llama2_chat.py` / `download_codellama.py` | Gated Meta models into `backend/models/<name>`. |
| `backend/scripts/download_chatterbox.py` | `ResembleAI/chatterbox` TTS. |
| `backend/download_dataset.py` | GSM8K. **Hardcoded path** `/Volumes/WD-SN850X/Project/projects/llm-webapp/backend/dataset` — edit before running. |

Weights, datasets, LoRA adapters, and logs are gitignored (`backend/models/`, `dataset/`, `lora/`, `training_logs/`, etc.).

## RAM / VRAM ballpark (unified memory)

Apple does not split VRAM the way NVIDIA does. Treat these as **process RSS + Metal** on a quiet machine:

| Workload | Rough need |
| --- | --- |
| Controller 3B 4-bit only | 8 GB machine is enough |
| Chat on Qwen 7B bf16 | ~20 GB comfortable |
| Chat on Qwen 14B 8-bit | ~24–32 GB |
| HRM full stack (7B + 14B + 32B 4-bit, sequential) | **32 GB**; 64 GB is happier |
| RAG embedder on top | +1 GB |
| PyTorch QLoRA (`backend/scripts/training_lora.py`) | NVIDIA CUDA (`bitsandbytes`, `PYTORCH_CUDA_ALLOC_CONF`). Not the Mac inference path. |
| PyTorch DPO demo (`backend/training/training-demo.py`) | MPS, TinyLlama, batch 4 — aimed at M1 Max 32 GB |

`POST /api/system/reload` unloads the main MLX model to reclaim memory.

## Python / Node

- Backend: Python 3.10–3.12 recommended. `backend/requirements.txt` is the MLX stack. Root `requirements.txt` is a pinned PyTorch/RAG set; `backend/requirements-qlora.txt` is CUDA QLoRA.
- Frontend: Node 20+, `cd frontend && npm install && npm run dev`.
- Create `backend/.venv` and activate it; `start-app.sh` will pick it up.

## Storage layout on disk

```
backend/models/          # HF_HOME; snapshot dirs models--org--repo/snapshots/<hash>
backend/models/hub/      # also scanned
backend/dataset/         # gitignored; GSM8K / eval
backend/lora/            # gitignored adapters
backend/sessions.json    # chat sessions (this file is in git today — treat as local state)
backend/raw_logs/        # gitignored
backend/training_logs/
backend/refinement_logs/
```

## If you are not on Apple Silicon

This repo will not run inference as-is. You would need a non-MLX `models.py` (transformers/vLLM/llama.cpp) and different weight files. That port is out of scope of this document.
