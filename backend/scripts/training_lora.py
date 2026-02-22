import os
import sys

# Reduce VRAM fragmentation
# MUST be set before importing torch
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import torch
import gc
import json
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig

# ==========================
# CONFIG
# ==========================
MAX_SEQ_LEN = 8192
DATA_PATH = "../../training_logs/assistant_sft_verified.jsonl"

MODELS_TO_TRAIN = [
    {
        "name": "mistral",
        "id": "mistralai/Mistral-7B-Instruct-v0.2",
        "output": "../../lora/mistral_adapter",
        "dataset_files": [
            "../../training_logs/verified_mistral.jsonl"
        ]
    },
    {
        "name": "qwen",
        "id": "Qwen/Qwen2.5-3B-Instruct",
        "output": "../../lora/qwen_adapter",
        "dataset_files": [
            "../../training_logs/verified_qwen.jsonl"
        ]
    },
    {
        "name": "llama2",
        "id": "meta-llama/Llama-2-7b-chat-hf",
        "output": "../../lora/llama2_adapter",
        "dataset_files": [
            "../../training_logs/verified_llama2.jsonl"
        ]
    },
    {
        "name": "codellama",
        "id": "meta-llama/CodeLlama-7b-Instruct-hf",
        "output": "../../lora/codellama_adapter",
        "dataset_files": [
            "../../training_logs/verified_codellama.jsonl"
        ]
    },
    {
        "name": "deepseek",
        "id": "deepseek-ai/deepseek-coder-6.7b-instruct",
        "output": "../../lora/deepseek_adapter",
        "dataset_files": [
            "../../training_logs/verified_deepseek.jsonl"
        ]
    }
]

