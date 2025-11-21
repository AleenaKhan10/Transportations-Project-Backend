# Spec Requirements: ElevenLabs Completion Webhook and WebSocket Features

## Initial Description

We need to complete the ElevenLabs integration by implementing two remaining parts:

**Part 3: Call Completion Webhook (`webhooks/elevenlabs/post-call/`)**
- Agent will call this webhook when the call is completed
- Update the Call status to COMPLETED in the database
- Reference documentation: https://elevenlabs.io/docs/agents-platform/workflows/post-call-webhooks.md

**Part 5: WebSocket for Real-time Interaction**
- Establish WebSocket connection for real-time transcription delivery
- Receive transcription data from Part 2 (webhooks/elevenlabs/transcription)
- Push transcription data to frontend clients in real-time
- Enable live conversation monitoring

**Context - Already Completed:**
- Part 1: Call initialization endpoint (call-elevenlabs/) - returns conversation_id and call_sid
- Part 2: Custom tool call webhook (webhooks/elevenlabs/transcription) - receives transcription per dialogue turn
- Part 4: Conversation fetching endpoint (/conversations/{conversation_id}/fetch) - fetches complete conversation history

## Requirements Discussion

### First Round Questions

**Q1:** For the WebSocket endpoint, should we use a single endpoint with subscription/topic system (Option C), separate endpoints per identifier (Option A), or query parameter differentiation (Option B)?

**Answer:** Option C - Single endpoint with subscription/topic system
- Connect to `/ws/calls/transcriptions`
- Client sends subscription messages after connecting (e.g., `{"subscribe": "call_sid_123"}` or `{"subscribe": "conversation_id_123"}`)

**Q2:** For storing post-call webhook metadata (analysis, transcript summary, costs, duration, etc.), should we create a new CallMetadata model (Option A), extend the existing Call model with new JSON/text fields (Option B), or store in both places (Option C)?

**Answer:** Option B - Extend existing Call model with new JSON/text fields for metadata
- Add fields to store webhook payload data

**Q3:** When a call completes, should the WebSocket send just a status message (Option A), full data in one message (Option B), or both sequentially (Option C)?

**Answer:** Option C - Both
- Send status message first
- Then send optional full data in separate message

**Q4:** For the WebSocket URL pattern, should we support both call_sid and conversation_id as identifiers with auto-detection (equally), or prefer one over the other?

**Answer:** Auto-detect equally
- Treat both call_sid and conversation_id equally
- Auto-detect which identifier was provided

**Q5:** For WebSocket authentication, should we use Bearer token in Authorization header during upgrade (Option A), token as query parameter (Option B), or initial message-based authentication (Option C)?

**Answer:** Option A - `Authorization: Bearer <token>` header during WebSocket upgrade

**Q6:** Are there any features or capabilities we should explicitly exclude from this implementation to keep scope manageable?

**Answer:** No specific exclusions mentioned by user.

### Existing Code to Reference

**Similar Features Identified:**

Based on the codebase analysis, the following existing code should be referenced:

- **Existing webhook pattern**: `services/webhooks_elevenlabs.py` - Implements transcription webhook with error handling, validation, and logging patterns
- **Call model**: `models/call.py` - Contains Call model with call_sid/conversation_id tracking, status management, and class methods
- **CallTranscription model**: `models/call_transcription.py` - Stores dialogue turns with speaker attribution and sequencing
- **Authentication pattern**: `logic/auth/security.py` - JWT token validation for protected endpoints
- **Database retry pattern**: `db/retry.py` - `@db_retry` decorator for resilient database operations

### Follow-up Questions

No follow-up questions needed. User provided clear, specific answers to all questions.

## Visual Assets

### Files Provided:

No visual assets provided.

### Visual Insights:

No visual insights available.

## Requirements Summary

### Functional Requirements

**Part 3: Post-Call Webhook**

1. **Endpoint**: POST `/webhooks/elevenlabs/post-call`
   - Public endpoint (no authentication for performance)
   - Receives webhook from ElevenLabs when call analysis is complete

2. **Webhook Payload Processing**:
   - Accept ElevenLabs post-call transcription webhook payload
   - Extract conversation_id from payload
   - Look up Call record by conversation_id
   - Update Call record with:
     - status = COMPLETED
     - call_end_time = extracted from payload metadata
     - Store additional metadata fields (see Database Schema Changes)

3. **HMAC Signature Validation** (Optional Security Enhancement):
   - Validate ElevenLabs-Signature header format: `t=timestamp,v0=hash`
   - Verify timestamp within 30-minute tolerance
   - Verify HMAC SHA256 signature of `timestamp.request_body`
   - Note: Can be implemented in future iteration if needed

4. **Error Handling**:
   - Return 200 OK only on successful processing
   - Return 400 Bad Request for invalid payload or missing conversation_id
   - Return 404 Not Found if Call record doesn't exist
   - Return 500 Internal Server Error for database failures
   - Never return 200 on failure to allow ElevenLabs retry

