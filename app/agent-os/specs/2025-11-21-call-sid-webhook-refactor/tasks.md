# Task Breakdown: Call SID Webhook Refactor

## Overview

Total Tasks: 42 organized across 6 strategic task groups

This refactoring project changes the ElevenLabs call transcription webhook to use call_sid (our generated identifier) instead of conversation_id (ElevenLabs identifier) as the primary identifier. The key workflow change: Call records are created BEFORE making the ElevenLabs API call, not reactively on first webhook.

## Task List

### Database Schema Layer

#### Task Group 1: Database Migrations and Schema Changes
**Dependencies:** None

- [x] 1.0 Complete database schema migrations
  - [x] 1.1 Write 2-8 focused tests for migration backfill logic
    - Test backfill generates correct call_sid format: EL_{driver_id}_{timestamp}
    - Test backfill handles NULL driver_id with 'UNKNOWN' placeholder
    - Test backfill processes all existing records
    - Test unique constraint prevents duplicate call_sid values
    - Limit to critical backfill scenarios only
  - [x] 1.2 Create migration 001: Add call_sid column as nullable
    - File: `migrations/001_add_call_sid_column.py`
    - Add call_sid as VARCHAR(255), nullable=True
    - Schema: dev
    - Follow pattern from existing migrations
    - Include rollback procedure
  - [x] 1.3 Create migration 002: Backfill existing Call records
    - File: `migrations/002_backfill_call_sid.py`
    - Generate call_sid using format: EL_{driver_id}_{created_at_timestamp}
    - Use 'UNKNOWN' for NULL driver_id
    - Log count of backfilled records
    - Include rollback (set all call_sid to NULL)
  - [x] 1.4 Create migration 003: Add constraints and indexes
    - File: `migrations/003_add_call_sid_constraints.py`
    - Add NOT NULL constraint to call_sid
    - Add unique constraint: uq_calls_call_sid
    - Add single index: idx_calls_call_sid
    - Add compound index: idx_calls_call_sid_status
    - Include rollback procedures for all changes
  - [x] 1.5 Create migration 004: Make conversation_id nullable
    - File: `migrations/004_make_conversation_id_nullable.py`
    - Alter conversation_id to nullable=True
    - Allows Call creation before ElevenLabs responds
    - Include rollback (may fail if NULL values exist)
    - Document rollback limitations
  - [x] 1.6 Test all migrations in sequence
    - Run migrations 001 -> 004 in order
    - Verify database schema changes
    - Test rollback procedures (004 -> 001)
    - Verify indexes created correctly
    - Check backfill data quality

**Acceptance Criteria:**
- All 4 migration files created with upgrade/downgrade functions
- Backfill tests pass (2-8 tests)
- Migrations run successfully in sequence
- call_sid column is non-nullable with unique constraint
- Indexes created: idx_calls_call_sid, idx_calls_call_sid_status
- conversation_id is nullable
- Rollback procedures documented and tested

### Model Layer

#### Task Group 2: Call Model Updates
**Dependencies:** Task Group 1

