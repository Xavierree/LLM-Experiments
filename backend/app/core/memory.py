import time
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer, util

# Global In-Memory Stores (In a real app, use a database like Chroma or SQLite)
USER_MEMORY = []
CHAT_HISTORY = []
EMBEDDER = None

def get_embedder():
    global EMBEDDER
    if EMBEDDER is None:
        print("🧠 Loading SentenceTransformer...")
        EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return EMBEDDER

def classify_memory(text: str) -> str:
    lowered = text.lower()
    if "my name is" in lowered: return "profile"
    if "i have " in lowered: return "possession"
    if any(x in lowered for x in ["i like", "i love", "my favorite"]): return "preference"
    if "my pet" in lowered or any(a in lowered for a in ["dog", "cat", "bird"]): return "pet"
    if "i am" in lowered: return "state"
    return "other"

def score_importance(mem_type: str) -> int:
    return {
        "profile": 3, "pet": 3, "preference": 2, 
        "possession": 1, "state": 1, "other": 1
    }.get(mem_type, 1)

def maybe_store_memory(text: str):
    """Analyzes text and stores it if it contains personal info."""
    mem_type = classify_memory(text)
    importance = score_importance(mem_type)
    
    # Store verified memory is usually important
    # For now, simplistic check: everything the user says that matches patterns
    # In full app, we might need a button to "Save to Memory" or auto-save.
    
    embedder = get_embedder()
    embedding = embedder.encode(text, convert_to_tensor=True)

    # Dedup
    for mem in USER_MEMORY:
        sim = util.cos_sim(embedding, mem["embedding"])
        if sim > 0.85:
            return # Duplicate

    entry = {
        "text": text,
        "embedding": embedding,
        "type": mem_type,
        "importance": importance,
        "timestamp": time.time()
    }
    USER_MEMORY.append(entry)
    print(f"💾 Memory Stored: [{mem_type}] {text}")

def retrieve_memory(query: str, k=3) -> str:
    if not USER_MEMORY:
        return ""
    
    embedder = get_embedder()
    q_emb = embedder.encode(query, convert_to_tensor=True)
    
    scored = []
    for mem in USER_MEMORY:
        sim = util.cos_sim(q_emb, mem["embedding"]).item()
        score = sim * mem["importance"]
        scored.append((score, mem["text"]))
    
    top = sorted(scored, reverse=True)[:k]
    return "\n".join(m[1] for m in top if m[0] > 0.25)

import uuid
import json
import os

# Persistence File
SESSIONS_FILE = "sessions.json"

# In-Memory Cache
SESSIONS = {}

def load_sessions():
    global SESSIONS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r") as f:
                SESSIONS = json.load(f)
        except:
            SESSIONS = {}
    print(f"📂 Loaded {len(SESSIONS)} sessions.")

def save_sessions():
    # Only save pinned sessions to disk
    to_save = {k: v for k, v in SESSIONS.items() if v.get("pinned", False)}
    with open(SESSIONS_FILE, "w") as f:
        json.dump(to_save, f, indent=2)

# Load on start
load_sessions()

def create_session(title: str = "New Chat") -> str:
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "id": session_id,
        "title": title,
        "created_at": time.time(),
        "turns": [], # List of Turn objects
        "messages": [], # Fallback for legacy chat
        "pinned": False 
    }
    save_sessions()
    print(f"🆕 Created Session {session_id}. Total Sessions: {len(SESSIONS)}")
    return session_id

def set_session_pin(session_id: str, pinned: bool):
    if session_id in SESSIONS:
        SESSIONS[session_id]["pinned"] = pinned
        save_sessions()

def get_session(session_id: str):
    return SESSIONS.get(session_id)

def list_sessions():
    listing = []
    for sid, data in SESSIONS.items():
        # Preview from last turn's final output or prompt
        preview = "Empty"
        turns = data.get("turns", [])
        if turns:
            last_turn = turns[-1]
            if last_turn.get("final_output"):
                 preview = last_turn["final_output"][:50]
            else:
                 preview = last_turn.get("prompt", "")[:50]
        elif "messages" in data and data["messages"]: # Fallback for old sessions
             preview = data["messages"][-1]["content"][:50]

        listing.append({
            "id": sid,
            "title": data.get("title", "Untitled"),
            "created_at": data.get("created_at", 0),
            "pinned": data.get("pinned", False),
            "preview": preview
        })
    sorted_list = sorted(listing, key=lambda x: (x["pinned"], x["created_at"]), reverse=True) 
    return sorted_list

def add_turn_to_session(session_id: str, turn_data: dict):
    if session_id not in SESSIONS: return
    if "turns" not in SESSIONS[session_id]: SESSIONS[session_id]["turns"] = []
    
    SESSIONS[session_id]["turns"].append(turn_data)
    
    # Auto-title
    if len(SESSIONS[session_id]["turns"]) == 1:
        prompt = turn_data.get("prompt", "")
        title = prompt[:30] + "..." if len(prompt) > 30 else prompt
        SESSIONS[session_id]["title"] = title
        
    save_sessions()

def update_last_turn(session_id: str, turn_data: dict):
    if session_id not in SESSIONS: return
    if "turns" not in SESSIONS[session_id] or not SESSIONS[session_id]["turns"]:
        add_turn_to_session(session_id, turn_data)
        return

    SESSIONS[session_id]["turns"][-1] = turn_data
    save_sessions()


def get_chat_history_str(session_id: str = None, n=6) -> str:
    # If session_id provided, use that session's history
    if session_id and session_id in SESSIONS:
        sess = SESSIONS[session_id]
        history_str = ""
        
        # New Turn-based history
        if "turns" in sess and sess["turns"]:
            # Get last n turns
            selected_turns = sess["turns"][-n:]
            for t in selected_turns:
                # Use final_output if accepted/done, otherwise use the last iteration's response (current state)
                response = t.get("final_output")
                if not response and "iterations" in t and t["iterations"]:
                    response = t["iterations"][-1].get("response", "")
                
                history_str += f"User: {t['prompt']}\nAssistant: {response}\n"
            return history_str.strip()

        # Fallback to legacy messages
        if "messages" in sess:
            msgs = sess["messages"]
            selected = msgs[-n:]
            return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in selected])
    
    # Fallback to global legacy history (or empty)
    return ""

# Legacy Global History (Deprecated but kept for compatibility during refactor)
CHAT_HISTORY = []
def add_message_to_session(session_id: str, role: str, content: str):
    if session_id not in SESSIONS: return
    if "messages" not in SESSIONS[session_id]:
        SESSIONS[session_id]["messages"] = []
    
    SESSIONS[session_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": time.time()
    })
    save_sessions()

def update_chat_history(user, assistant, session_id=None):
    # Global
    CHAT_HISTORY.append({"u": user, "a": assistant})
    if len(CHAT_HISTORY) > 10: CHAT_HISTORY.pop(0)
    
    # Session
    if session_id:
        add_message_to_session(session_id, "user", user)
        add_message_to_session(session_id, "assistant", assistant)

def get_all_memories() -> List[Dict]:
    # Return serializable list
    return [{k: v for k, v in m.items() if k != "embedding"} for m in USER_MEMORY]
