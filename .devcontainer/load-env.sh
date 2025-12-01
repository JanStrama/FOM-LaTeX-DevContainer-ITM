#!/bin/bash
# Load environment variables from .env file and export them
if [ -f ".devcontainer/.env" ]; then
    set -a
    source .devcontainer/.env
    set +a
    echo "Environment variables loaded from .devcontainer/.env"
else
    echo "No .env file found"
fi