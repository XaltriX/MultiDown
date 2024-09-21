# Use a slim version of Python 3.12
FROM python:3.12-slim

# Install system dependencies (FFmpeg)
RUN apt-get update && apt-get install -y ffmpeg

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all the bot source code into the container
COPY . .

# Set the command to run your bot
CMD ["python", "bot.py"]
