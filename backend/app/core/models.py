import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import warnings
# Suppress benign shutdown warning "resource_tracker: There appear to be 1 leaked semaphore objects"
warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")

# =====================================================
# Paths & Environment Setup (MUST be before imports)
# =====================================================
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
MODELS_DIR = os.path.join(BASE_DIR, "models")
# Set HF_HOME so MLX finds models in backend/models
os.environ["HF_HOME"] = MODELS_DIR

# Set HF_TOKEN if available (to avoid authentication warnings)
HF_TOKEN = os.getenv("HF_TOKEN")
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN
    print("🔐 HuggingFace token loaded from environment")

import gc
import re
from mlx_lm import load, generate as mlx_generate
from mlx_lm.sample_utils import make_sampler
from huggingface_hub import snapshot_download

# =====================================================
# Global state
# =====================================================
CURRENT_MODEL_NAME = None
MODEL = None
TOKENIZER = None

# Controller Model State (Persistent)
CONTROLLER_MODEL = None
CONTROLLER_TOKENIZER = None
CONTROLLER_MODEL_NAME = "qwen-3b"

# =====================================================
# Model Registry (MLX Community Optimized)
# =====================================================
# Hardcoded local paths to bypass HF validation/download
# Helper to resolve model path (check 'hub' subdir first)
def find_model_path(model_dir_name, snapshot_hash=None):
    # Check in MODELS_DIR and MODELS_DIR/hub
    candidates = [
        os.path.join(MODELS_DIR, model_dir_name),
        os.path.join(MODELS_DIR, "hub", model_dir_name)
    ]
    
    for base in candidates:
        if os.path.exists(base):
            if snapshot_hash:
                snap_path = os.path.join(base, "snapshots", snapshot_hash)
                if os.path.exists(snap_path):
                    return snap_path
                # If specified snapshot missing, try finding any snapshot
                snaps_dir = os.path.join(base, "snapshots")
                if os.path.exists(snaps_dir):
                    snaps = sorted(os.listdir(snaps_dir))
                    if snaps:
                        return os.path.join(snaps_dir, snaps[-1])
            return base
            
    # Fallback to default old behavior (root) even if missing
    if snapshot_hash:
        return os.path.join(MODELS_DIR, model_dir_name, "snapshots", snapshot_hash)
    return os.path.join(MODELS_DIR, model_dir_name)

QWEN_3B_PATH = find_model_path("models--mlx-community--converted--Qwen2.5-3B-mlx-4bit")
QWEN_7B_PATH = find_model_path("models--mlx-community--Qwen2.5-7B-Instruct-bf16", "349a12f0e5f131c3914e3a66e78a3db71e9f9527")
QWEN_14B_PATH = find_model_path("models--mlx-community--Qwen2.5-14B-Instruct-8bit", "dad22b7070c3f8d7521790316a73678e78f657ab")
QWEN_14B_PATH_FP16 = find_model_path("models--Fmuaddib--Qwen2.5-14B-Instruct-Uncensored-mlx-fp16", "c6e221d1fc74527e6f7b91824b1974c21891de7f")
QWEN_32B_PATH_4BIT = find_model_path("models--mlx-community--converted--Qwen3-32B-mlx-4bit")
DEEPSEEK_CODER_PATH = find_model_path("models--deepseek-ai--deepseek-coder-6.7b-instruct", "e5d64addd26a6a1db0f9b863abf6ee3141936807")
DEEPSEEK_CODER_MLX_PATH = find_model_path("models--mlx-community--conikeec-deepseek-coder-6.7b-instruct", "bbd44e19096038ff7a503bd3137ce900f1b73f01")
META_LLAMA_8B_PATH = find_model_path("models--mlx-community--Meta-Llama-3-8B-Instruct", "d9e88ded22c2c7fb6bdd246436b88f6ffbfe445a")
TINY_LLAMA_PATH = find_model_path("models--mlx-community--converted--TinyLlama-1.1B-Chat-v1.0-mlx-4bit")

