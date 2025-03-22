FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory (temporary storage)
WORKDIR /tmp

# Copy only necessary files (consider using .dockerignore)
COPY . /tmp/

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Ensure /app directory exists
RUN mkdir -p /app

# Expose port 5000
EXPOSE 5000

# Move files to /app on container startup, but only if they don't already exist
CMD ["sh", "-c", "if [ ! -f /app/config.json ]; then mv /tmp/config.json /app/; fi && if [ ! -f /app/commands_config.json ]; then mv /tmp/commands_config.json /app/; fi && if [ ! -f /app/motd.json ]; then mv /tmp/motd.json /app/; fi && python /app/meshtastic_ai.py"]
