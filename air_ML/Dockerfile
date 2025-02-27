FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

RUN pip install tf-keras>=2.15.0 --timeout 10000
RUN pip install opencv-python>=4.8.0 --timeout 10000
RUN pip install numpy>=1.24.0 --timeout 10000
RUN pip install deepface>=0.0.79 --timeout 10000
RUN pip install dlib>=19.24.0 --timeout 10000
RUN pip install openai==0.28.0 --timeout 10000
RUN pip install python-dotenv>=1.0.0 --timeout 10000
RUN pip install scipy>=1.10.0 --timeout 10000
RUN pip install flask==3.0.0 --timeout 10000
RUN pip install flask-cors==4.0.0 --timeout 10000
RUN pip install websockets==12.0 --timeout 10000
RUN pip install Pillow==10.1.0 --timeout 10000
RUN pip install aiohttp==3.9.1 --timeout 10000

RUN pip install torch==2.0.0 --no-deps --index-url https://download.pytorch.org/whl/cpu

RUN apt-get update && apt-get install -y \
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

RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download all required model weights
RUN mkdir -p /root/.deepface/weights && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/facenet_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/age_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/gender_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/facial_expression_model_weights.h5 && \
    wget -P /root/.deepface/weights https://github.com/serengil/deepface_models/releases/download/v1.0/race_model_single_batch.h5

RUN pip uninstall -y opencv-python opencv-python-headless && \
    pip install --no-cache-dir opencv-python-headless>=4.8.0

RUN apt-get update && apt-get install -y \
    libgtk2.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

RUN mkdir -p frames

# Make scripts executable
RUN chmod +x scripts/start_server.sh
RUN chmod +x scripts/start_main.sh
RUN chmod +x scripts/start_app.sh
