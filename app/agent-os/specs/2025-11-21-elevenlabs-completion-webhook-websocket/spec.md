# Specification: ElevenLabs Completion Webhook and WebSocket Integration

## Goal

Complete the ElevenLabs conversational AI integration by implementing Part 3 (post-call completion webhook) and Part 5 (real-time WebSocket system) to enable call completion tracking and live transcription streaming to frontend clients.

## User Stories

- As a dispatcher, I want to see when a driver call has completed so that I can review the outcome and take appropriate action
- As a dispatcher, I want to see transcription messages appear in real-time as the call progresses so that I can monitor conversations live without polling
- As a system administrator, I want call completion metadata stored in the database so that I can analyze call costs, durations, and outcomes

## Specific Requirements

### Part 3: Post-Call Completion Webhook

**Webhook Endpoint Implementation**
- Create POST `/webhooks/elevenlabs/post-call` endpoint in `services/webhooks_elevenlabs.py`
- Public endpoint (no authentication) following existing transcription webhook pattern
- Accept ElevenLabs post-call webhook payload containing conversation analysis and metadata
- Process both `post_call_transcription` and `call_initiation_failure` webhook types
- Extract conversation_id from webhook payload to identify Call record
- Update Call status to COMPLETED with call_end_time
- Store post-call metadata (summary, duration, cost, analysis) in new Call model fields
- Return appropriate HTTP status codes: 200 OK on success, 400/404/500 on errors
- Never return 200 on failure to enable ElevenLabs retry mechanism

**Database Schema Extension**
- Add new fields to Call model for storing post-call webhook data
- All new fields must be nullable for backward compatibility
- Fields include: transcript_summary (Text), call_duration_seconds (Integer), cost (Float), call_successful (Boolean), analysis_data (Text/JSON), metadata_json (Text/JSON)
- Create Alembic migration to add columns to `calls` table
- Add class method `update_post_call_data()` to Call model with @db_retry decorator
- Method accepts conversation_id and all metadata fields, updates Call record atomically

**Error Handling and Validation**
- Validate webhook payload structure and required fields
- Return 400 Bad Request for invalid/malformed payload
- Return 404 Not Found if conversation_id doesn't match any Call record
- Return 500 Internal Server Error for database failures
- Log all webhook receipts with structured logging (conversation_id, status, errors)
- Follow existing webhook logging patterns from transcription webhook

**ElevenLabs Webhook Payload Handling**
- Process `event_timestamp` (Unix timestamp) and convert to timezone-aware UTC datetime
- Extract `data.conversation_id` for Call lookup
- Parse `data.metadata.call_duration_secs` for duration tracking
- Extract `data.metadata.cost` for billing tracking
- Parse `data.analysis.call_successful` boolean for outcome tracking
- Store `data.analysis.transcript_summary` as text summary
- Serialize full `data.analysis` object to JSON string for analysis_data field
- Serialize full `data.metadata` object to JSON string for metadata_json field

### Part 5: Real-Time WebSocket System

**WebSocket Endpoint and Connection Management**
- Create WebSocket endpoint `/ws/calls/transcriptions` for real-time transcription streaming
- Implement JWT authentication during WebSocket upgrade using Authorization header
- Use existing `get_current_user()` dependency from `logic/auth/security.py` for token validation
- Create WebSocketConnectionManager class to track active connections in-memory
- Manager maintains dictionary mapping connection_id to WebSocket connection and subscribed identifiers
- Support graceful connection/disconnection with automatic cleanup
- Implement ping-pong heartbeat mechanism for connection health monitoring

**Subscription Protocol**
- After connection, client sends subscription message: `{"subscribe": "identifier"}`
- Server auto-detects whether identifier is call_sid or conversation_id
- Lookup Call record by identifier and validate it exists
- Add connection to subscription registry for that Call (support multiple clients per call)
- Support multiple subscriptions per connection (client can monitor multiple calls simultaneously)
- Support unsubscribe message: `{"unsubscribe": "identifier"}`
- Send confirmation or error message back to client after subscription attempt

**Real-Time Transcription Broadcasting**
- Integrate with existing `/webhooks/elevenlabs/transcription` endpoint
- After saving transcription to database, broadcast to subscribed WebSocket clients
- Message format includes: type="transcription", conversation_id, call_sid, transcription_id, sequence_number, speaker_type, message_text, timestamp
- Identify subscribed connections by looking up Call record (supports both call_sid and conversation_id subscriptions)
- Broadcast to all active WebSocket connections subscribed to that Call
- Handle broadcast failures gracefully (log error, remove dead connections)

**Call Completion Broadcasting**
- Integrate with Part 3 post-call webhook
- After updating Call to COMPLETED status, broadcast two sequential messages
- First message: status update with type="call_status", conversation_id, call_sid, status="completed", call_end_time
- Second message: full data with type="call_completed", conversation_id, call_sid, call_data (includes all metadata)
- Broadcast to all connections subscribed to that Call
- Remove completed calls from active subscription registry after broadcast

**Message Protocol and Types**
- Client-to-server: subscribe request, unsubscribe request
- Server-to-client: transcription message, call_status message, call_completed message, error message, subscription_confirmed message, unsubscribe_confirmed message
- All messages use JSON format with `type` field discriminator
- Error messages include type="error", message (human-readable), code (optional error code)
- Subscription confirmations include type="subscription_confirmed", identifier, call_sid, conversation_id

