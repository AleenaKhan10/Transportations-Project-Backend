# Implementation Notes: Call Transcription Webhook

## Overview
Key implementation decisions and technical details for the call transcription webhook feature.

## Driver Lookup Logic
- Queries Call table using conversation_id to find driver_id
- Returns None if no matching record or NULL driver_id
- Graceful degradation - NULL driver_id is acceptable

## Sequence Number Generation
- Algorithm: COUNT(existing transcriptions) + 1
- Starts at 1 for first transcription
- No locks needed (ElevenLabs guarantees sequential calls)

## Speaker Mapping Rules
- "user" maps to "driver" (ElevenLabs calls driver "user")
- "agent" maps to "agent"
- ValueError raised for invalid values

## Call Initialization Flow
- First dialogue creates Call record automatically
- call_start_time from first dialogue timestamp
- status set to "in_progress"
- driver_id from lookup (may be NULL)
- Idempotent - subsequent calls return existing Call

## Error Handling Strategy
- Never return 200 OK on failure (allows ElevenLabs retry)
- Validation errors return 400/422 with details
- Database errors return 500 with generic message
- @db_retry decorator provides automatic retry (3 attempts)

## Timezone Handling
- All timestamps stored as timezone-aware UTC
- Input: ISO8601 format with Z suffix
- make_timezone_aware() ensures consistency
- UTC everywhere approach

## ElevenLabs Integration Assumptions
- Sequential webhook calls per conversation_id guaranteed
- No concurrent webhooks for same conversation
- Webhooks retried on non-200 responses
- conversation_id unique per call

## Database Schema
- Call: conversation_id unique constraint, indexed
- CallTranscription: Foreign key to Call.conversation_id
- Text field for message_text (unlimited length)
- Composite index on (conversation_id, sequence_number)
- No cascade delete (prevents accidental data loss)

## Performance Optimizations
- Connection pooling (pool_size=10, max_overflow=20)
- Indexed queries on conversation_id
- No authentication (public endpoint for performance)
- Structured logging with conversation_id

## Testing
- 27 unit tests (models, helpers, API)
- 5 integration tests (end-to-end workflows)
- Total: 32 tests focused on critical paths

## Deployment
- Tables created automatically via SQLModel
- Router registered in main.py
- No new configuration required
