# Spec Requirements: ElevenLabs Integration

## Initial Description
Implement a service layer for ElevenLabs API to replace the current VAPI implementation. Create a new function similar to `make_drivers_violation_batch_call` that uses ElevenLabs API for outbound calls.

The ElevenLabs API endpoint to implement:
```
POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call

Headers:
- xi-api-key: [API key from config]
- Content-Type: application/json

Payload structure:
{
  "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
  "agent_phone_number_id": "phnum_8401k9ndc950ewza733y8thmpbrx",
  "to_number": "+923282828885",
  "conversation_initiation_client_data": {
    "dynamic_variables": {
      "prompt": "I am seeing and alert that your truck and trailer are not together, are you with your trailer right now?",
      "transfer_to": "+923282828886",
      "call_sid": "call_1763569135457_s11ttbe7g",
      "dispatcher_name": "Aleena "
    }
  }
}
```

## Requirements Discussion

### First Round Questions

**Q1:** Where should the ElevenLabs client be created and what naming pattern should it follow?
**Answer:** Create `utils/elevenlabs_client.py` with an `ElevenLabsClient` class (similar to the existing VAPIClient pattern)

**Q2:** What should the new function be named and where should it be located?
**Answer:** Create `make_drivers_violation_batch_call_elevenlabs` in the same `models/driver_data.py` file alongside the existing VAPI function

**Q3:** What request/response model structure should we use for the ElevenLabs implementation?
**Answer:**
- Use the same `BatchCallRequest` model for input (from `models/vapi.py`)
- Response structure from ElevenLabs API:
```json
{
  "success": true,
  "message": "Success",
  "conversation_id": "conv_9601kaf71jfne4d9syfynwc35hc9",
  "callSid": "CAbcaf01bde90eaced8c0013d7ca66d216"
}
```
- We need to include `conversation_id` in the response

**Q4:** How should configuration values be managed (API keys, agent IDs, phone number IDs)?
**Answer:**
- Store `ELEVENLABS_API_KEY` in `.env` file
- `agent_id` and `agent_phone_number_id` should be hardcoded as class variables at the top of the `ElevenLabsClient` class
- Rationale: Future changes will make agent and phone number configurable from frontend

**Q5:** Which dynamic variables should be generated vs. passed as parameters?
**Answer:**
- `prompt`: Should be dynamically generated based on driver violations (like current implementation)
- `transfer_to`, `call_sid`, `dispatcher_name`: Should be passed as parameters

**Q6:** What error handling and retry logic should be implemented?
**Answer:**
- Add error handling similar to VAPIClient
- Implement retry logic that is configurable from a constants file

**Q7:** Does ElevenLabs require webhooks or should it call the API directly?
**Answer:**
- ElevenLabs should call the API directly
- No webhooks needed

**Q8:** Should we create a new endpoint or modify the existing one?
**Answer:**
- Create a separate endpoint `/driver_data/call-elevenlabs` initially
- Keep the existing `/driver_data/call` endpoint with VAPI implementation for now

**Q9:** Should the ElevenLabs implementation be independent or share code with VAPI?
**Answer:**
- ElevenLabs implementation should be completely independent so VAPI can be removed entirely afterward
- This is a clean migration path

### Existing Code to Reference

**Similar Features Identified:**
- Feature: VAPIClient - Path: `utils/vapi_client.py`
- Components to potentially reuse: HTTP client pattern using httpx.AsyncClient, error handling structure, logging patterns
- Backend logic to reference: `make_drivers_violation_batch_call` function in `models/driver_data.py` (line 994)
- Request models: `BatchCallRequest`, `DriverData`, `Violations`, `ViolationDetail` from `models/vapi.py`

**Key Patterns from VAPIClient:**
- Class-based client with base_url and api_key attributes
- Async methods using httpx.AsyncClient
- Error handling with try/except blocks
- Logging using the helpers logger
- Timeout configuration (30 seconds for POST, 10 seconds for GET)
- Response validation checking status codes
- Return standardized response dictionaries

**Key Patterns from make_drivers_violation_batch_call:**
- Phone number normalization to E.164 format
- Violation details extraction from BatchCallRequest
- Webhook payload construction
- Detailed logging of incoming payloads
- Single driver processing (only processes first driver from array)

### Follow-up Questions

None required - all requirements clarified in first round.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
No visual assets provided.

## Requirements Summary

### Functional Requirements
- Create a new ElevenLabsClient class in `utils/elevenlabs_client.py` following the VAPIClient pattern
- Implement `make_drivers_violation_batch_call_elevenlabs` function in `models/driver_data.py`
- Use existing `BatchCallRequest` model from `models/vapi.py` for input
- Call ElevenLabs API endpoint: `POST https://api.elevenlabs.io/v1/convai/twilio/outbound-call`
- Return response including `conversation_id` from ElevenLabs
- Generate dynamic prompt based on driver violations (similar to current VAPI implementation)
- Accept `transfer_to`, `call_sid`, `dispatcher_name` as parameters
- Normalize phone numbers to E.164 format
- Process single driver per call (use first driver from array)
- Create new FastAPI endpoint `/driver_data/call-elevenlabs` for testing
- Keep existing `/driver_data/call` endpoint with VAPI implementation intact

