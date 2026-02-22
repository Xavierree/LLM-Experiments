
import os
from huggingface_hub import snapshot_download

# Defined in app/core/models.py
MODEL_SNAPSHOTS = {
    "qwen-chat":"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "qwen-base":"Qwen/Qwen2.5-7B",
    "planner":"mlx-community/Meta-Llama-3-8B-Instruct",
    "executor":"NousResearch/Meta-Llama-3-8B-Instruct",
    "retriever":"NousResearch/Meta-Llama-3-8B-Instruct",
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
            print(f"✅ Successfully downloaded {repo_id} -> {path}")
        except Exception as e:
            print(f"❌ Error downloading {repo_id}: {e}")

    print("\n🎉 All downloads complete!")

if __name__ == "__main__":
    download_all()
