# Spec Requirements: Call SID Webhook Refactor

## Initial Description

Refactor the ElevenLabs call transcription webhook system to use call_sid as the primary identifier instead of conversation_id. This change will enable better call tracking, improve the call creation workflow by establishing Call records before making API calls, and maintain backward compatibility during the transition while cleaning up the codebase.

## Requirements Discussion

### First Round Questions

**Q1:** Should call_sid be an additional field (keep conversation_id) or replace conversation_id entirely?
**Answer:** ADD call_sid as an additional field (keep conversation_id). Both identifiers should coexist in the Call model.

**Q2:** Does the webhook need to accept both call_sid and conversation_id during migration, or only call_sid?
**Answer:** Webhook accepts only call_sid. No transition period needed - clean switch.

**Q3:** How should call_sid be generated? Should we use the existing format from make_drivers_violation_batch_call_elevenlabs (EL_{driverId}_{timestamp})?
**Answer:** Yes, use the generated format: EL_{driverId}_{timestamp}.

**Q4:** Do we need backwards compatibility for existing webhook calls that might still send conversation_id?
**Answer:** No backwards compatibility needed. Clean switch with no transition period.

### Follow-up Questions

**Follow-up 1:** Should we backfill existing Call records with generated call_sid values?
**Answer:** Yes, backfill existing records with call_sid.

**Follow-up 2:** Should the CallTranscription model also store call_sid directly, or should it continue using conversation_id as the foreign key with lookups happening through the Call table?
**Answer:** Design the best approach for CallTranscription model (keep it clean and avoid duplication).

**Follow-up 3:** When should the Call record be created - before or after the ElevenLabs API call?
**Answer:** Create Call record BEFORE ElevenLabs API call.

**Follow-up 4:** Should there be a transition period where both identifiers are supported, or a clean switch?
**Answer:** Clean switch (no transition period).

**Follow-up 5:** Should we rename helper functions like lookup_driver_id_by_conversation() to work with call_sid?
**Answer:** Yes, rename helper functions to work with call_sid.

**Follow-up 6:** What database indexes should we add for optimal performance?
**Answer:** Design optimal database indexes for the refactored system.

**Follow-up 7:** Are there any specific exclusions or features we should NOT include?
**Answer:** No specific exclusions. Implement a comprehensive refactor.

### Existing Code to Reference

**Similar Features Identified:**
- Current Call model (models/call.py) - Has conversation_id as unique identifier
- Current CallTranscription model (models/call_transcription.py) - Uses conversation_id as foreign key
- Current webhook endpoint (services/webhooks_elevenlabs.py) - Accepts conversation_id
- Current helper functions (helpers/transcription_helpers.py) - Work with conversation_id
- Current call creation flow (models/driver_data.py) - Generates call_sid but doesn't store it

### Visual Assets

No visual assets provided.

## Requirements Summary

### Functional Requirements

**Core Functionality:**
1. Add call_sid field to Call model alongside existing conversation_id
2. Modify webhook to accept call_sid instead of conversation_id
3. Create Call records BEFORE making ElevenLabs API calls
4. Update all helper functions to work with call_sid
5. Maintain conversation_id for backward compatibility with existing data
6. Use two-step lookup pattern: call_sid -> Call -> conversation_id -> CallTranscription

**User Actions Enabled:**
- System can track calls by call_sid from the moment they're initiated
- Webhooks receive call_sid and can look up the corresponding Call record
- Database maintains both call_sid and conversation_id for complete tracking
- Failed ElevenLabs calls still have Call records for audit purposes

**Data to be Managed:**
- Call.call_sid: Generated identifier (format: EL_{driverId}_{timestamp})
- Call.conversation_id: ElevenLabs-provided identifier (populated after API call)
- CallTranscription records linked via conversation_id foreign key
- Backfilled call_sid values for existing Call records

### Reusability Opportunities

**Existing Patterns to Follow:**
- Database retry decorator (@db_retry) from db/retry.py
- Timezone-aware datetime handling from logic/auth/service.py
- Model class methods pattern from existing Call and CallTranscription models
- SQLModel with table=True and proper indexes
- Logging patterns from existing webhook and helper functions

