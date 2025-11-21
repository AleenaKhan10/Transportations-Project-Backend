# Spec Requirements: Call Transcription Webhook

## Initial Description
Create a webhook that our LLM will call to save the transcription of the ongoing call with a driver. It should be able to save each dialogue in the conversation like "this is agent said" and "this is driver said".

**Context from Existing System:**
- This is for AGY Logistics platform
- Currently has ElevenLabs integration for AI-powered driver violation calls
- FastAPI backend with PostgreSQL database
- Existing models in models/ directory
- Existing services/routers in services/ directory

## Requirements Discussion

### First Round Questions

**Q1: Who will be calling this webhook - our LLM making the calls, or the ElevenLabs service itself?**
**Answer:** YES - Called by ElevenLabs service (not our LLM)

**Q2: For the database model structure, do you want a single CallTranscription or ConversationTranscript model with fields like: id, conversation_id (linking to the call), speaker_type (enum: 'agent'/'driver'), message_text, timestamp, sequence_number? Or would you prefer a different structure with separate tables for agent and driver dialogues?**
**Answer:** Create new model `CallTranscription` or `ConversationTranscript` with:
- id
- conversation_id (links to ElevenLabs conversation_id)
- speaker_type (enum: 'agent'/'driver')
- message_text
- timestamp
- sequence_number
- NO metadata (no confidence scores or word-level timestamps)

