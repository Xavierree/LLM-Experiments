import json
import time
import os
import hashlib
import logging
import asyncio
from typing import List, Set

RAW_LOG_DIR = "../raw_logs"
REFINEMENT_LOG_DIR = "../refinement_logs"
os.makedirs(RAW_LOG_DIR, exist_ok=True)
os.makedirs(REFINEMENT_LOG_DIR, exist_ok=True)


class LogBroadcaster:
    def __init__(self):
        self.active_connections: Set = set()
        self.history: List[str] = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        for line in self.history[-100:]:
            await websocket.send_text(line)

    def disconnect(self, websocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: str):
        self.history.append(message)
        if len(self.history) > 1000:
            self.history.pop(0)

        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                to_remove.append(connection)

        for conn in to_remove:
            self.active_connections.discard(conn)


log_broadcaster = LogBroadcaster()


import sys


class StreamToLogger:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, buf):
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running() and buf.strip():
                asyncio.create_task(log_broadcaster.broadcast(buf.strip()))
        except Exception:
            pass

        self.original_stream.write(buf)
        self.original_stream.flush()

    def flush(self):
        self.original_stream.flush()

    def isatty(self):
        return getattr(self.original_stream, "isatty", lambda: False)()


if __name__ != "__main__":
    sys.stdout = StreamToLogger(sys.stdout)
    sys.stderr = StreamToLogger(sys.stderr)


class WebSocketLoggingHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(log_broadcaster.broadcast(log_entry))
        except Exception:
            pass


def setup_logging():
    root_val = logging.getLogger()
    root_val.setLevel(logging.INFO)

    for h in root_val.handlers:
        if isinstance(h, WebSocketLoggingHandler):
            return

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ws_handler = WebSocketLoggingHandler()
    ws_handler.setFormatter(formatter)
    root_val.addHandler(ws_handler)


setup_logging()


def log_raw_interaction(user, assistant, mode, system_prompt, memory_used, model="unknown"):
    """
    Legacy raw logger for general interactions.
    """
    record = {
        "timestamp": time.time(),
        "mode": mode,
        "model": model,
        "user": user,
        "assistant": assistant,
        "memory_used": bool(memory_used),
        "system_prompt_hash": hashlib.sha256(system_prompt.encode()).hexdigest(),
    }
    fname = time.strftime("%Y_%m_%d") + ".jsonl"
    path = os.path.join(RAW_LOG_DIR, fname)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def log_refinement_event(prompt, chosen, rejected, persona, timestamp=None):
    """
    Logs a refinement event for training data.
    Format:
      "prompt": "<|user|>\nPROMPT_TEXT\n<|assistant|>",
      "chosen": "FINAL_ACCEPTED_OUTPUT",
      "rejected": "FIRST_REJECTED_OUTPUT" (or - if none),
      "persona": "planner" (or chat/general/etc),
      "timestamp": 123456
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Format the prompt as requested
    formatted_prompt = f"<|user|>\n{prompt}\n<|assistant|>"

    # Handle rejected being None -> "nan" (or "-")
    # User said: "if the first output is accepted just make the "rejected" nan or "-" just fill the "chosen" one"
    rejected_val = rejected if rejected else "-"

    record = {
        "prompt": formatted_prompt,
        "chosen": chosen,
        "rejected": rejected_val,
        "persona": persona,
        "timestamp": timestamp
    }

    fname = "refinement.jsonl"
    path = os.path.join(REFINEMENT_LOG_DIR, fname)
    
    # Check if we should append or create (append is standard for jsonl)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"📝 Logged Refinement Event: {persona} (Rejected: {rejected_val != '-'})")


def log_hrm_event(
    session_id: str,
    original_prompt: str,
    
    plan_chosen: str,
    plan_rejected: str,
    
    execution_chosen: str,
    execution_rejected: str,
    
    synthesis_chosen: str,
    synthesis_rejected: str,
    
    timestamp=None
):
    """
    Logs 3 events for a single HRM turn.
    """
    if timestamp is None:
        timestamp = int(time.time())
        
    # 1. Planner Event
    # Input: Original Prompt
    log_refinement_event(
        prompt=original_prompt,
        chosen=plan_chosen,
        rejected=plan_rejected,
        persona="planner",
        timestamp=timestamp
    )
    
    # 2. Executor Event
    # Input: The PLAN (chosen)
    # We treat the plan as the "User Prompt" for the executor in this context? 
    # Or do we log the system flow?
    # User said: "executor's input is from the planner", so Prompt = Plan
    log_refinement_event(
        prompt=plan_chosen,
        chosen=execution_chosen,
        rejected=execution_rejected,
        persona="executioner",
        timestamp=timestamp
    )
    
    # 3. Synthesis Event
    # Input: The Execution (chosen)
    # User said: "synthesis's input is from the executor"
    log_refinement_event(
        prompt=execution_chosen,
        chosen=synthesis_chosen,
        rejected=synthesis_rejected,
        persona="synthesis",
        timestamp=timestamp
    )

