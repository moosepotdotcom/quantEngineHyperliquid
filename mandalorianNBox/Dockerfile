# Base Image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including TA-Lib build tools)
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    wget \
    tar \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build TA-Lib from source (required for the python wrapper)
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements and install
COPY requirements.txt .

# Install requirements
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port for Cloud Run
EXPOSE 8080

# Set PORT environment variable for Cloud Run
ENV PORT=8080

# Run cloud runner (bot + dashboard)
CMD ["python3", "cloud_runner.py"]
