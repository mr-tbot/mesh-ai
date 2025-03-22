FROM python:latest
LABEL Maintainer="mr-tbot"

RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install --upgrade pip

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

EXPOSE 5000
CMD [ "python", "meshtastic_ai.py"]
