# Task Breakdown: Call Transcription Webhook

## Overview
Total Task Groups: 4
Total Sub-Tasks: 29
Total Tests: 20-28 (focused on critical paths)

## Task List

### Database Layer

#### Task Group 1: Data Models and Schema
**Dependencies:** None
**Assigned Role:** Database Engineer

- [ ] 1.0 Complete database layer
  - [ ] 1.1 Write 5-8 focused tests for Call and CallTranscription models
    - Test Call model creation with required fields (conversation_id, driver_id, call_start_time, status)
    - Test Call model unique constraint on conversation_id
    - Test CallTranscription model creation with all required fields
    - Test speaker_type enum validation ('agent', 'driver')
    - Test foreign key relationship between CallTranscription.conversation_id and Call.conversation_id
    - Test timestamp timezone awareness (UTC)
    - Test CallStatus enum values ('in_progress', 'completed', 'failed')
    - Optional: Test cascade behavior when Call is deleted
  - [ ] 1.2 Create CallStatus enum
    - Values: 'in_progress', 'completed', 'failed'
    - Use Python enum.Enum as base class
    - Pattern: Reference UserStatus in models/user.py
  - [ ] 1.3 Create SpeakerType enum
    - Values: 'agent', 'driver'
    - Use Python enum.Enum as base class
  - [ ] 1.4 Create Call model (models/call.py)
    - Inherit from SQLModel with table=True
    - Fields:
      - id: int (primary key, auto-increment)
      - conversation_id: str (unique, indexed, not null)
      - driver_id: Optional[int] (foreign key to drivers table, nullable)
      - call_start_time: datetime (timezone-aware UTC, not null)
      - call_end_time: Optional[datetime] (timezone-aware UTC, nullable)
      - status: CallStatus (enum, default='in_progress', not null)
      - created_at: datetime (auto-generated UTC, not null)
      - updated_at: datetime (auto-generated UTC, not null)
    - Include __tablename__ = "calls"
    - Include __table_args__ = {"extend_existing": True}
    - Add UniqueConstraint on conversation_id
    - Add index on conversation_id for fast lookups
    - Use Field() for column definitions with constraints
    - Pattern: Reference models/user.py and models/driver_data.py
  - [ ] 1.5 Create CallTranscription model (models/call_transcription.py)
    - Inherit from SQLModel with table=True
    - Fields:
      - id: int (primary key, auto-increment)
      - conversation_id: str (foreign key to Call.conversation_id, indexed, not null)
      - speaker_type: SpeakerType (enum, not null)
      - message_text: str (Text type, not null)
      - timestamp: datetime (timezone-aware UTC, not null)
      - sequence_number: int (indexed, not null)
      - created_at: datetime (auto-generated UTC, not null)
    - Include __tablename__ = "call_transcriptions"
    - Include __table_args__ = {"extend_existing": True}
    - Add index on conversation_id for fast lookups
    - Add index on sequence_number for ordered retrieval
    - Add composite index on (conversation_id, sequence_number) for efficient queries
    - Use Field() for column definitions with constraints
    - Pattern: Reference models/user.py and models/driver_data.py
  - [ ] 1.6 Add model class methods for common operations
    - Call.get_by_conversation_id(conversation_id: str) -> Optional[Call]
    - Call.create_call(conversation_id, driver_id, call_start_time) -> Call
    - CallTranscription.get_count_by_conversation_id(conversation_id: str) -> int
    - CallTranscription.create_transcription(...) -> CallTranscription
    - Apply @db_retry decorator to all class methods
    - Use Session(engine) for database operations
    - Pattern: Reference existing class methods in models/driver_data.py
  - [ ] 1.7 Ensure database layer tests pass
    - Run ONLY the 5-8 tests written in 1.1
    - Verify models create tables successfully
    - Verify enum constraints work correctly
    - Verify foreign key relationships are enforced
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 5-8 tests written in 1.1 pass
- Call model creates with all required fields and constraints
- CallTranscription model creates with proper foreign key relationship
- Enum validations reject invalid values
- Indexes are created on conversation_id and sequence_number
- Timezone-aware datetimes are enforced
- Class methods work correctly with @db_retry decorator

### Business Logic Layer

#### Task Group 2: Helper Functions and Business Logic
**Dependencies:** Task Group 1
**Assigned Role:** Backend Engineer