5. **Logging**:
   - Structured logging with conversation_id, status updates, errors
   - Follow existing webhook logging patterns from transcription webhook

**Part 5: Real-time WebSocket System**

1. **WebSocket Endpoint**: `/ws/calls/transcriptions`
   - Single endpoint with subscription-based routing
   - Accepts both call_sid and conversation_id with auto-detection
   - JWT authentication via Authorization header during upgrade

2. **Connection Management**:
   - Authenticate client via Bearer token in WebSocket upgrade request
   - Maintain active connections in memory with connection registry
   - Handle graceful disconnections and cleanup
   - Support multiple simultaneous subscriptions per client

3. **Subscription Protocol**:
   - After connection, client sends subscription message:
     ```json
     {"subscribe": "call_sid_123"}
     ```
     or
     ```json
     {"subscribe": "conversation_id_abc"}
     ```
   - Server validates identifier and resolves to Call record
   - Auto-detect whether identifier is call_sid or conversation_id
   - Allow multiple subscriptions per connection

4. **Real-time Transcription Broadcasting**:
   - When transcription webhook receives new dialogue turn:
     - Save to database (existing behavior)
     - Identify subscribed WebSocket clients for that conversation
     - Broadcast transcription message to all subscribed clients
   - Message format:
     ```json
     {
       "type": "transcription",
       "conversation_id": "abc123",
       "call_sid": "EL_driver1_timestamp",
       "transcription_id": 456,
       "sequence_number": 3,
       "speaker_type": "agent",
       "message_text": "Hello, how are you?",
       "timestamp": "2025-11-21T10:30:00Z"
     }
     ```

5. **Call Completion Broadcasting**:
   - When post-call webhook completes:
     - Send status update message first:
       ```json
       {
         "type": "call_status",
         "conversation_id": "abc123",
         "call_sid": "EL_driver1_timestamp",
         "status": "completed",
         "call_end_time": "2025-11-21T10:35:00Z"
       }
       ```
     - Then send full call data message:
       ```json
       {
         "type": "call_completed",
         "conversation_id": "abc123",
         "call_sid": "EL_driver1_timestamp",
         "call_data": {
           "status": "completed",
           "call_start_time": "2025-11-21T10:30:00Z",
           "call_end_time": "2025-11-21T10:35:00Z",
           "duration_seconds": 300,
           "transcript_summary": "Driver confirmed delivery...",
           "cost": 0.05,
           "metadata": {...}
         }
       }
       ```

6. **Error Handling**:
   - Send error messages to client for failed subscriptions
   - Handle invalid identifiers gracefully
   - Auto-cleanup stale connections
   - Implement connection heartbeat/ping-pong for keepalive

7. **Unsubscribe Support**:
   - Allow clients to unsubscribe from conversations:
     ```json
     {"unsubscribe": "call_sid_123"}
     ```

### Database Schema Changes

**Extend Call Model** (models/call.py):

Add the following fields to store post-call webhook metadata:

```python
# Post-call webhook metadata fields
transcript_summary: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
call_duration_seconds: Optional[int] = Field(default=None, nullable=True)
cost: Optional[float] = Field(default=None, nullable=True)
call_successful: Optional[bool] = Field(default=None, nullable=True)
analysis_data: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))  # JSON string
metadata_json: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))  # JSON string
```

**Add Class Method to Call Model**:

```python
@classmethod
@db_retry(max_retries=3)
def update_post_call_data(
    cls,
    conversation_id: str,
    call_end_time: datetime,
    transcript_summary: Optional[str] = None,
    call_duration_seconds: Optional[int] = None,
    cost: Optional[float] = None,
    call_successful: Optional[bool] = None,
    analysis_data: Optional[str] = None,
    metadata_json: Optional[str] = None
) -> Optional["Call"]:
    """
    Update Call record with post-call webhook data.

    Args:
        conversation_id: ElevenLabs conversation identifier
        call_end_time: Timezone-aware UTC datetime when call ended
        transcript_summary: Optional summary of conversation
        call_duration_seconds: Optional call duration in seconds
        cost: Optional cost in dollars
        call_successful: Optional boolean indicating call success
        analysis_data: Optional JSON string of analysis results
        metadata_json: Optional JSON string of full metadata

    Returns:
        Updated Call object if found, None otherwise
    """
```

**Migration Required**:
- Create Alembic migration to add new columns to calls table
- All new fields should be nullable (backward compatible)

### Reusability Opportunities

1. **Webhook Authentication Pattern**: If implementing HMAC validation, create reusable middleware/decorator that can be applied to any webhook endpoint requiring signature verification

2. **WebSocket Connection Manager**: Create reusable WebSocketManager class that can be used for other real-time features in the future

3. **Subscription System**: The subscription/topic pattern can be extended to other entities (drivers, trips, alerts) beyond just calls