**Auto-Detection Logic for Identifiers**
- Accept both call_sid and conversation_id interchangeably in subscription messages
- Attempt Call.get_by_call_sid() first, then Call.get_by_conversation_id() if not found
- Store normalized identifier (always map to Call record) in subscription registry
- Support lookups from both directions for broadcasting (transcription webhook has call_sid, completion webhook has conversation_id)

## Visual Design

No visual assets provided.

## Existing Code to Leverage

**services/webhooks_elevenlabs.py - Transcription Webhook Pattern**
- Follow existing webhook structure for request validation, error responses, structured logging
- Reuse Pydantic BaseModel patterns for request/response schemas
- Follow error handling strategy: 400 for validation errors, 500 for database errors, never 200 on failure
- Use similar logging format with section separators and key information extraction
- Reference existing database retry logic with @db_retry decorator

**models/call.py - Call Model Structure**
- Extend existing Call model with new metadata fields
- Follow existing class method patterns (get_by_call_sid, update_status_by_call_sid)
- Replicate @db_retry decorator usage on new update_post_call_data method
- Maintain consistency with timezone-aware datetime handling
- Reference CallStatus enum pattern for status management

**models/call_transcription.py - Transcription Storage**
- Reuse existing CallTranscription.get_by_conversation_id() for fetching transcripts to broadcast
- Reference SpeakerType enum for speaker attribution in WebSocket messages
- Use sequence_number field for ordering messages in broadcasts
- Follow foreign key pattern (conversation_id FK to Call.conversation_id)

**logic/auth/security.py - JWT Authentication**
- Reuse get_current_user() dependency for WebSocket authentication
- Follow existing JWT token validation and session verification logic
- Use oauth2_scheme pattern for extracting Bearer token from Authorization header
- Reference existing HTTPException patterns for authentication failures

**services/calls.py - Call Response Models**
- Reuse TranscriptMessage, CallResponse models for WebSocket message payloads
- Reference existing call detail fetching logic for building call_data in call_completed message
- Follow pattern of converting datetime to isoformat() strings in responses
- Use existing Call and CallTranscription query patterns for data fetching

## Out of Scope

- HMAC signature validation for post-call webhook (future security enhancement)
- WebSocket rate limiting or per-client throttling
- Message delivery guarantees (at-least-once, exactly-once semantics)
- Persistent message queue for offline clients or reconnection history replay
- WebSocket connection pooling or clustering for horizontal scaling across multiple server instances
- Redis Pub/Sub for multi-instance WebSocket broadcasting
- Binary WebSocket message formats (text/JSON only)
- WebSocket compression (per-message-deflate extension)
- Frontend WebSocket client implementation
- Admin dashboard for monitoring active WebSocket connections
- Message size limits or pagination for large transcripts
- Webhook retry logic (handled by ElevenLabs)
- Conversation recording URL storage or retrieval

---

## Technical Architecture

### System Overview

This specification completes the ElevenLabs integration by adding the final two components:

**Completed Parts (Context):**
- Part 1: Call initialization endpoint (`POST /driver_data/call-elevenlabs`) - Creates Call record, initiates ElevenLabs call
- Part 2: Transcription webhook (`POST /webhooks/elevenlabs/transcription`) - Receives real-time dialogue turns, stores transcriptions
- Part 4: Conversation fetching endpoint (`GET /conversations/{conversation_id}/fetch`) - Fetches complete conversation from ElevenLabs API

**New Parts (This Spec):**
- Part 3: Post-call webhook (`POST /webhooks/elevenlabs/post-call`) - Updates Call on completion, stores metadata
- Part 5: WebSocket system (`/ws/calls/transcriptions`) - Streams real-time transcriptions and completion events to frontend

### Component Interaction Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ElevenLabs Platform                         │
└────────┬────────────────────────────────┬────────────────────┬──────┘
         │                                │                    │
         │ (Dialogue Turn)                │ (Call Complete)    │
         │                                │                    │
         v                                v                    │
┌────────────────────┐        ┌────────────────────────┐       │
│  POST /webhooks/   │        │  POST /webhooks/       │       │
│  elevenlabs/       │        │  elevenlabs/           │       │
│  transcription     │        │  post-call             │       │
│  (Part 2 - Exists) │        │  (Part 3 - NEW)        │       │
└─────────┬──────────┘        └──────────┬─────────────┘       │
          │                              │                     │
          │ save_transcription()         │ update_post_call_   │
          │                              │ data()              │
          v                              v                     │
┌────────────────────────────────────────────────────────┐     │
│              Database (PostgreSQL)                     │     │
│  ┌──────────────┐      ┌──────────────────────────┐   │     │
│  │ calls        │◄─────┤ call_transcriptions      │   │     │
│  │ - call_sid   │ FK   │ - conversation_id (FK)   │   │     │
│  │ - conv_id    │      │ - speaker_type           │   │     │
│  │ - status     │      │ - message_text           │   │     │
│  │ - summary    │◄─┐   │ - sequence_number        │   │     │
│  │ - cost       │  │   └──────────────────────────┘   │     │
│  └──────────────┘  │                                  │     │
│                    │ (NEW fields)                     │     │
└────────────────────┼──────────────────────────────────┘     │
                     │                                         │
                     v                                         │