- [x] 2.0 Complete business logic layer
  - [x] 2.1 Write 5-8 focused tests for business logic functions
    - Test driver lookup returns correct driver_id for valid conversation_id
    - Test driver lookup returns None for unknown conversation_id
    - Test sequence number generation returns 1 for first transcription
    - Test sequence number generation returns correct count + 1 for existing transcriptions
    - Test speaker mapping from 'user' to 'driver'
    - Test speaker mapping from 'agent' to 'agent'
    - Test call initialization creates Call record on first dialogue
    - Test call initialization skips creation if Call already exists
  - [x] 2.2 Create helper module (helpers/transcription_helpers.py)
    - Create new file following existing helpers/ directory pattern
    - Import necessary models, db_retry, and timezone utilities
  - [x] 2.3 Implement driver lookup function
    - Function: lookup_driver_id_by_conversation(conversation_id: str) -> Optional[int]
    - Query existing ElevenLabs call records from driver_data table or related table
    - Reference: make_drivers_violation_batch_call_elevenlabs in models/driver_data.py
    - Match conversation_id to find associated driver_id
    - Return driver_id or None if not found
    - Apply @db_retry decorator for resilience
    - Log warning if driver_id not found
    - Pattern: Use Session(engine) for database operations
  - [x] 2.4 Implement sequence number generation function
    - Function: generate_sequence_number(conversation_id: str) -> int
    - Count existing CallTranscription records for conversation_id
    - Use CallTranscription.get_count_by_conversation_id(conversation_id)
    - Return count + 1 as sequence_number
    - Apply @db_retry decorator for resilience
    - Pattern: session.query(CallTranscription).filter_by(conversation_id=conversation_id).count()
  - [x] 2.5 Implement speaker mapping function
    - Function: map_speaker_to_internal(speaker: str) -> SpeakerType
    - Map 'user' -> SpeakerType.driver
    - Map 'agent' -> SpeakerType.agent
    - Raise ValueError for invalid speaker values
    - Simple mapping logic, no database operations needed
  - [x] 2.6 Implement call initialization logic function
    - Function: ensure_call_exists(conversation_id: str, timestamp: datetime) -> Call
    - Check if Call record exists using Call.get_by_conversation_id(conversation_id)
    - If NOT exists:
      - Look up driver_id using lookup_driver_id_by_conversation(conversation_id)
      - Create Call record using Call.create_call(conversation_id, driver_id, timestamp)
      - Set status = CallStatus.in_progress
      - Set call_start_time = timestamp (use make_timezone_aware)
    - If exists: Return existing Call record
    - Apply @db_retry decorator for resilience
    - Both Call creation and return happen in same database transaction
  - [x] 2.7 Implement main transcription save orchestration function
    - Function: save_transcription(conversation_id, speaker, message, timestamp) -> tuple[int, int]
    - Orchestrate entire workflow:
      1. Ensure Call exists (call ensure_call_exists)
      2. Map speaker to internal format (call map_speaker_to_internal)
      3. Generate sequence number (call generate_sequence_number)
      4. Create CallTranscription record
      5. Return (transcription_id, sequence_number)
    - Apply @db_retry decorator for resilience
    - Use timezone utilities (make_timezone_aware) for timestamp
    - Handle all database operations in single transaction
    - Pattern: Use Session(engine) with context manager
  - [x] 2.8 Ensure business logic tests pass
    - Run ONLY the 5-8 tests written in 2.1
    - Verify driver lookup works correctly
    - Verify sequence number generation is accurate
    - Verify speaker mapping is correct
    - Verify call initialization logic works
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 5-8 tests written in 2.1 pass
- Driver lookup function queries existing records correctly
- Sequence number generation starts at 1 and increments properly
- Speaker mapping converts 'user' to 'driver' and 'agent' to 'agent'
- Call initialization creates Call only on first dialogue
- Main orchestration function coordinates all steps successfully
- All functions use @db_retry decorator for resilience
- Timezone-aware datetime handling is consistent

### API Layer

#### Task Group 3: Webhook Endpoint Implementation
**Dependencies:** Task Group 2
**Assigned Role:** API Engineer

