#!/bin/bash

# =================================================================
# Start llama-server with DentalGPT GGUF model
# Serves an OpenAI-compatible multimodal endpoint on port 8090
# =================================================================

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

MODEL_PATH="${DENTAL_GPT_GGUF_MODEL:-$PROJECT_ROOT/weights/dental_gpt_gguf/DentalGPT-7B-1026.f16.gguf}"
MMPROJ_PATH="${DENTAL_GPT_GGUF_MMPROJ:-$PROJECT_ROOT/weights/dental_gpt_gguf/DentalGPT-7B-1026.mmproj-f16.gguf}"
LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-$HOME/llama.cpp/build/bin/llama-server}"
PORT="${LLAMA_PORT:-8090}"
HOST="${LLAMA_HOST:-127.0.0.1}"

# Look for llama-server
FOUND_BIN=$(find "$HOME/llama.cpp" -name "llama-server" 2>/dev/null | head -n 1)
if [ -n "$FOUND_BIN" ] && [ -x "$FOUND_BIN" ]; then
    LLAMA_SERVER_BIN="$FOUND_BIN"
elif [ -n "$FOUND_BIN" ] && [ -f "$FOUND_BIN" ]; then
    chmod +x "$FOUND_BIN"
    LLAMA_SERVER_BIN="$FOUND_BIN"
elif command -v llama-server > /dev/null 2>&1; then
    LLAMA_SERVER_BIN="llama-server"
elif [ -f "$LLAMA_SERVER_BIN" ]; then
    chmod +x "$LLAMA_SERVER_BIN"
else
    echo "Error: llama-server executable not found."
    echo "Searched $HOME/llama.cpp and PATH. Please check installation."
    exit 1
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file not found at $MODEL_PATH"
    exit 1
fi

if [ ! -f "$MMPROJ_PATH" ]; then
    echo "Error: Vision projector file not found at $MMPROJ_PATH"
    exit 1
fi

mkdir -p "$SCRIPT_DIR/logs"

echo "========================================="
echo " Starting llama-server with DentalGPT"
echo " Model:  $MODEL_PATH"
echo " MMPROJ: $MMPROJ_PATH"
echo " Port:   $PORT"
echo "========================================="

nohup "$LLAMA_SERVER_BIN" \
    -m "$MODEL_PATH" \
    --mmproj "$MMPROJ_PATH" \
    -c 8192 \
    -ngl 99 \
    --host "$HOST" \
    --port "$PORT" > "$SCRIPT_DIR/logs/llama_server.log" 2>&1 &

echo "llama-server started with PID: $!"
echo "Log file: $SCRIPT_DIR/logs/llama_server.log"
