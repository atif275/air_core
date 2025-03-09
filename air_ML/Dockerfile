FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    cmake \
    build-essential \
    libgtk2.0-dev \
    pkg-config \
    wget \
    libxcb1 \
    libxcb-xinerama0 \
    libxcb-randr0 \
    libxcb-xtest0 \
    libxcb-shape0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    '^libxcb.*-dev' \
    libx11-xcb-dev \
    libglu1-mesa-dev \
    libxrender-dev \
    libxi-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --upgrade pip

# Install main dependencies
RUN pip install tf-keras>=2.15.0 --timeout 10000 \
    && pip install opencv-python>=4.8.0 --timeout 10000 \
    && pip install numpy>=1.24.0 --timeout 10000 \
    && pip install deepface>=0.0.79 --timeout 10000 \
    && pip install dlib>=19.24.0 --timeout 10000 \
    && pip install openai==0.28.0 --timeout 10000 \
    && pip install python-dotenv>=1.0.0 --timeout 10000 \
    && pip install scipy>=1.10.0 --timeout 10000 \
    && pip install websockets==12.0 --timeout 10000 \
    && pip install Pillow==10.1.0 --timeout 10000 \
    && pip install aiohttp==3.9.1 --timeout 10000 \
    && pip install quart==0.18.4 --timeout 10000 \
    && pip install quart-cors==0.7.0 --timeout 10000

# Install PyTorch
RUN pip install torch==2.0.0 --no-deps --index-url https://download.pytorch.org/whl/cpu

# Download DeepFace model weights
RUN mkdir -p /root/.deepface/weights && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/facenet_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/age_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/gender_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/facial_expression_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/race_model_single_batch.h5

# OpenCV setup
RUN pip uninstall -y opencv-python opencv-python-headless && \
    pip install --no-cache-dir opencv-python-headless>=4.8.0

# Create and set up persistent volumes
VOLUME ["/app/frames", "/app/data"]
RUN mkdir -p frames data

# Copy the entire project including .env
COPY . .

# Set default environment variables (can be overridden at runtime)
ENV PORT=5001 \
    HOST=0.0.0.0 \
    DISPLAY_MODE=save \
    SAVE_DIR=frames \
    PYTHONUNBUFFERED=1

# Make the combined server script executable
RUN chmod +x combined_server.py

# Expose the port
EXPOSE 5001

# Start the combined server
CMD ["python", "combined_server.py"]