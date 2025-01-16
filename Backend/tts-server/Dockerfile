FROM python:3.11-slim

# Install build dependencies and audio libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port (matching docker-compose)
EXPOSE 7431

# Command to run the server
CMD ["python3", "-m", "src"] 