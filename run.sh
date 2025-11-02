#!/bin/bash
# Start Semantic Bit GPU Server

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start server
echo "Starting Semantic Bit GPU Server..."
echo "API docs will be available at: http://localhost:8000/docs"
python -m server.main