┌────────────────────────────────────────────────────────┐    │
│         WebSocket Broadcasting (Part 5 - NEW)          │    │
│  ┌──────────────────────────────────────────────────┐  │    │
│  │ WebSocketConnectionManager                       │  │    │
│  │ - connections: Dict[conn_id, WebSocketConn]      │  │    │
│  │ - subscriptions: Dict[call_identifier, Set[...]] │  │    │
│  └──────────────────────────────────────────────────┘  │    │
└─────────┬──────────────────────────────────────────────┘    │
          │                                                    │
          │ broadcast_transcription()                          │
          │ broadcast_call_completion()                        │
          v                                                    │
┌─────────────────────────────────────────┐                    │
│   Frontend Clients (WebSocket)          │                    │
│   - Live call monitoring dashboard      │                    │
│   - Real-time transcription display     │                    │
│   - Call completion notifications       │                    │
└─────────────────────────────────────────┘                    │
                                                               │
                                      (Alternative: Part 4)    │
                                      GET /conversations/      │
                                      {id}/fetch ──────────────┘
                                      (Fetch full history
                                       from ElevenLabs API)
```

### Database Schema Changes

#### New Fields for Call Model

```python
# Add to models/call.py

# Post-call webhook metadata fields
transcript_summary: Optional[str] = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
    description="Summary of the call conversation from ElevenLabs analysis"
)

call_duration_seconds: Optional[int] = Field(
    default=None,
    nullable=True,
    description="Duration of the call in seconds from metadata"
)

cost: Optional[float] = Field(
    default=None,
    nullable=True,
    description="Cost of the call in dollars from ElevenLabs billing"
)

call_successful: Optional[bool] = Field(
    default=None,
    nullable=True,
    description="Boolean flag indicating if call was successful from analysis"
)

analysis_data: Optional[str] = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
    description="JSON string of full analysis results from post-call webhook"
)

metadata_json: Optional[str] = Field(
    default=None,
    sa_column=Column(Text, nullable=True),
    description="JSON string of full metadata from post-call webhook"
)
```

#### Alembic Migration

```sql
-- Migration: Add post-call webhook fields to calls table

ALTER TABLE dev.calls
ADD COLUMN transcript_summary TEXT NULL;

ALTER TABLE dev.calls
ADD COLUMN call_duration_seconds INTEGER NULL;

ALTER TABLE dev.calls
ADD COLUMN cost DOUBLE PRECISION NULL;

ALTER TABLE dev.calls
ADD COLUMN call_successful BOOLEAN NULL;

ALTER TABLE dev.calls
ADD COLUMN analysis_data TEXT NULL;

ALTER TABLE dev.calls
ADD COLUMN metadata_json TEXT NULL;

COMMENT ON COLUMN dev.calls.transcript_summary IS 'Summary of call conversation from ElevenLabs analysis';
COMMENT ON COLUMN dev.calls.call_duration_seconds IS 'Duration of call in seconds from metadata';
COMMENT ON COLUMN dev.calls.cost IS 'Cost of call in dollars from ElevenLabs billing';
COMMENT ON COLUMN dev.calls.call_successful IS 'Boolean flag indicating if call was successful';
COMMENT ON COLUMN dev.calls.analysis_data IS 'JSON string of full analysis results';
COMMENT ON COLUMN dev.calls.metadata_json IS 'JSON string of full metadata from webhook';
```

---

## API Specifications

### Part 3: POST /webhooks/elevenlabs/post-call

**Endpoint:** `POST /webhooks/elevenlabs/post-call`

**Authentication:** None (public webhook endpoint)

**Description:** Receives post-call analysis webhook from ElevenLabs when call completes or fails

#### Request Schema

**Headers:**
```
Content-Type: application/json
ElevenLabs-Signature: t=<timestamp>,v0=<hmac_sha256_hash> (optional, not validated in v1)
```

**Body (post_call_transcription type):**
```json
{
  "type": "post_call_transcription",
  "event_timestamp": 1732200000,
  "data": {
    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
    "conversation_id": "abc123xyz",
    "status": "done",
    "transcript": [
      {
        "role": "agent",
        "message": "Hello, how are you?",
        "time_in_call_secs": 0.5
      },
      {
        "role": "user",
        "message": "I'm good, thanks!",
        "time_in_call_secs": 3.2
      }
    ],
    "metadata": {
      "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
      "call_id": "twilio_call_sid",
      "start_time_unix_secs": 1732199700,
      "call_duration_secs": 145,
      "cost": 0.08,
      "from_number": "+14155551234",
      "to_number": "+14155555678"
    },
    "analysis": {
      "call_successful": true,
      "transcript_summary": "Agent greeted the driver and confirmed delivery location. Driver acknowledged and agreed to proceed to the new destination.",
      "evaluation_results": {
        "criteria_1": "passed",
        "criteria_2": "passed"
      }
    }
  }
}
```

**Body (call_initiation_failure type):**
```json
{
  "type": "call_initiation_failure",
  "event_timestamp": 1732200000,
  "data": {
    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
    "conversation_id": "abc123xyz",
    "status": "failed",
    "error_message": "Phone number unreachable",
    "metadata": {
      "from_number": "+14155551234",
      "to_number": "+14155555678"
    }
  }
}
```

#### Response Schemas

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Call completion data processed successfully",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "call_status": "completed"
}
```