MODEL_REPO_IDS = {
    "chat": QWEN_7B_PATH,              # FP16 (Local 14GB Direct Path)
    "general": QWEN_14B_PATH,          # Q8 (Local Direct Path)
    "code": DEEPSEEK_CODER_MLX_PATH,   # MLX Optimized (Local Direct Path)
    "planner": QWEN_7B_PATH,           # FP16 (Local 14GB Direct Path)
    "executioner": QWEN_14B_PATH,      # Q8 (Local Direct Path)
    "synthesis": QWEN_32B_PATH_4BIT,  # 32B Q8 (Local Direct Path)
    
    # Fallbacks for legacy/frontend compatibility
    "qwen": QWEN_7B_PATH, 
    "mistral": QWEN_14B_PATH,  # Using Qwen 14B instead (user doesn't have Mistral downloaded)
    "qwen-3b": QWEN_3B_PATH,   # 3B Controller Model
}

# =====================================================
# Adapter Registry
# =====================================================
# MLX supports adapters, but paths might need adjustment. 
# For now, we assume simple loading without adapters or update if user has MLX adapters.
ADAPTERS = {} 

# =====================================================
# Utilities
# =====================================================
def unload_model():
    """Clear memory and unload current model."""
    global MODEL, TOKENIZER, CURRENT_MODEL_NAME

    # In Python, just releasing references is usually enough.
    # MLX metal memory management is automatic but explicit helps.
    MODEL = None
    TOKENIZER = None
    CURRENT_MODEL_NAME = None
    
    # Force gc
    gc.collect()
    print("🧹 Main Model unloaded (MLX).")

def unload_controller_model():
    """Clear memory and unload controller model."""
    global CONTROLLER_MODEL, CONTROLLER_TOKENIZER
    CONTROLLER_MODEL = None
    CONTROLLER_TOKENIZER = None
    gc.collect()
    print("🧹 Controller Model unloaded (MLX).")

# =====================================================
# Model loader
# =====================================================
def load_model(name: str):
    """
    Load a local model by name using MLX.
    """
    global MODEL, TOKENIZER, CURRENT_MODEL_NAME

    if CURRENT_MODEL_NAME == name and MODEL is not None:
        return MODEL, TOKENIZER

    # Handle suffixes if needed, e.g. "-trained"
    base_name = name.replace("-trained", "") 

    if base_name not in MODEL_REPO_IDS:
        # Fallback to direct repo id if provided? Or Error.
        raise ValueError(
            f"Model '{base_name}' is not defined in MODEL_REPO_IDS. "
            f"Available: {list(MODEL_REPO_IDS.keys())}"
        )

    # Unload previous
    if MODEL is not None:
        print(f"🔄 Switching model from '{CURRENT_MODEL_NAME}' to '{name}'")
        unload_model()

    repo_id = MODEL_REPO_IDS[base_name]
    print(f"📥 Loading MLX model: {name} (Repo: {repo_id})")

    try:
        # Check if it's a direct local path (bypass HF checks completely)
        if os.path.exists(repo_id):
            print(f"📂 Loading directly from local path: {repo_id}")
            model, tokenizer = load(repo_id)
        else:
            # Try to load from local cache by repo_id first
            try:
                model_path = snapshot_download(repo_id, local_files_only=True)
                print(f"📦 Found local cache at: {model_path}")
                model, tokenizer = load(model_path)
            except Exception:
                # Fallback to standard download/load if not found locally
                print(f"⬇️ Local cache not found, downloading {repo_id}...")
                model, tokenizer = load(repo_id)

        MODEL = model
        TOKENIZER = tokenizer
        CURRENT_MODEL_NAME = name
        
        print(f"✅ Loaded {name} successfully.")
        return model, tokenizer

    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        raise e

