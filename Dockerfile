# Use Python latest image
FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory
WORKDIR /app

# Copy files explicitly
COPY . /app/

# List files after copying (for debugging)
RUN ls -l /app

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose port 5000
EXPOSE 5000

# Set the default command
CMD ["python", "/app/meshtastic_ai.py"]
