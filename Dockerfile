FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory (temporary storage)
WORKDIR /tmp

# Copy necessary files to avoid overwriting
COPY config.json /tmp/
COPY commands_config.json /tmp/
COPY motd.json /tmp/

# Copy the rest of the files
COPY . /tmp/

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Ensure /app directory exists
RUN mkdir -p /app

# Move all files except the specific ones to /app, avoiding overwriting them
RUN mv /tmp/* /app/ && \
    mv /tmp/config.json /app/ && \
    mv /tmp/commands_config.json /app/ && \
    mv /tmp/motd.json /app/

# Expose port 5000
EXPOSE 5000

# Run the Python script
CMD ["python", "/app/meshtastic_ai.py"]