- [x] 3.0 Complete webhook endpoint
  - [x] 3.1 Write 5-8 focused tests for webhook endpoint
    - Test successful transcription save returns 201 Created
    - Test response includes transcription_id and sequence_number
    - Test missing required field returns 400 Bad Request
    - Test invalid speaker value returns 400 Bad Request
    - Test invalid timestamp format returns 400 Bad Request
    - Test database connection failure returns 500 Internal Server Error
    - Test first dialogue creates Call record with correct call_start_time
    - Test subsequent dialogues do not create duplicate Call records
  - [x] 3.2 Create Pydantic request model (services/webhooks_elevenlabs.py)
    - Class: TranscriptionWebhookRequest
    - Fields:
      - conversation_id: str (required, min_length=1)
      - speaker: str (required, must be 'agent' or 'user')
      - message: str (required, min_length=1)
      - timestamp: str (required, ISO8601 format)
    - Add field validators for speaker enum and timestamp format
    - Pattern: Reference existing Pydantic models in services/
  - [x] 3.3 Create Pydantic response models
    - Class: TranscriptionWebhookSuccessResponse
      - status: str (default="success")
      - message: str
      - transcription_id: int
      - sequence_number: int
    - Class: TranscriptionWebhookErrorResponse
      - status: str (default="error")
      - message: str
      - details: Optional[str]
    - Pattern: Reference existing Pydantic models in services/
  - [x] 3.4 Create FastAPI router (services/webhooks_elevenlabs.py)
    - Create router: APIRouter(prefix="/webhooks/elevenlabs", tags=["webhooks"])
    - Pattern: Reference services/webhook.py or services/driver_data.py
  - [x] 3.5 Implement POST /transcription endpoint
    - Endpoint: @router.post("/transcription", status_code=201)
    - Accept TranscriptionWebhookRequest as request body
    - Parse and validate request data
    - Convert timestamp string to timezone-aware datetime using make_timezone_aware
    - Call save_transcription orchestration function from helpers/transcription_helpers.py
    - Return TranscriptionWebhookSuccessResponse with transcription_id and sequence_number
    - Return 201 Created on success
    - No authentication required (public endpoint)
    - Pattern: Reference existing endpoints in services/
  - [x] 3.6 Implement comprehensive error handling
    - Catch ValueError for invalid speaker or validation errors -> 400 Bad Request
    - Catch database connection errors (OperationalError, DisconnectionError) -> 500 Internal Server Error
    - Catch unexpected exceptions -> 500 Internal Server Error
    - Return TranscriptionWebhookErrorResponse with error details
    - Log all errors with structured logging (use existing logging pattern)
    - Never return 200 OK on failure (allow ElevenLabs to retry)
    - Pattern: Reference error handling in services/driver_data.py
  - [x] 3.7 Register router in main.py
    - Import router: from services.webhooks_elevenlabs import router as webhooks_elevenlabs_router
    - Register: app.include_router(webhooks_elevenlabs_router)
    - Add to routers list in main.py
    - Pattern: Reference existing router registrations in main.py
  - [x] 3.8 Ensure webhook endpoint tests pass
    - Run ONLY the 5-8 tests written in 3.1
    - Verify endpoint returns 201 on success
    - Verify response includes correct data
    - Verify validation errors return 400
    - Verify database errors return 500
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 5-8 tests written in 3.1 pass
- POST /webhooks/elevenlabs/transcription endpoint is accessible
- Request validation rejects invalid data with 400 Bad Request
- Successful saves return 201 Created with transcription_id and sequence_number
- Database connection failures return 500 Internal Server Error
- Speaker mapping from 'user' to 'driver' works correctly
- Call initialization happens on first dialogue only
- Error responses never return 200 OK (allow retries)
- All errors are logged with structured logging

### Testing & Documentation

#### Task Group 4: Integration Testing and Documentation
**Dependencies:** Task Groups 1-3
**Assigned Role:** QA Engineer

- [x] 4.0 Review existing tests and fill critical gaps
  - [x] 4.1 Review tests from Task Groups 1-3
    - Review the 5-8 tests written by database-engineer (Task 1.1)
    - Review the 5-8 tests written by backend-engineer (Task 2.1)
    - Review the 5-8 tests written by api-engineer (Task 3.1)
    - Total existing tests: approximately 15-24 tests
  - [x] 4.2 Analyze test coverage gaps for THIS feature only
    - Identify critical end-to-end workflows that lack test coverage
    - Focus ONLY on gaps related to webhook transcription feature
    - Do NOT assess entire application test coverage
    - Prioritize integration tests over additional unit tests
    - Key workflows to verify:
      - Complete webhook call flow from request to database persistence
      - Multiple dialogues in sequence for same conversation
      - Concurrent conversations (different conversation_ids)
      - Driver lookup failure handling (graceful degradation)
      - Timezone handling across entire flow
  - [x] 4.3 Write up to 5 additional strategic integration tests maximum
    - Test complete end-to-end flow: webhook request -> database -> response
    - Test multiple sequential transcriptions increment sequence_number correctly
    - Test multiple conversations (different conversation_ids) don't interfere
    - Test graceful handling when driver_id lookup fails (null driver_id allowed)
    - Test timezone consistency from webhook timestamp to database storage
    - Focus on integration points between models, business logic, and API
    - Do NOT write comprehensive coverage for all edge cases
    - Skip performance tests and load testing unless business-critical
  - [x] 4.4 Create test fixtures and utilities
    - Create test database setup/teardown helpers
    - Create mock data generators for Call and CallTranscription
    - Create helper for mocking ElevenLabs webhook payloads
    - Create helper for verifying database state after webhook calls
    - Pattern: Reference existing test utilities in tests/ directory
  - [x] 4.5 Run feature-specific tests only
    - Run ONLY tests related to call transcription webhook feature
    - Expected total: approximately 20-28 tests maximum
    - Verify all critical workflows pass
    - Do NOT run the entire application test suite
    - Document any test failures with clear reproduction steps
  - [x] 4.6 Update API documentation
    - Add endpoint documentation to relevant API docs file
    - Document request format with example JSON
    - Document success response format with example
    - Document error response formats (400, 500) with examples
    - Document webhook behavior (sequential calls, no auth, error handling)
    - Pattern: Reference existing API documentation style
  - [x] 4.7 Create implementation notes document
    - Document driver lookup logic and assumptions
    - Document sequence number generation algorithm
    - Document speaker mapping rules ('user' -> 'driver')
    - Document call initialization flow (first dialogue behavior)
    - Document error handling strategy (return errors, allow retries)
    - Document timezone handling approach (UTC everywhere)
    - Document ElevenLabs integration assumptions (sequential guarantee)
    - Save as: planning/implementation-notes.md in spec folder
  - [x] 4.8 Update CLAUDE.md with new patterns (if applicable)
    - Add webhook endpoint pattern to main CLAUDE.md if this is first webhook
    - Add Call/CallTranscription models to architecture overview
    - Add transcription helper functions to relevant section
    - Only update if this introduces new patterns not already documented
    - Pattern: Reference existing CLAUDE.md structure

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 20-28 tests total)
- Critical end-to-end workflows are covered by integration tests
- No more than 5 additional tests added when filling in testing gaps
- Test fixtures and utilities support efficient test writing
- API documentation is complete and accurate with examples
- Implementation notes document captures all key decisions and logic
- CLAUDE.md is updated if new patterns were introduced
- Testing focused exclusively on call transcription webhook feature requirements