**Error Responses:**

**400 Bad Request - Invalid Payload:**
```json
{
  "status": "error",
  "message": "Invalid webhook payload",
  "details": "Missing required field: conversation_id"
}
```

**404 Not Found - Call Not Found:**
```json
{
  "status": "error",
  "message": "Call not found for conversation_id: abc123xyz",
  "details": "No Call record exists with this conversation_id"
}
```

**500 Internal Server Error:**
```json
{
  "status": "error",
  "message": "Database error while processing webhook",
  "details": "Database temporarily unavailable"
}
```

#### Processing Logic

1. Validate webhook payload structure and extract `type` field
2. Extract `conversation_id` from `data.conversation_id`
3. Determine webhook type and process accordingly:
   - `post_call_transcription`: Normal completion flow
   - `call_initiation_failure`: Failure flow (update status to FAILED)
4. Look up Call record using `Call.get_by_conversation_id()`
5. If not found, return 404 Not Found
6. For completion: Extract metadata and analysis fields from payload
7. Convert `event_timestamp` (Unix seconds) to timezone-aware UTC datetime for call_end_time
8. Parse `data.metadata.call_duration_secs` as integer
9. Parse `data.metadata.cost` as float
10. Parse `data.analysis.call_successful` as boolean
11. Extract `data.analysis.transcript_summary` as string
12. Serialize `data.analysis` to JSON string for analysis_data
13. Serialize `data.metadata` to JSON string for metadata_json
14. Call `Call.update_post_call_data()` with all fields
15. Trigger WebSocket broadcast for call completion (Part 5 integration)
16. Return 200 OK success response
17. On any error, return appropriate error response (400/404/500)

---

### Part 5: WebSocket /ws/calls/transcriptions

**Endpoint:** `WebSocket /ws/calls/transcriptions`

**Authentication:** JWT token via Authorization header during WebSocket upgrade

**Description:** Real-time bidirectional WebSocket connection for subscribing to call transcriptions and receiving live updates

#### Connection Flow

```
Client                                Server
  |                                     |
  |--- WebSocket Upgrade Request ----->|
  |    Authorization: Bearer <token>   |
  |                                     |
  |<--- 101 Switching Protocols -------|
  |                                     |
  |--- {"subscribe": "call_sid_123"} ->|
  |                                     |
  |<--- {"type": "subscription_        |
  |      confirmed", ...}               |
  |                                     |
  |                                     | (Transcription webhook received)
  |<--- {"type": "transcription",      |
  |      "message_text": "..."}        |
  |                                     |
  |                                     | (Call completed webhook received)
  |<--- {"type": "call_status",        |
  |      "status": "completed"}        |
  |                                     |
  |<--- {"type": "call_completed",     |
  |      "call_data": {...}}           |
  |                                     |
  |--- {"unsubscribe": "call_sid_123"} |
  |                                     |
  |<--- {"type": "unsubscribe_         |
  |      confirmed", ...}               |
  |                                     |
  |--- Close Connection --------------->|
  |                                     |
```

#### Message Types

##### 1. Subscribe Request (Client -> Server)

```json
{
  "subscribe": "EL_driver123_1732199700"
}
```

or

```json
{
  "subscribe": "abc123xyz"
}
```

**Fields:**
- `subscribe` (string): Call identifier - can be either call_sid or conversation_id

**Server Processing:**
- Auto-detect identifier type (call_sid vs conversation_id)
- Look up Call record using `Call.get_by_call_sid()` or `Call.get_by_conversation_id()`
- Validate Call exists
- Add connection to subscription registry for that Call
- Send subscription_confirmed or error message

---

##### 2. Subscription Confirmed (Server -> Client)

```json
{
  "type": "subscription_confirmed",
  "identifier": "EL_driver123_1732199700",
  "call_sid": "EL_driver123_1732199700",
  "conversation_id": "abc123xyz",
  "status": "in_progress",
  "message": "Successfully subscribed to call updates"
}
```

**Fields:**
- `type`: "subscription_confirmed"
- `identifier`: Original identifier from subscribe request
- `call_sid`: Resolved call_sid from Call record
- `conversation_id`: Resolved conversation_id from Call record (may be null)
- `status`: Current call status (in_progress, completed, failed)
- `message`: Human-readable confirmation message

---

##### 3. Unsubscribe Request (Client -> Server)

```json
{
  "unsubscribe": "EL_driver123_1732199700"
}
```

**Fields:**
- `unsubscribe` (string): Call identifier to stop receiving updates for

---

##### 4. Unsubscribe Confirmed (Server -> Client)

```json
{
  "type": "unsubscribe_confirmed",
  "identifier": "EL_driver123_1732199700",
  "message": "Successfully unsubscribed from call updates"
}
```

**Fields:**
- `type`: "unsubscribe_confirmed"
- `identifier`: Original identifier from unsubscribe request
- `message`: Human-readable confirmation message