### API Integration Details

**ElevenLabs API Specifications:**
- Endpoint: `https://api.elevenlabs.io/v1/convai/twilio/outbound-call`
- Method: POST
- Authentication: Header `xi-api-key` with API key value
- Content-Type: `application/json`

**Request Payload Structure:**
```json
{
  "agent_id": "<hardcoded_agent_id>",
  "agent_phone_number_id": "<hardcoded_phone_number_id>",
  "to_number": "<normalized_E164_phone>",
  "conversation_initiation_client_data": {
    "dynamic_variables": {
      "prompt": "<generated_from_violations>",
      "transfer_to": "<parameter>",
      "call_sid": "<parameter>",
      "dispatcher_name": "<parameter>"
    }
  }
}
```

**Response Structure:**
```json
{
  "success": true,
  "message": "Success",
  "conversation_id": "conv_9601kaf71jfne4d9syfynwc35hc9",
  "callSid": "CAbcaf01bde90eaced8c0013d7ca66d216"
}
```

### Reusability Opportunities
- HTTP client pattern from VAPIClient (httpx.AsyncClient usage)
- Error handling patterns from VAPIClient
- Logging patterns using helpers.logger
- Phone number normalization logic from existing VAPI implementation
- BatchCallRequest model from models/vapi.py
- Violation processing logic from make_drivers_violation_batch_call
- Timeout configurations (30s for main operations)

### Scope Boundaries

**In Scope:**
- ElevenLabsClient class creation with basic call initiation
- New function for ElevenLabs batch calls in driver_data.py
- Configuration management for API key and agent/phone IDs
- Error handling similar to VAPIClient
- Retry logic (configurable from constants file)
- Phone number normalization
- Dynamic prompt generation from violations
- New FastAPI endpoint for ElevenLabs calls
- Response handling including conversation_id

**Out of Scope:**
- Webhook handling (ElevenLabs calls API directly)
- Removal of existing VAPI implementation (preserved for now)
- Frontend configuration of agent_id and agent_phone_number_id (hardcoded for now, future enhancement)
- Call status tracking or retrieval
- Call transcription processing
- Database updates based on call results
- Multi-driver batch processing (follows existing single-driver pattern)
- Migration of existing VAPI endpoints to ElevenLabs

### Technical Considerations

**Configuration:**
- Add `ELEVENLABS_API_KEY` to config.py Settings class
- Add `ELEVENLABS_API_KEY` to .env file (never commit)
- Hardcode `agent_id` and `agent_phone_number_id` as class variables in ElevenLabsClient
- Use existing Settings pattern from config.py with Pydantic BaseSettings

**Error Handling:**
- Implement try/except blocks similar to VAPIClient
- Handle httpx exceptions (TimeoutException, NetworkError)
- Handle API errors (4xx, 5xx status codes)
- Log errors using helpers.logger
- Raise appropriate HTTPException for FastAPI endpoints

**Retry Logic:**
- Make retry logic configurable from a constants file
- Follow exponential backoff pattern if applicable
- Consider max retry count (default 3 like db_retry)
- Log retry attempts

**Logging:**
- Use existing helpers.logger pattern
- Log incoming payloads (similar to make_drivers_violation_batch_call)
- Log outgoing API requests
- Log responses and errors
- Use consistent emoji-based logging for clarity

**Phone Number Handling:**
- Normalize to E.164 format: `+1{digits}` for US numbers
- Strip non-digit characters before normalization
- Handle numbers that already start with country code

**Independence from VAPI:**
- No shared code between ElevenLabs and VAPI implementations
- Separate client class, separate function
- Allows for clean VAPI removal in future
- Separate endpoint for testing before full migration

**Code Organization:**
- Follow existing FastAPI dual application architecture
- Place client in utils/ following VAPIClient pattern
- Place function in models/driver_data.py following existing pattern
- Use existing request models from models/vapi.py
- Follow SQLModel and Pydantic patterns used throughout codebase

**Testing Considerations:**
- New endpoint allows isolated testing without affecting existing VAPI functionality
- Can test side-by-side with VAPI implementation
- Single driver processing simplifies testing
- Response structure from ElevenLabs is simple and predictable

**Future Enhancements (noted but out of scope):**
- Make agent_id and agent_phone_number_id configurable from frontend
- Migrate all existing VAPI endpoints to ElevenLabs
- Remove VAPI implementation entirely
- Add call status tracking and retrieval
- Process call transcriptions and insights
- Update database based on call results
