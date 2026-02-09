# RunPod llama.cpp

This repository provides a RunPod-compatible implementation of llama.cpp that allows you to run large language models on NVIDIA GPUs via RunPod's infrastructure.

## Overview

This project is a bridge between RunPod's platform and llama.cpp, enabling the deployment of LLMs as RunPod-compatible services. It uses:

- **llama.cpp**: The core LLM inference engine
- **RunPod SDK**: For RunPod platform integration 
- **FastAPI**: For the HTTP API interface
- **Docker**: For containerized deployment

The service exposes an API compatible with the OpenAI API, making it easy to integrate with existing applications.

## Features

- OpenAI API compatible interface
- NVIDIA GPU acceleration
- RunPod platform integration
- Docker image building
- GPU memory monitoring
- Health check endpoints

## Prerequisites

- Docker installed
- NVIDIA GPU with CUDA support
- RunPod account (for deployment)

## Building the Docker Image

### Prerequisites

Before building the Docker image, you need to have:

1. Access to the RunPod infrastructure
2. A valid RunPod account 
3. An NVIDIA GPU with CUDA support

### Build Process

The Docker image is built in multiple stages:

1. **Model Preparation Stage**: Downloads the specified model from Hugging Face
2. **Production Image Stage**: Installs Python dependencies and sets up the environment

### Building with Docker

```bash
# Example: pass the Hugging Face model ID to download during build
# (defaults to unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF:Q8_0 if omitted)
docker build -t runpod-llama:latest --build-arg MODEL_NAME=unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF:Q8_0 .
```

### Building with RunPod

To build and deploy to RunPod, you'll typically use RunPod's build process where you:

1. Push your Docker image to a container registry
2. Create a RunPod template with your image
3. Configure environment variables for the model and GPU settings

## How to Run

### Local Testing

You can run locally for testing:

```bash
# Set environment variables
export MODEL_NAME="meta-llama/Llama-3.2-1B"
export PORT=5000
export LLAMA_PORT=1234
export GPU_LAYERS=9999

# Run the service
python src/handler.py
```

### RunPod Deployment

For deployment on RunPod:

1. Build your Docker image
2. Push to a container registry
3. Create a RunPod template with the following environment variables:
   - `MODEL_NAME`: The Hugging Face model ID (e.g., `meta-llama/Llama-3.2-1B`)
   - `PORT`: The port to run the service on (default: 5000)
   - `LLAMA_PORT`: The port for the llama.cpp server (default: 1234)
   - `GPU_LAYERS`: Number of GPU layers to load (default: 9999)
   - `MAX_CONTEXT`: Maximum context size
   - `PARALLEL_REQUESTS`: Number of parallel requests to handle

## Environment Variables

| Variable | Description | Default |
|------------|-------------|-----------|
| `MODEL_NAME` | Hugging Face model ID | Required |
| `PORT` | Service port | 5000 |
| `LLAMA_PORT` | Llama server port | 1234 |
| `GPU_LAYERS` | Number of GPU layers | 9999 |
| `MAX_CONTEXT` | Maximum context size | 0 (auto) |
| `PARALLEL_REQUESTS` | Number of parallel requests | 4 |
| `CACHE_TYPE_K` | Cache type for K | f16 |
| `CACHE_TYPE_V` | Cache type for V | f16 |

## API Endpoints

- `/ping` - Health check endpoint
- `/v1/chat/completions` - Chat completions endpoint (OpenAI compatible)

## Dockerfile Structure

The Dockerfile uses a multi-stage build:

1. **Builder Stage**: Installs Python dependencies and builds the environment
2. **Runtime Stage**: Copies the built environment and sets up the service

## Troubleshooting

### Common Issues

1. **Model download failures**: Ensure `MODEL_NAME` is a valid Hugging Face model ID
2. **GPU memory issues**: Reduce `GPU_LAYERS` or `MAX_CONTEXT`
3. **Port conflicts**: Ensure `PORT` and `LLAMA_PORT` are not in use

## Contributing

Contributions are welcome. Please submit a pull request with your changes.

## License

This project is licensed under the MIT License.
