# ================================
# Stage 1: Model Preparation
# ================================
FROM ghcr.io/ggml-org/llama.cpp:light-cuda AS model-downloader

WORKDIR /app
# Make sure /build/models exists even if nothing is downloaded
RUN mkdir -p /app/models

# =================================
# Stage 2: Prepare production image
# =================================
FROM ghcr.io/ggml-org/llama.cpp:server-cuda AS builder

RUN apt-get update && apt-get install -y python3 python3-venv unzip supervisor openssh-server \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /var/log/supervisor /var/run/sshd /root/.ssh \
 && chmod 700 /root/.ssh

RUN python3 -m venv /app/.venv 
# Python packages (RunPod SDK + utilities)
RUN /app/.venv/bin/python3 -m pip install --no-cache-dir --upgrade pip && \
    /app/.venv/bin/python3 -m pip install --no-cache-dir \
        runpod \
        fastapi \
        requests \
        huggingface_hub \
        psutil

WORKDIR /app
COPY FabioTestOcr /app
RUN /app/.venv/bin/python3 -m pip install --no-cache-dir -r /app/requirements.txt
RUN mkdir -p /app/data/ftp /app/output /app/logs

COPY src/entrypoint.sh /app/entrypoint.sh
COPY src/start-llama-server.sh /app/start-llama-server.sh
#COPY src/main.py /app/main.py
COPY src/supervisord.conf /app/supervisord.conf
COPY src/docker-entrypoint.sh /app/docker-entrypoint.sh

# Create non-root user
# RUN groupadd -r llama && useradd -r -g llama -u 1001 llamauser

# Copy built binary and models
FROM builder AS runtime
COPY --from=builder /app/llama-server /usr/local/bin/llama-server
COPY --from=builder /app /app
# Make scripts executable and setup supervisor
RUN chmod +x /app/entrypoint.sh /app/start-llama-server.sh /app/main.py /app/docker-entrypoint.sh || true \
 && cp /app/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Defaults for runtime; do NOT download model at build time
ARG MODEL_NAME=""
ARG MODEL_FILENAME=Qwen3-VL-30B-A3B-Instruct-Q8_0.gguf
ENV MODEL_NAME=${MODEL_NAME}
ENV MODEL_FILENAME=${MODEL_FILENAME}
ENV API_KEY=${LLAMA_API_KEY}
ENV PORT=8000

# Env
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV GGML_CUDA_NO_PINNED=0
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
ENV PYTHONUNBUFFERED=1
ENV HF_HUB_ENABLE_HF_TRANSFER=1

EXPOSE ${PORT:-80}

# Health check for RunPod compatibility
# HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
#   CMD curl -f http://localhost:${PORT}/ping || exit 1

# ENV CUDA_VISIBLE_DEVICES=0
# Run as non-root after files are in place

# Explicit entrypoint for supervisor
ENTRYPOINT ["/app/docker-entrypoint.sh"]
