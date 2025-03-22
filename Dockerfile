FROM python:latest
LABEL Maintainer="mr-tbot"

# Set user to root
USER root

# Set working directory (temporary storage)
WORKDIR /tmp

# Copy all files to the temporary directory
COPY . /tmp/

# Install dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Ensure /app directory exists
RUN mkdir -p /app

# Expose port 5000
EXPOSE 5000

# Move specific files to /app, then copy all other files to /app
CMD ["sh", "-c", \
  "mv /tmp/config.json /app/ 2>/dev/null; \
   mv /tmp/commands_config.json /app/ 2>/dev/null; \
   mv /tmp/motd.json /app/ 2>/dev/null; \
   cp -r /tmp/* /app/ && \
   python /app/meshtastic_ai.py"]
