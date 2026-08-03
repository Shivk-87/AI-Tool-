FROM python:3.10-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir fastapi uvicorn numpy pydantic

# Copy model-serving code
COPY src/model-serving /app/src/model-serving

# Expose the server port
EXPOSE 8001

# Run the FastAPI mock server
CMD ["uvicorn", "src.model-serving.mock_server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
