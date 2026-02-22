import json, time, os, hashlib

RAW_LOG_DIR = "raw_logs"
os.makedirs(RAW_LOG_DIR, exist_ok=True)

def log_raw_interaction(
    user,
    assistant,
    mode,
    system_prompt,
    memory_used
):
    record = {
        "timestamp": time.time(),
        "mode": mode,
        "user": user,
        "assistant": assistant,
        "memory_used": bool(memory_used),
        "system_prompt_hash": hashlib.sha256(
            system_prompt.encode()
        ).hexdigest()
    }

    fname = time.strftime("%Y_%m_%d") + ".jsonl"
    path = os.path.join(RAW_LOG_DIR, fname)

    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
