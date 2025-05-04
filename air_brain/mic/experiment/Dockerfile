FROM debian:bullseye-slim

# Set architecture
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    libatlas-base-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir numpy
RUN pip3 install --no-cache-dir pyaudio
RUN pip3 install --no-cache-dir python-dotenv
RUN pip3 install --no-cache-dir openai

# Install PyTorch using the official ARM wheel
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Set working directory
WORKDIR /app

# Copy your application files
COPY . /app/

# Command to run your application
CMD ["python3", "vad.py"] 