## Execution Order

Recommended implementation sequence:
1. Database Layer (Task Group 1) - Models and schema first
2. Business Logic Layer (Task Group 2) - Helper functions and orchestration
3. API Layer (Task Group 3) - Webhook endpoint implementation
4. Testing & Documentation (Task Group 4) - Integration tests and docs

## Key Implementation Notes

### Database Considerations
- Use `dev` schema (automatic via SQLAlchemy events in db/database.py)
- Apply @db_retry decorator from db/retry.py on all database operations
- Use timezone-aware datetimes (UTC) via utc_now() and make_timezone_aware() from logic/auth/service.py
- Index conversation_id for fast lookups
- Use composite index on (conversation_id, sequence_number) for efficient ordered queries

### Business Logic Patterns
- Driver lookup queries existing ElevenLabs call records (reference models/driver_data.py)
- Sequence number auto-generation uses COUNT query + 1
- Speaker mapping is simple string conversion ('user' -> 'driver', 'agent' -> 'agent')
- Call initialization happens on first dialogue only (check existence first)
- All operations use @db_retry for resilience

### API Design Patterns
- Public endpoint (no authentication) for performance
- Return 201 Created on success (not 200 OK)
- Return 400 Bad Request for validation errors
- Return 500 Internal Server Error for database/unexpected errors
- Never return 200 OK on failure (allow ElevenLabs to retry)
- Use Pydantic models for request/response validation
- Follow existing FastAPI router pattern from services/ directory

### Testing Strategy
- Test-driven approach: write tests first (x.1 sub-task), then implementation
- Each task group writes 5-8 focused tests maximum
- Testing group adds maximum 5 additional integration tests
- Total expected: 20-28 tests focused on critical paths
- Run only feature-specific tests during development (not entire suite)
- Focus on integration points and end-to-end workflows
- Skip exhaustive edge case testing during development

### Error Handling
- Validate all required fields (conversation_id, speaker, message, timestamp)
- Return appropriate HTTP status codes (400, 500)
- Log all errors with structured logging
- Handle driver lookup failures gracefully (allow null driver_id)
- Use existing error handling patterns from services/driver_data.py
- Follow centralized error handling approach (handle at API boundary)

### Timezone Handling
- Use utc_now() for current UTC time
- Use make_timezone_aware(dt) to ensure datetime has UTC timezone
- Store all timestamps as timezone-aware UTC in database
- Convert incoming timestamp strings to timezone-aware datetime objects
- Pattern: Import from logic/auth/service.py

### Code Reuse
- Reference existing models (models/user.py, models/driver_data.py)
- Reference existing services (services/webhook.py, services/driver_data.py)
- Use db_retry decorator pattern from db/retry.py
- Use timezone utilities from logic/auth/service.py
- Follow SQLModel patterns with table=True and Field() definitions
- Use existing logging patterns from utils/cloud_logger.py

## Total Task Count by Group
- Task Group 1 (Database Layer): 7 sub-tasks + 5-8 tests
- Task Group 2 (Business Logic Layer): 8 sub-tasks + 5-8 tests
- Task Group 3 (API Layer): 8 sub-tasks + 5-8 tests
- Task Group 4 (Testing & Documentation): 8 sub-tasks + up to 5 additional tests

**Total: 31 sub-tasks with 20-28 tests**
