# Tech Stack

This document defines the complete technical stack for AGY Logistics, covering backend, frontend, cloud infrastructure, AI services, and all integrated systems.

## Backend Framework & Runtime

- **Application Framework:** FastAPI (dual application architecture)
  - Main API ([main.py](../main.py)) - Primary intelligence hub with 30+ routers
  - Ingest Service ([ingest_app.py](../ingest_app.py)) - Dedicated data ingestion service
- **Language/Runtime:** Python 3.x
- **Package Manager:** pip with virtual environment (.venv)
- **ASGI Server:** Uvicorn with --reload for development

## Frontend

- **JavaScript Framework:** ReactJS
- **CSS Framework:** TBD (not documented in current codebase)
- **UI Components:** Custom components (not documented in current codebase)
- **Build Tool:** Not documented (likely Vite or Create React App)

Note: Frontend application is separate from backend. Specific versions and additional dependencies not yet documented.

## Database & Storage

- **Database:** PostgreSQL
- **ORM/Query Builder:** SQLModel (SQLAlchemy 2.0 + Pydantic)
- **Schema:** `dev` schema (configured via SQLAlchemy events)
- **Connection Pooling:**
  - pool_size=10
  - max_overflow=20
  - pool_pre_ping=True (automatic reconnection)
- **Retry Logic:** Custom `@db_retry` decorator with exponential backoff (3 retries default)
- **Data Warehouse:** Google BigQuery (queries and schemas in /bigquery directory)
- **Caching:** Not currently implemented (planned enhancement)

## AI & Voice Services

### Current (Being Deprecated)
- **Voice AI Platform:** VAPI
  - Call handling and campaign management
  - Being replaced due to latency and feature limitations

### New (Migration Target)
- **Voice AI Platform:** ElevenLabs
  - Lower latency conversational AI
  - Bidirectional streaming
  - Superior voice quality
  - Real-time transcription
  - Action execution capabilities

## Data Ingestion & Fleet Management

- **Samsara Integration:** Fleet management data ingestion
  - Vehicle locations, sensor data, driver logs
  - Real-time monitoring and alerts
- **Ditat Integration:** Alternative data source ingestion
- **PCMiler API:** Route calculation and mileage optimization
- **Weather API:** Location-based weather data for route planning and alerts

## Communication & Notifications

- **Slack Integration:**
  - Bot-based alert delivery
  - Team notifications
  - Configured via SLACK_BOT_TOKEN
- **Email/SMTP:** Configured via environment variables for transactional emails
- **SMS/Voice:** Currently via VAPI, migrating to ElevenLabs

## Authentication & Security

- **Authentication Method:** JWT-based with refresh tokens
- **Token Management:** Custom implementation in [logic/auth/security.py](../logic/auth/security.py)
- **Session Management:** Database-backed sessions with audit logging
- **Password Flow:** OAuth2 password flow supporting username/email login
- **Token Expiration:** 24 hours (configurable via ACCESS_TOKEN_EXPIRE_MINUTES)
- **RBAC System:** Role-based access control with:
  - Roles and permissions
  - Session tracking
  - Comprehensive audit trails
- **Security Headers:** Configured via FastAPI middleware

## Error Tracking & Monitoring

- **Error Tracking:** Sentry / GlitchTip
  - Custom before_send filter to exclude HTTPException and ValidationError
  - Only captures severity 'error' or 'fatal'
  - Automatic critical API failure logging
- **Logging:** Custom cloud_logger.py for structured logging
- **Health Checks:** Built-in endpoints for service monitoring

## Cloud Infrastructure & Deployment

- **Hosting Platform:** Google Cloud Run
  - Containerized deployment
  - Automatic scaling
  - Unix socket support for Cloud SQL
- **CI/CD:** Not documented (likely GitHub Actions or Cloud Build)
- **Environment Configuration:**
  - Local: .env file (never committed)
  - Production: Cloud Run secrets and environment variables
- **Serverless Functions:** Google Cloud Functions (in /cloud_functions directory)

## External Integrations

