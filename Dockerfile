# Use Python latest image
FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory (temporary storage)
WORKDIR /tmp

# Check if all required files already exist in the project directory
RUN [ ! -d "/app" ] && mkdir -p /app
RUN [ ! -f "/app/meshtastic_ai.py" ] && cp meshtastic_ai.py /app/
RUN [ ! -f "/app/requirements.txt" ] && cp requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Expose port 5000
EXPOSE 5000

# Move files to /app on container startup
CMD ["sh", "-c", "mv /tmp/* /app/ && python /app/meshtastic_ai.py"]