---

##### 5. Transcription Message (Server -> Client)

```json
{
  "type": "transcription",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "transcription_id": 456,
  "sequence_number": 3,
  "speaker_type": "agent",
  "message_text": "Hello, how are you doing today?",
  "timestamp": "2025-11-21T15:30:45.123456Z"
}
```

**Fields:**
- `type`: "transcription"
- `conversation_id`: ElevenLabs conversation identifier
- `call_sid`: Our generated call identifier
- `transcription_id`: Database ID of transcription record
- `sequence_number`: Sequence number in conversation (for ordering)
- `speaker_type`: "agent" or "driver"
- `message_text`: Dialogue text
- `timestamp`: ISO 8601 timestamp when message occurred

**Trigger:** Sent immediately after transcription webhook saves new dialogue turn to database

---

##### 6. Call Status Message (Server -> Client)

```json
{
  "type": "call_status",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "status": "completed",
  "call_end_time": "2025-11-21T15:35:00.000000Z"
}
```

**Fields:**
- `type`: "call_status"
- `conversation_id`: ElevenLabs conversation identifier
- `call_sid`: Our generated call identifier
- `status`: New call status ("completed" or "failed")
- `call_end_time`: ISO 8601 timestamp when call ended (nullable)

**Trigger:** Sent immediately after post-call webhook updates Call status (first message in completion sequence)

---

##### 7. Call Completed Message (Server -> Client)

```json
{
  "type": "call_completed",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "call_data": {
    "status": "completed",
    "driver_id": "driver123",
    "call_start_time": "2025-11-21T15:30:00.000000Z",
    "call_end_time": "2025-11-21T15:35:00.000000Z",
    "duration_seconds": 300,
    "transcript_summary": "Agent greeted the driver and confirmed delivery location. Driver acknowledged and agreed to proceed to the new destination.",
    "cost": 0.08,
    "call_successful": true,
    "analysis_data": {
      "call_successful": true,
      "transcript_summary": "...",
      "evaluation_results": {}
    },
    "metadata": {
      "call_duration_secs": 300,
      "cost": 0.08,
      "from_number": "+14155551234",
      "to_number": "+14155555678"
    }
  }
}
```

**Fields:**
- `type`: "call_completed"
- `conversation_id`: ElevenLabs conversation identifier
- `call_sid`: Our generated call identifier
- `call_data`: Full Call record data including all new metadata fields
  - `status`: Final call status
  - `driver_id`: Driver identifier (nullable)
  - `call_start_time`: ISO 8601 timestamp
  - `call_end_time`: ISO 8601 timestamp
  - `duration_seconds`: Calculated or extracted duration
  - `transcript_summary`: Text summary from analysis
  - `cost`: Call cost in dollars
  - `call_successful`: Boolean success indicator
  - `analysis_data`: Parsed JSON object from analysis_data field
  - `metadata`: Parsed JSON object from metadata_json field

**Trigger:** Sent immediately after call_status message (second message in completion sequence)

---

##### 8. Error Message (Server -> Client)

```json
{
  "type": "error",
  "message": "Call not found for identifier: invalid_id_123",
  "code": "CALL_NOT_FOUND"
}
```

**Fields:**
- `type`: "error"
- `message`: Human-readable error description
- `code`: Optional error code for programmatic handling

**Common Error Codes:**
- `CALL_NOT_FOUND`: Identifier doesn't match any Call record
- `INVALID_IDENTIFIER`: Malformed identifier format
- `AUTHENTICATION_FAILED`: JWT token invalid or expired
- `SUBSCRIPTION_FAILED`: Failed to subscribe to call updates
- `INVALID_MESSAGE_FORMAT`: Client message doesn't match expected schema

---

### WebSocket Connection Manager Architecture

#### Class Structure

```python
class WebSocketConnectionManager:
    """
    Manages active WebSocket connections and subscriptions.

    Attributes:
        connections: Dict mapping connection_id to WebSocket connection object
        subscriptions: Dict mapping call_identifier to Set of connection_ids
        connection_metadata: Dict mapping connection_id to metadata (user, subscribed_calls)
    """

    async def connect(websocket: WebSocket, user: User) -> str:
        """Accept WebSocket connection after JWT authentication."""

    async def disconnect(connection_id: str):
        """Clean up connection and remove all subscriptions."""

    async def subscribe(connection_id: str, identifier: str) -> Call:
        """Subscribe connection to a call's updates."""

    async def unsubscribe(connection_id: str, identifier: str):
        """Unsubscribe connection from a call's updates."""

    async def broadcast_to_call(call: Call, message: dict):
        """Broadcast message to all connections subscribed to a call."""

    async def broadcast_transcription(call_sid: str, transcription: CallTranscription):
        """Broadcast new transcription to subscribed clients."""

    async def broadcast_call_completion(conversation_id: str, call: Call):
        """Broadcast call completion (status + full data)."""
```

#### In-Memory Data Structures

