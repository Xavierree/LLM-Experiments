from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
import uvicorn
from dotenv import load_dotenv
import warnings

# Suppress benign shutdown warning "resource_tracker: There appear to be 1 leaked semaphore objects"
warnings.filterwarnings("ignore", category=UserWarning, module="multiprocessing.resource_tracker")

load_dotenv()

app = FastAPI(title="LLM WebApp Backend")

# CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "running"}

if __name__ == "__main__":
    # Start server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
