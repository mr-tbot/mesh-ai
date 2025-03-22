# Use Python latest image
FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory (temporary storage)
WORKDIR /tmp

# Copy all files to /tmp first
COPY . /tmp/

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Ensure /app directory exists
RUN mkdir -p /app

# Expose port 5000
EXPOSE 5000

# Move files to /app on container startup
CMD ["sh", "-c", "mv /tmp/* /app/ && python /app/meshtastic_ai.py"]
