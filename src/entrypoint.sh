#!/bin/sh
set -eu

# Defaults
: "${MODEL_FILENAME:=Qwen3-VL-30B-A3B-Instruct-Q8_0.gguf}"
# MODEL_NAME may be empty; in that case we expect the model to be present in /app/models

mkdir -p /app/models

if [ ! -f "/app/models/${MODEL_FILENAME}" ]; then
  if [ -n "${MODEL_NAME:-}" ]; then
    echo "Model not found at /app/models/${MODEL_FILENAME}; attempting to download ${MODEL_NAME}..."
    
    # Parse MODEL_NAME format: user/model:quant or user/model
    HF_REPO=$(echo "${MODEL_NAME}" | cut -d: -f1)
    HF_FILE=$(echo "${MODEL_NAME}" | grep -o ':.*' | cut -d: -f2 || echo "")
    
    # Download using huggingface_hub Python package
    /app/.venv/bin/python3 -c "
from huggingface_hub import hf_hub_download, list_repo_files
import os
import sys
import shutil

repo_id = '${HF_REPO}'
quant_spec = '${HF_FILE}' if '${HF_FILE}' else None
target_path = '/app/models/${MODEL_FILENAME}'

print(f'Downloading from HuggingFace: {repo_id}')

try:
    if quant_spec:
        # Extract base model name from repo (e.g., 'Qwen3-VL-30B-A3B-Instruct-GGUF' -> 'Qwen3-VL-30B-A3B-Instruct')
        base_name = repo_id.split('/')[-1]
        if base_name.endswith('-GGUF'):
            base_name = base_name[:-5]
        
        # Construct possible filenames with the pattern: basename-quant.gguf
        possible_names = [
            f'{base_name}-{quant_spec}.gguf',
            f'{base_name}_{quant_spec}.gguf',
            f'{base_name}.{quant_spec}.gguf',
            f'{quant_spec}.gguf',
            quant_spec,
        ]
        
        print(f'  Quant specifier: {quant_spec}')
        print(f'  Base name: {base_name}')
        
        downloaded = None
        for fname in possible_names:
            try:
                print(f'  Trying filename: {fname}')
                downloaded = hf_hub_download(repo_id=repo_id, filename=fname)
                print(f'  Success! Downloaded to: {downloaded}')
                break
            except Exception as e:
                print(f'    Failed: {str(e)[:100]}')
                continue
        
        if not downloaded:
            print(f'Failed to download any variant. Listing available files...', file=sys.stderr)
            try:
                files = list_repo_files(repo_id=repo_id)
                gguf_files = [f for f in files if f.endswith('.gguf')]
                print(f'Available .gguf files in repo:', file=sys.stderr)
                for f in gguf_files[:10]:
                    print(f'  - {f}', file=sys.stderr)
            except:
                pass
            sys.exit(1)
    else:
        # List and download first .gguf file
        files = list_repo_files(repo_id=repo_id)
        gguf_files = [f for f in files if f.endswith('.gguf')]
        
        if not gguf_files:
            print('No .gguf files found in repository', file=sys.stderr)
            sys.exit(1)
        
        print(f'  Found {len(gguf_files)} .gguf file(s), downloading first: {gguf_files[0]}')
        downloaded = hf_hub_download(repo_id=repo_id, filename=gguf_files[0])
    
    # Copy to target location
    shutil.copy2(downloaded, target_path)
    print(f'Model saved to: {target_path}')
    
except Exception as e:
    print(f'Download failed: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
      echo "Failed to download model from HuggingFace" >&2
      exit 1
    fi
    
    echo "Successfully downloaded model to /app/models/${MODEL_FILENAME}"
  else
    echo "No model file at /app/models/${MODEL_FILENAME} and MODEL_NAME not set; cannot proceed" >&2
    exit 1
  fi
else
  echo "Using existing model at /app/models/${MODEL_FILENAME}"
fi

# Start the llama server (exec to forward signals)
exec /usr/local/bin/llama-server -m "/app/models/${MODEL_FILENAME}" --mmproj "/app/models/ggml-model-qwen3vl-30b-instruct-mmproj-bf16.gguf" -ngl 999 -fa on -c 128000 --jinja --port "${PORT}" --host "0.0.0.0" --api-key "${API_KEY}"