4. **Broadcast Helper**: Create generic broadcast utility that takes a set of connection IDs and message, abstracting the WebSocket send logic

### Scope Boundaries

**In Scope:**

1. POST `/webhooks/elevenlabs/post-call` endpoint
2. Call model extension with metadata fields
3. Database migration for new fields
4. Update Call status to COMPLETED
5. WebSocket endpoint `/ws/calls/transcriptions`
6. JWT authentication for WebSocket connections
7. Subscription-based routing for both call_sid and conversation_id
8. Real-time broadcasting of new transcriptions
9. Call completion status and data broadcasting
10. Unsubscribe functionality
11. Connection management and cleanup
12. Error handling and logging

**Out of Scope:**

1. HMAC signature validation for post-call webhook (can be added later)
2. WebSocket rate limiting or throttling
3. Message delivery guarantees (at-least-once, exactly-once)
4. Persistent message queue for offline clients
5. WebSocket connection pooling/clustering for horizontal scaling
6. Message history replay on reconnection
7. Binary WebSocket messages (text/JSON only)
8. Compression (per-message-deflate)
9. Frontend implementation (WebSocket client code)

### Technical Considerations

**Integration Points:**

1. **Existing Transcription Webhook**: The WebSocket system must integrate with the existing `/webhooks/elevenlabs/transcription` endpoint to broadcast new transcriptions in real-time

2. **Call Model**: Both webhook and WebSocket features depend on the Call model and must use existing class methods where possible

3. **Authentication System**: WebSocket authentication must use existing JWT validation from `logic/auth/security.py`

4. **Database Retry Logic**: All database operations must use `@db_retry` decorator for resilience

**Technology Stack:**

- FastAPI WebSocket support (built-in)
- Python asyncio for concurrent connection handling
- PostgreSQL for Call model persistence
- SQLModel ORM for database operations
- JWT tokens for WebSocket authentication
- JSON for all message payloads

**Performance Considerations:**

1. **Connection Scaling**: In-memory connection registry limits horizontal scaling. Consider Redis Pub/Sub for multi-instance deployments (future enhancement)

2. **Database Load**: Each transcription triggers database write + WebSocket broadcast. Ensure indexes on conversation_id and call_sid remain performant

3. **Message Size**: Full call_data messages may be large. Consider pagination or selective field inclusion

4. **Broadcast Efficiency**: Filter subscribed connections efficiently to avoid iterating all connections on every message

**Existing System Constraints:**

1. **Authentication**: Must be compatible with existing JWT token system (24-hour expiration)

2. **Database Schema**: `dev` schema in PostgreSQL must be used

3. **Timezone Handling**: All timestamps must be timezone-aware UTC

4. **Error Tracking**: Integrate with Sentry/GlitchTip for WebSocket errors

5. **Logging**: Follow existing structured logging patterns with cloud_logger.py

**Similar Code Patterns to Follow:**

1. **Webhook Pattern**: Follow the structure of `services/webhooks_elevenlabs.py` for request validation, error responses, and logging

2. **Model Methods**: Follow Call model patterns for database operations with `@db_retry` decorator

3. **Router Registration**: Register WebSocket router in `main.py` following existing patterns

4. **Timezone Utilities**: Use `utc_now()` and `make_timezone_aware()` from `logic/auth/service.py`

**ElevenLabs Webhook Specifications:**

- **Webhook Type**: `post_call_transcription` (type field in payload)
- **HTTP Method**: POST
- **Payload Fields**:
  - `type`: "post_call_transcription"
  - `event_timestamp`: Unix timestamp (UTC)
  - `data.agent_id`: Agent identifier
  - `data.conversation_id`: Conversation identifier
  - `data.status`: "done"
  - `data.transcript`: Array of conversation turns
  - `data.metadata`: Call timing, costs, phone details
  - `data.analysis`: Evaluation results, summary, success status
  - `data.metadata.start_time_unix_secs`: Call start time
  - `data.metadata.call_duration_secs`: Duration in seconds
  - `data.metadata.cost`: Cost in dollars
  - `data.analysis.call_successful`: Boolean success flag
  - `data.analysis.transcript_summary`: Text summary
- **Retry Behavior**: Must return 200 OK for success; non-200 triggers retry
- **Auto-disable**: 10+ consecutive failures over 7 days

**WebSocket Message Types Summary:**

1. **Subscription Request** (client -> server):
   ```json
   {"subscribe": "identifier"}
   ```

2. **Unsubscribe Request** (client -> server):
   ```json
   {"unsubscribe": "identifier"}
   ```

3. **Transcription Message** (server -> client):
   ```json
   {"type": "transcription", ...transcription data...}
   ```

4. **Call Status Message** (server -> client):
   ```json
   {"type": "call_status", ...status data...}
   ```

5. **Call Completed Message** (server -> client):
   ```json
   {"type": "call_completed", ...full call data...}
   ```

6. **Error Message** (server -> client):
   ```json
   {"type": "error", "message": "error description"}
   ```
