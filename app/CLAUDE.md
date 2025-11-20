# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

**Main API Server:**
```bash
source .venv/Scripts/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Ingest Service (separate app):**
```bash
source .venv/Scripts/activate
python -m uvicorn ingest_app:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Overview

### Dual FastAPI Application Structure

This project contains **two separate FastAPI applications**:

1. **Main API** ([main.py](main.py)) - Primary intelligence hub with 30+ routers for authentication, trips, alerts, drivers, VAPI calls, reports, admin functions, and more
2. **Ingest Service** ([ingest_app.py](ingest_app.py)) - Dedicated service for data ingestion operations (Samsara, Ditat)

### Database Architecture

- **Database**: PostgreSQL with SQLModel ORM
- **Schema**: Uses `dev` schema (set via SQLAlchemy events in [db/database.py](db/database.py))
- **Connection Pooling**: Configured with pool_size=10, max_overflow=20, pool_pre_ping enabled
- **Retry Logic**: All database operations should use the `@db_retry` decorator from [db/retry.py](db/retry.py) for connection resilience
- **Tables**: Auto-created on startup via `SQLModel.metadata.create_all(engine)`

### Project Structure

```
app/
├── config.py                 # Pydantic settings with .env configuration
├── main.py                   # Main FastAPI application
├── ingest_app.py            # Separate ingest FastAPI application
├── db/
│   ├── database.py          # SQLAlchemy engine with dev schema
│   └── retry.py             # Database retry decorator
├── models/                   # SQLModel database models (18 files)
├── services/                 # FastAPI routers (30 files)
├── logic/                    # Business logic layer
│   ├── auth/                # Authentication/authorization services
│   ├── alerts/              # Alert filtering and Slack integration
│   └── ingest/              # Samsara and Ditat data ingestion
├── helpers/                  # Utility functions
│   ├── agy_utils.py
│   ├── pandas_utils.py
│   ├── time_utils.py
│   └── cloud_logger.py
└── utils/                    # External service clients
    ├── vapi_client.py       # VAPI AI call integration
    ├── elevenlabs_client.py # ElevenLabs conversational AI integration
    ├── weather_api.py
    └── call_insights.py

bigquery/                     # BigQuery queries and schemas
cloud_functions/              # Google Cloud Functions
```

### Service Layer Pattern

**Services** ([services/](services/)) contain FastAPI routers with endpoint definitions. Most business logic is delegated to:
- **Logic layer** ([logic/](logic/)) - Core business operations
- **Models** ([models/](models/)) - SQLModel classes with class methods for database operations
- **Helpers/Utils** - Shared utilities

### Key Integrations

- **Authentication**: JWT-based with refresh tokens, sessions, and audit logging
- **VAPI**: AI-powered driver call system with campaign management
- **ElevenLabs**: Conversational AI for driver violation calls (independent alternative to VAPI)
- **Samsara**: Fleet management data ingestion
- **Ditat**: Alternative data source ingestion
- **Slack**: Alert delivery via bot integration
- **PCMiler**: Route and mileage calculation
- **Weather API**: Location-based weather data
- **Sentry/GlitchTip**: Error tracking with filtered event capture

### Authentication & Security

- JWT tokens managed through [logic/auth/security.py](logic/auth/security.py)
- User service and audit logging in [logic/auth/service.py](logic/auth/service.py)
- Admin RBAC system with roles, permissions, sessions, and audit trails
- OAuth2 password flow with username/email login support
- Token expiration: 24 hours (configurable via ACCESS_TOKEN_EXPIRE_MINUTES)

### Configuration

All configuration via [config.py](config.py) using Pydantic Settings:
- Database credentials (DB_USER, DB_PASS, DB_HOST, DB_NAME, DB_PORT)
- Cloud Run settings (INSTANCE_UNIX_SOCKET, CLOUD_RUN_URL)
- API tokens (DITAT_TOKEN, SAMSARA_TOKEN, VAPI_API_KEY, ELEVENLABS_API_KEY, etc.)
- External service keys (PCMILER_API_KEY, WEATHER_API_KEY, SLACK_BOT_TOKEN)
- JWT settings (SECRET_KEY, ALGORITHM)
- Email/SMTP configuration
- Sentry/GlitchTip DSN

**Note**: Never commit `.env` file. Use environment variables or Cloud Run secrets.

## Important Patterns

### Database Operations
Always wrap database queries with the retry decorator:
```python
from db.retry import db_retry

@db_retry(max_retries=3)
def get_data():
    with Session(engine) as session:
        # database operations
```

### Timezone Handling
Use timezone-aware datetimes. Helpers provided in [logic/auth/service.py](logic/auth/service.py):
```python
def utc_now():
    return datetime.now(timezone.utc)

def make_timezone_aware(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
```

### Router Registration
New routers must be:
1. Created in [services/](services/)
2. Imported in [main.py](main.py)
3. Registered with `app.include_router()`

### Model Pattern
Models inherit from SQLModel with table=True and include class methods for common operations:
```python
from sqlmodel import SQLModel, Field

class MyModel(SQLModel, table=True):
    id: int = Field(primary_key=True)

    @classmethod
    def get_by_id(cls, id: int):
        # implementation
```

### Error Handling
- Global exception handler captures all unhandled exceptions
- Sentry integration filters out HTTPException and ValidationError
- Only errors with severity 'error' or 'fatal' are captured
- Critical API failures automatically logged to Sentry

### ElevenLabs Call Workflow (Alternative to VAPI)
1. Driver data retrieved from database
2. Phone number normalized to E.164 format
3. Dynamic prompt generated using existing prompt generation logic
4. Call initiated via [utils/elevenlabs_client.py](utils/elevenlabs_client.py)
5. Response includes conversation_id and callSid for tracking
6. Endpoint: POST /driver_data/call-elevenlabs
7. Independent implementation - can coexist with VAPI or replace it

**Key Features:**
- Processes single driver per request (matches VAPI pattern)
- Comprehensive retry logic with exponential backoff (3 attempts)
- Detailed logging with structured sections
- Hardcoded agent configuration (future: configurable from frontend)
- US phone number support with E.164 normalization

**Limitations:**
- No webhook handling (call status updates not processed)
- Single driver processing only (first in array)
- Hardcoded agent ID and phone number ID
- See agent-os/specs/elevenlabs-integration/planning/limitations.md

### VAPI Call Workflow
1. Driver data retrieved from database
2. Optional VAPI data merged into driver dict
3. Call initiated via [utils/vapi_client.py](utils/vapi_client.py)
4. Call insights and results processed through webhooks
5. Driver reports and morning reports updated

## Development Notes

- Virtual environment activation required: `source .venv/Scripts/activate`
- Database schema is always `dev` (not public)
- Connection pooling handles reconnections automatically
- Use `@db_retry` for resilient database operations
- Sentry before_send filter prevents noise from expected HTTP errors
- Two separate FastAPI apps run independently (main vs ingest)