**Q3: How should the webhook save the dialogues - should it accept real-time streaming transcription data (each word/phrase as it's spoken), or receive complete dialogue turns (full agent message, then full driver message)?**
**Answer:** NOT real-time streaming. ElevenLabs will call our API endpoint periodically (after each dialogue turn completes - user speaks, then agent speaks). So it's "real-time updates" but not streaming - discrete webhook calls per dialogue turn.

**Q4: Should the webhook require authentication (API key, signature verification) from the caller, or should it be a public endpoint?**
**Answer:** NO authentication - keep API public for performance (faster response)

**Q5: For the endpoint structure, I'm assuming it should be something like `POST /webhooks/elevenlabs/transcription` that accepts: conversation_id, speaker (who is speaking), message (the dialogue text), and timestamp. Is that the right approach?**
**Answer:** YES - `POST /webhooks/elevenlabs/transcription`
- Accepts: speaker (who is speaking/dialogue owner)
- Accepts: conversation_id
- Accepts: message (the dialogue text)
- Accepts: timestamp
- Accepts: all fields discussed in Q2

**Q6: How does ElevenLabs identify speakers in their webhook payload - do they use "agent"/"user", "assistant"/"customer", or some other format? Should we map this to our "agent"/"driver" terminology?**
**Answer:** Handle "agent"/"user" format from ElevenLabs. Map "user" to "driver" in our system.

**Q7: Should we track the overall call metadata (start time, end time, status) in a separate Call or Conversation model, or just rely on the conversation_id from ElevenLabs without storing call-level information in our database?**
**Answer:** Create a NEW model for Call to track call metadata. Don't rely solely on conversation_id without a Call tracking model.

**Q8: For error handling, should the webhook return HTTP 200 OK even if saving fails (to prevent ElevenLabs from retrying), or should it return error codes so ElevenLabs knows to resend the data?**
**Answer:** Return errors to ElevenLabs (NOT 200 OK on failure). If dialogue not saved in database, ElevenLabs should resend that dialogue.

**Q9: Do you need to display these transcriptions in any UI (dashboard, admin panel), or is this purely for backend storage and later retrieval?**
**Answer:** Need to display data on dashboard in REAL-TIME. However, the real-time UI webhook will be created in FUTURE spec (not this one). This spec focuses on storage webhook only.

**Q10: Should we store the raw webhook payload in a JSONB column for debugging/audit purposes, or only store the parsed structured data?**
**Answer:** NO - only store structured data (no raw_payload JSONB column)

**Q11: Are there any specific requirements for post-processing the transcription data (sentiment analysis, keyword extraction, compliance checking), or should the webhook purely focus on storing the raw dialogue?**
**Answer:** NO - webhook purely focuses on storing raw dialogue as received

**Q12: Should the conversation_id link to an existing Call/Conversation tracking system, or is this the first step in building that capability?**
**Answer:** Create NEW Call tracking model first (not using existing conversation_id directly without Call model)

### Existing Code to Reference

No similar existing features identified for reference.

### Follow-up Questions

None required - all requirements clarified.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A

## Requirements Summary

### Functional Requirements

**Core Webhook Functionality:**
- Accept POST requests from ElevenLabs service at `/webhooks/elevenlabs/transcription`
- Process dialogue turn data (discrete webhook calls per dialogue turn, not streaming)
- Save structured transcription data to database
- Handle both agent and driver (user) dialogue attribution
- Return appropriate HTTP status codes (errors on failure, not always 200 OK)

**Data Capture:**
- conversation_id (from ElevenLabs)
- speaker (agent/user from ElevenLabs, map "user" to "driver" internally)
- message (the dialogue text)
- timestamp (when dialogue occurred)
- sequence_number (order of dialogues in conversation)

**Call Tracking:**
- Create new Call model to track call-level metadata
- Link transcriptions to calls via conversation_id

**Endpoint Characteristics:**
- Public endpoint (no authentication required)
- Optimized for performance (fast response times)
- Proper error handling with meaningful HTTP status codes

### Database Models Required

**Model 1: Call (New)**
- Purpose: Track call-level metadata
- Links to: CallTranscription records via conversation_id
- Fields to include:
  - id (primary key)
  - conversation_id (unique, from ElevenLabs)
  - call_start_time
  - call_end_time (nullable, updated when call ends)
  - status (enum: 'in_progress', 'completed', 'failed', etc.)
  - driver_id (foreign key, if applicable)
  - created_at
  - updated_at

**Model 2: CallTranscription or ConversationTranscript (New)**
- Purpose: Store individual dialogue turns
- Fields required:
  - id (primary key)
  - conversation_id (foreign key to Call.conversation_id)
  - speaker_type (enum: 'agent', 'driver')
  - message_text (the actual dialogue)
  - timestamp (when this dialogue occurred)
  - sequence_number (integer, order in conversation)
  - created_at

**Excluded from models:**
- No metadata fields (confidence scores, word-level timestamps)
- No raw_payload JSONB column
- No separate tables for agent vs driver dialogues

### API Endpoint Specification

**Endpoint:** `POST /webhooks/elevenlabs/transcription`

**Request Format:**
```json
{
  "conversation_id": "string",
  "speaker": "agent" | "user",
  "message": "string",
  "timestamp": "ISO8601 datetime string",
  "sequence_number": integer (optional, can be auto-generated)
}
```

**Response Format (Success):**
```json
{
  "status": "success",
  "message": "Transcription saved",
  "transcription_id": integer
}
```
HTTP Status: 201 Created

**Response Format (Error):**
```json
{
  "status": "error",
  "message": "Error description",
  "details": "Additional error context"
}
```
HTTP Status: 400 Bad Request, 500 Internal Server Error, etc.

**Key Behaviors:**
- Map "user" speaker to "driver" internally
- Create Call record if conversation_id doesn't exist
- Append CallTranscription record to existing conversation
- Return errors (not 200 OK) so ElevenLabs can retry failed saves
- Validate required fields before saving
- Handle database connection errors gracefully

### Integration Points

**ElevenLabs Service:**
- Receives webhook calls from ElevenLabs after each dialogue turn completes
- ElevenLabs sends: conversation_id, speaker ("agent"/"user"), message, timestamp
- ElevenLabs expects: HTTP status codes indicating success/failure
- ElevenLabs will retry on error responses

**Database:**
- PostgreSQL with SQLModel ORM
- Uses `dev` schema (per existing architecture)
- Apply `@db_retry` decorator for resilient database operations
- Timezone-aware datetime handling (UTC)

**Future Integration (Out of Scope for This Spec):**
- Real-time UI webhook for dashboard updates
- WebSocket or SSE connection for live transcription display
- Frontend dashboard components

### Reusability Opportunities

**Existing Patterns to Follow:**
- Use SQLModel pattern from existing models/ directory
- Follow FastAPI router pattern from existing services/ directory
- Apply `@db_retry` decorator from db/retry.py
- Use timezone utilities from logic/auth/service.py (utc_now, make_timezone_aware)
- Follow error handling patterns from existing ElevenLabs integration

**Similar Code to Reference:**
- Existing ElevenLabs integration code (utils/elevenlabs_client.py)
- Existing model patterns in models/ directory
- Existing webhook or API endpoint patterns in services/ directory

### Scope Boundaries

**In Scope:**
- POST endpoint `/webhooks/elevenlabs/transcription`
- Call model creation with metadata tracking
- CallTranscription model creation with dialogue storage
- Speaker mapping (ElevenLabs "user" to internal "driver")
- Error response handling (no always-200-OK pattern)
- Database persistence with retry logic
- Validation of incoming webhook data

**Out of Scope:**
- Authentication/authorization for webhook endpoint
- Real-time UI updates or WebSocket implementation
- Dashboard display components (future spec)
- Transcription post-processing (sentiment analysis, keyword extraction, compliance)
- Raw payload storage (JSONB audit column)
- Metadata fields (confidence scores, word-level timestamps)
- Call status webhooks from ElevenLabs (separate from transcription webhook)
- Bulk transcription import or historical data migration

**Future Enhancements:**
- Real-time dashboard webhook for live transcription updates
- WebSocket/SSE integration for frontend real-time display
- Admin UI for viewing call transcriptions
- Search and filtering capabilities for transcriptions
- Analytics on call transcriptions
- Integration with existing driver reports

### Technical Considerations

**Architecture Constraints:**
- FastAPI framework (existing main.py application)
- PostgreSQL database with `dev` schema
- SQLModel ORM for models
- No authentication required (public endpoint)

**Performance Requirements:**
- Fast response times (public endpoint, no auth overhead)
- Efficient database writes (one insert per dialogue turn)
- Connection pooling already configured (pool_size=10, max_overflow=20)

**Error Handling Strategy:**
- Return appropriate HTTP status codes (not always 200)
- Allow ElevenLabs to retry failed saves
- Log errors for debugging
- Graceful handling of database connection issues
- Validation errors for malformed requests

**Database Considerations:**
- Use `@db_retry` decorator for all database operations
- Timezone-aware datetimes (UTC)
- Foreign key relationship: CallTranscription.conversation_id -> Call.conversation_id
- Index on conversation_id for fast lookups
- Index on sequence_number for ordered retrieval

**Code Location:**
- Model: `models/call_transcription.py` (or similar)
- Model: `models/call.py` (or similar)
- Router/Service: `services/webhooks_elevenlabs.py` (or similar)
- Follow existing project structure conventions

**Integration Notes:**
- ElevenLabs sends discrete webhook calls (not streaming)
- Each webhook call represents one completed dialogue turn
- Must handle conversation initialization (first dialogue creates Call record)
- Must handle concurrent webhook calls for same conversation (rare but possible)

**Validation Requirements:**
- conversation_id: required, non-empty string
- speaker: required, must be "agent" or "user"
- message: required, non-empty string
- timestamp: required, valid ISO8601 datetime
- sequence_number: optional (can auto-increment if not provided)
