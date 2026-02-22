import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict

# Usage: [{"text": "content...", "source": "filename.txt"}]
DOCUMENTS: List[Dict[str, str]] = [] 
INDEX = None
EMBEDDER = None

def get_embedder():
    global EMBEDDER
    if EMBEDDER is None:
        EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
    return EMBEDDER

def rebuild_index():
    """Rebuilds FAISS index from current DOCUMENTS."""
    global INDEX
    if not DOCUMENTS:
        INDEX = None
        print("📚 RAG Index cleared (empty).")
        return

    texts = [doc["text"] for doc in DOCUMENTS]
    embedder = get_embedder()
    embeddings = embedder.encode(texts, batch_size=32, convert_to_numpy=True)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    INDEX = index
    print(f"📚 RAG Index rebuilt with {len(DOCUMENTS)} chunks.")

def add_documents(texts: List[str], source: str):
    """Adds new documents and rebuilds index."""
    global DOCUMENTS
    new_docs = [{"text": t, "source": source} for t in texts]
    DOCUMENTS.extend(new_docs)
    rebuild_index()

def delete_document(source: str) -> int:
    """Deletes all chunks for a given source. Returns count of deleted chunks."""
    global DOCUMENTS
    initial_count = len(DOCUMENTS)
    DOCUMENTS = [doc for doc in DOCUMENTS if doc["source"] != source]
    deleted_count = initial_count - len(DOCUMENTS)
    
    if deleted_count > 0:
        rebuild_index()
    
    return deleted_count

def list_documents() -> List[str]:
    """Returns list of unique source filenames."""
    sources = set(doc["source"] for doc in DOCUMENTS)
    return list(sources)

def retrieve_context(query: str, k=5) -> str:
    if INDEX is None or not DOCUMENTS:
        return ""
    
    embedder = get_embedder()
    q_emb = embedder.encode([query]).astype("float32")
    
    # Search
    # D, I = index.search(data, k)
    _, idxs = INDEX.search(q_emb, k)
    
    # Retrieve
    # Retrieve with character limit to prevent OOM
    MAX_CTX_CHARS = 6000 # ~1500-2000 tokens
    
    results = []
    current_len = 0
    
    for i in idxs[0]:
        if i != -1 and i < len(DOCUMENTS):
           doc = DOCUMENTS[i]
           text = doc["text"]
           
           if current_len + len(text) > MAX_CTX_CHARS:
               # Take partial if possible or just stop
               remaining = MAX_CTX_CHARS - current_len
               if remaining > 100:
                   results.append(text[:remaining] + "...(truncated)")
               break
               
           results.append(text)
           current_len += len(text)
           
    return "\n\n".join(results)
