#!/usr/bin/env python3
"""List available Groq models."""

import os
import warnings
warnings.filterwarnings('ignore')

os.environ['GROQ_API_SSL_VERIFY'] = '0'

import httpx
from groq import Groq
from src.config.settings import GROQ_API_KEY

print("📋 Available Groq models:\n")

try:
    client = Groq(api_key=GROQ_API_KEY, http_client=httpx.Client(verify=False))
    models = client.models.list()
    
    for model in models.data:
        print(f"  {model.id}")
        
except Exception as e:
    print(f"Error: {e}")