- [x] 2.0 Complete Call model refactoring
  - [x] 2.1 Write 2-8 focused tests for new Call model methods
    - Test Call.create_call_with_call_sid() creates record with NULL conversation_id
    - Test Call.get_by_call_sid() retrieves correct record
    - Test Call.update_conversation_id() updates existing record
    - Test Call.update_status_by_call_sid() updates status and call_end_time
    - Test timezone-aware datetime handling
    - Limit to critical model behaviors only
  - [x] 2.2 Update Call model schema definition
    - File: `app/models/call.py`
    - Add field: call_sid (max_length=255, nullable=False, unique=True)
    - Change conversation_id to nullable=True
    - Update __table_args__ with new indexes
    - Add UniqueConstraint("call_sid", name="uq_calls_call_sid")
    - Add Index("idx_calls_call_sid", "call_sid")
    - Add Index("idx_calls_call_sid_status", "call_sid", "status")
    - Follow existing SQLModel pattern from Call model
  - [x] 2.3 Add Call.create_call_with_call_sid() class method
    - Parameters: call_sid, driver_id, call_start_time, status=IN_PROGRESS
    - Create Call with conversation_id=NULL initially
    - Apply @db_retry(max_retries=3) decorator
    - Use timezone-aware datetimes
    - Follow existing Call.create_call() pattern
    - Return created Call object
  - [x] 2.4 Add Call.get_by_call_sid() class method
    - Parameter: call_sid (string)
    - Query Call table with WHERE call_sid = ?
    - Apply @db_retry decorator
    - Return Optional[Call]
    - Follow existing Call.get_by_conversation_id() pattern
  - [x] 2.5 Add Call.update_conversation_id() class method
    - Parameters: call_sid, conversation_id
    - Lookup Call by call_sid
    - Update conversation_id and updated_at fields
    - Apply @db_retry decorator
    - Return updated Call object or None
    - Use timezone-aware datetime for updated_at
  - [x] 2.6 Add Call.update_status_by_call_sid() class method
    - Parameters: call_sid, status, call_end_time=None
    - Lookup Call by call_sid
    - Update status, optional call_end_time, and updated_at
    - Apply @db_retry decorator
    - Return updated Call object or None
    - Follow existing Call.update_status() pattern
  - [x] 2.7 Update Call model docstrings
    - Document call_sid field and purpose
    - Document conversation_id nullable behavior
    - Update class docstring with refactored workflow
    - Document all new class methods
  - [x] 2.8 Ensure Call model tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify create, get, and update methods work
    - Verify timezone handling
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- Call model tests pass (2-8 tests)
- call_sid field added with unique constraint
- conversation_id is nullable
- Four new class methods added with @db_retry decorator
- All methods use timezone-aware datetimes
- Docstrings updated
- CallTranscription model remains unchanged

### Helper Functions Layer

#### Task Group 3: Helper Function Refactoring
**Dependencies:** Task Group 2

- [x] 3.0 Complete helper function refactoring
  - [x] 3.1 Write 2-8 focused tests for refactored helpers
    - Test lookup_driver_id_by_call_sid() returns correct driver_id
    - Test get_conversation_id_from_call_sid() two-step lookup
    - Test get_conversation_id_from_call_sid() raises ValueError for NULL conversation_id
    - Test generate_sequence_number() with call_sid parameter
    - Test save_transcription() end-to-end with call_sid
    - Limit to critical helper behaviors only
  - [x] 3.2 Rename lookup_driver_id_by_conversation to lookup_driver_id_by_call_sid
    - File: `app/helpers/transcription_helpers.py`
    - Change parameter from conversation_id to call_sid
    - Update query: WHERE Call.call_sid = call_sid
    - Apply @db_retry decorator
    - Update logging to reference call_sid
    - Return Optional[int]
  - [x] 3.3 Add get_conversation_id_from_call_sid() helper function
    - File: `app/helpers/transcription_helpers.py`
    - Parameter: call_sid (string)
    - Implement two-step lookup: call_sid -> Call -> conversation_id
    - Return None if Call not found
    - Raise ValueError if Call exists but conversation_id is NULL
    - Apply @db_retry decorator
    - Add detailed logging for lookup failures
  - [x] 3.4 Update generate_sequence_number() to accept call_sid
    - Change parameter from conversation_id to call_sid
    - Use get_conversation_id_from_call_sid() for lookup
    - Raise ValueError if conversation_id not found
    - Count existing transcriptions for that conversation_id
    - Return sequence_number (count + 1)
    - Follow existing pattern with @db_retry decorator
  - [x] 3.5 Remove ensure_call_exists() function
    - Delete ensure_call_exists() entirely
    - No longer needed since Call created before API call
    - Document removal in migration notes
    - Update any imports/references
  - [x] 3.6 Update save_transcription() to accept call_sid
    - Change parameter from conversation_id to call_sid
    - Step 1: Call get_conversation_id_from_call_sid(call_sid)
    - Step 2: Raise ValueError if conversation_id is None
    - Step 3: Call generate_sequence_number(call_sid)
    - Step 4: Create CallTranscription with conversation_id FK
    - Update logging to reference both call_sid and conversation_id
    - Return tuple: (transcription_id, sequence_number)
    - Follow existing orchestration pattern
  - [x] 3.7 Update all helper docstrings
    - Document two-step lookup pattern
    - Update parameter descriptions (call_sid vs conversation_id)
    - Document error conditions and exceptions
    - Update function purpose statements
  - [x] 3.8 Ensure helper function tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify two-step lookup works correctly
    - Verify error handling for NULL conversation_id
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- Helper function tests pass (2-8 tests)
- lookup_driver_id_by_call_sid() uses call_sid parameter
- get_conversation_id_from_call_sid() implements two-step lookup with error handling
- generate_sequence_number() and save_transcription() use call_sid
- ensure_call_exists() removed
- All functions maintain @db_retry decorator
- Docstrings updated with new workflow

