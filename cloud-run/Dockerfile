FROM python:3.11-slim

WORKDIR /app

# Copy requirements và install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy crawler code
COPY extract.py .

# Cloud Run expects a process listening on PORT (default 8080)
# But our crawler runs as a job, so we create a simple HTTP server wrapper
COPY run_server.py .

# Run the server (Cloud Run will send HTTP requests to trigger crawler)
CMD ["python", "run_server.py"]

