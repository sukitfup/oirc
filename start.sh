#!/bin/bash

# Check if venv directory exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating venv..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Virtual environment already exists."
    source venv/bin/activate
fi

# Run your main Python script
python3 main.py