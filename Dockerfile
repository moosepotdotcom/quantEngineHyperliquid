FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY cloud_runner.py .
COPY quant_engine.py .
COPY hyperliquid_live_trader.py .
COPY live_trading_engine.py .
COPY models/ ./models/
COPY utils/ ./utils/
COPY monitoring/ ./monitoring/
COPY ml/ ./ml/

# Create logs directory
RUN mkdir -p logs

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Expose port for health check
EXPOSE 8080

# Run the application with Flask wrapper
CMD ["python", "cloud_runner.py"]
