import runpod
import subprocess
import requests
import json
import os
import time
import psutil
import logging

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware import Middleware
from threading import Thread, Lock
from datetime import datetime

from models import ChatCompletionsRequest, ChatCompletionsResponse
from health import check_llama_server_health, get_comprehensive_health_status
from middleware import dispatch

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Global server state
server_process = None
model_loaded = False
server_lock = Lock()
health_stats = {
    "requests_processed": 0,
    "errors": 0,
    "last_request": None,
    "start_time": time.time()
}

# Get the port from environment variable or default to 1234
llama_port = os.getenv("LLAMA_PORT", 1234)
llama_server_url = f"http://localhost:{llama_port}"

# The FastAPI application
app = FastAPI()

def start_llama_server():
    """Start llama.cpp server with health monitoring"""
    global server_process, model_loaded
    
    model_name = os.getenv("MODEL_NAME", "").strip()
    # Check if model file exists
    if not model_name:
        raise FileNotFoundError(f"Model not defined")
    
    cmd = [
        "/app/llama-server",
        "--hf-repo", model_name,
        "--mmproj", "/app/models/ggml-model-qwen3vl-30b-instruct-mmproj-bf16.gguf",
        "--port", os.getenv("LLAMA_PORT", "1234"),
        "--host", "0.0.0.0",
        "--ctx-size", os.getenv("MAX_CONTEXT", "0"),
        "--n-gpu-layers", os.getenv("GPU_LAYERS", "9999"),
        "--parallel", os.getenv("PARALLEL_REQUESTS", "4"),
        "--jinja",
        "--cache-type-k", os.getenv("CACHE_TYPE_K", "f16"),
        "--cache-type-v", os.getenv("CACHE_TYPE_V", "f16"),
        "--cont-batching",
        "--flash-attn",
        "--api-key", os.getenv("LLAMA_API_KEY", ""),
    ]
    
    print(f"Starting llama.cpp server with command: {' '.join(cmd)}")
    server_process = subprocess.Popen(
        cmd, 
        stdout=None, 
        stderr=None,
        universal_newlines=True
    )
    
    # Monitor server startup
    start_time = time.time()
    while time.time() - start_time < 300:  # 60 second timeout
        if check_llama_server_health():
            model_loaded = True
            print("✓ llama.cpp server is ready")
            
            # Log initial health status
            health = get_comprehensive_health_status()
            print(f"Initial health check: {json.dumps(health, indent=2)}")
            return
        
        # Check if process crashed
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print(f"stdout {stdout}, stderr {stderr}")
            raise Exception(f"Server crashed during startup. stderr: {stderr}")
        
        time.sleep(1)
    
    raise Exception("Server failed to start within 300 seconds")

@app.get("/ping")
async def health_check():
    return get_comprehensive_health_status()

@app.middleware('http')
async def llama_server_proxy(request: Request, call_next):
    return await dispatch(llama_server_url, request, call_next)

# Initialize everything
if __name__ == "__main__":
    print("Initializing RunPod llama.cpp handler...")
    
    # Start the llama.cpp server
    try:
        start_thread = Thread(target=start_llama_server)
        start_thread.start()
        start_thread.join()  # Wait for server to be ready
        
        import uvicorn
        port = int(os.getenv("PORT", 5000))
        print(f"Starting server on port {port} ...")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")
        
    except Exception as e:
        print(f"Failed to initialize: {e}")
        if server_process:
            server_process.terminate()
        raise
