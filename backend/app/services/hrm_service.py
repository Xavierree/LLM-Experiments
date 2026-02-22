import json
import re
import asyncio
import mlx.core as mx
from app.core import models, memory, logger
from app.services import search_service
from starlette.concurrency import run_in_threadpool

def extract_plan(text: str):
    """Parses the JSON plan from the LLM output."""
    try:
        # Attempt direct JSON fetch
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback/Mock if parsing fails or model refuses to output JSON
    return {
        "objective": text[:50] + "...",
        "steps": [text] 
    }

async def run_hrm(query: str, yield_steps=False, force_search: bool = False):
    """
    Executes the Harmonic Reasoner workflow.
    """
    # 1. Planner (Mistral) - Swapped as per user request
    print("🧠 HRM: Calling Planner...")
    model, tokenizer = await run_in_threadpool(models.load_model, "planner")
    
    system_prompt = (
        "You are a Planner AI.\n"
        "Respond ONLY with valid JSON.\n"
        "Format:\n"
        "{\n"
        "  \"objective\": \"<clear restatement of user goal>\",\n"
        "  \"steps\": [\n"
        "    \"<specific step 1>\",\n"
        "    \"<specific step 2>\",\n"
        "    \"...\"\n"
        "  ]\n"
        "}\n"
        "Do not use generic placeholders like 'step1'."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    inputs = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    raw_plan = await run_in_threadpool(models.generate, inputs)
    plan = extract_plan(raw_plan)
    
    if yield_steps: yield {"type": "plan", "content": plan}
    
    
    
    # 1.5 Web Search (Upfront) - REMOVED favoring Step-by-Step Search
    # We now analyze each step individually.
    search_context = "" 
    search_results_list = []
    
    # 2. Executor (mistral) - Swapped as per user request
    print("🔧 HRM: Switching to Executor...")
    
    # Explicitly clear previous model reference to allow GC
    del model
    del tokenizer
    # Also clear raw_plan if it's large, though unlikely
    mx.clear_cache()
    await asyncio.sleep(1.5)
    
    model, tokenizer = await run_in_threadpool(models.load_model, "executioner")
    
    results = []
    context_so_far = ""
    
    # Specialized System Prompt for Plans
    HRM_SEARCH_PROMPT = """You are a Search Decision Controller for an Agent. 
Your job is to analyze a specific STEP in a plan and decide if Google Search is needed to execute it.

[Rules]
1. OUTPUT STRICT JSON ONLY: {"needs_search": true/false, "query": "exact search query"}
2. SET needs_search = true IF:
   - The step uses verbs like "Research", "Find", "Check", "Look up", "Investigate", "Verify".
   - The step asks for specific external information (prices, weather, availability, news, specs).
   - The step implies gathering data you don't have.
3. SET needs_search = false IF:
   - The step is internal logic (Calculations, Reasoning, Summarizing, "Prepare a list" based on known info).
   - The step is "Contact..." or "Call..." (You cannot do this, so searching won't help unless finding the number).
   - The step is generic "Organize...", "Write...".
4. QUERY GENERATION:
   - Extract the core topic of the step for the search query.
"""

    for i, step in enumerate(plan.get("steps", [])):
        # --- STEP-BY-STEP SEARCH ANALYSIS ---
        print(f"🕵️ HRM Analysis: Checking if Step {i+1} needs search...")
        
        # Ask Controller about THIS SPECIFIC STEP
        # We might want to give it context (Objective + Step)
        step_search_prompt = f"Objective: {plan['objective']}\nStep: {step}\nDoes this step require external information to execute?"
        
        print(f"🔍 HRM Controller Prompt:\n---\n{step_search_prompt}\n---")
        
        # Keep controller loaded for subsequent steps in the loop!
        decision = await run_in_threadpool(search_service.extract_search_decision, step_search_prompt, keep_loaded=True, system_prompt=HRM_SEARCH_PROMPT)
        
        print(f"🤖 HRM Controller Decision for Step {i+1}: {decision}")
        
        if decision.get("needs_search") or force_search:
            query_to_search = decision.get("query") or step
            print(f"🌍 HRM: Searching for Step {i+1}: {query_to_search}")
            step_results = await run_in_threadpool(search_service.perform_search, query_to_search)
            
            if step_results:
                search_results_list.extend(step_results)
                step_search_context = f"\n[Search Results for Step {i+1} ({query_to_search})]:\n"
                for res in step_results:
                    step_search_context += f"- [{res['title']}]({res['link']}): {res['snippet']}\n"
                
                # Add to global context for Synthesis later
                search_context += step_search_context
        else:
             print(f"⏭️ HRM: Step {i+1} does NOT need search.")

        # Inject search context into step query
        # We include the global search context accumulated so far? 
        # Or just the specific one for this step?
        # Let's include specific + global if needed, but context_so_far handles previous steps.
        # Let's pass the specific step context strongly, and maybe previous search context is less relevant if previous steps solved it.
        # Actually, let's keep `search_context` accumulating so the model sees everything found so far.
        
        step_query = f"Objective: {plan['objective']}\nContext: {context_so_far}\nExternal Info: {search_context}\nTask: {step}"
        
        # Executor System Prompt
        sys_p = "You are an Executor AI. precise and technical."
        msgs = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": step_query}
        ]
        
        inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        result = await run_in_threadpool(models.generate, inp)
        
        results.append(result)
        context_so_far += f"\nStep {i+1}: {step}\nResult: {result}\n"
        
        if yield_steps: yield {"type": "step", "index": i, "step": step, "result": result, "search_decision": decision}
        
    # 3. Final Synthesis (codellama) - Kept as codellama
    print("🎓 HRM: Switching to Synthesis...")
    
    # EXPLICITLY UNLOAD CONTROLLER before loading the big synthesis model
    models.unload_controller_model() # Clear the 2GB Qwen 3B
    
    # Explicitly clear previous model reference to allow GC
    del model
    del tokenizer
    mx.clear_cache()
    await asyncio.sleep(1.5)
    
    # Ensure codellama is loaded (it should be, but load_model handles check)
    model, tokenizer = await run_in_threadpool(models.load_model, "synthesis")
    
    final_query = (
        f"Original Query: {query}\n\n"
        f"Execution Results:\n{context_so_far}\n\n"
        "Synthesize a final, comprehensive answer. "
        "Structure the response clearly with headers. "
        "Explain the reasoning logic used to arrive at the conclusion."
    )
    
    msgs = [{"role": "user", "content": final_query}]
    inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    final_answer = await run_in_threadpool(models.generate, inp, max_new_tokens=8192)
    
    # Remove string appending
    # if search_results_list:
    #    final_answer += ...
    
    # Log
    logger.log_raw_interaction(
        user=query,
        assistant=final_answer,
        mode="reasoning",
        system_prompt="HRM Logic",
        memory_used=False,
        model="codellama"
    )
    
    
    print(f"🎓 HRM: Final Yield Sources Count: {len(search_results_list)}")
    print(f"🎓 HRM: Final Yield Sources Count: {len(search_results_list)}")
    
    # Construct full state object for history
    full_state = {
        "plan": plan,
        "execution_steps": results, # List of strings/results
        "final_output": final_answer,
        "search_results": search_results_list
    }
    
    if yield_steps: yield {"type": "final", "content": final_answer, "sources": search_results_list, "state": full_state}


