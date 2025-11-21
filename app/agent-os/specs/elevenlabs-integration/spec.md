# Specification: ElevenLabs API Integration for Driver Violation Calls

## Goal
Replace VAPI implementation with ElevenLabs API for outbound driver violation calls while maintaining complete independence from existing VAPI code to enable clean removal later.

## User Stories
- As a dispatcher, I want to initiate violation calls using ElevenLabs API so that I can gradually migrate away from VAPI
- As a developer, I want independent ElevenLabs implementation so that VAPI code can be cleanly removed after migration

## Specific Requirements

**ElevenLabs Client Class**
- Create `utils/elevenlabs_client.py` with `ElevenLabsClient` class
- Follow VAPIClient pattern with base_url, api_key attributes
- Use httpx.AsyncClient for async HTTP operations
- Set base_url to `https://api.elevenlabs.io/v1/convai`
- Hardcode `agent_id` and `agent_phone_number_id` as class variables (future: configurable from frontend)
- Implement `create_outbound_call` async method for initiating calls
- Include timeout configuration (30 seconds for POST requests)

**Configuration Management**
- Add `ELEVENLABS_API_KEY` to `config.py` Settings class as required string field
- Add to `.env` file (never commit to version control)
- Access via `settings.ELEVENLABS_API_KEY` from config module
- Agent ID and phone number ID hardcoded in client class, not environment variables

**Batch Call Function**
- Create `make_drivers_violation_batch_call_elevenlabs` in `models/driver_data.py`
- Accept same `BatchCallRequest` model from `models/vapi.py` as input
- Process only first driver from drivers array (matches existing VAPI pattern)
- Return response dictionary including `conversation_id` from ElevenLabs API
- Use existing prompt generation logic from `generate_enhanced_conversational_prompt`

**API Integration**
- Call POST endpoint: `https://api.elevenlabs.io/v1/convai/twilio/outbound-call`
- Set headers: `xi-api-key` with API key, `Content-Type: application/json`
- Build payload with agent_id, agent_phone_number_id, to_number, conversation_initiation_client_data
- Include dynamic_variables with prompt, transfer_to, call_sid, dispatcher_name
- No webhook configuration needed (direct API call only)

**Phone Number Normalization**
- Normalize phone numbers to E.164 format before sending to API
- Strip non-digit characters using filter(str.isdigit, phone_number)
- Prepend +1 if number doesn't start with country code
- Handle numbers that already include country code prefix

**Dynamic Variable Handling**
- Generate prompt dynamically using existing `generate_enhanced_conversational_prompt` function
- Fetch trip data using `get_trip_data_for_violations` for personalized prompts
- Pass transfer_to, call_sid, dispatcher_name as parameters to function
- Include all dynamic variables in conversation_initiation_client_data.dynamic_variables

**Error Handling**
- Wrap API calls in try/except blocks catching httpx exceptions
- Handle httpx.TimeoutException with clear "Unable to reach ElevenLabs API" message
- Check response status codes, raise HTTPException for 4xx/5xx responses
- Log all errors using helpers.logger with descriptive messages
- Return user-friendly error messages without exposing technical details

**Retry Logic**
- Implement configurable retry mechanism for transient failures
- Use exponential backoff strategy for retries
- Default to 3 max retries (consistent with @db_retry pattern)
- Make retry count and delay configurable via constants file
- Log each retry attempt with attempt number

**FastAPI Endpoint**
- Create new POST endpoint `/driver_data/call-elevenlabs` in `services/driver_data.py`
- Accept `BatchCallRequest` as request body
- Call `make_drivers_violation_batch_call_elevenlabs` function
- Return success response with driver info, conversation_id, and metadata
- Keep existing `/driver_data/call` endpoint unchanged for gradual migration

**Logging and Debugging**
- Log incoming payload with full JSON structure (match existing pattern)
- Log normalized phone number for verification
- Log outgoing API request payload before sending
- Log API response including conversation_id and callSid
- Use consistent logging format with section separators (=== lines)
- Include emoji indicators for clarity (phone, checkmark, error symbols)

## Visual Design
No visual assets provided.

## Existing Code to Leverage

**utils/vapi_client.py**
- HTTP client pattern using httpx.AsyncClient with async/await
- Error handling structure with try/except blocks for httpx exceptions
- Timeout configuration (30 seconds POST, 10 seconds GET)
- Response validation checking status codes before parsing JSON
- Logging pattern using helpers.logger for info and error messages

**models/driver_data.py (make_drivers_violation_batch_call function, line 994)**
- Phone number normalization to E.164 format using filter and string operations
- Payload logging with full JSON dumps and section separators
- Single driver processing pattern (first item from drivers array)
- Integration with generate_enhanced_conversational_prompt for dynamic prompts
- HTTPException raising pattern for error responses

**models/driver_data.py (generate_enhanced_conversational_prompt function)**
- Dynamic prompt generation based on violation types and trip data
- Trip data fetching using get_trip_data_for_violations helper
- ViolationDetail object processing and mapping to database prompts
- Personalized prompt building with driver name and violation context
- Comprehensive logging of prompt generation process

**config.py Settings class**
- Pydantic BaseSettings pattern for environment variable management
- String fields for API keys and tokens
- Optional fields with default values using | None syntax
- Config class with env_file and extra="ignore" settings

**services/driver_data.py router pattern**
- APIRouter with prefix and tags for organization
- Async endpoint definitions using @router.post decorator
- Request model validation with Pydantic models
- Consistent response format with message and data/result fields

## Out of Scope
- Webhook handling or callback endpoints for ElevenLabs responses
- Call status tracking or retrieval functionality
- Call transcription processing or storage
- Database updates based on call results or outcomes
- Multi-driver batch processing (follows single-driver pattern)
- Frontend configuration interface for agent_id and agent_phone_number_id
- Migration of existing VAPI endpoints to ElevenLabs
- Removal or deprecation of existing VAPI implementation
- Integration testing or end-to-end test coverage
- Performance benchmarking between VAPI and ElevenLabs