```python
# Example internal state
manager = WebSocketConnectionManager()

manager.connections = {
    "conn_001": <WebSocket object>,
    "conn_002": <WebSocket object>,
    "conn_003": <WebSocket object>
}

manager.subscriptions = {
    "EL_driver123_1732199700": {"conn_001", "conn_002"},  # call_sid
    "abc123xyz": {"conn_001"},  # conversation_id (same call)
    "EL_driver456_1732199800": {"conn_002", "conn_003"}
}

manager.connection_metadata = {
    "conn_001": {
        "user_id": "user123",
        "username": "dispatcher@example.com",
        "connected_at": "2025-11-21T15:00:00Z",
        "subscribed_calls": {"EL_driver123_1732199700"}
    },
    "conn_002": {
        "user_id": "user456",
        "username": "admin@example.com",
        "connected_at": "2025-11-21T15:05:00Z",
        "subscribed_calls": {"EL_driver123_1732199700", "EL_driver456_1732199800"}
    }
}
```

---

## Integration Points

### Part 2 Integration: Transcription Webhook

**File:** `services/webhooks_elevenlabs.py`

**Modification Point:** After successful `save_transcription()` in `receive_transcription()` endpoint

**Integration Code:**
```python
# After line ~181 (after transcription saved successfully)
from services.websocket_calls import websocket_manager

# Broadcast transcription to subscribed WebSocket clients
await websocket_manager.broadcast_transcription(
    call_sid=request.call_sid,
    transcription_id=transcription_id,
    sequence_number=sequence_number,
    speaker=request.speaker,
    message=request.message,
    timestamp=timestamp_dt
)
```

**Impact:** No changes to existing functionality, only adds WebSocket broadcast as side effect

---

### Part 3 Integration: Post-Call Webhook

**File:** `services/webhooks_elevenlabs.py` (new endpoint in same file)

**Integration Code:**
```python
# After updating Call record with post-call data
from services.websocket_calls import websocket_manager

# Broadcast call completion to subscribed WebSocket clients
await websocket_manager.broadcast_call_completion(
    conversation_id=conversation_id,
    call_sid=call.call_sid,
    call=call  # Full updated Call object
)
```

**Database Integration:** Uses new `Call.update_post_call_data()` class method

---

### Identifier Support Strategy

**Two-Way Lookup Pattern:**

1. **Transcription Webhook (has call_sid):**
   - Receives `call_sid` from ElevenLabs
   - Looks up Call record by call_sid
   - Broadcasts using call_sid
   - WebSocket manager also checks conversation_id subscriptions

2. **Post-Call Webhook (has conversation_id):**
   - Receives `conversation_id` from ElevenLabs
   - Looks up Call record by conversation_id
   - Retrieves call_sid from Call record
   - Broadcasts using both identifiers

3. **WebSocket Subscription (accepts either):**
   - Client provides identifier (call_sid or conversation_id)
   - Server attempts both lookup methods
   - Stores subscription under normalized key (Call.id or both identifiers)
   - Broadcast matching checks both identifier types

**Auto-Detection Algorithm:**
```python
def resolve_call_identifier(identifier: str) -> Optional[Call]:
    """Auto-detect and resolve call identifier."""
    # Try call_sid format first (starts with "EL_")
    if identifier.startswith("EL_"):
        call = Call.get_by_call_sid(identifier)
        if call:
            return call

    # Try conversation_id format
    call = Call.get_by_conversation_id(identifier)
    if call:
        return call

    return None
```

---

## Implementation Phases

### Phase 1: Database Schema Extension

**Tasks:**
1. Add new fields to `models/call.py` Call model
2. Add `update_post_call_data()` class method to Call model
3. Create Alembic migration for new columns
4. Test migration on development database
5. Verify backward compatibility with existing Call records

**Acceptance Criteria:**
- Migration runs successfully without errors
- Existing Call records unaffected (NULL values for new fields)
- New class method callable with all parameters

---

### Phase 2: Post-Call Webhook Implementation

**Tasks:**
1. Create request/response Pydantic models for post-call webhook
2. Implement `POST /webhooks/elevenlabs/post-call` endpoint
3. Add payload validation and type detection logic
4. Implement Call lookup and update logic
5. Add error handling for all failure scenarios
6. Add structured logging for webhook receipts
7. Register router in `main.py`

**Acceptance Criteria:**
- Endpoint accepts valid post-call webhook payloads
- Call status updated to COMPLETED with metadata
- Error responses match specification (400/404/500)
- Logging includes conversation_id, status, errors

---

### Phase 3: WebSocket Connection Manager

**Tasks:**
1. Create `WebSocketConnectionManager` class
2. Implement connection/disconnection lifecycle methods
3. Implement subscription/unsubscription logic
4. Add identifier auto-detection and Call lookup
5. Implement broadcast methods for transcriptions and completions
6. Add connection health monitoring (ping-pong)
7. Add error handling for dead connections

**Acceptance Criteria:**
- Connections tracked in-memory with metadata
- Subscriptions support both call_sid and conversation_id
- Dead connections automatically cleaned up
- Broadcast methods handle multiple recipients

---

### Phase 4: WebSocket Endpoint Implementation

**Tasks:**
1. Create WebSocket endpoint `/ws/calls/transcriptions`
2. Implement JWT authentication during upgrade
3. Add message parsing and routing logic
4. Implement subscription confirmation messages
5. Implement error message handling
6. Add graceful disconnection handling
7. Register WebSocket route in `main.py`

