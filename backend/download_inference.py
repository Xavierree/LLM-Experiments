import os
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable not set")

MODEL_SNAPSHOTS = {
    "qwen-chat":"Qwen/Qwen2.5-7B-Instruct",
    "qwen-base":"Qwen/Qwen2.5-3B",
    "qwen-coder":"Qwen/Qwen3-32B",
    "executor":"google/flan-t5-xl",
    "retriever":"Qwen/Qwen2.5-7B-Instruct",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def download_all():
    print(f"🚀 Starting bulk download to: {MODELS_DIR}")
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    unique_repos = sorted(list(set(MODEL_SNAPSHOTS.values())))
    
    for repo_id in unique_repos:
        print(f"\n⬇️  Downloading {repo_id}...")
        try:
            path = snapshot_download(
                repo_id=repo_id,
                cache_dir=MODELS_DIR,
                token=HF_TOKEN,   # 🔥 Authentication added
                resume_download=True,
                ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onex"],
            )
            print(f"✅ Successfully downloaded {repo_id} -> {path}")
        except Exception as e:
            print(f"❌ Error downloading {repo_id}: {e}")

    print("\n🎉 All downloads complete!")

if __name__ == "__main__":
    download_all()