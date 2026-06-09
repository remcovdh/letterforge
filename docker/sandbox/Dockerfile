FROM python:3.12-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m sandboxuser && \
    mkdir -p /workspace/inputs /workspace/outputs && \
    chown -R sandboxuser:sandboxuser /workspace

USER sandboxuser
