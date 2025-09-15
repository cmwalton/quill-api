#!/usr/bin/env python3
"""
Test script to check which Claude models you have access to
"""
import os
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    print("❌ ANTHROPIC_API_KEY not found in environment")
    exit(1)

client = Anthropic(api_key=anthropic_api_key)

# Models to test - try ALL possible current model names
models_to_test = [
    # 2025 Claude 4 models
    "claude-sonnet-4-20250514",      # Claude Sonnet 4 (latest)
    "claude-opus-4-20250514",        # Claude Opus 4
    "claude-opus-4-1-20250805",      # Claude Opus 4.1 (most recent)
    "claude-4-sonnet-20250514",      # Alternative naming
    "claude-4-opus-20250514",        # Alternative naming
    "claude-sonnet-4-0",             # Alternative naming
    "claude-opus-4-0",               # Alternative naming
    
    # 2025 Claude 3.7 model
    "claude-3-7-sonnet-20250219",    # Claude 3.7 Sonnet
    
    # Legacy models (may still work)
    "claude-3-5-sonnet-20241022",    # Latest 3.5 Sonnet (deprecated)
    "claude-3-5-haiku-20241022",     # Latest 3.5 Haiku  
    "claude-3-haiku-20240307",       # Claude 3 Haiku
    "claude-3-sonnet-20240229",      # Claude 3 Sonnet
    "claude-3-opus-20240229",        # Claude 3 Opus
    
    # Try alternative naming patterns
    "claude-3-5-sonnet-latest",
]

print("Testing Claude model access...\n")

working_models = []
failed_models = []

for model in models_to_test:
    try:
        print(f"Testing {model}... ", end="")
        
        # Try a simple request
        message = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": "Say hello"
            }]
        )
        
        if message.content:
            print("[WORKS]")
            working_models.append(model)
        else:
            print("[NO RESPONSE]")
            failed_models.append(model)
            
    except Exception as e:
        print(f"[FAILED]: {str(e)}")
        failed_models.append((model, str(e)))

print(f"\n{'='*50}")
print("RESULTS:")
print(f"{'='*50}")

if working_models:
    print("Working models:")
    for model in working_models:
        print(f"  - {model}")
else:
    print("No working models found")

if failed_models:
    print(f"\nFailed models:")
    for item in failed_models:
        if isinstance(item, tuple):
            model, error = item
            print(f"  - {model}: {error}")
        else:
            print(f"  - {item}")

print(f"\n{'='*50}")
print(f"You have access to {len(working_models)} out of {len(models_to_test)} models tested")