#!/usr/bin/env python3
"""
Check account status and credits
"""
import os
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    print("ANTHROPIC_API_KEY not found in environment")
    exit(1)

print(f"Using API key: {anthropic_api_key[:8]}...{anthropic_api_key[-8:]}")

# Try to get account info
headers = {
    "x-api-key": anthropic_api_key,
    "Content-Type": "application/json"
}

try:
    # Check if there's an account endpoint
    response = requests.get("https://api.anthropic.com/v1/account", headers=headers)
    print(f"Account check status: {response.status_code}")
    if response.status_code == 200:
        print("Account data:", response.json())
    else:
        print("Account response:", response.text)
except Exception as e:
    print(f"Account check failed: {e}")

# Check with a simple model request to see the error details
try:
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Hi"}]
        }
    )
    print(f"\nModel request status: {response.status_code}")
    print("Response:", response.text)
    
except Exception as e:
    print(f"Model request failed: {e}")