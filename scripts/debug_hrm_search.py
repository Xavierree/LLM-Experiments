
import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services import search_service
from app.core import models

# Mock Plan Data from User Report
plan_objective = "Plan a family outing in Bogor"
steps = [
    "Research indoor family-friendly activities in Bogor, such as museums, indoor play centers, and cultural centers",
    "Check the weather forecast for the planned day",
    "Contact the chosen venues to confirm availability and booking procedures",
    "Prepare a list of emergency indoor activities in case the primary choice is unavailable"
]

async def test_search_decision():
    print("🚀 Starting HRM Search Debugger...")
    
    # Ensure model is checked/loaded
    # models.load_controller_model() 
    # (extracted_search_decision calls this internally if needed, but we can pre-load)
    
    for i, step in enumerate(steps):
        print(f"\n--- Testing Step {i+1} ---")
        step_search_prompt = f"Objective: {plan_objective}\nStep: {step}\nDoes this step require external information to execute?"
        print(f"Prompt Sent:\n{step_search_prompt}")
        
        decision = search_service.extract_search_decision(step_search_prompt, keep_loaded=True)
        print(f"Decision: {decision}")
        
    # Unload at end
    models.unload_controller_model()
    print("\n✅ Debug Complete.")

if __name__ == "__main__":
    asyncio.run(test_search_decision())
