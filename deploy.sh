#!/bin/bash

# Update and install system dependencies
apt-get update && apt-get install -y ffmpeg

# Install Python dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
