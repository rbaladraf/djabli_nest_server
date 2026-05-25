FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/entrypoint.sh

ENV PYTHONPATH=/app
ENV UPLOAD_DIR=/app/uploads

EXPOSE 8000

CMD ["/app/scripts/entrypoint.sh"]
