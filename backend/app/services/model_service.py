import os
import glob
from pathlib import Path
from mlx_lm import convert
import logging
import sys
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")

def list_local_models():
    """
    Scans the models directory for HuggingFace models and checks if they have MLX conversions.
    """
    models = []
    
    # Define directories to scan: root models dir and the hub subdirectory (for HF_HOME structure)
    scan_dirs = [MODELS_DIR, os.path.join(MODELS_DIR, "hub")]
    
    seen_paths = set()

    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue
            
        for item in os.listdir(scan_dir):
            full_path = os.path.join(scan_dir, item)
            
            if full_path in seen_paths:
                continue

            if item.startswith("models--") and os.path.isdir(full_path):
                # Parse model name from folder name (e.g., models--org--repo)
                parts = item.split("--")
                if len(parts) >= 3:
                    org = parts[1]
                    repo = "--".join(parts[2:])
                    model_id = f"{org}/{repo}"
                    
                    # Check if MLX version exists
                    # We look for MLX version in the SAME directory as the source model
                    mlx_path = os.path.join(scan_dir, f"mlx-community--{repo}")
                    mlx_exists = os.path.exists(mlx_path)
                    
                    models.append({
                        "id": model_id,
                        "path": full_path, # Use full path!
                        "is_mlx": False, # This is a HF source model
                        "has_mlx_converted": mlx_exists,
                        "mlx_path": mlx_path if mlx_exists else None
                    })
                    seen_paths.add(full_path)

            elif item.startswith("mlx-community--"):
                 # This is an already converted model or downloaded mlx model
                 parts = item.split("--")
                 if len(parts) >= 2:
                     repo = "--".join(parts[1:])
                     models.append({
                         "id": f"mlx-community/{repo}",
                         "path": full_path, # Use full path
                         "is_mlx": True,
                         "has_mlx_converted": True,
                         "mlx_path": full_path
                     })
                     seen_paths.add(full_path)

    return models

async def convert_model_to_mlx(model_path_name: str, quantization: str = "4bit"):
    """
    Converts a local HF model to MLX format.
    model_path_name: The folder name in backend/models (e.g. models--NousResearch--Meta-Llama-3-8B-Instruct)
    """
    try:
        # Resolve HF path (handle snapshots)
        base_path = os.path.join(MODELS_DIR, model_path_name)
        start_hf_path = base_path
        
        # Check if snapshots directory exists
        snapshots_dir = os.path.join(base_path, "snapshots")
        if os.path.exists(snapshots_dir):
            # Get the first snapshot folder (usually latest)
            # HF convention: snapshots/<commit_hash>
            snapshots = os.listdir(snapshots_dir)
            if snapshots:
                # Sort to ensure determinism, though usually just one
                snapshots.sort()
                hf_path = os.path.join(snapshots_dir, snapshots[-1])
                logger.info(f"Resolved HF path to snapshot: {hf_path}")
            else:
                 hf_path = base_path # Fallback
        else:
             hf_path = base_path
        
        # Derive output path
        # Convention: mlx-community--{repo_name}-{quantization}
        # Determine quantization bits
        bits = None # Default: No quantization (fp16/bf16 based on source)
        
        if quantization == "4bit":
             bits = "4"
        elif quantization == "8bit":
             bits = "8"
        
        # Derive output path
        # Convention: mlx-community--{repo_name}-{quantization}
        parts = model_path_name.split("--")
        repo_name = parts[-1] if len(parts) > 0 else model_path_name
        
        # Construct directory name
        if bits:
            output_dir_name = f"models--mlx-community--converted--{repo_name}-mlx-{quantization}"
        else:
            # If no quantization, use the provided tag (e.g. fp16, bf16) or default to "float16" if none provided
            tag = quantization if quantization and quantization.lower() != "none" else "float16"
            output_dir_name = f"models--mlx-community--converted--{repo_name}-mlx-{tag}"

        output_path = os.path.join(MODELS_DIR, output_dir_name)
        
        logger.info(f"Starting conversion for {model_path_name} to {output_path} with quantization={quantization}...")
        
        # Use subprocess to run the conversion script for better isolation and memory management
        # Command: python -m mlx_lm.convert --hf-path <hf_path> --mlx-path <output_path> [-q -q-bits <bits>]
             
        cmd = [
            sys.executable, "-m", "mlx_lm.convert",
            "--hf-path", hf_path,
            "--mlx-path", output_path,
        ]
        
        if bits:
            cmd.extend(["-q", "--q-bits", bits])
        
        logger.info(f"Running conversion command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Conversion complete: {output_path}")
            
            # AUTOMATION: Copy chat_template from source to destination if missing
            try:
                import json
                
                # paths
                src_tok_config = os.path.join(hf_path, "tokenizer_config.json")
                dst_tok_config = os.path.join(output_path, "tokenizer_config.json")
                
                if os.path.exists(src_tok_config) and os.path.exists(dst_tok_config):
                    with open(src_tok_config, "r") as f:
                        src_data = json.load(f)
                        
                    with open(dst_tok_config, "r") as f:
                        dst_data = json.load(f)
                        
                    # Check if source has template and dest doesn't (or we overwrite to be safe?)
                    # Let's overwrite to ensure it matches the source behavior
                    if "chat_template" in src_data:
                        logger.info(f"Transferring chat_template from {src_tok_config} to {dst_tok_config}")
                        dst_data["chat_template"] = src_data["chat_template"]
                        
                        # Write back
                        with open(dst_tok_config, "w") as f:
                            json.dump(dst_data, f, indent=4)
                    else:
                        logger.warning(f"Source model {src_tok_config} has no chat_template")
                        
            except Exception as e:
                logger.error(f"Failed to transfer chat_template: {e}")
                # Don't fail the whole conversion for this, just log it
            
            return {"status": "success", "output_path": output_path, "logs": stdout.decode()}
        else:
            error_msg = stderr.decode()
            logger.error(f"Conversion failed: {error_msg}")
            return {"status": "error", "message": error_msg}
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return {"status": "error", "message": str(e)}
