# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy the requirements file to the container
COPY requirements.txt ./

# Install the required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Run the bot
CMD ["python", "bot.py"]
