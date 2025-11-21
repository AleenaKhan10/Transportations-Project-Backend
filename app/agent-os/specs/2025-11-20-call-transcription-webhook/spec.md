# Specification: Call Transcription Webhook

## Goal
Create a public webhook endpoint that receives and stores real-time call transcription data from ElevenLabs, including dialogue attribution (agent/driver), sequencing, and call initialization logic for driver violation calls.

## User Stories
- As the ElevenLabs service, I want to send completed dialogue turns to the webhook so that each conversation segment is stored in the database
- As a system, I want to automatically create Call records on first dialogue and track transcription sequences so that conversation history is complete and ordered

## Specific Requirements

**Webhook Endpoint**
- Create POST endpoint `/webhooks/elevenlabs/transcription`
- Public endpoint with no authentication (optimized for performance)
- Accept JSON payload with: conversation_id, speaker, message, timestamp
- Return 201 Created on success with transcription_id and sequence_number
- Return appropriate error codes (400, 500) on failure to allow ElevenLabs retry
- ElevenLabs guarantees sequential webhook calls per conversation (no concurrency control needed)

**Call Model (New Database Table)**
- Table name: `calls` (or follow existing naming pattern)
- Primary key: id (auto-increment integer)
- conversation_id: String (unique, indexed) - ElevenLabs conversation identifier
- driver_id: Integer (nullable, foreign key to drivers table) - looked up from existing call records
- call_start_time: DateTime (timezone-aware UTC) - set from first dialogue timestamp
- call_end_time: DateTime (nullable) - updated by separate status webhook (out of scope)
- status: Enum ('in_progress', 'completed', 'failed') - initially 'in_progress'
- created_at: DateTime (auto-generated UTC timestamp)
- updated_at: DateTime (auto-generated UTC timestamp)

**CallTranscription Model (New Database Table)**
- Table name: `call_transcriptions` (or follow existing naming pattern)
- Primary key: id (auto-increment integer)
- conversation_id: String (indexed, foreign key to Call.conversation_id)
- speaker_type: Enum ('agent', 'driver') - mapped from ElevenLabs 'agent'/'user'
- message_text: Text - the actual dialogue content
- timestamp: DateTime (timezone-aware UTC) - when this dialogue occurred
- sequence_number: Integer (indexed) - auto-generated as count + 1
- created_at: DateTime (auto-generated UTC timestamp)

**Driver Lookup Logic**
- Query existing ElevenLabs call records (created by `/driver_data/call-elevenlabs` endpoint)
- Match conversation_id to find associated driver_id from previous call initiation
- Reference existing `make_drivers_violation_batch_call_elevenlabs` function in models/driver_data.py
- Handle gracefully if driver_id not found (allow null driver_id, log warning)
- Store driver_id in Call record for future reference

**Sequence Number Generation**
- Count existing CallTranscription records for given conversation_id
- Use count + 1 as sequence_number for new transcription
- Query: `session.query(CallTranscription).filter_by(conversation_id=conversation_id).count()`
- Ensures sequential ordering even without ElevenLabs providing sequence numbers
- No locks needed due to ElevenLabs sequential guarantee

**Call Initialization on First Dialogue**
- Check if Call record exists for conversation_id before creating transcription
- If NOT exists: Create Call record with call_start_time from first dialogue timestamp, status='in_progress', driver_id from lookup
- If exists: Skip Call creation, proceed to transcription creation
- Both Call creation and transcription creation happen in same database transaction
- Use @db_retry decorator for resilient database operations

**Speaker Mapping**
- ElevenLabs sends "agent" → store as "agent" in speaker_type
- ElevenLabs sends "user" → store as "driver" in speaker_type
- Map during request processing before database insertion
- No other speaker types expected or supported

**Error Handling Strategy**
- Validate all required fields (conversation_id, speaker, message, timestamp)
- Return 400 Bad Request for invalid speaker values or missing fields
- Return 500 Internal Server Error for database connection failures
- Return 500 for unexpected errors
- Log all errors with structured logging for debugging
- Allow ElevenLabs to retry failed saves (never return 200 OK on failure)

## Existing Code to Leverage

**Database Retry Decorator (db/retry.py)**
- Use @db_retry decorator for all database operations
- Provides automatic retry with exponential backoff (3 attempts by default)
- Handles OperationalError and DisconnectionError gracefully
- Pattern: `@db_retry(max_retries=3)` on database query functions

**SQLModel Pattern (models/user.py, models/driver_data.py)**
- Inherit from SQLModel with table=True for database models
- Use Field() for column definitions with constraints
- Include __tablename__ and __table_args__ = {"extend_existing": True}
- Use Enum classes for status fields (follow UserStatus pattern)
- Add timezone-aware datetime fields using datetime.utcnow
- Include classmethod get_session() returning Session(engine)

**FastAPI Router Pattern (services/driver_data.py, services/webhook.py)**
- Create router with APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])
- Define async endpoint handlers with proper type hints
- Use Pydantic models for request/response validation
- Return JSONResponse with appropriate status codes
- Import and include router in main.py

**ElevenLabs Integration (utils/elevenlabs_client.py, models/driver_data.py)**
- Reference conversation_id structure from elevenlabs_client.py response
- Reuse phone number normalization logic: `"".join(filter(str.isdigit, phone)) → +1{digits}`
- Follow logging pattern with structured sections (="*100)
- Reference driver lookup from make_drivers_violation_batch_call_elevenlabs function

**Timezone Handling (logic/auth/service.py)**
- Use timezone-aware datetimes throughout
- Import and use utc_now() and make_timezone_aware() helper functions
- Store all timestamps in UTC in database
- Pattern: `datetime.now(timezone.utc)` for current time

## Out of Scope
- Authentication or authorization for webhook endpoint (public for performance)
- Real-time UI updates or WebSocket implementation for dashboard display
- Dashboard display components or frontend integration
- Transcription post-processing (sentiment analysis, keyword extraction, compliance checking)
- Raw payload storage (no JSONB audit column for webhook data)
- Metadata fields (confidence scores, word-level timestamps, audio quality)
- Call status update webhook (separate future implementation handles 'completed'/'failed' status)
- Call end time updates (handled by separate status webhook)
- Status transitions from 'in_progress' to 'completed' or 'failed'
- Bulk transcription import or historical data migration tools
- Concurrency control mechanisms (ElevenLabs guarantees sequential calls per conversation)
- WebSocket or Server-Sent Events for live transcription streaming
- Admin UI for viewing, searching, or filtering call transcriptions
- Analytics, reporting, or visualization of transcription data
