# Base Image
FROM python:3.9-slim

# Set Working Directory
WORKDIR /app

# Install System Dependencies (Minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Requirements
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Engine Code & Models
COPY phase3_engine.py .
COPY quant_engine.py .
COPY utils/ utils/
COPY models/ models/

# Copy State (Optional: In production, use a persistent volume or Cloud Storage)
# COPY phase3_state.json . 

# Environment Variables
ENV PYTHONUNBUFFERED=1

# Run the Engine
CMD ["python", "phase3_engine.py"]
