import os
from dotenv import load_dotenv
from huggingface_hub import snapshot_download

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def download_llama_instruct():
    # Using Llama-2-7b-chat-hf as the official "7B Instruct" equivalent from Meta (Llama 2)
    model_id = "meta-llama/Llama-2-7b-chat-hf"
    
    # Define target directory relative to backend root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "models", "llama-2-7b-chat")
    
    print(f"Preparing to download {model_id} to {target_dir}...")
    
    # Check for token in env or rely on cached login
    token = os.getenv("HF_TOKEN")
    if not token:
        print("Note: HF_TOKEN not found in environment variables.")
        print("If the download fails with 401/403, please run `huggingface-cli login` or set HF_TOKEN.")
    
    try:
        snapshot_download(
            repo_id=model_id, 
            local_dir=target_dir, 
            local_dir_use_symlinks=False,
            token=token
        )
        print(f"Successfully downloaded {model_id}.")
    except Exception as e:
        print(f"Error downloading {model_id}: {e}")
        print("Ensure you have accepted the license at https://huggingface.co/meta-llama/Llama-2-7b-chat-hf")

if __name__ == "__main__":
    download_llama_instruct()
