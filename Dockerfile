# Use an official Python image with Nginx support
FROM python:latest

# Set the maintainer label
LABEL Maintainer="mr-tbot"

# Update package lists and install apt packages
RUN apt-get update && apt-get install -y python3-pip

# Upgrade pip to the latest version
RUN pip3 install --upgrade pip

# Change the working directory to /app
WORKDIR /app

# Mount a volume at /app to persist data between restarts
VOLUME ["/app"]

# Install dependencies by running pip
RUN pip install -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Set the default command to start the Python interpreter
CMD ["python3", "meshtastic_ai.py"]