def load_controller_model(name: str = "qwen-3b"):
    """
    Loads the lightweight controller model if not already loaded.
    """
    global CONTROLLER_MODEL, CONTROLLER_TOKENIZER
    
    if CONTROLLER_MODEL is not None:
        return CONTROLLER_MODEL, CONTROLLER_TOKENIZER
        
    print(f"📥 Loading Controller Model: {name}")
    
    if name not in MODEL_REPO_IDS:
         # Fallback to direct repo id if provided? Or Error.
        if name == "qwen-3b":
            # Ensure it maps to something, or use the global const
             model_path_local = QWEN_3B_PATH
        else:
            model_path_local = MODEL_REPO_IDS.get(name, QWEN_3B_PATH)
    else:
        model_path_local = MODEL_REPO_IDS[name]

    # Explicit Repo ID for downloading if missing
    # This matches the MLX Community convention
    DOWNLOAD_REPO_ID = "mlx-community/Qwen2.5-3B-Instruct-4bit"

    try:
        if os.path.exists(model_path_local):
            print(f"📂 Loading controller directly from local path: {model_path_local}")
            model, tokenizer = load(model_path_local)
        else:
            print(f"⬇️ Downloading/Loading controller {DOWNLOAD_REPO_ID} required (Local: {model_path_local} not found)...")
            # Download to the cache, return the cache path
            model_path = snapshot_download(DOWNLOAD_REPO_ID, local_files_only=False) 
            print(f"✅ Downloaded to: {model_path}")
            model, tokenizer = load(model_path)
            
        CONTROLLER_MODEL = model
        CONTROLLER_TOKENIZER = tokenizer
        print(f"✅ Controller {name} loaded successfully.")
        return model, tokenizer
        
    except Exception as e:
        print(f"❌ Failed to load controller model: {e}")
        # Non-critical failure logic could go here, but for now prompt to download
        raise e


# =====================================================
# Text generation
# =====================================================
def generate_response(prompt: str, max_new_tokens: int = 8192, temperature: float = 0.7) -> str:
    """
    High-level generation function using MLX.
    """
    global MODEL, TOKENIZER
    
    if MODEL is None:
        print("⚠️ No model loaded. Auto-loading 'chat'...")
        load_model("chat")
        
    print(f"🎛️ Generating (MLX) | temp={temperature}, max_tokens={max_new_tokens}")
    
    # Create sampler explicitly for this MLX version
    sampler = make_sampler(temp=temperature)

    response = mlx_generate(
        MODEL,
        TOKENIZER,
        prompt=prompt,
        max_tokens=max_new_tokens,
        sampler=sampler,
        verbose=True
    )
    
    # Cleanup heuristics
    stop_patterns = [
        r"\nUser:",
        r"\nAssistant:",
        r"System:",
        r"Conversation so far:",
    ]
    
    # MLX generate returns the text directly (string)
    text = response
    
    for pattern in stop_patterns:
        match = re.search(pattern, text)
        if match:
            text = text[: match.start()]

    return text.strip()

def generate_controller_response(prompt: str, max_new_tokens: int = 64, keep_loaded: bool = False) -> str:
    """
    Deterministic generation for the controller model (Temperature 0).
    keep_loaded: If True, skips unload to allow rapid subsequent calls (e.g. HRM loop).
    """
    global CONTROLLER_MODEL, CONTROLLER_TOKENIZER
    
    if CONTROLLER_MODEL is None:
        load_controller_model()
        
    # Strict deterministic generation
    sampler = make_sampler(temp=0.0)
    
    response = mlx_generate(
        CONTROLLER_MODEL,
        CONTROLLER_TOKENIZER,
        prompt=prompt,
        max_tokens=max_new_tokens,
        sampler=sampler,
        verbose=False 
    )
    
    # MEMORY OPTIMIZATION: Unload immediately to save RAM for main model
    # UNLESS explicitly told to keep it loaded (for multi-step flows like HRM)
    if not keep_loaded:
        unload_controller_model()
    
    return response.strip()

# Alias for compatibility with other services
def generate(prompt: str, max_new_tokens: int = 8192, temperature: float = 0.7) -> str:
    return generate_response(prompt, max_new_tokens, temperature)