### Logistics & Operations
- **PCMiler:** Route optimization, mileage calculation, toll estimation
- **Samsara:** Fleet tracking, ELD compliance, vehicle diagnostics
- **Ditat:** Secondary data ingestion source

### Communication
- **VAPI:** Current voice AI (deprecated)
- **ElevenLabs:** Next-generation voice AI (migration target)
- **Slack:** Team notifications and alerts
- **SMTP:** Email delivery

### Data & Analytics
- **Weather API:** Real-time weather data for route planning
- **BigQuery:** Data warehousing and analytics

## Development Tools & Quality

- **Test Framework:** Not currently documented (planned)
- **Linting/Formatting:** Not currently documented
- **Code Style:**
  - Consistent naming conventions
  - DRY principle adherence
  - Small, focused functions
  - Meaningful variable names
- **Version Control:** Git with feature branch workflow
- **Code Review:** Required before merging (process defined in conventions)

## Mobile (Planned - Not Yet Implemented)

- **Platform:** iOS and Android native apps (planned Phase 4)
- **Framework:** Not yet decided (likely React Native or Flutter)
- **Features:**
  - AI chat interface
  - Voice calling integration
  - Document scanning/OCR
  - Electronic signatures
  - Offline mode with sync
  - Push notifications

## Key Architectural Patterns

### Service Layer Pattern
- **Services** ([services/](../services/)) - FastAPI routers with endpoint definitions
- **Logic Layer** ([logic/](../logic/)) - Core business operations
- **Models** ([models/](../models/)) - SQLModel classes with class methods for DB operations
- **Helpers/Utils** ([helpers/](../helpers/), [utils/](../utils/)) - Shared utilities

### Database Resilience
- All database operations wrapped with `@db_retry` decorator
- Automatic connection pooling and reconnection
- Pool pre-ping for stale connection detection
- Schema isolation using `dev` schema

### Timezone Handling
- All datetimes are timezone-aware (UTC)
- Helper functions in [logic/auth/service.py](../logic/auth/service.py):
  - `utc_now()` - Returns current UTC time
  - `make_timezone_aware()` - Ensures datetime is timezone-aware

### Configuration Management
- Pydantic Settings ([config.py](../config.py)) for type-safe configuration
- Environment variables for all secrets and API keys
- Separate config for local vs. cloud deployment
- Never commit .env files

## Environment Variables (Required)

### Database
- DB_USER, DB_PASS, DB_HOST, DB_NAME, DB_PORT
- INSTANCE_UNIX_SOCKET (Cloud Run only)

### Cloud Services
- CLOUD_RUN_URL
- SENTRY_DSN / GLITCHTIP_DSN

### API Tokens
- VAPI_API_KEY (current)
- ELEVENLABS_API_KEY (planned)
- SAMSARA_TOKEN
- DITAT_TOKEN
- PCMILER_API_KEY
- WEATHER_API_KEY
- SLACK_BOT_TOKEN

### Authentication
- SECRET_KEY (JWT signing)
- ALGORITHM (default: HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES

### Email/SMTP
- SMTP configuration variables (not fully documented)

## Performance & Optimization Priorities

1. **Latency Reduction:** Target sub-500ms AI response times with ElevenLabs
2. **Caching Layer:** Implement Redis/Memcached for frequently accessed data
3. **Database Query Optimization:** Add indexes, optimize N+1 queries
4. **Code Optimization:** Refactor performance bottlenecks identified in profiling
5. **Connection Pooling:** Tune pool sizes based on production load patterns

## Future Stack Additions (Roadmap)

- **Caching:** Redis or Memcached for query and API response caching
- **Message Queue:** Consider Pub/Sub or RabbitMQ for async job processing
- **ML/AI:** TensorFlow or PyTorch for predictive analytics and sentiment analysis
- **Testing:** pytest with comprehensive test coverage
- **Linting:** Ruff or Black + isort for Python formatting
- **Mobile Backend:** Specialized endpoints and WebSocket support for mobile apps
- **Real-time:** WebSocket support for live call transcriptions and notifications
