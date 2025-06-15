FROM debian:bookworm-slim

ENV PYTHON_VERSION=3.13.2

# Install dependencies
RUN apt-get update && apt-get install -y \
    wget build-essential libssl-dev zlib1g-dev \
    libncurses5-dev libreadline-dev libsqlite3-dev \
    libgdbm-dev libbz2-dev libexpat1-dev liblzma-dev \
    tk-dev libffi-dev curl git ca-certificates \
    && apt-get clean

# Install Python 3.13.2
RUN wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz && \
    tar -xf Python-${PYTHON_VERSION}.tgz && \
    cd Python-${PYTHON_VERSION} && \
    ./configure --enable-optimizations && \
    make -j$(nproc) && \
    make altinstall && \
    cd .. && rm -rf Python-${PYTHON_VERSION}*

RUN ln -s /usr/local/bin/python3.13 /usr/local/bin/python && \
    ln -s /usr/local/bin/pip3.13 /usr/local/bin/pip

WORKDIR /app

COPY meshtastic_ai.py .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "meshtastic_ai.py"]