async def refine_hrm(session_id: str, corrections: dict):
    """
    Refines an HRM turn.
    corrections = {
        "planner": "...",
        "executor": "...",
        "synthesis": "..."
    }
    """
    session = memory.get_session(session_id)
    if not session: raise ValueError("Session not found")
    
    # Get the last turn (which must be an HRM turn)
    # in standard chat, we store "role": "assistant", "content": "..."
    # We need to find where we stored the HRM state.
    # In `run_hrm`, we currently yield "state". 
    # `endpoints.py` needs to store this state in the message history or a "runs" list.
    # For now, let's assume `memory.py` has been updated or we store it in a way we can retrieve.
    # Actually, the user asked for a "Turn" structure like refinement_service.
    # But HRM currently runs via WebSocket and just appends text to history.
    # We need to retroactively create a "Turn"-like structure or assume the last message has metadata.
    
    # HACK: Retrieve the last assistant message. We assume it has the "state" metadata 
    # if we update `messages` in memory to include it.
    # Let's check `memory.py`... it stores list of dicts.
    
    messages = session.get("messages", [])
    if not messages or messages[-1]["role"] != "assistant":
        raise ValueError("No active assistant response to refine")
        
    last_msg = messages[-1]
    # We need to ensure `endpoints.py` saved the `state` into `last_msg`.
    # If not, we can't refine. 
    # Let's assume `state` field exists in the message dict.
    
    old_state = last_msg.get("state", {})
    if not old_state:
        # Fallback: maybe we can't refine if state wasn't saved.
        # But we must support it.
        # Let's assume we can re-generate if needed, but we need the old output to reject.
        pass

    original_prompt = messages[-2]["content"] if len(messages) >= 2 else ""
    
    # Old Data
    old_plan = old_state.get("plan", {"objective": "Unknown", "steps": []})
    old_execution = old_state.get("execution_steps", []) # List[str]
    old_final = old_state.get("final_output", last_msg.get("content", ""))
    
    # Determine what to run
    run_planner = bool(corrections.get("planner"))
    run_executor = bool(corrections.get("executor")) or run_planner
    run_synthesis = bool(corrections.get("synthesis")) or run_executor
    
    # 1. PLANNER
    new_plan = old_plan
    if run_planner:
        print("🧠 HRM Refine: Re-running Planner...")
        correction = corrections["planner"]
        # Input: Original Prompt + Correction
        # We use a refinement prompt similar to refinement_service
        prompt_text = f"User Request: {original_prompt}\nPrevious Plan: {json.dumps(old_plan)}\nUser Correction: {correction}\nPlease generate a new, corrected plan JSON."
        
        model, tokenizer = await run_in_threadpool(models.load_model, "planner")
        msgs = [{"role": "user", "content": prompt_text}]
        # MLX Fix
        inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        raw_plan = await run_in_threadpool(models.generate, inp)
        new_plan = extract_plan(raw_plan)
        
    # 2. EXECUTOR
    new_execution = old_execution
    if run_executor:
        print("🔧 HRM Refine: Re-running Executor...")
        
        # If plan changed, we re-run all steps.
        # If only executor corrected, we might re-run with correction.
        # If plan didn't change but executor corrected:
        # We inject correction into the Executor's system prompt or context?
        
        correction = corrections.get("executor", "")
        
        # Re-run execution loop
        new_execution = []
        model, tokenizer = await run_in_threadpool(models.load_model, "executioner")
        
        context_so_far = ""
        search_context = "" # Reuse old search? or re-search? Let's reuse if possible, or empty.
        # Getting search from old_state if available
        if old_state.get("search_results"):
             # reconstruct string
             for res in old_state["search_results"]:
                 search_context += f"- [{res['title']}]({res['link']}): {res['snippet']}\n"
        
        for i, step in enumerate(new_plan.get("steps", [])):
            step_query = f"Objective: {new_plan['objective']}\nContext: {context_so_far}\nExternal Info: {search_context}\nTask: {step}"
            if correction:
                 step_query += f"\n\nUser Correction for Execution: {correction}"
            
            msgs = [{"role": "user", "content": step_query}]
            inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            result = await run_in_threadpool(models.generate, inp)
            new_execution.append(result)
            context_so_far += f"\nStep {i+1}: {step}\nResult: {result}\n"

    # 3. SYNTHESIS
    new_final = old_final
    if run_synthesis:
        print("🎓 HRM Refine: Re-running Synthesis...")
        correction = corrections.get("synthesis", "")
        
        # Build context from (New/Old) Execution
        context_str = ""
        steps = new_plan.get("steps", [])
        for i, res in enumerate(new_execution):
            if i < len(steps):
                context_str += f"\nStep {i+1}: {steps[i]}\nResult: {res}\n"
        
        final_query = (
            f"Original Query: {original_prompt}\n\n"
            f"Execution Results:\n{context_str}\n\n"
            "Synthesize a final answer."
        )
        if correction:
            final_query += f"\n\nUser Correction: {correction}"
            
        model, tokenizer = await run_in_threadpool(models.load_model, "synthesis")
        msgs = [{"role": "user", "content": final_query}]
        inp = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        new_final = await run_in_threadpool(models.generate, inp, max_new_tokens=8192)

    # LOGGING
    # Chosen = New, Rejected = Old (if it ran)
    # If it didn't run, we don't log? Or log as chosen=old?
    # User said: "if the executor is getting corrected only the executor and synthesis get corrected"
    # We should log what changed.
    
    # DEFERRED LOGGING (CUMULATIVE)
    # Check if we already have a pending log from a previous refinement step.
    # If so, we want to keep the ORIGINAL rejected state (the very first one)
    # and update the chosen state to the current one.
    existing_log = old_state.get("pending_log")
    
    if existing_log:
        pending_log = {
            "session_id": session_id,
            "original_prompt": existing_log["original_prompt"],
            
            # Chosen is ALWAYS the new result
            "plan_chosen": json.dumps(new_plan),
            # Rejected is the ORIGINAL rejected one
            "plan_rejected": existing_log["plan_rejected"],
            
            "execution_chosen": json.dumps(new_execution),
            "execution_rejected": existing_log["execution_rejected"],
            
            "synthesis_chosen": new_final,
            "synthesis_rejected": existing_log["synthesis_rejected"]
        }
        
        # If a stage ran this time but was "-" in previous log (meaning it wasn't rejected originally),
        # we should technically set it to the old_state of this run?
        # User requirement: "logged the first one until its accepted".
        # This implies we compare Start State vs End State.
        # If Start State was OK (rejected="-") and we changed it now, then Start State IS the rejected one.
        # But wait, if it was "-" originally, it means the user didn't correct it then.
        # If they correct it NOW, then the "Original" version of that stage IS the rejected one.
        # So we should populate it if it was empty.
        
        if pending_log["plan_rejected"] == "-" and run_planner:
            pending_log["plan_rejected"] = json.dumps(old_plan)
            
        if pending_log["execution_rejected"] == "-" and run_executor:
             pending_log["execution_rejected"] = json.dumps(old_execution)
             
        if pending_log["synthesis_rejected"] == "-" and run_synthesis:
             pending_log["synthesis_rejected"] = old_final
             
    else:
        # First Refinement
        pending_log = {
            "session_id": session_id,
            "original_prompt": original_prompt,
            
            "plan_chosen": json.dumps(new_plan),
            "plan_rejected": json.dumps(old_plan) if run_planner else "-",
            
            "execution_chosen": json.dumps(new_execution),
            "execution_rejected": json.dumps(old_execution) if run_executor else "-",
            
            "synthesis_chosen": new_final,
            "synthesis_rejected": old_final if run_synthesis else "-"
        }
    
    # Return new state
    new_state = {
        "plan": new_plan,
        "execution_steps": new_execution,
        "final_output": new_final,
        "search_results": old_state.get("search_results", []),
        "pending_log": pending_log
    }
    
    # Update Memory
    # We need to overwrite the last message content and state?
    messages[-1]["content"] = new_final
    messages[-1]["state"] = new_state
    memory.save_sessions()
    
    return new_state

