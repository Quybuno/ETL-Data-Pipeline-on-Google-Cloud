FROM python:3.11-slim

# Giảm log buffer và bỏ tạo .pyc để container gọn nhẹ
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements và install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy crawler code
COPY extract.py .
COPY run_server.py .

# Thiết lập và expose cổng cho Cloud Run
ENV PORT=8080
EXPOSE 8080

# Run the server (Cloud Run sẽ gọi HTTP để trigger crawler)
CMD ["python", "run_server.py"]

