import time
import uuid
from app.core import memory, models, logger
from app.services import chat_service

async def start_turn(session_id: str, prompt: str, model_choice: str = None, mode: str = "chat", temperature: float = 0.7, max_new_tokens: int = 1024, force_search: bool = False) -> dict:
    """
    Starts a new turn in the session. 
    1. Records the user prompt.
    2. Generates initial response from LLM.
    3. Stores as Iteration 0.
    """
    if not session_id:
        raise ValueError("Session ID required")
    
    # 1. Generate Response
    # We use chat_service to get the raw response. 
    # Note: chat_service currently adds to memory itself, we might need to decouple that
    # or just use the raw generation and handle memory here. 
    # For now, let's assume we call a lower-level generate to avoid double memory.
    
    # 1. Generate Response via Chat Service (for RAG/Search/System Prompts)
    # We disable save_history because we store it as a Turn object below.
    print(f"Generating response for turn: {prompt[:50]}...")
    
    response_text, sources = chat_service.run_chat(
        query=prompt,
        mode=mode,
        use_rag=True, # Default to True for refinement turns? Or pass from request?
        session_id=session_id,
        model_choice=model_choice,
        save_history=False,
        save_logs=True,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        force_search=force_search
    )
    
    # response_text = models.generate(full_prompt, max_new_tokens=1024, temperature=0.7)
    
    # 2. Create Turn Object
    turn_id = str(uuid.uuid4())
    new_turn = {
        "id": turn_id,
        "prompt": prompt,
        "mode": mode,
        "status": "pending", # pending, accepted
        "iterations": [
            {
                "index": 0,
                "response": response_text,
                "sources": sources,
                "correction": None, # None for first one
                "timestamp": time.time()
            }
        ],
        "final_output": None
    }
    
    # 3. Save to Session
    memory.add_turn_to_session(session_id, new_turn)
    
    return new_turn

async def refine_turn(session_id: str, correction: str, temperature: float = 0.7, max_new_tokens: int = 1024) -> dict:
    """
    User rejects the last response and offers a correction.
    1. Get current turn.
    2. Construct prompt with: Original Prompt -> System Response -> User Correction.
    3. Generate new response.
    4. Append new iteration.
    """
    session = memory.get_session(session_id)
    if not session or not session.get("turns"):
        raise ValueError("No active turn to refine")
    
    current_turn = session["turns"][-1]
    
    # Check if already accepted?
    if current_turn.get("status") == "accepted":
         raise ValueError("Turn already accepted. Cannot refine.")
         
    # Get last iteration response
    last_iteration = current_turn["iterations"][-1]
    last_response = last_iteration["response"]
    
    # Build Refinement Prompt using Chat Template
    messages = []
    
    # 1. System Prompt (Reuse logic from chat_service or simple default)
    # For refinement, we want it to be helpful and follow instructions.
    messages.append({"role": "system", "content": "You are a helpful AI assistant. The user is correcting your previous response. Please provide a new, improved response based on the correction."})
    
    # 2. History (Previous Turns)
    # We iterate through all turns except the current one
    turns = session.get("turns", [])
    current_turn_index = len(turns) - 1
    
    for i, t in enumerate(turns):
        if i == current_turn_index: break # Stop before current
        
        # Add User Prompt
        messages.append({"role": "user", "content": t["prompt"]})
        
        # Add Final Response (or last iteration)
        resp = t.get("final_output")
        if not resp and t.get("iterations"):
             resp = t["iterations"][-1].get("response", "")
        
        if resp:
            messages.append({"role": "assistant", "content": resp})

    # 3. Current Turn Context
    # User Prompt
    messages.append({"role": "user", "content": current_turn['prompt']})
    
    # Assistant's "Bad" Response (that is being corrected)
    messages.append({"role": "assistant", "content": last_response})
    
    # 4. User Correction
    messages.append({"role": "user", "content": f"Correction: {correction}\nPlease rewrite the response."})

    print(f"Refining with correction: {correction[:50]}...")
    
    # Apply Template
    if models.TOKENIZER:
        full_prompt = models.TOKENIZER.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
    else:
        # Fallback if tokenizer not loaded (shouldn't happen if model is loaded)
        full_prompt = f"User: {current_turn['prompt']}\nAssistant: {last_response}\nUser: {correction}\nAssistant:"

    new_response = models.generate(full_prompt, max_new_tokens=max_new_tokens, temperature=temperature)
    
    # Record the correction on the *previous* iteration (the one being corrected)
    # Actually, the data model had "correction" in the iteration structure. 
    # Let's say iteration[0] has correction="Too verbose". Then iteration[1] is the result.
    current_turn["iterations"][-1]["correction"] = correction
    
    # Create new iteration
    new_iteration = {
        "index": len(current_turn["iterations"]),
        "response": new_response,
        "correction": None,
        "timestamp": time.time()
    }
    
    current_turn["iterations"].append(new_iteration)
    memory.update_last_turn(session_id, current_turn)
    
    return current_turn

def accept_turn(session_id: str) -> dict:
    session = memory.get_session(session_id)
    if not session or not session.get("turns"):
        raise ValueError("No active turn to accept")
        
    current_turn = session["turns"][-1]
    current_turn["status"] = "accepted"
    
    # The final output is the response of the last iteration
    current_turn["final_output"] = current_turn["iterations"][-1]["response"]
    
    memory.update_last_turn(session_id, current_turn)
    
    # --- LOGGING FOR REFINEMENT ---
    # "prompt": "<|user|>\nPROMPT_TEXT\n<|assistant|>",
    # "chosen": "FINAL_ACCEPTED_OUTPUT",
    # "rejected": "FIRST_REJECTED_OUTPUT" (or nan),
    # "persona": "planner",
    
    prompt_text = current_turn.get("prompt", "")
    persona = current_turn.get("mode", "chat")
    
    final_output = current_turn["final_output"]
    first_output = current_turn["iterations"][0]["response"]
    
    # If there was only 1 iteration (accepted immediately), rejected is None
    num_iterations = len(current_turn["iterations"])
    rejected_output = first_output if num_iterations > 1 else None
    
    # If the first output IS value, but it was rejected later, then first_output is the rejected one.
    # Logic: 
    # If user accepted immediately (iters=1), chosen=first_output, rejected=None.
    # If user rejected once (iters=2), chosen=second, rejected=first.
    # If user rejected twice (iters=3), chosen=third, rejected=first (per user instruction "first output that model generate").
    
    logger.log_refinement_event(
        prompt=prompt_text,
        chosen=final_output,
        rejected=rejected_output,
        persona=persona
    )

    return current_turn
