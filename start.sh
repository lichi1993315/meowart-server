#!/bin/bash

# Meowart Server Start Script
# Usage: ./start.sh

set -e

PORT=9901
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$APP_DIR/server.log"
PID_FILE="$APP_DIR/server.pid"

echo "🐱 Starting Meowart Server..."

# Kill any existing process on the port
if lsof -i :$PORT -t > /dev/null 2>&1; then
    echo "⚠️  Found existing process on port $PORT, stopping it..."
    lsof -i :$PORT -t | xargs -r kill -9
    sleep 1
fi

# Change to app directory
cd "$APP_DIR"

# Start uvicorn with nohup
echo "🚀 Starting uvicorn on port $PORT..."
nohup uvicorn app.main:app --host 0.0.0.0 --port $PORT > "$LOG_FILE" 2>&1 &

# Save PID
echo $! > "$PID_FILE"

# Wait a moment and check if started successfully
sleep 2

if lsof -i :$PORT -t > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "   PID: $(cat $PID_FILE)"
    echo "   Port: $PORT"
    echo "   Log: $LOG_FILE"
    echo ""
    echo "📍 Endpoints:"
    echo "   Local:  http://localhost:$PORT"
    echo "   Public: https://api.meowart.ai"
    echo "   Docs:   https://api.meowart.ai/docs"
else
    echo "❌ Failed to start server. Check logs:"
    tail -20 "$LOG_FILE"
    exit 1
fi
