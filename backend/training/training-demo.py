import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model
from datasets import Dataset
from trl import DPOTrainer, DPOConfig
from transformers import TrainingArguments
import os

# Set working directory to script location for relative paths to work
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

MODELS_DIR = "../models"
OUTPUT_DIR = "../trained-models"
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Ensure directories exist
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Download once, reuse locally
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    cache_dir=MODELS_DIR
)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    cache_dir=MODELS_DIR,
    dtype=torch.float32,        # keep FP32 for training stability on Mac
    low_cpu_mem_usage=True
)

# Optional: enable gradient checkpointing (important for LoRA/RL)
model.gradient_checkpointing_enable()

# Device handling (Mac MPS or CPU fallback)
device = (
    torch.device("mps") if torch.backends.mps.is_available()
    else torch.device("cpu")
)
print(f"Using device: {device}")

model.to(device)

lora_config = LoraConfig(
    r=16,                      # start small
    lora_alpha=32,
    target_modules=[
        "q_proj", "k_proj", "v_proj",
        "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Sample Dataset
data = [
    {
        "prompt": "Explain LoRA simply.",
        "chosen": "LoRA is a low-rank adaptation technique that freezes pre-trained model weights...",
        "rejected": "LoRA is a random training trick that changes everything."
    }
]

dataset = Dataset.from_list(data)

# Use DPOConfig which inherits from TrainingArguments
training_args = DPOConfig(
    output_dir=f"{OUTPUT_DIR}/raw/tinyllama_dpo",
    per_device_train_batch_size=4,  # Increased for M1 Max (32GB+ RAM)
    gradient_accumulation_steps=2,  # Reduced to keep effective batch size reasonable
    learning_rate=5e-5,
    num_train_epochs=1,
    logging_steps=1,
    fp16=False,         # MPS unstable with fp16
    bf16=False,         # M1 series does not support BF16 acceleration (M2/M3 do)
    gradient_checkpointing=True,
    save_strategy="no",
    use_cpu=False,
    dataloader_num_workers=0, # Avoid multiprocessing issues on MPS
    beta=0.1,                 # KL strength (now part of DPOConfig)
    max_length=512,           # (now part of DPOConfig)
    max_prompt_length=256,    # (now part of DPOConfig)
    remove_unused_columns=False
)

trainer = DPOTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    processing_class=tokenizer,
)

print("Starting training...")
trainer.train()
print("Training complete.")

print("Merging model...")
model = model.merge_and_unload()
output_path = f"{OUTPUT_DIR}/tinyllama_1.1B_dpo_merged"
model.save_pretrained(output_path)
tokenizer.save_pretrained(output_path)
print(f"Model saved to {output_path}")

# Note: To convert to MLX, run: mlx_lm.convert --hf-path ...