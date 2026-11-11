#!/bin/bash

# =================================================================
# Start llama-server with Qwen2.5-7B-Instruct (Reasoning Brain)
# Serves an OpenAI-compatible text/tool endpoint on port 8091
# =================================================================

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

PORT="${BRAIN_PORT:-8091}"
HOST="${BRAIN_HOST:-127.0.0.1}"
CTX_SIZE="${BRAIN_CTX:-24576}"

# Look for Qwen GGUF model (case-insensitive search)
MODEL_PATH=$(find "$PROJECT_ROOT/weights/brain_gguf" -iname "*qwen2.5-7b-instruct*.gguf" 2>/dev/null | head -n 1)

if [ -z "$MODEL_PATH" ] || [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Error: Qwen GGUF model file not found in $PROJECT_ROOT/weights/brain_gguf"
    exit 1
fi

# Look for llama-server binary
LLAMA_SERVER_BIN=$(find "$HOME/llama.cpp" -name "llama-server" 2>/dev/null | head -n 1)
if [ -z "$LLAMA_SERVER_BIN" ] && command -v llama-server > /dev/null 2>&1; then
    LLAMA_SERVER_BIN="llama-server"
fi

if [ -z "$LLAMA_SERVER_BIN" ] || { [ "$LLAMA_SERVER_BIN" != "llama-server" ] && [ ! -f "$LLAMA_SERVER_BIN" ]; }; then
    echo "❌ Error: llama-server executable not found."
    exit 1
fi

chmod +x "$LLAMA_SERVER_BIN" 2>/dev/null

BIN_DIR="$(dirname "$LLAMA_SERVER_BIN")"
export LD_LIBRARY_PATH="$BIN_DIR:/usr/local/cuda/lib64:$LD_LIBRARY_PATH"
export CUDA_VISIBLE_DEVICES=0
export NO_PROXY="localhost,127.0.0.1,0.0.0.0,::1"

mkdir -p "$SCRIPT_DIR/logs"

# Terminate any previous instance running on this port to ensure new context size takes effect
if pgrep -f "llama-server.*${PORT}" > /dev/null 2>&1; then
    echo "Restarting llama-server on port $PORT..."
    pkill -f "llama-server.*${PORT}" 2>/dev/null || true
    sleep 2
fi

echo "========================================="
echo " Starting Brain LLM (Qwen2.5-7B-Instruct)"
echo " Model:   $MODEL_PATH"
echo " Context: $CTX_SIZE tokens"
echo " Port:    $PORT"
echo "========================================="

nohup "$LLAMA_SERVER_BIN" \
    -m "$MODEL_PATH" \
    -c "$CTX_SIZE" \
    -ngl 99 \
    --host "$HOST" \
    --port "$PORT" > "$SCRIPT_DIR/logs/brain_server.log" 2>&1 &

PID=$!
echo "Brain llama-server launched with PID: $PID"

# Wait for startup
for i in {1..30}; do
    if curl -s --noproxy "*" "http://$HOST:$PORT/health" 2>/dev/null | grep -q "ok"; then
        echo "✓ Brain server is ready on http://$HOST:$PORT (PID $PID)"
        exit 0
    fi
    sleep 1
done

echo "⚠️ Server started (PID $PID), check logs if needed: $SCRIPT_DIR/logs/brain_server.log"