### Endpoint & Integration Layer

#### Task Group 4: Webhook Endpoint and Call Creation Updates
**Dependencies:** Task Group 3

- [x] 4.0 Complete webhook and call creation refactoring
  - [x] 4.1 Write 2-8 focused tests for endpoint changes
    - Test webhook accepts call_sid in request payload
    - Test webhook returns 400 for invalid call_sid
    - Test webhook returns 400 when Call has NULL conversation_id
    - Test end-to-end call creation workflow (create Call, call ElevenLabs, update conversation_id)
    - Test Call status updates to FAILED when ElevenLabs fails
    - Limit to critical endpoint behaviors only
  - [x] 4.2 Update TranscriptionWebhookRequest model
    - File: `app/services/webhooks_elevenlabs.py`
    - Change field from conversation_id to call_sid
    - Update Field description: "Generated call identifier (format: EL_{driverId}_{timestamp})"
    - Keep existing validators for speaker and timestamp
    - Update model docstring
  - [x] 4.3 Refactor receive_transcription() endpoint
    - Update parameter: request.call_sid instead of request.conversation_id
    - Call save_transcription(call_sid=request.call_sid, ...)
    - Add error handling for ValueError (Call not found or NULL conversation_id)
    - Return 400 Bad Request with descriptive message for lookup failures
    - Update all logging to reference call_sid
    - Update success response message to include call_sid
    - Maintain existing response format for compatibility
  - [x] 4.4 Update make_drivers_violation_batch_call_elevenlabs() workflow
    - File: `app/models/driver_data.py`
    - Step 1: Generate call_sid (existing code: EL_{driverId}_{timestamp})
    - Step 2: Create Call record using Call.create_call_with_call_sid()
    - Step 3: Handle Call creation failure with HTTPException 500
    - Step 4: Call ElevenLabs API with call_sid
    - Step 5: Update Call status to FAILED if API call fails
    - Step 6: Update Call with conversation_id if API succeeds
    - Step 7: Return response with both call_sid and conversation_id
    - Add comprehensive logging for each step
  - [x] 4.5 Update endpoint error handling
    - Add specific error messages for missing Call records
    - Add specific error messages for NULL conversation_id
    - Maintain existing database error handling
    - Log all errors with call_sid for traceability
  - [x] 4.6 Update endpoint docstrings and OpenAPI docs
    - Update receive_transcription() docstring with two-step lookup
    - Update make_drivers_violation_batch_call_elevenlabs() docstring
    - Update API response examples
    - Document new error conditions (400 for invalid call_sid)
  - [x] 4.7 Ensure endpoint tests pass
    - Run ONLY the 2-8 tests written in 4.1
    - Verify webhook accepts call_sid
    - Verify error handling for invalid call_sid
    - Verify end-to-end call creation workflow
    - Do NOT run entire test suite at this stage

**Acceptance Criteria:**
- Endpoint tests pass (2-8 tests)
- TranscriptionWebhookRequest accepts call_sid field
- Webhook returns 400 for invalid call_sid or NULL conversation_id
- Call records created BEFORE ElevenLabs API call
- Call status updated to FAILED if API fails
- conversation_id populated after successful API call
- All logging references call_sid
- Response formats maintained for backward compatibility