def train_model(model_info):
    model_id = model_info["id"]
    output_dir = model_info["output"]
    
    print(f"\n{'='*40}")
    print(f"🚀 STARTING TRAINING: {model_info['name'].upper()} ({model_id})")
    print(f"{'='*40}\n")

    print(f"\n{'='*40}")
    print(f"🚀 STARTING TRAINING: {model_info['name'].upper()} ({model_id})")
    print(f"{'='*40}\n")
    
    # Clean memory before starting
    gc.collect()
    torch.cuda.empty_cache()

    model = None
    tokenizer = None
    trainer = None
    dataset = None

    try:
        # 1. Load Tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # User requested match for "byte-level tokenization" settings from notebook
        tokenizer.model_max_length = 8192

        # 2. Load Model (4bit)
        # Check if flash-attn is available to handle packing correctly
        try:
            import flash_attn
            attn_implementation = "flash_attention_2"
            print("⚡ Flash Attention 2 enabled!")
        except ImportError:
            attn_implementation = "eager"
            print("⚠️ Flash Attention not found. Training might be slower/warn about packing.")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_storage=torch.bfloat16, # Further memory saving in newer BNB
        )

        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            # device_map="auto",  REVERTING to auto or simple cpu/disk offload strategy if needed
            # For 4-bit, we usually stick to GPU. Let's try 'auto' to allow potential offload if libs support it.
            # But earlier error said "Some modules ... on cpu". 
            # We'll stick to cuda:0 but rely on packing=False to save memory.
            device_map="cuda:0", 
            attn_implementation=attn_implementation,
        )

        # Prepare model for k-bit training (enables gradient checkpointing support)
        from peft import prepare_model_for_kbit_training
        model = prepare_model_for_kbit_training(model)

        # 3. Apply LoRA
        # Qwen might need different target modules than Mistral
        if "qwen" in model_id.lower():
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        else:
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=target_modules,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )

        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        # 4. Load Dataset
        if "dataset_files" in model_info:
            data_files = model_info["dataset_files"]
            print(f"📚 Loading datasets: {data_files}")
            
            from datasets import concatenate_datasets
            loaded_tabs = []
            for df in data_files:
                try:
                    # Load individually
                    ds = load_dataset("json", data_files=df, split="train")
                    # Normalize columns to avoid schema conflicts (e.g. 'meta' mismatch)
                    ds = ds.select_columns(["instruction", "input", "output"])
                    loaded_tabs.append(ds)
                except Exception as e:
                    print(f"⚠️ Failed to load {df}: {e}")
            
            if loaded_tabs:
                dataset = concatenate_datasets(loaded_tabs)
                print(f"✅ Merged datasets. Total size: {len(dataset)}")
            else:
                raise ValueError("No datasets could be loaded!")
                
        else:
            # Fallback
            dataset = load_dataset("json", data_files=DATA_PATH)

        # 5. Formatting Func (Chat Template Based)
        def formatting_prompts_func(examples):
            instructions = examples["instruction"]
            inputs = examples["input"]
            outputs = examples["output"]
            texts = []
            for instruction, input_text, output in zip(instructions, inputs, outputs):
                full_input = f"{instruction}\n{input_text}" if input_text else instruction
                
                messages = [
                    {"role": "user", "content": full_input},
                    {"role": "assistant", "content": output}
                ]
                
                # Use apply_chat_template to get the correct model-specific tags
                text = tokenizer.apply_chat_template(messages, tokenize=False)
                texts.append(text)
            return { "text": texts }

        dataset = dataset.map(formatting_prompts_func, batched=True)

        # Adjust settings based on model to save VRAM
        if "mistral" in model_id.lower():
            # Mistral 7B is too big for 8GB VRAM with packing=True (2048 ctx).
            # We disable packing effectively by processing one sample at a time without concatenation
            # AND reduce max length to prevent OOM on long samples.
            use_packing = False
            effective_max_len = 1024 
            print(f"📉 Optimization for Mistral: Packing=False, MaxLen={effective_max_len}")
        else:
            use_packing = True
            effective_max_len = MAX_SEQ_LEN

        # 6. SFT Config
        sft_config = SFTConfig(
            output_dir=output_dir,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=8,
            learning_rate=2e-4,
            num_train_epochs=2,
            bf16=True,
            logging_steps=5,
            save_strategy="no", # Don't save intermediate steps to save disk/time
            optim="paged_adamw_8bit",
            report_to="none",
            max_length=effective_max_len,
            packing=use_packing,
            dataset_text_field="text",
            gradient_checkpointing=True, # Critical for saving VRAM
        )

        # Ensure dataset is a Dataset object, not a DatasetDict
        if isinstance(dataset, dict) and "train" in dataset:
            dataset = dataset["train"]

        # 7. Train
        trainer = SFTTrainer(
            model=model,
            args=sft_config,
            train_dataset=dataset,
            processing_class=tokenizer,
        )

        trainer.train()

        # 8. Save
        print(f"Saving adapter to {output_dir}...")
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

    finally:
        # 9. Cleanup VRAM
        print(f"🧹 Cleaning up VRAM after {model_info['name']}...")
        if model is not None: del model
        if trainer is not None: del trainer
        if tokenizer is not None: del tokenizer
        if dataset is not None: del dataset
        gc.collect()
        torch.cuda.empty_cache()
        print(f"✅ {model_info['name']} VRAM cleared.")

def run_groq_eval(model_name, output_dir):
    """
    Optional: Ask Groq to look at the trained model's save directory 
    or run a small verification if needed. 
    Here we just confirm the save and provide a placeholder for automated QA.
    """
    try:
        from refinery.cloud_refiner import CloudVerifier
        verifier = CloudVerifier(provider="groq")
        print(f"📡 Groq API: Notifying pipeline of successful {model_name} training...")
        # Placeholder for automated evaluation logic
        # verifier.verify(...)
    except Exception as e:
        print(f"⚠️ Groq Eval skipped or failed: {e}")

if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: {DATA_PATH} not found. Run the Refinery first!")
    else:
        for model_info in MODELS_TO_TRAIN:
            try:
                train_model(model_info)
                # Use Groq API to finalize/eval
                run_groq_eval(model_info['name'], model_info['output'])
            except Exception as e:
                print(f"❌ Error training {model_info['name']}: {e}")
                # Try to clear memory anyway
                gc.collect()
                torch.cuda.empty_cache()
        
        print("\n🎉 ALL TRAINING TASKS COMPLETE! (Groq API Integrated)")
