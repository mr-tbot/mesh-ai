# Use Python latest image
FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory
WORKDIR /app

# Copy only required files first
COPY meshtastic_ai.py requirements.txt /app/

# Then copy everything else
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose port 5000
EXPOSE 5000

# Run the script
CMD ["python", "/app/meshtastic_ai.py"]
