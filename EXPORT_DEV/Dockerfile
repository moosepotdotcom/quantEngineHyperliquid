FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for lightgbm/xgboost)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Environment Variables
ENV PYTHONUNBUFFERED=TRUE
ENV PORT=8080

# Start Command
# CRITICAL: We use python directly (single worker) because app.py starts a background TradingThread.
# Multiple gunicorn workers would spawn multiple trading bots!
CMD ["python", "dashboard/app.py"]
