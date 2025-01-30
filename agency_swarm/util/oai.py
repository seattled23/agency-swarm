"""
OpenAI client utility functions for agency-swarm.
"""

import os
import threading
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional

load_dotenv()

client_lock = threading.Lock()
_openai_client: Optional[OpenAI] = None

def get_openai_client() -> OpenAI:
    """Get the OpenAI client instance."""
    global _openai_client
    if _openai_client is None:
        raise ValueError("OpenAI client not initialized. Call set_openai_key() or set_openai_client() first.")
    return _openai_client

def set_openai_key(api_key: str) -> None:
    """Set the OpenAI API key and initialize the client."""
    global _openai_client
    _openai_client = OpenAI(api_key=api_key)

def set_openai_client(client: OpenAI) -> None:
    """Set a custom OpenAI client instance."""
    global _openai_client
    _openai_client = client

def init_openai(api_key: Optional[str] = None, client: Optional[OpenAI] = None) -> None:
    """Initialize OpenAI with either an API key or client instance."""
    if client is not None:
        set_openai_client(client)
    elif api_key is not None:
        set_openai_key(api_key)
    else:
        raise ValueError("Either api_key or client must be provided")
