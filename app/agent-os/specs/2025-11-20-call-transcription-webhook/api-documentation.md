# API Documentation: Call Transcription Webhook

## Overview

The call transcription webhook endpoint receives real-time dialogue transcriptions from ElevenLabs conversational AI calls.

## Endpoint

POST /webhooks/elevenlabs/transcription

- Public endpoint (no authentication required)
- Returns 201 Created on success
- Returns 400/422 for validation errors
- Returns 500 for server errors

## Request Format

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| conversation_id | string | Yes | ElevenLabs conversation identifier |
| speaker | string | Yes | Speaker attribution ("agent" or "user") |
| message | string | Yes | The dialogue message text |
| timestamp | string | Yes | ISO8601 timestamp |

### Example Request

```json
{
  "conversation_id": "conv_abc123xyz",
  "speaker": "agent",
  "message": "Hello, this is dispatch calling.",
  "timestamp": "2025-01-15T10:30:45.123456Z"
}
```

## Response Formats

### Success Response (201 Created)

```json
{
  "status": "success",
  "message": "Transcription saved successfully",
  "transcription_id": 12345,
  "sequence_number": 1
}
```

### Validation Error (422)

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "conversation_id"],
      "msg": "Field required"
    }
  ]
}
```

### Bad Request (400)

```json
{
  "status": "error",
  "message": "Invalid request data",
  "details": "Invalid speaker value"
}
```

### Internal Server Error (500)

```json
{
  "status": "error",
  "message": "Database connection error. Please retry.",
  "details": "Database temporarily unavailable"
}
```

## Behavior Notes

### Call Initialization

- First dialogue creates Call record automatically
- call_start_time set from first dialogue timestamp
- status initially set to "in_progress"
- driver_id looked up from existing records (may be NULL)

### Speaker Mapping

- "user" maps to "driver" internally
- "agent" maps to "agent" internally

### Sequence Numbers

- Auto-generated as COUNT + 1 per conversation
- ElevenLabs guarantees sequential webhooks per conversation

### Error Handling

- Never returns 200 OK on failure
- Allows ElevenLabs to retry failed requests
- All errors logged with conversation_id

### Timezone Handling

- All timestamps stored as timezone-aware UTC
- ISO8601 format with Z suffix or +00:00

## Example Conversation Flow

### First Dialogue

Request:
```json
{
  "conversation_id": "conv_001",
  "speaker": "agent",
  "message": "Hello, this is dispatch.",
  "timestamp": "2025-01-15T14:30:00Z"
}
```

Response:
```json
{
  "status": "success",
  "transcription_id": 100,
  "sequence_number": 1
}
```

### Second Dialogue

Request:
```json
{
  "conversation_id": "conv_001",
  "speaker": "user",
  "message": "Yes, this is John.",
  "timestamp": "2025-01-15T14:30:05Z"
}
```

Response:
```json
{
  "status": "success",
  "transcription_id": 101,
  "sequence_number": 2
}
```

## Integration Points

- Call model: Stores conversation metadata
- CallTranscription model: Stores dialogue turns
- Foreign key: CallTranscription.conversation_id -> Call.conversation_id

## Performance

- No authentication for speed
- Database connection pooling
- Automatic retry with @db_retry
- Indexed queries on conversation_id

## Monitoring

Key log patterns:
- INFO: Transcription webhook received
- INFO: Driver lookup successful/failed
- INFO: Transcription saved successfully
- ERROR: Database connection error
