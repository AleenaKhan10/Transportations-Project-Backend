# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-slim

# Cloud Run expects applications to listen on PORT environment variable
EXPOSE 8080
ENV PORT 8080

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Use PORT environment variable for Cloud Run compatibility
CMD exec gunicorn --bind 0.0.0.0:$PORT -k uvicorn.workers.UvicornWorker ingest_app:app