### Testing & Gap Analysis Layer

#### Task Group 5: Test Review and Integration Testing
**Dependencies:** Task Groups 1-4

- [x] 5.0 Review existing tests and fill critical gaps only
  - [x] 5.1 Review tests from Task Groups 1-4
    - Review migration tests (Task 1.1): approximately 2-8 tests
    - Review model tests (Task 2.1): approximately 2-8 tests
    - Review helper tests (Task 3.1): approximately 2-8 tests
    - Review endpoint tests (Task 4.1): approximately 2-8 tests
    - Total existing tests: approximately 8-32 tests
  - [x] 5.2 Analyze test coverage gaps for refactor feature only
    - Identify critical integration points lacking coverage
    - Focus on end-to-end workflows across all layers
    - Check coverage for error paths (failed API calls, NULL conversation_id)
    - Prioritize two-step lookup integration tests
    - DO NOT assess entire application coverage
  - [x] 5.3 Write up to 10 additional strategic tests maximum
    - Integration test: Full call lifecycle (create, call API, receive webhook, save transcription)
    - Integration test: Failed ElevenLabs call updates Call status correctly
    - Integration test: Webhook with NULL conversation_id returns 400
    - Performance test: Two-step lookup with compound index is efficient
    - Migration integration: Backfilled records work in webhook flow
    - DO NOT write comprehensive coverage for all scenarios
    - Skip redundant unit tests already covered in groups 1-4
  - [x] 5.4 Run feature-specific tests only
    - Run migration tests (1.1)
    - Run model tests (2.1)
    - Run helper tests (3.1)
    - Run endpoint tests (4.1)
    - Run additional integration tests (5.3)
    - Expected total: approximately 18-42 tests maximum
    - DO NOT run entire application test suite
    - Verify all critical workflows pass

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 18-42 tests total)
- Critical integration workflows covered
- End-to-end call lifecycle tested
- Two-step lookup pattern validated
- Error handling tested (failed API, NULL conversation_id)
- No more than 10 additional tests added in gap analysis
- Testing focused exclusively on call_sid refactor feature

### Deployment & Integration Layer

#### Task Group 6: Deployment and ElevenLabs Integration
**Dependencies:** Task Group 5

- [x] 6.0 Complete deployment and integration updates
  - [x] 6.1 Document deployment procedure
    - Create deployment checklist
    - Document migration order (001 -> 002 -> 003 -> 004)
    - Document rollback procedures for each migration
    - Document ElevenLabs webhook configuration update steps
    - Include timing recommendations (low-traffic period)
    - Create troubleshooting guide
  - [x] 6.2 Test migrations in staging environment
    - Run all 4 migrations in sequence
    - Verify backfill data quality
    - Check indexes created correctly
    - Test rollback procedures
    - Verify existing functionality unaffected
  - [x] 6.3 Deploy code to staging environment
    - Deploy updated Call model
    - Deploy updated helper functions
    - Deploy updated webhook endpoint
    - Deploy updated call creation flow
    - Verify application starts successfully
  - [x] 6.4 Test end-to-end workflow in staging
    - Create test call using make_drivers_violation_batch_call_elevenlabs()
    - Verify Call record created BEFORE API call
    - Verify conversation_id populated after API success
    - Send test webhook with call_sid
    - Verify transcription saved correctly
    - Check two-step lookup performance
  - [x] 6.5 Prepare ElevenLabs webhook configuration
    - Create new webhook payload JSON with call_sid field
    - Remove conversation_id from payload
    - Document webhook update API call
    - Prepare rollback configuration (restore conversation_id)
    - Test webhook configuration in ElevenLabs dashboard/API
  - [x] 6.6 Execute production deployment
    - Run migrations during low-traffic period
    - Deploy code to production
    - Monitor logs for migration errors
    - Verify application health
    - Update ElevenLabs webhook configuration
    - Send single test call to verify webhook
  - [x] 6.7 Monitor and validate production deployment
    - Monitor first 10-20 production calls
    - Verify Call records created before API calls
    - Verify webhooks receive call_sid correctly
    - Check error rates and response times
    - Verify database index usage with EXPLAIN queries
    - Confirm backfilled records work correctly
  - [x] 6.8 Update documentation
    - Update CLAUDE.md with refactored workflow
    - Document call_sid generation format
    - Document two-step lookup pattern
    - Update API documentation for webhook endpoint
    - Document rollback procedures
    - Create troubleshooting guide for common issues

