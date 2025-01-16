import os
import threading

import httpx
import openai
from dotenv import load_dotenv
from ollama import Ollama
from agency_swarm import Agent

load_dotenv()

client_lock = threading.Lock()
client = None

ceo = Agent(name="ceo", description="I am the CEO", model='ollama/llama3')

def get_openai_client():
    global client
    with client_lock:
        if client is None:
            # Check if the API key is set
            api_key = openai.api_key or os.getenv("OPENAI_API_KEY")
            if api_key is None:
                raise ValueError(
                    "OpenAI API key is not set. Please set it using set_openai_key."
                )
            client = openai.OpenAI(
                api_key=api_key,
                timeout=httpx.Timeout(60.0, read=40, connect=5.0),
                max_retries=10,
                default_headers={"OpenAI-Beta": "assistants=v2"},
            )
    return client


def set_openai_client():
    global client
    client = Ollama(
        model_path="path/to/your/local/ollama/model",
        timeout=5,
        max_retries=5,
    )
    return client


def set_openai_key(key):
    if not key:
        raise ValueError("Invalid API key. The API key cannot be empty.")
    openai.api_key = key
    global client
    with client_lock:
        client = None

## Using Local Ollama Models

To use local Ollama models with agency-swarm, follow these steps:

**1. Install the required dependencies:**

```sh
pip install ollama
