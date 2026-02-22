from app.core import models, memory, rag, logger
from app.services import search_service

def run_chat(query: str, mode: str = "chat", use_rag: bool = False, session_id: str = None, force_search: bool = False, model_choice: str = None, temperature: float = 0.7, max_new_tokens: int = 1024, save_history: bool = True, save_logs: bool = True) -> tuple[str, list]:
    """
    Orchestrates the chat pipeline based on mode.
    """
    # 1. Retrieve Memory
    user_mem = memory.retrieve_memory(query)
    
    # 2. Retrieve RAG (if enabled)
    rag_ctx = ""
    if use_rag:
        rag_ctx = rag.retrieve_context(query)
        if rag_ctx:
            print(f"📖 Retrieved RAG Context (len={len(rag_ctx)})")
            rag_ctx = (
                f"\n\n=== CONTEXT FROM USER UPLOADED FILES ===\n"
                f"{rag_ctx}\n"
                f"=== END OF UPLOADED FILES ===\n"
                f"Instructions: The content above is strictly from the files uploaded by the user. "
                f"If the user asks about 'the file', 'my document', or 'uploaded content', use the text above to answer.\n"
            )

    # 2.5 Web Search Logic (Controller Architecture)
    search_context = ""
    search_results_list = []
    
    # Check if we should search (Force or Controller Decision)
    if force_search:
        print(f"🌍 Force Search Enabled. Executing search for: {query}")
        decision = {"needs_search": True, "query": query}
    else:
        # Use the 3B Controller to decide
        decision = search_service.extract_search_decision(query)

    if decision.get("needs_search"):
        search_query = decision.get("query") or query
        print(f"🌍 Controller decided to search. Query: {search_query}")
        
        results = search_service.perform_search(search_query)
        if results:
            search_results_list = results
            search_context += f"\n=== WEB SEARCH RESULTS ({search_query}) ===\n"
            for res in results:
                search_context += f"- [{res['title']}]({res['link']}): {res['snippet']}\n"
            search_context += "=== END SEARCH RESULTS ===\n"
            
            # Instructions for the model on how to use search
            search_context += (
                "\nInstructions: Use the above search results to answer the user's question. "
                "Cite your sources using markdown links [Title](URL). "
                "If the search results don't contain the answer, say so.\n"
            )
    else:
        print("⏭️ Controller decided to SKIP search.")

    # 3. Build Context
    context_str = ""
    if user_mem:
        context_str += f"\nUser Facts:\n{user_mem}\n"
    if rag_ctx:
        context_str += rag_ctx
    if search_context:
        context_str += search_context

    # 4. Define System Prompt (Based on MODE, independent of model)
    if mode == "general":
        system_base = (
                    "You are my technical AI assistant."

                    "Response style:"
                    "- Clear, technical, structured"
                    "- No unnecessary explanations"
                    "- Prefer code, commands, and comparisons"
                    "- Enclose all code/commands in Markdown code blocks (e.g. ```python, ```bash)"
        )
    elif mode == "code":
        system_base = (
                    "You are my technical AI assistant."
                    "Your role:"
                    "- Optimize my ML, LLM, and system workflows"
                    "- Provide accurate, concise, and actionable guidance"
                    "- Focus on performance, hardware efficiency, and debugging"
                    
                    "My background:"
                    "- Mainly MacOS user"
                    "- ML/AI practitioner"
                    "- Interested in local LLMs, GPUs, VRAM, and system tuning"

                    "Response style:"
                    "- Clear, technical, structured"
                    "- No unnecessary explanations"
                    "- Prefer code, commands, and comparisons"
                    "- Enclose all code/commands in Markdown code blocks (e.g. ```python, ```bash)"
        )
    elif mode == "chat":
        system_base = (
            "You are chatting casually with a human. "
            "Friendly, expressive, brief, natural. "
            "Remember: Keep the tone casual, friendly, and concise."
        )
    else:
        system_base = "You are a helpful AI."

    # 5. Select Model
    # Use user choice if provided, otherwise defaults
    if model_choice:
        model_name = model_choice
        print(f"👉 User selected model: {model_name}")
    else:
        # Defaults
        if mode == "general":
            model_name = "chat"
        elif mode == "chat":
            model_name = "chat"
        elif mode == "code":
            model_name = "synthesis"
        else:
            model_name = "chat"

    # Load Model
    model, tokenizer = models.load_model(model_name)
    
    # Construct Messages
    system_prompt = system_base + context_str
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # History
    # If session_id is active, load from session
    if session_id:
        sess = memory.get_session(session_id)
        if sess:
            # 1. Try to get context from Refinement Turns (preferred)
            if "turns" in sess and sess["turns"]:
                for t in sess["turns"][-3:]: # Last 3 turns
                    messages.append({"role": "user", "content": t["prompt"]})
                    # Get response
                    resp = t.get("final_output")
                    if not resp and t.get("iterations"):
                        resp = t["iterations"][-1].get("response", "")
                    if resp:
                        messages.append({"role": "assistant", "content": resp})
            
            # 2. Add Legacy Messages (if any)
            # This handles the "Chat" mode simpler sessions
            if "messages" in sess:
                for m in sess["messages"][-6:]:
                    messages.append({"role": m["role"], "content": m["content"]})
    else:
        # Fallback to legacy
        for turn in memory.CHAT_HISTORY[-6:]:
            messages.append({"role": "user", "content": turn["u"]})
            messages.append({"role": "assistant", "content": turn["a"]})
        
    # Append User Query
    user_content = query
    # if mode == "chat":
    #    user_content += "\n\n(Remember: Keep the tone casual, friendly, and concise.)"
    
    messages.append({"role": "user", "content": user_content})
    
    # Generate
    # Generate (MLX Compatible)
    prompt = tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    response = models.generate_response(prompt, max_new_tokens=max_new_tokens, temperature=temperature)
    
    
    # Update History / Memory
    if save_history:
        memory.update_chat_history(query, response, session_id=session_id)
        memory.maybe_store_memory(query)
    
    # LOGGING
    if save_logs:
        logger.log_raw_interaction(
            system_prompt=system_prompt,
            user=query,
            assistant=response,
            mode=mode,
            memory_used=bool(user_mem),
            model=model_name
        )

    return response, search_results_list
