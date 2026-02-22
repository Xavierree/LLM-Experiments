import os
from huggingface_hub import snapshot_download

def download_model():
    model_id = "ResembleAI/chatterbox"
    # Define target directory relative to backend root
    # script is in backend/scripts/, so we go up one level then to models/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "models", "resemble-chatterbox")
    
    print(f"Downloading {model_id} to {target_dir}...")
    
    try:
        snapshot_download(repo_id=model_id, local_dir=target_dir, local_dir_use_symlinks=False)
        print("Download complete successfully.")
    except Exception as e:
        print(f"Error downloading model: {e}")

if __name__ == "__main__":
    download_model()
