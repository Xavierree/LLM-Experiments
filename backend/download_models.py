
import os
from huggingface_hub import snapshot_download

# Defined in app/core/models.py
MODEL_SNAPSHOTS = {
    "qwen": "Qwen/Qwen2.5-3B-Instruct",
    "mistral": "mistralai/Mistral-7B-Instruct-v0.2",
    "deepseek": "deepseek-ai/deepseek-coder-6.7b-instruct",
    "llama2": "meta-llama/Llama-2-7b-chat-hf", 
    "codellama": "meta-llama/CodeLlama-7b-Instruct-hf",
    "llama-2-7b-chat-hf": "meta-llama/Llama-2-7b-chat-hf"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def download_all():
    print(f"🚀 Starting bulk download to: {MODELS_DIR}")
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # Deduplicate repos
    unique_repos = sorted(list(set(MODEL_SNAPSHOTS.values())))
    
    for repo_id in unique_repos:
        print(f"\n⬇️  Downloading {repo_id}...")
        try:
            path = snapshot_download(
                repo_id=repo_id,
                cache_dir =MODELS_DIR,
                local_files_only=False,
                resume_download=True,
                ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onex"], # Optimize sLLllmtorage
            )
            print(f"✅ Sucessfully downloaded {repo_id} -> {path}")
        except Exception as e:
            print(f"❌ Error downloading {repo_id}: {e}")

    print("\n🎉 All downloads complete!")

if __name__ == "__main__":
    download_all()
