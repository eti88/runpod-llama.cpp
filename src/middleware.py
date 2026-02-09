from fastapi import Request, Response, HTTPException
import httpx
import requests
import logging

logger = logging.getLogger(__name__)

async def dispatch(llama_server_url: str, request: Request, call_next):
    path = request.url.path
    if not path.startswith('/v1'):
        # Let the request pass through to the next middleware
        return await call_next(request)
    
    # Forward the request to the llama.cpp server
    try:
        # Prepare the request to send to llama.cpp server
        query_params = request.url.query

        # Construct the full URL for llama.cpp server
        if query_params:
            full_url = f"{llama_server_url}{path}?{query_params}"
        else:
            full_url = f"{llama_server_url}{path}"
        # Prepare headers for the forward request
        headers = dict(request.headers)
        # Remove the 'host' header to avoid issues
        headers.pop('host', None)
        
        logger.debug(f"Forwarding request to: {full_url}")
        if request.method == "post" or request.method == "put" or request.method == "patch":
            body = await request.json()
        else:
            body = None
        # Make the request to llama.cpp server
        response = requests.request(method=request.method, url=full_url, json=body, headers=headers)
        return Response(
            content=response.content,
            status_code=response.status_code
        )   
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="Request to llama.cpp server timed out")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with llama.cpp server: {str(e)}")
