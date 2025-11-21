# Specification: Call SID Webhook Refactor

## Goal
Refactor the ElevenLabs call transcription webhook system to use call_sid as the primary identifier for incoming webhook requests, enabling proactive Call record creation before API calls and improving call tracking throughout the entire lifecycle.

## User Stories
- As a system administrator, I want Call records created before ElevenLabs API calls so that I can track all call attempts including failures
- As a developer, I want webhooks to use call_sid instead of conversation_id so that call tracking is consistent and predictable from initiation to completion

## Specific Requirements

**Add call_sid field to Call model**
- Add call_sid as non-nullable string field with max_length=255
- Add unique constraint on call_sid to prevent duplicates
- Add single column index idx_calls_call_sid for fast lookups
- Add compound index idx_calls_call_sid_status for status queries
- Make conversation_id nullable to support Call creation before ElevenLabs responds
- Keep both call_sid and conversation_id fields for backward compatibility

**Backfill existing Call records**
- Create migration to add call_sid column as nullable initially
- Generate call_sid for existing records using format: EL_{driver_id}_{created_at_timestamp}
- Use 'UNKNOWN' placeholder for records with NULL driver_id
- Run backfill during low-traffic period to minimize impact
- Add NOT NULL constraint after backfill completes
- Verify all existing records have call_sid before deploying code changes

**Create Call records before ElevenLabs API call**
- Generate call_sid in make_drivers_violation_batch_call_elevenlabs using format: EL_{driverId}_{timestamp}
- Create Call record with call_sid, driver_id, call_start_time, and status=IN_PROGRESS
- Initial Call has conversation_id=NULL until ElevenLabs responds
- If Call creation fails, raise HTTPException with 500 status
- Update Call status to FAILED if ElevenLabs API call fails
- Update Call with conversation_id after successful ElevenLabs response
- Preserve audit trail for all call attempts regardless of outcome

**Add new Call model class methods**
- create_call_with_call_sid: Create Call before ElevenLabs call with call_sid, driver_id, call_start_time, status
- get_by_call_sid: Retrieve Call by call_sid for webhook lookups
- update_conversation_id: Update Call with conversation_id from ElevenLabs response
- update_status_by_call_sid: Update Call status and optional call_end_time by call_sid
- All methods use @db_retry decorator for database resilience
- All methods return timezone-aware UTC datetimes

**Refactor webhook to accept call_sid**
- Change TranscriptionWebhookRequest to accept call_sid instead of conversation_id
- Implement two-step lookup: call_sid -> Call -> conversation_id
- Return 400 Bad Request if Call record not found for call_sid
- Return 400 Bad Request if Call exists but conversation_id is NULL
- Update all logging to reference call_sid instead of conversation_id
- Update response messages to include call_sid
- Maintain existing response format for backward compatibility

**Update helper functions for call_sid workflow**
- Rename lookup_driver_id_by_conversation to lookup_driver_id_by_call_sid
- Add get_conversation_id_from_call_sid for two-step lookup pattern
- Update generate_sequence_number to accept call_sid and internally lookup conversation_id
- Remove ensure_call_exists function (no longer needed since Call created proactively)
- Update save_transcription to accept call_sid parameter instead of conversation_id
- All helper functions maintain @db_retry decorator for resilience

**Maintain CallTranscription model unchanged**
- Keep conversation_id as foreign key to Call.conversation_id
- No changes to CallTranscription model structure or indexes
- Two-step lookup pattern: webhook receives call_sid, looks up Call to get conversation_id, saves CallTranscription with conversation_id FK
- Avoids data duplication by not adding call_sid to CallTranscription table
- Existing indexes on conversation_id remain for optimal query performance

**Update ElevenLabs webhook configuration**
- Modify webhook payload to send call_sid instead of conversation_id
- ElevenLabs echoes back the call_sid we provide in create_outbound_call request
- Update webhook configuration after code deployment completes
- Test webhook with single test call before enabling for all traffic
- Document rollback procedure for webhook configuration

**Implement comprehensive testing**
- Unit tests for all new Call model class methods
- Unit tests for updated helper functions
- Integration test for end-to-end call creation workflow
- Migration test for backfill logic with NULL driver_id handling
- Webhook test with valid call_sid
- Webhook test with invalid call_sid returning 400
- Performance test for two-step lookup with compound indexes

**Create migration scripts**
- Migration 001: Add call_sid column as nullable
- Migration 002: Backfill existing records with generated call_sid
- Migration 003: Add NOT NULL constraint and indexes on call_sid
- Migration 004: Make conversation_id nullable
- All migrations include rollback/downgrade procedures
- Migrations follow zero-downtime deployment patterns

## Visual Design
No visual assets provided for this backend refactoring project.

## Existing Code to Leverage

**Call model class methods pattern**
- Existing Call.get_by_conversation_id() pattern should be replicated for get_by_call_sid()
- Existing Call.create_call() pattern should be extended for create_call_with_call_sid()
- Existing Call.update_status() pattern should be replicated for update_status_by_call_sid()
- All existing methods use @db_retry decorator and Session context manager pattern
- Follow existing pattern of returning Optional[Call] for lookup methods

**Database retry decorator from db/retry.py**
- Apply @db_retry(max_retries=3) to all new database operations
- Follows existing pattern used in Call and CallTranscription models
- Ensures resilience against transient database connection failures
- Used in all helper functions and model class methods

**Timezone handling from logic/auth/service.py**
- Use make_timezone_aware() for all datetime objects before database storage
- Use datetime.now(timezone.utc) for generating current timestamps
- Follows existing pattern in Call and CallTranscription models
- Ensures consistency across all timezone-aware datetime fields

**SQLModel table pattern with indexes**
- Use __table_args__ tuple for UniqueConstraint and Index definitions
- Follow existing pattern in Call model for conversation_id indexes
- Add {"extend_existing": True} to __table_args__ for compatibility
- Use Field with sa_column=Column(DateTime(timezone=True)) for datetime fields

**ElevenLabs call_sid generation in models/driver_data.py**
- Existing format: EL_{driver.driverId}_{request.timestamp}
- Already generated at line 1226 but not stored in database
- Reuse exact same generation logic for consistency
- call_sid already passed to elevenlabs_client.create_outbound_call()

## Out of Scope
- Changes to VAPI integration or VAPI-related models
- Frontend changes or UI updates for call tracking
- Real-time call monitoring dashboard modifications
- Analytics or reporting feature enhancements
- Changes to other webhook endpoints beyond ElevenLabs transcription
- Migration to different AI provider or telephony system
- Modifications to CallTranscription model structure
- Changes to existing conversation_id-based queries outside webhook flow
- Performance optimization beyond required indexes
- Automated testing infrastructure setup
