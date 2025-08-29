FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create outbox directory
RUN mkdir -p /app/outbox

# Expose port 7860 (Hugging Face Spaces expects this)
EXPOSE 7860

# Health check (optional but recommended)
HEALTHCHECK CMD curl --fail http://localhost:7860/health || exit 1

# Run the FastAPI app with uvicorn
# Hugging Face Spaces expects the app to run on port 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]