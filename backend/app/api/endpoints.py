import asyncio
import asyncio
import os
from fastapi import APIRouter, HTTPException, WebSocket, BackgroundTasks, WebSocketDisconnect, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from app.services import chat_service, hrm_service, ingestion_service, refinement_service, model_service
from app.core import memory, logger, models, rag

router = APIRouter()

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, TXT) for RAG ingestion.
    """
    result = await ingestion_service.ingestion_service.process_file(file)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/rag/files")
def list_rag_files():
    """List all uploaded files in RAG."""
    return {"files": rag.list_documents()}

@router.delete("/rag/files/{filename}")
def delete_rag_file(filename: str):
    """Delete a file from RAG."""
    count = rag.delete_document(filename)
    if count == 0:
        return {"message": "File not found or already deleted", "chunks_deleted": 0}
    return {"message": f"Deleted {filename}", "chunks_deleted": count}

class ChatRequest(BaseModel):
    message: str
    mode: str = "chat" # chat, general, reasoning
    use_rag: bool = False
    force_search: bool = False
    model: Optional[str] = None # New model param
    temperature: float = 0.7
    max_tokens: int = 1024

@router.post("/train")
async def train_models(background_tasks: BackgroundTasks):
    """Triggers the LoRA training pipeline."""
    
    async def run_training_pipeline():
        print("🏋️ Starting Training Pipeline...")
        
        cwd = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # backend root
        script_train = os.path.join(cwd, "scripts", "training_lora.py")
        
        scripts_dir = os.path.join(cwd, "scripts")
        
        proc = await asyncio.create_subprocess_exec(
            "python3", "training_lora.py",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, 
            cwd=scripts_dir
        )
        
        stdout, stderr = await proc.communicate()
        
        if stdout:
            print(f"[Training STDOUT]\n{stdout.decode()}")
        if stderr:
            print(f"[Training STDERR]\n{stderr.decode()}")
            
        print("✅ Training Pipeline Complete.")

    background_tasks.add_task(run_training_pipeline)
    return {"status": "started", "message": "Training pipeline started in background. Check terminal for logs."}

class MemoryItem(BaseModel):
    text: str
    type: str
    importance: int

@router.post("/chat_mode")
def set_mode(mode: str):
    return {"status": "mode_set", "mode": mode}

class StartTurnRequest(BaseModel):
    session_id: str
    prompt: str
    model: Optional[str] = None
    mode: str = "chat"
    temperature: float = 0.7
    max_tokens: int = 1024
    force_search: bool = False

class RefineTurnRequest(BaseModel):
    session_id: str
    correction: str
    temperature: float = 0.7
    max_tokens: int = 1024

class AcceptTurnRequest(BaseModel):
    session_id: str

@router.post("/chat/turn/start")
async def start_turn(req: StartTurnRequest):
    """Starts a new turn with an initial response."""
    return await refinement_service.start_turn(
        req.session_id, 
        req.prompt, 
        req.model, 
        req.mode,
        temperature=req.temperature,
        max_new_tokens=req.max_tokens,
        force_search=req.force_search
    )

@router.post("/chat/turn/refine")
async def refine_turn(req: RefineTurnRequest):
    """Refines the current turn based on user correction."""
    return await refinement_service.refine_turn(
        req.session_id, 
        req.correction,
        temperature=req.temperature,
        max_new_tokens=req.max_tokens
    )

@router.post("/chat/turn/accept")
def accept_turn(req: AcceptTurnRequest):
    """Accepts the current turn and saves it."""
    try:
        return refinement_service.accept_turn(req.session_id)
    except ValueError:
        # If Agent/HRM mode, the turn might not be in refinement_service's tracking
        # but is already saved in memory by hrm_service.
        
        # Check for pending logging from HRM Refinement
        session = memory.get_session(req.session_id)
        if session and session.get("messages"):
            last_msg = session["messages"][-1]
            if last_msg.get("role") == "assistant":
                state = last_msg.get("state", {})
                pending_log = state.get("pending_log")
                
                if pending_log:
                    print("📝 Committing Deferred HRM Log...")
                    logger.log_hrm_event(**pending_log)
                    
                    # Clear pending log to prevent duplicate
                    del state["pending_log"]
                    memory.save_sessions()

        return {"status": "ok", "msg": "Turn accepted (Agent mode)"}

class RefineAgentRequest(BaseModel):
    session_id: str
    corrections: dict

@router.post("/chat/agent/refine")
async def refine_agent(req: RefineAgentRequest):
    """Refines an Agent (HRM) turn."""
    return await hrm_service.refine_hrm(req.session_id, req.corrections)

@router.post("/chat/stream")
async def chat_endpoint(req: ChatRequest):
    """
    streaming is hard with standard HTTP, usually use SSE or WebSocket.
    For this prototype, we return full response for 'chat'/'general' 
    and use a generator for 'reasoning' (but FastAPI needs StreamingResponse).
    """
    if req.mode == "reasoning" or req.mode == "agent":
        # HRM is complex, better use WebSocket or StreamingResponse
        # For simplicity in this step, we just run it and return final.
        # Ideally, use WebSocket for the "Step Visualizer"
        res = ""
        async for chunk in hrm_service.run_hrm(req.message, yield_steps=True, force_search=req.force_search):
            if chunk["type"] == "final":
                res = {"response": chunk["content"], "sources": chunk.get("sources", [])}
        return res
        
    else:
        # Standard Chat - Pass Model Choice
        response, sources = chat_service.run_chat(
            req.message, req.mode, req.use_rag, 
            force_search=req.force_search, 
            model_choice=req.model,
            temperature=req.temperature,
            max_new_tokens=req.max_tokens
        )
        return {"response": response, "sources": sources}

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    print("🔌 WebSocket Connected!")
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("message")
            mode = data.get("mode", "chat")
            model = data.get("model") # Get selected model
            temperature = data.get("temperature", 0.7)
            max_tokens = data.get("maxTokens", 1024)
            force_search = data.get("forceSearch", False)
            session_id = data.get("sessionId") # Frontend will send this
            
            use_rag = data.get("useRag", True) # Default to True to use uploaded files
            
            if mode == "reasoning" or mode == "agent":
                final_content = ""
                async for step in hrm_service.run_hrm(query, yield_steps=True, force_search=force_search):
                    if step["type"] == "final":
                        final_content = step["content"]
                        
                        # Save state!
                        if session_id:
                            session = memory.get_session(session_id)
                            # Add User
                            memory.add_message_to_session(session_id, "user", query)
                            
                            # Add Assistant with State
                            am = {
                                "role": "assistant",
                                "content": final_content,
                                "timestamp": memory.time.time(),
                                "mode": mode,
                                "state": step.get("state", {})
                            }
                            if "messages" not in session: session["messages"] = []
                            session["messages"].append(am)
                            memory.save_sessions()
                            
                    await websocket.send_json(step)
                        
            else:
                resp, sources = chat_service.run_chat(
                    query, mode, use_rag=use_rag, 
                    session_id=session_id, 
                    force_search=force_search, 
                    model_choice=model,
                    temperature=temperature,
                    max_new_tokens=max_tokens
                )
                await websocket.send_json({"type": "final", "content": resp, "sources": sources})
    except WebSocketDisconnect:
        print("🔌 WebSocket Disconnected")

@router.get("/sessions")
def list_sessions():
    return memory.list_sessions()

@router.post("/sessions")
def create_session(item: dict):
    # item can contain optional 'title'
    sid = memory.create_session(item.get("title", "New Chat"))
    return {"id": sid}

class SessionUpdate(BaseModel):
    pinned: Optional[bool] = None
    title: Optional[str] = None

@router.patch("/sessions/{session_id}")
def update_session(session_id: str, updates: SessionUpdate):
    if updates.pinned is not None:
        memory.set_session_pin(session_id, updates.pinned)
    return {"status": "ok"}

@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    sess = memory.get_session(session_id)
    if not sess: raise HTTPException(status_code=404, detail="Session not found")
    return sess

@router.get("/memory")
def get_memories():
    return memory.get_all_memories()

@router.post("/memory")
def add_memory(item: MemoryItem):
    memory.maybe_store_memory(item.text) 
    return {"status": "ok"}

# --- System Endpoints ---

@router.get("/system/status")
async def get_system_status():
    """Returns current model status."""
    return {
        "current_model": models.CURRENT_MODEL_NAME,
        "is_loaded": models.MODEL is not None
    }

@router.post("/system/reload")
async def reload_system():
    """Unloads models to clear VRAM."""
    models.unload_model()
    return {"status": "VRAM Cleared. Models Unloaded."}

class ModelLoadRequest(BaseModel):
    model_name: str

@router.post("/system/load")
async def load_system_model(req: ModelLoadRequest):
    """Manually loads a model."""
    print(f"🔄 Request to load model: {req.model_name}")
    models.load_model(req.model_name)
    return {"status": f"Loaded {req.model_name}"}

@router.get("/models/local")
def list_local_models_endpoint():
    """Lists local models available for conversion or loading."""
    return model_service.list_local_models()

class ConvertRequest(BaseModel):
    model_path_name: str
    quantization: str = "4bit"

@router.post("/models/convert")
async def convert_model_endpoint(req: ConvertRequest, background_tasks: BackgroundTasks):
    """
    Triggers model conversion in background.
    """
    # Create a wrapper task to run the async conversion
    async def run_conversion():
        print(f"🔄 Starting background conversion for {req.model_path_name}")
        result = await model_service.convert_model_to_mlx(req.model_path_name, req.quantization)
        if result["status"] == "success":
            print(f"✅ Conversion task finished for {req.model_path_name}")
        else:
            print(f"❌ Conversion task FAILED for {req.model_path_name}: {result.get('message')}")

    background_tasks.add_task(run_conversion)
    return {"status": "started", "message": f"Conversion started for {req.model_path_name}"}

@router.websocket("/ws/system/logs")
async def websocket_logs(websocket: WebSocket):
    await logger.log_broadcaster.connect(websocket)
    try:
        while True:
            # Just keep connection alive, broadcaster handles sending
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.log_broadcaster.disconnect(websocket)

