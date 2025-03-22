# Use Python latest image
FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Install necessary dependencies
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --upgrade pip

# Set working directory
WORKDIR /app

# Copy all files to the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000
EXPOSE 5000

# Set entry point command
CMD ["python", "meshtastic_ai.py"]