**Components to Reuse:**
- Existing Call model structure (add field, don't replace)
- Existing CallTranscription model (no changes needed)
- Existing prompt generation and call initiation logic
- Existing database session management and retry logic
- Existing error handling patterns in webhook endpoints

### Scope Boundaries

**In Scope:**
1. Database schema changes:
   - Add call_sid column to Call model
   - Add unique index on Call.call_sid
   - Add compound index on (call_sid, status)
   - Backfill existing Call records with generated call_sid
   - Make call_sid non-nullable after backfill

2. Call creation workflow changes:
   - Modify make_drivers_violation_batch_call_elevenlabs() to create Call record before ElevenLabs API call
   - Store call_sid, driver_id, call_start_time, status=in_progress initially
   - Update Call record with conversation_id after ElevenLabs returns

3. Webhook endpoint changes:
   - Update TranscriptionWebhookRequest to accept call_sid instead of conversation_id
   - Implement two-step lookup: call_sid -> Call -> conversation_id
   - Update error messages and validation

4. Helper function updates:
   - Rename lookup_driver_id_by_conversation() to lookup_driver_id_by_call_sid()
   - Update generate_sequence_number() to accept call_sid and look up conversation_id
   - Update ensure_call_exists() to work with call_sid
   - Update save_transcription() to accept call_sid
   - Add new function: get_conversation_id_from_call_sid()

5. ElevenLabs integration changes:
   - Update webhook configuration JSON to send call_sid instead of conversation_id
   - Update webhook description for ElevenLabs AI

6. Migration implementation:
   - Create migration to add call_sid column (nullable initially)
   - Create backfill script to populate existing records
   - Create migration to add constraints and indexes
   - Update ElevenLabs webhook configuration

**Out of Scope:**
- Changes to VAPI integration (deprecated, out of scope)
- Frontend changes (this is backend-only refactor)
- Changes to CallTranscription model structure
- Real-time call monitoring dashboard updates
- Analytics or reporting changes
- Changes to other webhook endpoints
- Migration to different AI provider

### Technical Considerations

**Database Design Decisions:**
- CallTranscription keeps conversation_id as foreign key (cleaner, avoids duplication)
- Call model has both call_sid and conversation_id
- Two-step lookup pattern maintains referential integrity
- Unique constraint on call_sid ensures no duplicates
- Compound index on (call_sid, status) for efficient status queries

**Call Creation Flow:**
1. Generate call_sid in make_drivers_violation_batch_call_elevenlabs()
2. Create Call record with: call_sid, driver_id, call_start_time (now), status=in_progress
3. Call ElevenLabs API with call_sid in webhook configuration
4. Update Call record with conversation_id from ElevenLabs response
5. Webhooks use call_sid to find Call, then conversation_id to save transcriptions

**Error Handling:**
- If ElevenLabs call fails, Call record exists with status=failed
- If webhook receives unknown call_sid, return 400 Bad Request
- Database retry logic applies to all operations
- Failed lookups logged with appropriate error messages

**Integration Points:**
- ElevenLabs webhook configuration must be updated to send call_sid
- Webhook URL remains the same (POST /webhooks/elevenlabs/transcription)
- Response format unchanged (maintains compatibility)

**Technology Constraints:**
- PostgreSQL database with SQLModel ORM
- FastAPI framework for endpoints
- Python 3.x with timezone-aware datetimes
- Existing database schema in 'dev' schema
- Connection pooling with retry logic

**Performance Considerations:**
- Unique index on call_sid for fast lookups
- Compound index on (call_sid, status) for status queries
- Existing indexes on conversation_id remain
- Two-step lookup adds minimal overhead (indexed joins)
- Backfill migration should be run during low-traffic period

## Executive Summary

### What We're Changing and Why

We are refactoring the ElevenLabs call transcription webhook system to use call_sid as the primary identifier for incoming webhook requests, while maintaining conversation_id as the foreign key for CallTranscription records. This change addresses a critical workflow issue where Call records are currently created reactively (on first webhook) rather than proactively (when initiating the call).

### Benefits of Using call_sid Over conversation_id

**1. Proactive Call Tracking:**
- Call records created BEFORE ElevenLabs API call, not after first dialogue
- Failed API calls still have Call records for audit and troubleshooting
- Complete lifecycle tracking from initiation to completion

**2. Better Control:**
- call_sid is generated by our system, not external provider
- Consistent format (EL_{driverId}_{timestamp}) aids debugging
- Webhook receives our identifier, looks up our data, then uses ElevenLabs identifier

**3. Improved Reliability:**
- Two-step lookup maintains referential integrity
- No duplication of conversation_id in CallTranscription table
- Clear separation: call_sid for call management, conversation_id for transcription linkage

**4. Audit Trail:**
- All call attempts tracked, even if ElevenLabs fails
- Easier correlation between system logs and database records
- Better troubleshooting and debugging capabilities

### High-Level Scope

**Database Changes:**
- Add call_sid to Call model
- Backfill existing records
- Add indexes for performance

**Code Changes:**
- Create Call record before ElevenLabs API call
- Update webhook to accept call_sid
- Refactor helper functions to use call_sid
- Implement two-step lookup pattern

**Integration Changes:**
- Update ElevenLabs webhook configuration
- Maintain backward compatibility with existing transcriptions

## Current Implementation Analysis

### How call_sid is Currently Generated but Not Stored

In the current implementation (models/driver_data.py, line 1226):

```python
# Call ElevenLabs client with generated data
transfer_to = "+18005551234"  # Default transfer number
call_sid = f"EL_{driver.driverId}_{request.timestamp}"  # Generate unique call SID
dispatcher_name = "AGY Dispatcher"  # Default dispatcher name

logger.info(f"Initiating ElevenLabs call to {normalized_phone}")

try:
    elevenlabs_response = await elevenlabs_client.create_outbound_call(
        to_number=normalized_phone,
        prompt=prompt_text,
        transfer_to=transfer_to,
        call_sid=call_sid,  # Sent to ElevenLabs but not stored in database
        dispatcher_name=dispatcher_name
    )
```

**Issue:** The call_sid is generated and sent to ElevenLabs, but it's never stored in the database. The Call record is only created later when the first webhook arrives (in ensure_call_exists() function).

### How conversation_id is Used for All Lookups

**Current Flow:**

1. **Call Initiation (models/driver_data.py):**
   - Generates call_sid but doesn't store it
   - Calls ElevenLabs API
   - Returns conversation_id from ElevenLabs response
   - No Call record created at this point

2. **Webhook Reception (services/webhooks_elevenlabs.py):**
   - Receives conversation_id from ElevenLabs
   - Calls save_transcription() with conversation_id

3. **Call Initialization (helpers/transcription_helpers.py, ensure_call_exists()):**
   - Checks if Call exists by conversation_id
   - If not, creates Call record with conversation_id
   - Attempts to look up driver_id (fails because Call doesn't exist yet)
   - Creates Call with driver_id=None

4. **Transcription Storage:**
   - Uses conversation_id as foreign key
   - All queries use conversation_id

**Problems with Current Flow:**
- Call record created reactively, not proactively
- Driver lookup fails on first webhook (Call doesn't exist yet)
- No audit trail for failed ElevenLabs calls
- call_sid generated but discarded

### Current Webhook Payload Structure

**Current TranscriptionWebhookRequest (services/webhooks_elevenlabs.py, lines 32-62):**

```python
class TranscriptionWebhookRequest(BaseModel):
    """
    Request model for ElevenLabs transcription webhook.

    Fields:
        conversation_id: ElevenLabs conversation identifier (required)
        speaker: Speaker attribution - 'agent' or 'user' (required)
        message: The dialogue message text (required)
        timestamp: ISO8601 timestamp when dialogue occurred (required)
    """
    conversation_id: str = Field(..., min_length=1, description="ElevenLabs conversation identifier")
    speaker: str = Field(..., description="Speaker attribution - 'agent' or 'user'")
    message: str = Field(..., min_length=1, description="The dialogue message text")
    timestamp: str = Field(..., description="ISO8601 timestamp when dialogue occurred")

    @validator('speaker')
    def validate_speaker(cls, v):
        """Validate that speaker is either 'agent' or 'user'."""
        if v not in ['agent', 'user']:
            raise ValueError("speaker must be 'agent' or 'user'")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate that timestamp is in valid ISO8601 format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("timestamp must be a valid ISO8601 format")
        return v
```

**Current Endpoint Logic (services/webhooks_elevenlabs.py, lines 114-178):**

```python
async def receive_transcription(request: TranscriptionWebhookRequest):
    """
    Receive and store real-time call transcription data from ElevenLabs.
    """
    logger.info(f"ElevenLabs Transcription Webhook - Received request for conversation: {request.conversation_id}")

    # Parse timestamp
    timestamp_dt = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
    timestamp_dt = make_timezone_aware(timestamp_dt)

    # Call save_transcription orchestration function
    transcription_id, sequence_number = save_transcription(
        conversation_id=request.conversation_id,  # Uses conversation_id
        speaker=request.speaker,
        message=request.message,
        timestamp=timestamp_dt
    )

    return TranscriptionWebhookSuccessResponse(
        status="success",
        message=f"Transcription saved successfully for conversation {request.conversation_id}",
        transcription_id=transcription_id,
        sequence_number=sequence_number
    )
```

## Proposed Changes

### A. Database Schema Changes

#### Call Model Changes

**Current Call Model (models/call.py, lines 25-54):**

```python
class Call(SQLModel, table=True):
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_calls_conversation_id"),
        Index("idx_calls_conversation_id", "conversation_id"),
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(max_length=255, nullable=False, index=True, unique=True)
    driver_id: Optional[int] = Field(default=None, nullable=True)
    call_start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    call_end_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    status: CallStatus = Field(default=CallStatus.IN_PROGRESS, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
```

**Updated Call Model:**

```python
class Call(SQLModel, table=True):
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint("conversation_id", name="uq_calls_conversation_id"),
        UniqueConstraint("call_sid", name="uq_calls_call_sid"),  # NEW
        Index("idx_calls_conversation_id", "conversation_id"),
        Index("idx_calls_call_sid", "call_sid"),  # NEW
        Index("idx_calls_call_sid_status", "call_sid", "status"),  # NEW - compound index
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: Optional[str] = Field(max_length=255, nullable=True, index=True, unique=True)  # CHANGED: nullable=True
    call_sid: str = Field(max_length=255, nullable=False, index=True, unique=True)  # NEW
    driver_id: Optional[int] = Field(default=None, nullable=True)
    call_start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    call_end_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    status: CallStatus = Field(default=CallStatus.IN_PROGRESS, nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
```

**Key Changes:**
1. Add call_sid field (non-nullable, unique, indexed)
2. Make conversation_id nullable (will be NULL until ElevenLabs returns it)
3. Add unique constraint on call_sid
4. Add single index on call_sid
5. Add compound index on (call_sid, status) for status queries

#### CallTranscription Model - NO CHANGES

**Decision:** Keep CallTranscription model unchanged. It continues to use conversation_id as the foreign key to maintain referential integrity and avoid data duplication.

**Rationale:**
- conversation_id uniquely identifies a conversation in ElevenLabs system
- CallTranscription records are dialogue turns within a conversation
- Foreign key relationship: CallTranscription.conversation_id -> Call.conversation_id
- No need to duplicate call_sid in CallTranscription table
- Two-step lookup is efficient with proper indexes

**Current CallTranscription Model (unchanged):**

```python
class CallTranscription(SQLModel, table=True):
    __tablename__ = "call_transcriptions"
    __table_args__ = (
        Index("idx_call_transcriptions_conversation_id", "conversation_id"),
        Index("idx_call_transcriptions_sequence_number", "sequence_number"),
        Index("idx_call_transcriptions_conversation_seq", "conversation_id", "sequence_number"),
        {"extend_existing": True}
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(max_length=255, nullable=False, index=True, foreign_key="calls.conversation_id")
    speaker_type: SpeakerType = Field(nullable=False)
    message_text: str = Field(sa_column=Column(Text, nullable=False))
    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    sequence_number: int = Field(nullable=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), nullable=False))
```

#### Index Strategy

**New Indexes to Add:**
1. **idx_calls_call_sid**: Single column index on call_sid for fast lookups
2. **idx_calls_call_sid_status**: Compound index on (call_sid, status) for efficient status queries
3. **uq_calls_call_sid**: Unique constraint to prevent duplicate call_sid values

**Existing Indexes to Keep:**
1. **idx_calls_conversation_id**: For conversation_id lookups
2. **idx_call_transcriptions_conversation_id**: For transcription lookups
3. **idx_call_transcriptions_conversation_seq**: Compound index for ordered transcription retrieval

**Index Usage Patterns:**
- Webhook lookup: call_sid -> Call (uses idx_calls_call_sid)
- Status queries: WHERE call_sid = ? AND status = ? (uses idx_calls_call_sid_status)
- Transcription retrieval: conversation_id -> CallTranscription (uses existing indexes)

#### Backfill Strategy

**Approach:**
1. Add call_sid column as nullable
2. Run backfill script to populate existing records
3. Make call_sid non-nullable
4. Add unique constraint and indexes

**Backfill Logic:**

```python
# Migration script (pseudo-code)
def backfill_call_sid():
    """
    Backfill call_sid for existing Call records.

    Format: EL_{driver_id}_{created_at_timestamp}
    Uses created_at as proxy for original timestamp since we don't have the original.
    """
    with Session(engine) as session:
        # Get all Call records without call_sid
        calls = session.exec(select(Call).where(Call.call_sid.is_(None))).all()

        for call in calls:
            # Generate call_sid using driver_id and created_at timestamp
            # Convert created_at to Unix timestamp for consistency
            timestamp = int(call.created_at.timestamp())
            call.call_sid = f"EL_{call.driver_id or 'UNKNOWN'}_{timestamp}"
            session.add(call)

        session.commit()
        logger.info(f"Backfilled {len(calls)} Call records with call_sid")
```

**Migration Steps:**
1. **Step 1**: Add call_sid column (nullable, no constraints)
2. **Step 2**: Run backfill script to populate existing records
3. **Step 3**: Add NOT NULL constraint to call_sid
4. **Step 4**: Add unique constraint on call_sid
5. **Step 5**: Add indexes (single and compound)
6. **Step 6**: Make conversation_id nullable (for future Call records created before ElevenLabs responds)

### B. Call Creation Workflow Changes

#### New Workflow in make_drivers_violation_batch_call_elevenlabs()

**Current Flow (models/driver_data.py, lines 1223-1263):**

```python
# Generate call_sid (but don't store it)
call_sid = f"EL_{driver.driverId}_{request.timestamp}"

# Call ElevenLabs
elevenlabs_response = await elevenlabs_client.create_outbound_call(
    to_number=normalized_phone,
    prompt=prompt_text,
    transfer_to=transfer_to,
    call_sid=call_sid,
    dispatcher_name=dispatcher_name
)

# Return response (no Call record created)
return {
    "message": "Call initiated successfully via ElevenLabs",
    "conversation_id": elevenlabs_response.get("conversation_id"),
    "callSid": elevenlabs_response.get("callSid"),
}
```

**New Flow:**

```python
# Step 1: Generate call_sid
call_sid = f"EL_{driver.driverId}_{request.timestamp}"
logger.info(f"Generated call_sid: {call_sid}")

# Step 2: Create Call record BEFORE calling ElevenLabs
from models.call import Call, CallStatus
from datetime import datetime, timezone

try:
    # Create Call record with initial data
    call_record = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=driver.driverId,
        call_start_time=datetime.now(timezone.utc),
        status=CallStatus.IN_PROGRESS
    )
    logger.info(f"Created Call record (ID: {call_record.id}) before ElevenLabs API call")

except Exception as db_err:
    logger.error(f"Failed to create Call record: {str(db_err)}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"Failed to create call record: {str(db_err)}"
    )

# Step 3: Call ElevenLabs API
try:
    elevenlabs_response = await elevenlabs_client.create_outbound_call(
        to_number=normalized_phone,
        prompt=prompt_text,
        transfer_to=transfer_to,
        call_sid=call_sid,  # Send our call_sid to ElevenLabs
        dispatcher_name=dispatcher_name
    )
    logger.info(f"ElevenLabs call initiated - Conversation ID: {elevenlabs_response.get('conversation_id')}")

except Exception as api_err:
    # Update Call record status to FAILED
    Call.update_status_by_call_sid(
        call_sid=call_sid,
        status=CallStatus.FAILED
    )
    logger.error(f"ElevenLabs API call failed: {str(api_err)}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"Failed to initiate ElevenLabs call: {str(api_err)}"
    )

# Step 4: Update Call record with conversation_id from ElevenLabs
try:
    Call.update_conversation_id(
        call_sid=call_sid,
        conversation_id=elevenlabs_response.get("conversation_id")
    )
    logger.info(f"Updated Call record with conversation_id: {elevenlabs_response.get('conversation_id')}")

except Exception as update_err:
    logger.error(f"Failed to update Call with conversation_id: {str(update_err)}", exc_info=True)
    # Don't fail the request - Call record exists, webhook can still work

# Step 5: Return success response
return {
    "message": "Call initiated successfully via ElevenLabs",
    "call_sid": call_sid,  # Our identifier
    "conversation_id": elevenlabs_response.get("conversation_id"),  # ElevenLabs identifier
    "callSid": elevenlabs_response.get("callSid"),  # Twilio call SID
    "timestamp": request.timestamp,
    "driver": {
        "driverId": driver.driverId,
        "driverName": driver.driverName,
        "phoneNumber": normalized_phone,
    },
    "triggers_count": len(violation_details),
}
```

**Key Workflow Changes:**
1. Create Call record BEFORE ElevenLabs API call
2. Initial Call has: call_sid, driver_id, call_start_time, status=IN_PROGRESS, conversation_id=NULL
3. If ElevenLabs fails, update Call status to FAILED (audit trail preserved)
4. If ElevenLabs succeeds, update Call with conversation_id
5. Webhooks can now find Call record using call_sid

#### New Call Model Class Methods

**Add to models/call.py:**

```python
@classmethod
@db_retry(max_retries=3)
def create_call_with_call_sid(
    cls,
    call_sid: str,
    driver_id: int,
    call_start_time: datetime,
    status: CallStatus = CallStatus.IN_PROGRESS
) -> "Call":
    """
    Create a new Call record with call_sid (before calling ElevenLabs).

    This method creates the Call record proactively, before the ElevenLabs API call.
    The conversation_id will be NULL initially and updated after ElevenLabs responds.

    Args:
        call_sid: Generated call identifier (format: EL_{driverId}_{timestamp})
        driver_id: Driver ID
        call_start_time: Timezone-aware UTC datetime when call is initiated
        status: Initial status (default: IN_PROGRESS)

    Returns:
        Created Call object
    """
    with cls.get_session() as session:
        call = cls(
            call_sid=call_sid,
            conversation_id=None,  # Will be updated after ElevenLabs responds
            driver_id=driver_id,
            call_start_time=call_start_time,
            status=status
        )
        session.add(call)
        session.commit()
        session.refresh(call)
        return call


@classmethod
@db_retry(max_retries=3)
def get_by_call_sid(cls, call_sid: str) -> Optional["Call"]:
    """
    Fetch a Call by call_sid.

    Args:
        call_sid: Generated call identifier

    Returns:
        Call object if found, None otherwise
    """
    with cls.get_session() as session:
        stmt = select(cls).where(cls.call_sid == call_sid)
        return session.exec(stmt).first()


@classmethod
@db_retry(max_retries=3)
def update_conversation_id(
    cls,
    call_sid: str,
    conversation_id: str
) -> Optional["Call"]:
    """
    Update Call record with conversation_id from ElevenLabs response.

    Args:
        call_sid: Generated call identifier
        conversation_id: ElevenLabs conversation identifier

    Returns:
        Updated Call object if found, None otherwise
    """
    with cls.get_session() as session:
        call = session.exec(
            select(cls).where(cls.call_sid == call_sid)
        ).first()

        if call:
            call.conversation_id = conversation_id
            call.updated_at = datetime.now(timezone.utc)
            session.add(call)
            session.commit()
            session.refresh(call)

        return call


@classmethod
@db_retry(max_retries=3)
def update_status_by_call_sid(
    cls,
    call_sid: str,
    status: CallStatus,
    call_end_time: Optional[datetime] = None
) -> Optional["Call"]:
    """
    Update call status by call_sid.

    Args:
        call_sid: Generated call identifier
        status: New status to set
        call_end_time: Optional timezone-aware UTC datetime when call ended

    Returns:
        Updated Call object if found, None otherwise
    """
    with cls.get_session() as session:
        call = session.exec(
            select(cls).where(cls.call_sid == call_sid)
        ).first()

        if call:
            call.status = status
            if call_end_time:
                call.call_end_time = call_end_time
            call.updated_at = datetime.now(timezone.utc)
            session.add(call)
            session.commit()
            session.refresh(call)

        return call
```

### C. Helper Function Changes

**Current Helper Functions (helpers/transcription_helpers.py):**

1. `lookup_driver_id_by_conversation(conversation_id)` - Lines 28-54
2. `generate_sequence_number(conversation_id)` - Lines 58-74
3. `ensure_call_exists(conversation_id, timestamp)` - Lines 103-150
4. `save_transcription(conversation_id, speaker, message, timestamp)` - Lines 154-214

**Updated Helper Functions:**

#### 1. Rename and Update lookup_driver_id_by_call_sid()

```python
@db_retry(max_retries=3)
def lookup_driver_id_by_call_sid(call_sid: str) -> Optional[int]:
    """
    Look up driver_id for a given call_sid from Call records.

    Args:
        call_sid: Generated call identifier (format: EL_{driverId}_{timestamp})

    Returns:
        driver_id if found, None otherwise

    Note:
        Logs a warning if driver_id is not found.
    """
    with Session(engine) as session:
        # Query Call table for call_sid
        stmt = select(Call).where(Call.call_sid == call_sid)
        call = session.exec(stmt).first()

        if call and call.driver_id is not None:
            logger.info(f"Driver lookup successful - call_sid: {call_sid}, driver_id: {call.driver_id}")
            return call.driver_id
        else:
            logger.warning(f"Driver lookup failed - call_sid: {call_sid} not found or has null driver_id")
            return None
```

#### 2. Add get_conversation_id_from_call_sid()

```python
@db_retry(max_retries=3)
def get_conversation_id_from_call_sid(call_sid: str) -> Optional[str]:
    """
    Get conversation_id for a given call_sid.

    This function implements the first step of the two-step lookup pattern:
    call_sid -> Call -> conversation_id

    Args:
        call_sid: Generated call identifier

    Returns:
        conversation_id if found, None otherwise

    Raises:
        ValueError: If Call record exists but has no conversation_id
    """
    with Session(engine) as session:
        stmt = select(Call).where(Call.call_sid == call_sid)
        call = session.exec(stmt).first()

        if not call:
            logger.error(f"Call record not found for call_sid: {call_sid}")
            return None

        if not call.conversation_id:
            logger.error(f"Call record found but conversation_id is NULL for call_sid: {call_sid}")
            raise ValueError(f"Call {call_sid} has no conversation_id - ElevenLabs call may have failed")

        logger.info(f"Conversation ID lookup successful - call_sid: {call_sid}, conversation_id: {call.conversation_id}")
        return call.conversation_id
```

#### 3. Update generate_sequence_number()

```python
@db_retry(max_retries=3)
def generate_sequence_number(call_sid: str) -> int:
    """
    Generate the next sequence number for a transcription.

    Uses two-step lookup: call_sid -> conversation_id -> count transcriptions.

    Args:
        call_sid: Generated call identifier

    Returns:
        Next sequence number (count + 1, starting at 1 for first transcription)

    Raises:
        ValueError: If call_sid not found or has no conversation_id
    """
    # Step 1: Get conversation_id from call_sid
    conversation_id = get_conversation_id_from_call_sid(call_sid)
    if not conversation_id:
        raise ValueError(f"Cannot generate sequence number - no conversation_id for call_sid: {call_sid}")

    # Step 2: Count existing transcriptions
    count = CallTranscription.get_count_by_conversation_id(conversation_id)
    sequence_number = count + 1
    logger.debug(f"Generated sequence number {sequence_number} for call_sid {call_sid} (conversation {conversation_id})")
    return sequence_number
```

#### 4. Update ensure_call_exists() - REMOVED

**Decision:** Remove ensure_call_exists() function entirely. It's no longer needed because:
- Call records are created BEFORE ElevenLabs API call
- Webhook will never encounter a missing Call record (except in error cases)
- If Call is missing, it's an error condition that should fail the webhook

#### 5. Update save_transcription()

```python
@db_retry(max_retries=3)
def save_transcription(
    call_sid: str,  # CHANGED: was conversation_id
    speaker: str,
    message: str,
    timestamp: datetime
) -> Tuple[int, int]:
    """
    Orchestrate the complete transcription save workflow.

    This function coordinates all steps using the two-step lookup pattern:
    1. Look up conversation_id from call_sid
    2. Map speaker to internal format
    3. Generate sequence number (using call_sid)
    4. Create CallTranscription record (using conversation_id)
    5. Return (transcription_id, sequence_number)

    Args:
        call_sid: Generated call identifier (from webhook)
        speaker: ElevenLabs speaker value ('user' or 'agent')
        message: The dialogue message text
        timestamp: Timezone-aware UTC datetime when dialogue occurred

    Returns:
        Tuple of (transcription_id, sequence_number)

    Raises:
        ValueError: If speaker is invalid or call_sid not found
        Database exceptions: If database operations fail after retries
    """
    logger.info(f"Starting transcription save - call_sid: {call_sid}, speaker: {speaker}")

    # Step 1: Get conversation_id from call_sid (two-step lookup)
    aware_timestamp = make_timezone_aware(timestamp)
    conversation_id = get_conversation_id_from_call_sid(call_sid)

    if not conversation_id:
        raise ValueError(f"Cannot save transcription - Call record not found for call_sid: {call_sid}")

    logger.info(f"Resolved conversation_id: {conversation_id} for call_sid: {call_sid}")

    # Step 2: Map speaker to internal format
    speaker_type = map_speaker_to_internal(speaker)

    # Step 3: Generate sequence number (uses call_sid internally)
    sequence_number = generate_sequence_number(call_sid)

    # Step 4: Create CallTranscription record (uses conversation_id as FK)
    transcription = CallTranscription.create_transcription(
        conversation_id=conversation_id,  # Foreign key to Call
        speaker_type=speaker_type,
        message_text=message,
        timestamp=aware_timestamp,
        sequence_number=sequence_number
    )

    logger.info(
        f"Transcription saved successfully - ID: {transcription.id}, "
        f"sequence: {sequence_number}, speaker: {speaker_type.value}, "
        f"call_sid: {call_sid}, conversation_id: {conversation_id}"
    )

    # Step 5: Return results
    return (transcription.id, sequence_number)
```

### D. Webhook Endpoint Changes

**Current Webhook Request Model (services/webhooks_elevenlabs.py, lines 32-62):**

```python
class TranscriptionWebhookRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, description="ElevenLabs conversation identifier")
    speaker: str = Field(..., description="Speaker attribution - 'agent' or 'user'")
    message: str = Field(..., min_length=1, description="The dialogue message text")
    timestamp: str = Field(..., description="ISO8601 timestamp when dialogue occurred")
```

**Updated Webhook Request Model:**

```python
class TranscriptionWebhookRequest(BaseModel):
    """
    Request model for ElevenLabs transcription webhook.

    Fields:
        call_sid: Generated call identifier from our system (required)
        speaker: Speaker attribution - 'agent' or 'user' (required)
        message: The dialogue message text (required)
        timestamp: ISO8601 timestamp when dialogue occurred (required)
    """
    call_sid: str = Field(..., min_length=1, description="Generated call identifier (format: EL_{driverId}_{timestamp})")
    speaker: str = Field(..., description="Speaker attribution - 'agent' or 'user'")
    message: str = Field(..., min_length=1, description="The dialogue message text")
    timestamp: str = Field(..., description="ISO8601 timestamp when dialogue occurred")

    @validator('speaker')
    def validate_speaker(cls, v):
        """Validate that speaker is either 'agent' or 'user'."""
        if v not in ['agent', 'user']:
            raise ValueError("speaker must be 'agent' or 'user'")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate that timestamp is in valid ISO8601 format."""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            raise ValueError("timestamp must be a valid ISO8601 format")
        return v
```

**Updated Webhook Endpoint Logic:**

```python
@router.post(
    "/transcription",
    status_code=status.HTTP_201_CREATED,
    response_model=TranscriptionWebhookSuccessResponse,
    responses={
        201: {"description": "Transcription saved successfully"},
        400: {"description": "Invalid request data or call_sid not found"},
        500: {"description": "Internal server error"}
    }
)
async def receive_transcription(request: TranscriptionWebhookRequest):
    """
    Receive and store real-time call transcription data from ElevenLabs.

    This endpoint is called by ElevenLabs for each completed dialogue turn.
    It handles:
    - Two-step lookup: call_sid -> Call -> conversation_id
    - Speaker mapping from ElevenLabs format to internal format
    - Sequence number generation
    - Transcription storage

    Args:
        request: Validated webhook request with call_sid, speaker, message, timestamp

    Returns:
        201 Created: TranscriptionWebhookSuccessResponse
        400 Bad Request: Invalid speaker, timestamp, or call_sid not found
        500 Internal Server Error: Database connection failure
    """
    logger.info("=" * 100)
    logger.info(f"ElevenLabs Transcription Webhook - Received request for call_sid: {request.call_sid}")
    logger.info(f"Speaker: {request.speaker} | Message length: {len(request.message)} chars")
    logger.info("=" * 100)

    try:
        # Parse and validate timestamp
        try:
            timestamp_dt = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
            timestamp_dt = make_timezone_aware(timestamp_dt)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid timestamp format: {request.timestamp} - {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": "Invalid timestamp format. Expected ISO8601 format.",
                    "details": str(e)
                }
            )

        # Call save_transcription orchestration function (now uses call_sid)
        try:
            transcription_id, sequence_number = save_transcription(
                call_sid=request.call_sid,  # CHANGED: was conversation_id
                speaker=request.speaker,
                message=request.message,
                timestamp=timestamp_dt
            )
        except ValueError as lookup_err:
            # Call record not found or has no conversation_id
            logger.error(f"Call lookup failed for call_sid {request.call_sid}: {str(lookup_err)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "error",
                    "message": f"Call record not found or incomplete for call_sid: {request.call_sid}",
                    "details": str(lookup_err)
                }
            )

        logger.info(f"Transcription saved successfully - ID: {transcription_id}, Sequence: {sequence_number}")
        logger.info("=" * 100)

        return TranscriptionWebhookSuccessResponse(
            status="success",
            message=f"Transcription saved successfully for call_sid {request.call_sid}",
            transcription_id=transcription_id,
            sequence_number=sequence_number
        )

    except ValueError as e:
        # Invalid speaker value or other validation error
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "message": "Invalid request data",
                "details": str(e)
            }
        )

    except (OperationalError, DisconnectionError) as e:
        # Database connection failure
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Database connection error. Please retry.",
                "details": "Database temporarily unavailable"
            }
        )

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error processing transcription: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Internal server error. Please retry.",
                "details": str(e)
            }
        )
```

**Key Changes:**
1. TranscriptionWebhookRequest now accepts `call_sid` instead of `conversation_id`
2. Error handling for call_sid lookup failures (returns 400 if Call not found)
3. Updated logging to reference call_sid
4. save_transcription() now called with call_sid parameter

### E. ElevenLabs Integration Changes

#### Update Webhook Configuration JSON

**Current Webhook Configuration (sent to ElevenLabs):**

```json
{
  "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
  "events": ["conversation.dialogue.completed"],
  "payload": {
    "conversation_id": "{{conversation_id}}",
    "speaker": "{{speaker}}",
    "message": "{{message}}",
    "timestamp": "{{timestamp}}"
  }
}
```

**Updated Webhook Configuration:**

```json
{
  "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
  "events": ["conversation.dialogue.completed"],
  "payload": {
    "call_sid": "{{call_sid}}",
    "speaker": "{{speaker}}",
    "message": "{{message}}",
    "timestamp": "{{timestamp}}"
  }
}
```

**Note:** The call_sid that ElevenLabs sends back is the same call_sid we provided in the create_outbound_call() request. ElevenLabs echoes it back to us in webhooks.

#### Update ElevenLabs Client Call Configuration

**No changes needed to elevenlabs_client.py** - We're already sending call_sid in the create_outbound_call() request. ElevenLabs will now echo it back in webhooks.

## Migration Plan

### Step 1: Add call_sid Column (Nullable)

**Migration File: 001_add_call_sid_column.py**

```python
"""
Migration: Add call_sid column to calls table (nullable)

This is the first step in the call_sid refactor migration.
The column is nullable initially to allow backfilling.
"""
from sqlalchemy import Column, String
from alembic import op

def upgrade():
    """Add call_sid column as nullable."""
    op.add_column(
        'calls',
        Column('call_sid', String(255), nullable=True),
        schema='dev'
    )
    print("Added call_sid column (nullable) to calls table")

def downgrade():
    """Remove call_sid column."""
    op.drop_column('calls', 'call_sid', schema='dev')
    print("Removed call_sid column from calls table")
```

### Step 2: Backfill Existing Records

**Migration File: 002_backfill_call_sid.py**

```python
"""
Migration: Backfill call_sid for existing Call records

Generates call_sid for all existing records using format:
EL_{driver_id}_{created_at_timestamp}

For records with NULL driver_id, uses 'UNKNOWN' as placeholder.
"""
from alembic import op
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Backfill call_sid for all existing Call records."""
    connection = op.get_bind()

    # Get count of records to backfill
    result = connection.execute(text("""
        SELECT COUNT(*) FROM dev.calls WHERE call_sid IS NULL
    """))
    count = result.scalar()
    logger.info(f"Backfilling {count} Call records with call_sid")

    # Update records with generated call_sid
    connection.execute(text("""
        UPDATE dev.calls
        SET call_sid = CONCAT(
            'EL_',
            COALESCE(CAST(driver_id AS VARCHAR), 'UNKNOWN'),
            '_',
            CAST(EXTRACT(EPOCH FROM created_at) AS INTEGER)
        )
        WHERE call_sid IS NULL
    """))

    logger.info(f"Successfully backfilled {count} Call records")
    print(f"Backfilled {count} Call records with call_sid")

def downgrade():
    """Set all call_sid values to NULL."""
    connection = op.get_bind()
    connection.execute(text("""
        UPDATE dev.calls SET call_sid = NULL
    """))
    print("Set all call_sid values to NULL")
```

### Step 3: Add Unique Constraint and Indexes

**Migration File: 003_add_call_sid_constraints.py**

```python
"""
Migration: Add constraints and indexes for call_sid

Adds:
- NOT NULL constraint on call_sid
- Unique constraint on call_sid
- Single column index on call_sid
- Compound index on (call_sid, status)
"""
from alembic import op

def upgrade():
    """Add NOT NULL constraint, unique constraint, and indexes."""
    # Make call_sid non-nullable
    op.alter_column(
        'calls',
        'call_sid',
        nullable=False,
        schema='dev'
    )
    print("Made call_sid non-nullable")

    # Add unique constraint
    op.create_unique_constraint(
        'uq_calls_call_sid',
        'calls',
        ['call_sid'],
        schema='dev'
    )
    print("Added unique constraint on call_sid")

    # Add single column index
    op.create_index(
        'idx_calls_call_sid',
        'calls',
        ['call_sid'],
        schema='dev'
    )
    print("Added index on call_sid")

    # Add compound index on (call_sid, status)
    op.create_index(
        'idx_calls_call_sid_status',
        'calls',
        ['call_sid', 'status'],
        schema='dev'
    )
    print("Added compound index on (call_sid, status)")

def downgrade():
    """Remove indexes and constraints."""
    op.drop_index('idx_calls_call_sid_status', 'calls', schema='dev')
    op.drop_index('idx_calls_call_sid', 'calls', schema='dev')
    op.drop_constraint('uq_calls_call_sid', 'calls', schema='dev')
    op.alter_column('calls', 'call_sid', nullable=True, schema='dev')
    print("Removed indexes and constraints from call_sid")
```

### Step 4: Make conversation_id Nullable

**Migration File: 004_make_conversation_id_nullable.py**

```python
"""
Migration: Make conversation_id nullable

This allows Call records to be created before ElevenLabs responds.
conversation_id will be NULL initially and populated after API call succeeds.
"""
from alembic import op

def upgrade():
    """Make conversation_id nullable."""
    op.alter_column(
        'calls',
        'conversation_id',
        nullable=True,
        schema='dev'
    )
    print("Made conversation_id nullable")

def downgrade():
    """Make conversation_id non-nullable again."""
    # NOTE: This downgrade may fail if there are NULL values
    op.alter_column(
        'calls',
        'conversation_id',
        nullable=False,
        schema='dev'
    )
    print("Made conversation_id non-nullable")
```

### Step 5: Deploy Code Changes

**Deployment Order:**

1. Run database migrations (Steps 1-4)
2. Deploy updated backend code:
   - Updated Call model (with call_sid field)
   - Updated webhook endpoint (accepts call_sid)
   - Updated helper functions (use call_sid)
   - Updated call creation flow (creates Call before API call)
3. Verify migrations succeeded (check database)
4. Monitor logs for errors

**Rollback Plan:**

If issues occur:
1. Revert code deployment
2. Rollback migrations in reverse order (4 -> 3 -> 2 -> 1)
3. Verify database state
4. Investigate issues before retry

### Step 6: Update ElevenLabs Webhook Configuration

**After code deployment succeeds:**

1. Update ElevenLabs webhook configuration via API or dashboard
2. Change payload from conversation_id to call_sid
3. Test with a test call to verify webhook works
4. Monitor production webhooks for errors

**Webhook Update Command (example):**

```bash
curl -X PUT "https://api.elevenlabs.io/v1/webhooks/{webhook_id}" \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
    "events": ["conversation.dialogue.completed"],
    "payload": {
      "call_sid": "{{call_sid}}",
      "speaker": "{{speaker}}",
      "message": "{{message}}",
      "timestamp": "{{timestamp}}"
    }
  }'
```

## Testing Strategy

### Unit Tests for Modified Functions

#### Test: Call.create_call_with_call_sid()

```python
def test_create_call_with_call_sid():
    """Test creating Call record with call_sid before ElevenLabs call."""
    from models.call import Call, CallStatus
    from datetime import datetime, timezone

    call_sid = "EL_123_1700000000"
    driver_id = 123
    call_start_time = datetime.now(timezone.utc)

    # Create call
    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=driver_id,
        call_start_time=call_start_time
    )

    # Assertions
    assert call.call_sid == call_sid
    assert call.driver_id == driver_id
    assert call.conversation_id is None  # Should be NULL initially
    assert call.status == CallStatus.IN_PROGRESS
    assert call.call_start_time == call_start_time
```

#### Test: Call.get_by_call_sid()

```python
def test_get_by_call_sid():
    """Test retrieving Call by call_sid."""
    from models.call import Call

    # Create test call
    call_sid = "EL_456_1700000001"
    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=456,
        call_start_time=datetime.now(timezone.utc)
    )

    # Retrieve by call_sid
    retrieved = Call.get_by_call_sid(call_sid)

    # Assertions
    assert retrieved is not None
    assert retrieved.id == call.id
    assert retrieved.call_sid == call_sid
```

#### Test: Call.update_conversation_id()

```python
def test_update_conversation_id():
    """Test updating Call with conversation_id from ElevenLabs."""
    from models.call import Call

    # Create call without conversation_id
    call_sid = "EL_789_1700000002"
    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=789,
        call_start_time=datetime.now(timezone.utc)
    )
    assert call.conversation_id is None

    # Update with conversation_id
    conversation_id = "conv_abcdef123456"
    updated = Call.update_conversation_id(call_sid, conversation_id)

    # Assertions
    assert updated is not None
    assert updated.conversation_id == conversation_id
    assert updated.call_sid == call_sid
```

#### Test: get_conversation_id_from_call_sid()

```python
def test_get_conversation_id_from_call_sid():
    """Test two-step lookup: call_sid -> conversation_id."""
    from helpers.transcription_helpers import get_conversation_id_from_call_sid
    from models.call import Call

    # Create call with conversation_id
    call_sid = "EL_111_1700000003"
    conversation_id = "conv_xyz789"

    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=111,
        call_start_time=datetime.now(timezone.utc)
    )
    Call.update_conversation_id(call_sid, conversation_id)

    # Test lookup
    result = get_conversation_id_from_call_sid(call_sid)
    assert result == conversation_id
```

#### Test: save_transcription() with call_sid

```python
def test_save_transcription_with_call_sid():
    """Test saving transcription using call_sid."""
    from helpers.transcription_helpers import save_transcription
    from models.call import Call
    from datetime import datetime, timezone

    # Setup: Create call with conversation_id
    call_sid = "EL_222_1700000004"
    conversation_id = "conv_test123"

    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=222,
        call_start_time=datetime.now(timezone.utc)
    )
    Call.update_conversation_id(call_sid, conversation_id)

    # Save transcription using call_sid
    transcription_id, sequence_number = save_transcription(
        call_sid=call_sid,
        speaker="agent",
        message="Hello, this is a test message",
        timestamp=datetime.now(timezone.utc)
    )

    # Assertions
    assert transcription_id is not None
    assert sequence_number == 1  # First transcription
```

### Integration Tests for New Workflow

#### Test: End-to-End Call Creation Workflow

```python
async def test_call_creation_workflow():
    """Test complete call creation workflow with ElevenLabs."""
    from models.driver_data import make_drivers_violation_batch_call_elevenlabs
    from models.vapi import BatchCallRequest, DriverData, Violations, ViolationDetail
    from models.call import Call, CallStatus

    # Create test request
    request = BatchCallRequest(
        callType="violation",
        timestamp="2024-11-21T10:00:00Z",
        drivers=[
            DriverData(
                driverId=333,
                driverName="Test Driver",
                phoneNumber="+15551234567",
                customRules="",
                violations=Violations(
                    tripId="trip_123",
                    violationDetails=[
                        ViolationDetail(
                            type="temperature",
                            description="Temperature out of range"
                        )
                    ]
                )
            )
        ]
    )

    # Call the function
    response = await make_drivers_violation_batch_call_elevenlabs(request)

    # Verify Call record was created
    call_sid = response["call_sid"]
    call = Call.get_by_call_sid(call_sid)

    assert call is not None
    assert call.driver_id == 333
    assert call.status in [CallStatus.IN_PROGRESS, CallStatus.COMPLETED]
    assert call.conversation_id is not None  # Should be populated from ElevenLabs
```

### Migration Tests for Backfill

#### Test: Backfill Migration

```python
def test_backfill_migration():
    """Test backfill migration generates correct call_sid values."""
    from models.call import Call, CallStatus
    from datetime import datetime, timezone

    # Create test calls with old schema (no call_sid)
    # This simulates pre-migration data
    with Session(engine) as session:
        call1 = Call(
            conversation_id="conv_old_1",
            driver_id=444,
            call_start_time=datetime.now(timezone.utc),
            status=CallStatus.COMPLETED
        )
        call2 = Call(
            conversation_id="conv_old_2",
            driver_id=None,  # NULL driver_id case
            call_start_time=datetime.now(timezone.utc),
            status=CallStatus.COMPLETED
        )
        session.add_all([call1, call2])
        session.commit()

    # Run backfill (simulated)
    # In real migration, this would be the migration script

    # Verify backfill results
    call1_after = Call.get_by_conversation_id("conv_old_1")
    call2_after = Call.get_by_conversation_id("conv_old_2")

    assert call1_after.call_sid is not None
    assert "EL_444_" in call1_after.call_sid

    assert call2_after.call_sid is not None
    assert "EL_UNKNOWN_" in call2_after.call_sid  # NULL driver_id case
```

### End-to-End Webhook Tests with call_sid

#### Test: Webhook with call_sid

```python
async def test_webhook_with_call_sid():
    """Test webhook endpoint accepts call_sid and saves transcription."""
    from fastapi.testclient import TestClient
    from main import app
    from models.call import Call
    from datetime import datetime, timezone

    client = TestClient(app)

    # Setup: Create Call record
    call_sid = "EL_555_1700000005"
    conversation_id = "conv_webhook_test"

    call = Call.create_call_with_call_sid(
        call_sid=call_sid,
        driver_id=555,
        call_start_time=datetime.now(timezone.utc)
    )
    Call.update_conversation_id(call_sid, conversation_id)

    # Send webhook request with call_sid
    webhook_payload = {
        "call_sid": call_sid,
        "speaker": "agent",
        "message": "Test webhook message",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    response = client.post(
        "/webhooks/elevenlabs/transcription",
        json=webhook_payload
    )

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["sequence_number"] == 1
```

#### Test: Webhook with Invalid call_sid

```python
async def test_webhook_with_invalid_call_sid():
    """Test webhook returns 400 for unknown call_sid."""
    from fastapi.testclient import TestClient
    from main import app
    from datetime import datetime, timezone

    client = TestClient(app)

    # Send webhook request with non-existent call_sid
    webhook_payload = {
        "call_sid": "EL_INVALID_999999",
        "speaker": "agent",
        "message": "Test message",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    response = client.post(
        "/webhooks/elevenlabs/transcription",
        json=webhook_payload
    )

    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "not found" in data["message"].lower()
```

## API Changes Summary

### Webhook Request Payload Before/After

**Before (Current):**

```json
{
  "conversation_id": "conv_abcdef123456",
  "speaker": "agent",
  "message": "Hello, how are you doing?",
  "timestamp": "2024-11-21T10:30:00Z"
}
```

**After (New):**

```json
{
  "call_sid": "EL_123_2024-11-21T10:00:00Z",
  "speaker": "agent",
  "message": "Hello, how are you doing?",
  "timestamp": "2024-11-21T10:30:00Z"
}
```

**Key Changes:**
- `conversation_id` field replaced with `call_sid`
- `call_sid` format: `EL_{driverId}_{timestamp}`
- All other fields remain identical

### Response Formats (Unchanged)

**Success Response (201 Created):**

```json
{
  "status": "success",
  "message": "Transcription saved successfully for call_sid EL_123_2024-11-21T10:00:00Z",
  "transcription_id": 456,
  "sequence_number": 1
}
```

**Error Response (400 Bad Request):**

```json
{
  "status": "error",
  "message": "Call record not found or incomplete for call_sid: EL_INVALID_999",
  "details": "Cannot save transcription - Call record not found for call_sid: EL_INVALID_999"
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "status": "error",
  "message": "Database connection error. Please retry.",
  "details": "Database temporarily unavailable"
}
```

**Note:** Response formats remain unchanged for backward compatibility.

### Breaking Changes

**Breaking Change 1: Webhook Payload Structure**

- **Impact:** ElevenLabs webhook configuration must be updated
- **Action Required:** Update webhook payload to send `call_sid` instead of `conversation_id`
- **Timing:** After code deployment, before production traffic

**Breaking Change 2: Helper Function Signatures**

- **Impact:** Internal code only (no external API changes)
- **Functions Changed:**
  - `lookup_driver_id_by_conversation()` -> `lookup_driver_id_by_call_sid()`
  - `generate_sequence_number()` parameter changed
  - `save_transcription()` parameter changed
  - `ensure_call_exists()` removed
- **Action Required:** None for external consumers

**No Breaking Changes for:**
- Call creation endpoint (POST /driver_data/call-elevenlabs)
- Response formats
- CallTranscription model
- Database foreign keys

## Implementation Checklist

### Database Changes
- [ ] Create migration to add call_sid column (nullable)
- [ ] Create backfill script to populate existing records
- [ ] Test backfill script in staging environment
- [ ] Create migration to add NOT NULL constraint
- [ ] Create migration to add unique constraint on call_sid
- [ ] Create migration to add single index on call_sid
- [ ] Create migration to add compound index on (call_sid, status)
- [ ] Create migration to make conversation_id nullable
- [ ] Verify all migrations in staging
- [ ] Run migrations in production during low-traffic period

### Model Updates
- [ ] Update Call model to include call_sid field
- [ ] Update Call model table args with new indexes
- [ ] Make conversation_id nullable in Call model
- [ ] Add Call.create_call_with_call_sid() class method
- [ ] Add Call.get_by_call_sid() class method
- [ ] Add Call.update_conversation_id() class method
- [ ] Add Call.update_status_by_call_sid() class method
- [ ] Verify CallTranscription model remains unchanged
- [ ] Update model docstrings to reflect changes

### Helper Function Updates
- [ ] Rename lookup_driver_id_by_conversation() to lookup_driver_id_by_call_sid()
- [ ] Add get_conversation_id_from_call_sid() function
- [ ] Update generate_sequence_number() to accept call_sid
- [ ] Remove ensure_call_exists() function
- [ ] Update save_transcription() to accept call_sid parameter
- [ ] Update all docstrings for modified functions
- [ ] Add proper error handling for two-step lookups

### Endpoint Updates
- [ ] Update TranscriptionWebhookRequest model (conversation_id -> call_sid)
- [ ] Update receive_transcription() endpoint logic
- [ ] Add error handling for missing Call records
- [ ] Update logging to reference call_sid
- [ ] Update endpoint docstrings and OpenAPI documentation
- [ ] Verify response models remain unchanged

### Call Creation Flow Updates
- [ ] Update make_drivers_violation_batch_call_elevenlabs() function
- [ ] Add Call record creation BEFORE ElevenLabs API call
- [ ] Add error handling if Call creation fails
- [ ] Add Call status update to FAILED if ElevenLabs fails
- [ ] Add conversation_id update after ElevenLabs succeeds
- [ ] Update function docstrings and logging
- [ ] Verify call_sid generation format matches spec

### Test Updates
- [ ] Write unit tests for Call.create_call_with_call_sid()
- [ ] Write unit tests for Call.get_by_call_sid()
- [ ] Write unit tests for Call.update_conversation_id()
- [ ] Write unit tests for get_conversation_id_from_call_sid()
- [ ] Write unit tests for save_transcription() with call_sid
- [ ] Write integration test for end-to-end call workflow
- [ ] Write migration test for backfill logic
- [ ] Write webhook test with call_sid
- [ ] Write webhook test with invalid call_sid
- [ ] Run full test suite and verify all pass

### Documentation Updates
- [ ] Update API documentation for webhook endpoint
- [ ] Update architecture documentation for two-step lookup pattern
- [ ] Document migration steps and rollback procedures
- [ ] Update CLAUDE.md with refactored workflow
- [ ] Document call_sid format and generation logic
- [ ] Add troubleshooting guide for common issues
- [ ] Update database schema documentation

### Integration Updates
- [ ] Update ElevenLabs webhook configuration JSON
- [ ] Test webhook configuration in ElevenLabs dashboard
- [ ] Verify call_sid is echoed back by ElevenLabs
- [ ] Create rollback plan for webhook configuration
- [ ] Document webhook update procedure

### Deployment
- [ ] Run migrations in staging environment
- [ ] Deploy code to staging environment
- [ ] Test end-to-end workflow in staging
- [ ] Verify webhook receives call_sid correctly
- [ ] Run migrations in production (during low traffic)
- [ ] Deploy code to production
- [ ] Update ElevenLabs webhook configuration
- [ ] Monitor logs for errors
- [ ] Verify first production call works correctly
- [ ] Document any issues encountered

### Post-Deployment Verification
- [ ] Verify Call records created before ElevenLabs calls
- [ ] Verify webhooks successfully save transcriptions
- [ ] Verify two-step lookup performance acceptable
- [ ] Check database indexes are being used
- [ ] Monitor error rates and response times
- [ ] Verify backfilled records work correctly
- [ ] Confirm no regression in existing functionality

---

**END OF REQUIREMENTS DOCUMENT**