**Acceptance Criteria:**
- WebSocket accepts connections with valid JWT tokens
- Rejects connections with invalid/expired tokens
- Parses and routes subscribe/unsubscribe messages
- Sends confirmation and error messages correctly

---

### Phase 5: WebSocket Integration with Webhooks

**Tasks:**
1. Integrate Part 2 transcription webhook with broadcast_transcription()
2. Integrate Part 3 post-call webhook with broadcast_call_completion()
3. Test end-to-end flow: webhook -> database -> WebSocket broadcast
4. Add error handling for broadcast failures
5. Add logging for broadcast events

**Acceptance Criteria:**
- New transcriptions broadcast to subscribed clients in real-time
- Call completions broadcast status + full data messages sequentially
- Webhook processing succeeds even if no clients subscribed
- Broadcast failures logged but don't break webhook processing

---

### Phase 6: Testing and Documentation

**Tasks:**
1. Write unit tests for Call model methods
2. Write unit tests for webhook endpoints
3. Write unit tests for WebSocketConnectionManager
4. Write integration tests for WebSocket subscription flow
5. Write end-to-end tests for complete webhook -> broadcast flow
6. Update API documentation with new endpoints
7. Create WebSocket client example code

**Acceptance Criteria:**
- All unit tests pass with >80% coverage
- Integration tests verify WebSocket functionality
- End-to-end tests simulate real ElevenLabs webhook flow
- Documentation includes request/response examples

---

## Testing Requirements

### Unit Tests

**models/call.py:**
- Test `update_post_call_data()` with all fields
- Test `update_post_call_data()` with conversation_id not found
- Test nullable field handling
- Test JSON serialization/deserialization

**services/webhooks_elevenlabs.py (post-call):**
- Test valid post_call_transcription webhook processing
- Test valid call_initiation_failure webhook processing
- Test invalid payload structure (400 error)
- Test conversation_id not found (404 error)
- Test database error handling (500 error)
- Test timestamp conversion to timezone-aware datetime
- Test JSON field parsing and storage

**services/websocket_calls.py (manager):**
- Test connection registration
- Test disconnection cleanup
- Test subscription with call_sid
- Test subscription with conversation_id
- Test subscription with invalid identifier
- Test unsubscribe functionality
- Test broadcast to single client
- Test broadcast to multiple clients
- Test broadcast with dead connection removal

---

### Integration Tests

**WebSocket Connection Flow:**
- Test WebSocket upgrade with valid JWT token
- Test WebSocket upgrade with invalid token (401 error)
- Test WebSocket upgrade with expired token (401 error)
- Test multiple concurrent connections from same user
- Test graceful disconnection

**Subscription Flow:**
- Test subscribe with call_sid for active call
- Test subscribe with conversation_id for active call
- Test subscribe with invalid identifier (error message)
- Test subscribe to multiple calls on same connection
- Test unsubscribe from call
- Test subscription confirmation message format

**Broadcasting Flow:**
- Test transcription broadcast to subscribed clients
- Test transcription broadcast with no subscribed clients
- Test call completion broadcast (status + data messages)
- Test broadcast to multiple clients for same call
- Test broadcast with dead connection handling

---

### End-to-End Tests

**Complete Transcription Flow:**
1. Create Call record with call_sid
2. Update with conversation_id
3. Connect WebSocket client and subscribe to call_sid
4. Simulate transcription webhook receipt
5. Verify WebSocket client receives transcription message
6. Verify transcription saved to database

**Complete Call Completion Flow:**
1. Create Call record and transcriptions
2. Connect WebSocket client and subscribe
3. Simulate post-call webhook receipt
4. Verify Call record updated with metadata
5. Verify WebSocket client receives call_status message
6. Verify WebSocket client receives call_completed message
7. Verify message order (status before data)

**Multi-Client Flow:**
1. Create active call
2. Connect 3 WebSocket clients
3. All clients subscribe to same call
4. Simulate transcription webhook
5. Verify all 3 clients receive transcription message
6. Disconnect 1 client
7. Simulate another transcription
8. Verify only 2 remaining clients receive message

---

## Deployment Considerations

### Migration Steps

1. **Database Migration:**
   - Apply Alembic migration to add new columns to `calls` table
   - Verify migration on staging environment first
   - Run migration during low-traffic window
   - No data backfill required (all fields nullable)

2. **Code Deployment:**
   - Deploy new code with Part 3 webhook endpoint
   - Deploy WebSocket infrastructure (Part 5)
   - Restart application servers
   - Verify webhook endpoint accessible from ElevenLabs

3. **ElevenLabs Configuration:**
   - Configure post-call webhook URL in ElevenLabs dashboard
   - Set webhook URL to: `https://<domain>/webhooks/elevenlabs/post-call`
   - Test webhook delivery with test call
   - Monitor webhook receipt logs

4. **Monitoring:**
   - Monitor webhook receipt logs for errors
   - Monitor WebSocket connection counts
   - Monitor database write performance
   - Set up alerts for webhook failures

---

### Rollback Strategy

**If Post-Call Webhook Issues:**
1. Disable webhook in ElevenLabs dashboard
2. Calls continue to work but completion data not stored
3. Fix issue and re-enable webhook
4. Lost completion data can be fetched via Part 4 (conversation fetch endpoint)

