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
├── models/                   # SQLModel database models (20 files - includes Call, CallTranscription)
├── services/                 # FastAPI routers (30 files)
├── logic/                    # Business logic layer
│   ├── auth/                # Authentication/authorization services
│   ├── alerts/              # Alert filtering and Slack integration
│   └── ingest/              # Samsara and Ditat data ingestion
├── helpers/                  # Utility functions
│   ├── agy_utils.py
│   ├── pandas_utils.py
│   ├── time_utils.py
│   ├── cloud_logger.py
│   └── transcription_helpers.py  # Call transcription business logic
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

### ElevenLabs Call Workflow (Refactored - November 2025)

**Proactive Call Tracking with call_sid:**

1. Generate call_sid (format: EL_{driverId}_{timestamp})
2. Create Call record BEFORE ElevenLabs API call (conversation_id=NULL, status=IN_PROGRESS)
3. Phone number normalized to E.164 format
4. Dynamic prompt generated using existing prompt generation logic
5. Call initiated via [utils/elevenlabs_client.py](utils/elevenlabs_client.py) with call_sid
6. Update Call record with conversation_id from ElevenLabs response (or status=FAILED if API fails)
7. Endpoint: POST /driver_data/call-elevenlabs
8. Independent implementation - can coexist with VAPI or replace it

**Key Features:**
- Proactive Call record creation enables complete audit trail (including failed calls)
- call_sid (our identifier) used for initial tracking
- conversation_id (ElevenLabs identifier) populated after successful API call
- Processes single driver per request (matches VAPI pattern)
- Comprehensive retry logic with exponential backoff (3 attempts)
- Detailed logging with structured sections
- Hardcoded agent configuration (future: configurable from frontend)
- US phone number support with E.164 normalization

**Limitations:**
- Single driver processing only (first in array)
- Hardcoded agent ID and phone number ID
- See agent-os/specs/2025-11-20-call-transcription-webhook/planning/limitations.md

**Webhook Integration (Refactored):**
- POST /webhooks/elevenlabs/transcription receives call_sid (not conversation_id)
- Two-step lookup pattern: call_sid -> Call -> conversation_id
- Stores dialogue turns with speaker attribution and sequencing
- Returns 400 Bad Request if Call not found or has NULL conversation_id
- Broadcasts transcription to subscribed WebSocket clients in real-time
- See [services/webhooks_elevenlabs.py](services/webhooks_elevenlabs.py) and [helpers/transcription_helpers.py](helpers/transcription_helpers.py)

**Post-Call Completion Webhook (November 2025):**
- POST /webhooks/elevenlabs/post-call receives post-call analysis from ElevenLabs
- Processes `post_call_transcription` webhook type for normal completion
- Processes `call_initiation_failure` webhook type for failed calls
- Updates Call status to COMPLETED (or FAILED) with call_end_time
- Stores post-call metadata in 6 new Call model fields:
  - `transcript_summary` (Text): AI-generated summary of conversation
  - `call_duration_seconds` (Integer): Duration in seconds from metadata
  - `cost` (Float): Call cost in USD from ElevenLabs billing
  - `call_successful` (Boolean): Success indicator from AI analysis
  - `analysis_data` (Text/JSON): Full analysis results from ElevenLabs
  - `metadata_json` (Text/JSON): Full metadata (phone numbers, timestamps, etc.)
- Broadcasts two sequential WebSocket messages to subscribed clients:
  - `call_status`: Immediate notification that call ended
  - `call_completed`: Full call data with all metadata
- Returns 400 Bad Request for invalid payload, 404 Not Found if Call not found, 500 for database errors
- Never returns 200 on failure to enable ElevenLabs retry mechanism (up to 10 retries)
- See [services/webhooks_elevenlabs.py](services/webhooks_elevenlabs.py)

**Real-Time WebSocket System (November 2025):**
- **Endpoint:** `/ws/calls/transcriptions?token=JWT_TOKEN`
- **Authentication:** JWT via query parameter (WebSocket upgrade doesn't support headers reliably)
- **Connection Manager:** [services/websocket_manager.py](services/websocket_manager.py) - Tracks active connections, subscriptions, and broadcasts
- **Message Models:** [models/websocket_messages.py](models/websocket_messages.py) - Pydantic models for all message types
- **Subscription Protocol:**
  - Client sends `{"subscribe": "identifier"}` with call_sid or conversation_id
  - Server auto-detects identifier type and looks up Call record
  - Server confirms with `subscription_confirmed` message containing call details
  - Client receives real-time updates for that call
  - Multiple clients can subscribe to same call
  - Single client can subscribe to multiple calls simultaneously
- **Message Types (Client -> Server):**
  - `subscribe` - Subscribe to call updates (accepts call_sid or conversation_id)
  - `unsubscribe` - Unsubscribe from call updates
- **Message Types (Server -> Client):**
  - `subscription_confirmed` - Confirmation with resolved call identifiers and status
  - `unsubscribe_confirmed` - Unsubscribe confirmation
  - `transcription` - Real-time dialogue turn with speaker attribution, sequence number, timestamp
  - `call_status` - Status update when call completes (first completion message)
  - `call_completed` - Full call data with analysis/metadata (second completion message)
  - `error` - Error notification with optional error code (CALL_NOT_FOUND, INVALID_IDENTIFIER, etc.)
- **Broadcasting:**
  - Transcription webhook broadcasts `transcription` message after saving dialogue turn
  - Post-call webhook broadcasts `call_status` then `call_completed` messages sequentially
  - Dead connections automatically cleaned up during broadcast
  - Broadcast failures don't affect webhook processing (graceful degradation)
  - Completed calls automatically removed from subscription registry
- **Connection Management:**
  - In-memory subscription tracking (for single-instance deployment)
  - Automatic cleanup on disconnect (removes all subscriptions)
  - Graceful handling of network failures and timeouts
  - Connection metadata tracking (user, connected_at, subscribed_calls)
- **API Documentation:** agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/deployment/api-documentation.md
  - Includes complete connection examples for JavaScript (browser) and Python (asyncio)
  - Documents all 8 message types with JSON examples
  - Provides subscription flow diagrams and error handling guidance

**Integration Points:**
- Transcription webhook -> WebSocket broadcast (after database save)
- Post-call webhook -> WebSocket broadcast (after Call update)
- Both webhooks succeed even if WebSocket broadcast fails
- WebSocket failures don't prevent data persistence
- All data stored in database regardless of real-time delivery success

**Database Schema:**
- Call model has both call_sid (unique, indexed, non-nullable) and conversation_id (nullable until API responds)
- Post-call metadata fields all nullable for backward compatibility
- CallTranscription model unchanged - uses conversation_id as foreign key
- Indexes: idx_calls_call_sid, idx_calls_call_sid_status for performance
- Backfilled existing records with generated call_sid values

**Refactor Details:**
- Call_sid refactor: agent-os/specs/2025-11-21-call-sid-webhook-refactor/spec.md
- WebSocket integration: agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/spec.md
- Implementation Notes: agent-os/specs/2025-11-21-call-sid-webhook-refactor/deployment/implementation-notes.md
- Deployment Checklists: Available in respective spec deployment directories

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
