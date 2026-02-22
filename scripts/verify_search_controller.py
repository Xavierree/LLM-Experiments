import sys
import os

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app.services import search_service
from app.core import models

def test_controller():
    print("🚀 Initializing Search Controller Verification...")
    
    # Pre-load model to avoid timeout in first query
    print("📦 Loading Controller Model...")
    models.load_controller_model()
    
    test_queries = [
        "Who won the Super Bowl 2024?",
        "Write a python script to sort a list.",
        "What is the price of Bitcoin right now?",
        "Explain the theory of relativity.",
        "Weather in Tokyo today"
    ]
    
    for q in test_queries:
        print(f"\n❓ Query: {q}")
        decision = search_service.extract_search_decision(q)
        print(f"🤖 Decision: {decision}")
        
    print("\n✅ Verification Complete.")

if __name__ == "__main__":
    test_controller()
