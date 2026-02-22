from datasets import load_dataset
from pathlib import Path

# Target directory
BASE_PATH = Path("/Volumes/WD-SN850X/Project/projects/llm-webapp/backend/dataset")

# Create directory if it doesn't exist
BASE_PATH.mkdir(parents=True, exist_ok=True)

# Load dataset
dataset = load_dataset("gsm8k", "main")

# Save to specified directory
dataset.save_to_disk(str(BASE_PATH / "gsm8k"))

print("GSM8K downloaded and saved successfully.")