**If WebSocket Issues:**
1. WebSocket endpoint can be disabled without affecting core functionality
2. Frontend falls back to polling `/calls/{call_sid}/transcript` endpoint
3. Webhook processing continues to save data to database
4. Fix WebSocket issue and re-enable

**If Database Migration Issues:**
1. Rollback Alembic migration to remove new columns
2. Redeploy previous code version
3. Investigate migration issue
4. Re-apply migration after fix

**Zero Data Loss:**
- Webhook failures trigger ElevenLabs retry (up to 10 attempts)
- WebSocket failures don't affect data persistence
- All data saved to database regardless of WebSocket broadcast success
- Post-call data can be retrieved via conversation fetch endpoint if webhook fails

---

## Error Handling

### Webhook Error Scenarios

**Invalid Payload Structure:**
- Response: 400 Bad Request
- Log: Warning level with payload excerpt
- Action: ElevenLabs will retry (expected to fail again)

**Missing conversation_id:**
- Response: 400 Bad Request
- Log: Error level with full payload
- Action: ElevenLabs will retry, manual investigation needed

**Call Record Not Found:**
- Response: 404 Not Found
- Log: Error level with conversation_id
- Action: ElevenLabs will retry, check Part 1 call initiation logs

**Database Connection Error:**
- Response: 500 Internal Server Error
- Log: Error level with full traceback
- Action: ElevenLabs will retry, database should recover
- Alert: Trigger Sentry alert for database issues

**JSON Parsing Error:**
- Response: 500 Internal Server Error
- Log: Error level with malformed JSON
- Action: ElevenLabs will retry, manual investigation needed

---

### WebSocket Error Scenarios

**Authentication Failure:**
- Action: Reject WebSocket upgrade with 401 Unauthorized
- Message: Close connection immediately with error code 1008 (policy violation)
- Log: Warning level with attempted username

**Invalid Identifier Format:**
- Action: Send error message to client
- Message: `{"type": "error", "message": "Invalid identifier format", "code": "INVALID_IDENTIFIER"}`
- Log: Warning level with identifier value

**Call Not Found:**
- Action: Send error message to client
- Message: `{"type": "error", "message": "Call not found", "code": "CALL_NOT_FOUND"}`
- Log: Info level (expected scenario for invalid subscriptions)

**Broadcast Failure (Dead Connection):**
- Action: Remove connection from registry silently
- Log: Debug level with connection_id
- No alert: Expected during normal disconnections

**Message Parse Error:**
- Action: Send error message to client
- Message: `{"type": "error", "message": "Invalid message format", "code": "INVALID_MESSAGE_FORMAT"}`
- Log: Warning level with malformed message

**Connection Timeout:**
- Action: Close connection with code 1000 (normal closure)
- Log: Info level with connection duration
- Cleanup: Remove all subscriptions for that connection

---

## Future Enhancements

### Redis Pub/Sub for Horizontal Scaling

**Problem:** In-memory connection manager doesn't work across multiple server instances

**Solution:**
- Replace in-memory subscriptions with Redis Pub/Sub
- Each server instance subscribes to Redis channels for calls
- Webhook broadcasts message to Redis channel
- All servers with subscribed clients receive and forward message
- Allows unlimited horizontal scaling of WebSocket servers

**Implementation:**
- Add Redis client to application
- Create Redis channels: `call_updates:{call_sid}` and `call_updates:{conversation_id}`
- Webhook publishes to Redis instead of direct broadcast
- WebSocket manager subscribes to Redis channels
- Forwards Redis messages to local WebSocket connections

---

### Message Delivery Acknowledgments

**Problem:** No confirmation that client received message

**Solution:**
- Add message IDs to all server -> client messages
- Client sends acknowledgment: `{"ack": "message_id_123"}`
- Server tracks unacknowledged messages per connection
- Resend unacknowledged messages on reconnection

---

### Reconnection History Replay

**Problem:** Client disconnects and misses messages

**Solution:**
- Store recent messages in Redis with TTL (5 minutes)
- Client reconnects and sends last received sequence number
- Server replays missed messages from Redis cache
- Ensures client gets complete conversation history

---

### WebSocket Compression

**Problem:** Large transcript messages use bandwidth

**Solution:**
- Enable per-message-deflate WebSocket extension
- Compress messages over 1KB in size
- Reduces bandwidth usage for long conversations

---

### Admin Dashboard for WebSocket Monitoring

**Problem:** No visibility into active WebSocket connections

**Solution:**
- Create admin endpoint: `GET /admin/websockets/status`
- Returns: active connection count, subscriptions, memory usage
- Add metrics: messages sent, errors, disconnections
- Integrate with monitoring dashboard

---

### Rate Limiting per Client

**Problem:** Malicious client could subscribe to many calls

**Solution:**
- Add per-connection subscription limit (e.g., 10 calls max)
- Add rate limiting for subscribe/unsubscribe messages
- Reject new subscriptions over limit with error message

---

### Binary Message Support

**Problem:** JSON encoding overhead for large messages

**Solution:**
- Support binary WebSocket frames with MessagePack encoding
- Client negotiates protocol during connection
- Server detects and uses appropriate serialization
- Reduces message size by 30-50% for large payloads