**Acceptance Criteria:**
- Migrations run successfully in staging and production
- Code deployed without errors
- End-to-end workflow tested in staging
- ElevenLabs webhook configuration updated
- Production calls work correctly with call_sid
- No regression in existing functionality
- Monitoring confirms proper operation
- Documentation updated with new workflow

## Execution Order

Recommended implementation sequence:

1. **Database Schema Layer** (Task Group 1)
   - Create all 4 migrations with rollback procedures
   - Test migrations in development environment
   - Verify backfill logic handles NULL driver_id

2. **Model Layer** (Task Group 2)
   - Update Call model schema
   - Add 4 new class methods
   - Test model methods independently

3. **Helper Functions Layer** (Task Group 3)
   - Refactor helper functions to use call_sid
   - Implement two-step lookup pattern
   - Remove ensure_call_exists()

4. **Endpoint & Integration Layer** (Task Group 4)
   - Update webhook endpoint to accept call_sid
   - Refactor call creation workflow
   - Test error handling

5. **Testing & Gap Analysis Layer** (Task Group 5)
   - Review all tests from groups 1-4
   - Add strategic integration tests
   - Validate end-to-end workflows

6. **Deployment & Integration Layer** (Task Group 6)
   - Deploy to staging and validate
   - Execute production deployment
   - Update ElevenLabs webhook configuration
   - Monitor and document

## Important Notes

### Testing Constraints
- Each development task group (1-4) writes 2-8 focused tests maximum
- Task Group 5 adds maximum 10 additional integration tests
- Total expected tests: approximately 18-42 tests
- Test verification runs ONLY feature-specific tests, not entire suite
- Focus on critical workflows, skip exhaustive coverage

### Database Considerations
- Migrations must run in exact order: 001 -> 002 -> 003 -> 004
- Backfill migration handles NULL driver_id with 'UNKNOWN' placeholder
- Run migrations during low-traffic period to minimize impact
- All migrations include rollback/downgrade procedures
- conversation_id nullable allows Call creation before API response

### Workflow Changes
- **Old flow**: Generate call_sid -> Call ElevenLabs -> Webhook creates Call
- **New flow**: Generate call_sid -> Create Call -> Call ElevenLabs -> Update Call -> Webhook uses call_sid
- Call records now exist for ALL call attempts (including failures)
- Two-step lookup: call_sid -> Call -> conversation_id maintains referential integrity

### Integration Points
- ElevenLabs webhook configuration must be updated AFTER code deployment
- Webhook payload changes from conversation_id to call_sid
- ElevenLabs echoes back the call_sid we provide in create_outbound_call()
- CallTranscription model remains unchanged (still uses conversation_id FK)

### Error Handling
- Call creation failure raises HTTPException 500
- ElevenLabs API failure updates Call status to FAILED
- Webhook returns 400 if call_sid not found
- Webhook returns 400 if Call exists but conversation_id is NULL
- All database operations use @db_retry decorator for resilience

### Performance
- Indexes ensure two-step lookup remains efficient
- idx_calls_call_sid for fast call_sid lookups
- idx_calls_call_sid_status for status queries
- Existing conversation_id indexes maintained for transcription queries
- Monitor index usage with EXPLAIN queries post-deployment

### Rollback Procedures
- Migrations can be rolled back in reverse order (4 -> 3 -> 2 -> 1)
- Migration 004 rollback may fail if NULL conversation_id values exist
- ElevenLabs webhook can be reverted to conversation_id payload
- Code deployment can be reverted to previous version
- Document all rollback steps before production deployment
