# Cloud Run Deployment Guide

This document provides a comprehensive guide for deploying the AGY Backend (FastAPI) application to Google Cloud Run, including common errors and their solutions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cost-Optimized Deployment Settings](#cost-optimized-deployment-settings)
3. [Deployment Commands](#deployment-commands)
4. [Environment Variables & Secrets](#environment-variables--secrets)
5. [Common Errors & Solutions](#common-errors--solutions)
6. [Troubleshooting Checklist](#troubleshooting-checklist)

---

## Prerequisites

### Required Tools
- Google Cloud SDK (`gcloud`) installed and configured
- Docker (for local testing, optional)
- Git

### Authentication
```bash
# Login to Google Cloud
gcloud auth login

# Set the project
gcloud config set project agy-intelligence-hub
```

### Project Configuration
- **Project ID:** `agy-intelligence-hub`
- **Region:** `us-central1`
- **Service Name:** `agy-backend`
- **Container Registry:** `gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend`

---

## Cost-Optimized Deployment Settings

For cost optimization while maintaining good performance, use these settings:

| Setting | Value | Description |
|---------|-------|-------------|
| `--min-instances` | 0 | Scale to zero when idle (biggest cost saver) |
| `--max-instances` | 5 | Prevent runaway scaling costs |
| `--cpu-throttling` | Enabled | Only bill for CPU during request processing |
| `--memory` | 512Mi | Minimal footprint for FastAPI |
| `--cpu` | 1 | Single vCPU is sufficient |
| `--concurrency` | 80 | Handle 80 requests per instance (reduces instance count) |
| `--timeout` | 300 | 5 minute request timeout |
| `--port` | 8080 | Cloud Run default port |

### Cost Impact
- **When idle (no traffic):** ~$0 (scales to zero)
- **Per request:** Only billed for actual CPU time used
- **High concurrency (80):** Maximizes requests per instance, reducing total instance count

---

## Deployment Commands

### Step 1: Pull Latest Code
```bash
cd /path/to/agy-backend
git pull origin main
```

### Step 2: Build Docker Image
```bash
cd app
gcloud builds submit --tag gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend:latest .
```

**Important:** The build uses `Dockerfile` in the `app/` directory. If using a custom Dockerfile name like `main.Dockerfile`, copy it to `Dockerfile` first:
```bash
cp main.Dockerfile Dockerfile
```

### Step 3: Deploy to Cloud Run
```bash
gcloud run deploy agy-backend \
  --image=gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend:latest \
  --region=us-central1 \
  --project=agy-intelligence-hub \
  --min-instances=0 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --concurrency=80 \
  --timeout=300 \
  --cpu-throttling \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="DUMMY_TOKEN=<token>,DB_NAME=postgres,..." \
  --set-secrets="DB_USER=DB_USER_SUPABASE:latest,..." \
  --add-cloudsql-instances=agy-intelligence-hub:us-central1:agy-intelligence-hub-instance
```

---

## Environment Variables & Secrets

### Required Environment Variables (Plain Text)
```
DUMMY_TOKEN=<your_token>
DB_NAME=postgres
INSTANCE_UNIX_SOCKET=/cloudsql/agy-intelligence-hub:us-central1:agy-intelligence-hub-instance
SECRET_KEY=<your_secret_key>
WEBHOOK_TOKEN=<your_webhook_token>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=no-replay@agylogistics.com
```

### Required Secrets (From Secret Manager)
```
DITAT_TOKEN=DITAT_TOKEN:latest
SAMSARA_TOKEN=SAMSARA_TOKEN:latest
SLACK_BOT_TOKEN=SLACK_BOT_TOKEN:latest
DB_USER=DB_USER_SUPABASE:latest
DB_PASS=DB_PASS_SUPABASE:latest
DB_HOST=DB_HOST_SUPABASE:latest
DB_PORT=DB_PORT_SUPABASE2:1
VAPI_API_KEY=VAPI_API_KEY:latest
VAPI_ASSISTANT_ID=VAPI_ASSISTANT_ID:latest
VAPI_PHONENUMBER_ID=VAPI_PHONENUMBER_ID:latest
PCMILER_API_KEY=PCMILER_API_KEY:latest
SLACK_SIGNING_SECRET=SLACK_SIGNING_SECRET:latest
ENABLE_SCHEDULER=ENABLE_SCHEDULER:latest
HERE_API_KEY_PRIMARY=HERE_API_KEY_PRIMARY:latest
HERE_API_KEY_SECONDARY=HERE_API_KEY_SECONDARY:latest
HERE_API_KEY_TERTIARY=HERE_API_KEY_TERTIARY:latest
WEATHER_API_KEY=WEATHER_API_KEY:latest
SENDER_PASSWORD=SENDER_PASSWORD_NEW:latest
```

### Creating a New Secret
```bash
# Create a new secret
echo "your_secret_value" | gcloud secrets create SECRET_NAME --data-file=- --project=agy-intelligence-hub

# Or add a new version to existing secret
echo "your_secret_value" | gcloud secrets versions add SECRET_NAME --data-file=- --project=agy-intelligence-hub
```

---

## Common Errors & Solutions

### Error 1: Missing Python Module (ModuleNotFoundError)

**Error Message:**
```
ModuleNotFoundError: No module named 'pgvector'
```

**Cause:**
A Python package is imported in the code but not listed in `requirements.txt`.

**Solution:**
1. Identify the missing module from the error message
2. Add it to `app/requirements.txt`:
   ```
   pgvector==0.3.6
   ```
3. Rebuild the Docker image
4. Redeploy

**Prevention:**
- Always run `pip freeze` after adding new imports
- Test locally with `pip install -r requirements.txt` before deploying
- Review all new model files for import statements

---

### Error 2: ASGI/WSGI Server Mismatch

**Error Message:**
```
TypeError: FastAPI.__call__() missing 1 required positional argument: 'send'
```

**Cause:**
Cloud Build's Buildpacks used Gunicorn with sync workers instead of ASGI-compatible Uvicorn. FastAPI requires ASGI.

**Solution:**
Ensure the `Dockerfile` uses Uvicorn directly:
```dockerfile
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
```

**NOT this (Gunicorn sync):**
```dockerfile
CMD exec gunicorn --bind 0.0.0.0:$PORT main:app
```

**Prevention:**
- Always use explicit `Dockerfile` instead of relying on Buildpacks
- Use `--source .` only when you have a proper `Dockerfile` in place
- For FastAPI with WebSocket support, use Uvicorn directly

---

### Error 3: Missing Required Environment Variables

**Error Message:**
```
pydantic_core._pydantic_core.ValidationError: 11 validation errors for Settings
DITAT_TOKEN
  Field required [type=missing, input_value={'PORT': '8080'}, input_type=dict]
```

**Cause:**
Pydantic Settings requires certain environment variables that weren't provided during deployment.

**Solution:**
1. Check `app/config.py` for all required fields (those without default values)
2. Ensure ALL required variables are set via `--set-env-vars` or `--set-secrets`
3. Copy environment configuration from a working service:
   ```bash
   gcloud run services describe agy-backend-seperate-ingest-apis \
     --region=us-central1 \
     --project=agy-intelligence-hub \
     --format="yaml(spec.template.spec.containers[0].env)"
   ```

**Prevention:**
- Maintain a documented list of all required environment variables
- Use a deployment script that includes all variables
- Test with `.env` file locally before deploying

---

### Error 4: Container Failed to Start (Port Timeout)

**Error Message:**
```
ERROR: The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable within the allocated timeout.
```

**Cause:**
Multiple possible causes:
1. Missing environment variables causing crash
2. Database connection timeout
3. Import errors
4. Insufficient memory

**Solution:**
1. Check logs for the specific revision:
   ```bash
   gcloud run services logs read agy-backend \
     --region=us-central1 \
     --project=agy-intelligence-hub \
     --limit=50
   ```

2. Deploy a test service to isolate the issue:
   ```bash
   gcloud run deploy agy-backend-test \
     --image=gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend:latest \
     --region=us-central1 \
     --project=agy-intelligence-hub \
     --allow-unauthenticated \
     --set-env-vars="..." \
     --set-secrets="..."
   ```

3. Check logs for the test service

**Prevention:**
- Always check logs immediately after deployment failure
- Use `--cpu-boost` for faster cold starts
- Increase memory if startup is resource-intensive

---

### Error 5: Secret/Environment Variable Type Conflict

**Error Message:**
```
ERROR: Cannot update environment variable [SMTP_SERVER] to string literal because it has already been set with a different type.
```

**Cause:**
Trying to set an environment variable that was previously configured as a secret reference (or vice versa).

**Solution:**
1. First remove the existing configuration:
   ```bash
   gcloud run services update agy-backend \
     --region=us-central1 \
     --project=agy-intelligence-hub \
     --remove-secrets="SMTP_SERVER,SMTP_PORT,SENDER_EMAIL,SENDER_PASSWORD"
   ```

2. Then add as environment variable:
   ```bash
   gcloud run services update agy-backend \
     --region=us-central1 \
     --project=agy-intelligence-hub \
     --update-env-vars="SMTP_SERVER=smtp.gmail.com"
   ```

**Prevention:**
- Be consistent: use secrets for sensitive data, env vars for configuration
- Document which variables are secrets vs plain env vars
- When changing type, always remove first then add

---

### Error 6: gcloud Authentication Expired

**Error Message:**
```
ERROR: There was a problem refreshing your current auth tokens: Reauthentication failed.
```

**Solution:**
```bash
gcloud auth login
```

**Prevention:**
- Run `gcloud auth login` at the start of deployment sessions
- Consider using service account for automated deployments

---

### Error 7: Windows Command Line Space Issues

**Error Message:**
```
'C:\Program' is not recognized as an internal or external command
```

**Cause:**
Environment variable values containing spaces break Windows command parsing.

**Solution:**
1. Create a secret for values with spaces:
   ```bash
   echo "value with spaces" | gcloud secrets create SECRET_NAME --data-file=- --project=agy-intelligence-hub
   ```

2. Reference the secret instead of inline value:
   ```bash
   --set-secrets="VAR_NAME=SECRET_NAME:latest"
   ```

**Prevention:**
- Always use secrets for values containing spaces
- Test commands with `echo` first to verify parsing
- Consider using deployment scripts or Cloud Build YAML

---

## Troubleshooting Checklist

When deployment fails, follow this checklist:

### 1. Check Authentication
```bash
gcloud auth print-access-token
```

### 2. Verify Image Exists
```bash
gcloud container images describe gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend:latest
```

### 3. Check Service Status
```bash
gcloud run services describe agy-backend \
  --region=us-central1 \
  --project=agy-intelligence-hub \
  --format="value(status.latestReadyRevisionName)"
```

### 4. View Recent Logs
```bash
gcloud run services logs read agy-backend \
  --region=us-central1 \
  --project=agy-intelligence-hub \
  --limit=50
```

### 5. List All Revisions
```bash
gcloud run revisions list \
  --service=agy-backend \
  --region=us-central1 \
  --project=agy-intelligence-hub
```

### 6. Check Traffic Distribution
```bash
gcloud run services describe agy-backend \
  --region=us-central1 \
  --project=agy-intelligence-hub \
  --format="value(status.traffic)"
```

### 7. Verify All Secrets Exist
```bash
gcloud secrets list --project=agy-intelligence-hub
```

### 8. Test Container Locally (Optional)
```bash
docker build -t agy-backend-test -f Dockerfile .
docker run -p 8080:8080 --env-file .env agy-backend-test
```

---

## Quick Reference: Full Deployment Command

```bash
gcloud run deploy agy-backend \
  --image=gcr.io/agy-intelligence-hub/github.com/agylogistics/agy-backend:latest \
  --region=us-central1 \
  --project=agy-intelligence-hub \
  --min-instances=0 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --concurrency=80 \
  --timeout=300 \
  --cpu-throttling \
  --port=8080 \
  --allow-unauthenticated \
  --set-env-vars="DUMMY_TOKEN=cdfdd076cdcdabfd2d10b2c43b4ef2ce0f0a8b122bd5f27982509fd5610e86e6,DB_NAME=postgres,INSTANCE_UNIX_SOCKET=/cloudsql/agy-intelligence-hub:us-central1:agy-intelligence-hub-instance,SECRET_KEY=f85b07e546fb7800b282f3ec6358bcbdbaa7224656e5ea1b5d6efb082db67a12,WEBHOOK_TOKEN=02f44e5a01934646aa60276a5a93a705aa5de15a62a9ef63902367b1233ca136,SMTP_SERVER=smtp.gmail.com,SMTP_PORT=587,SENDER_EMAIL=no-replay@agylogistics.com" \
  --set-secrets="DITAT_TOKEN=DITAT_TOKEN:latest,SAMSARA_TOKEN=SAMSARA_TOKEN:latest,SLACK_BOT_TOKEN=SLACK_BOT_TOKEN:latest,DB_USER=DB_USER_SUPABASE:latest,DB_PASS=DB_PASS_SUPABASE:latest,VAPI_API_KEY=VAPI_API_KEY:latest,VAPI_ASSISTANT_ID=VAPI_ASSISTANT_ID:latest,VAPI_PHONENUMBER_ID=VAPI_PHONENUMBER_ID:latest,PCMILER_API_KEY=PCMILER_API_KEY:latest,SLACK_SIGNING_SECRET=SLACK_SIGNING_SECRET:latest,ENABLE_SCHEDULER=ENABLE_SCHEDULER:latest,HERE_API_KEY_PRIMARY=HERE_API_KEY_PRIMARY:latest,HERE_API_KEY_SECONDARY=HERE_API_KEY_SECONDARY:latest,HERE_API_KEY_TERTIARY=HERE_API_KEY_TERTIARY:latest,DB_HOST=DB_HOST_SUPABASE:latest,DB_PORT=DB_PORT_SUPABASE2:1,WEATHER_API_KEY=WEATHER_API_KEY:latest,SENDER_PASSWORD=SENDER_PASSWORD_NEW:latest" \
  --add-cloudsql-instances=agy-intelligence-hub:us-central1:agy-intelligence-hub-instance
```

---

## Service URLs

- **Production API:** https://agy-backend-181509438418.us-central1.run.app
- **API Documentation:** https://agy-backend-181509438418.us-central1.run.app/docs
- **OpenAPI Schema:** https://agy-backend-181509438418.us-central1.run.app/openapi.json

---

## Dockerfile Reference

The application uses `app/main.Dockerfile`:

```dockerfile
FROM python:3.11-slim

EXPOSE 8080
ENV PORT 8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Use Uvicorn for ASGI support (required for FastAPI + WebSockets)
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Key Points:**
- Uses Python 3.11-slim for smaller image size
- Runs as non-root user for security
- Uses Uvicorn directly for full ASGI/WebSocket support
- PORT is set via environment variable (Cloud Run standard)

---

*Last Updated: December 2024*
