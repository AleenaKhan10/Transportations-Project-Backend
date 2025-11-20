# Task Breakdown: ElevenLabs API Integration for Driver Violation Calls

## Overview
Total Tasks: 4 Task Groups with approximately 25-30 sub-tasks
Estimated Duration: 2-3 days

## Task List

### Backend Integration Layer

#### Task Group 1: Configuration and Client Setup
**Dependencies:** None

- [x] 1.0 Complete configuration and ElevenLabs client implementation
  - [x] 1.1 Write 2-8 focused tests for ElevenLabsClient functionality
    - Limit to 2-8 highly focused tests maximum
    - Test only critical client behaviors (e.g., successful call creation, API authentication, timeout handling)
    - Skip exhaustive coverage of all error scenarios and edge cases
    - Place tests in appropriate test directory following project structure
  - [x] 1.2 Add ELEVENLABS_API_KEY to config.py Settings class
    - Add as required string field in Settings class
    - Follow existing pattern from VAPI_API_KEY
    - Verify it loads from .env using Pydantic BaseSettings
  - [x] 1.3 Update .env file with ELEVENLABS_API_KEY
    - Add placeholder: ELEVENLABS_API_KEY=your_api_key_here
    - Include comment: # Never commit this file to version control
    - Verify .env is in .gitignore
  - [x] 1.4 Create utils/elevenlabs_client.py with ElevenLabsClient class
    - Define class with __init__ method
    - Set base_url to "https://api.elevenlabs.io/v1/convai"
    - Load api_key from settings.ELEVENLABS_API_KEY
    - Hardcode agent_id as class variable: "agent_5501k9czkv3qepy815bm59nt04qk"
    - Hardcode agent_phone_number_id as class variable: "phnum_8401k9ndc950ewza733y8thmpbrx"
    - Import httpx and helpers.logger
    - Follow VAPIClient structure from utils/vapi_client.py
  - [x] 1.5 Implement create_outbound_call async method
    - Accept parameters: to_number (str), prompt (str), transfer_to (str), call_sid (str), dispatcher_name (str)
    - Build payload with agent_id, agent_phone_number_id, to_number, conversation_initiation_client_data
    - Include dynamic_variables dict with prompt, transfer_to, call_sid, dispatcher_name
    - Use httpx.AsyncClient with 30 second timeout
    - Set headers: xi-api-key and Content-Type: application/json
    - POST to f"{self.base_url}/twilio/outbound-call"
    - Return parsed JSON response
  - [x] 1.6 Add comprehensive error handling to client
    - Wrap API call in try/except block
    - Handle httpx.TimeoutException with "Unable to reach ElevenLabs API" message
    - Check response.status_code >= 400 and raise Exception with status and text
    - Log all errors using logger.error with descriptive messages
    - Follow error handling pattern from VAPIClient
  - [x] 1.7 Implement retry logic with exponential backoff
    - Create retry decorator or inline retry logic
    - Default max_retries to 3 (configurable via class constant)
    - Use exponential backoff: delay = 2 ** attempt seconds
    - Log each retry attempt with attempt number
    - Follow @db_retry pattern from db/retry.py
  - [x] 1.8 Add detailed logging throughout client
    - Log call initiation with driver info and phone number
    - Log outgoing API request payload (use logger.info)
    - Log API response with conversation_id and callSid
    - Use emoji indicators for clarity (phone, checkmark, error symbols)
    - Follow logging pattern from VAPIClient
  - [x] 1.9 Create global client instance
    - Add at bottom of file: elevenlabs_client = ElevenLabsClient()
    - Follow pattern from vapi_client.py
  - [x] 1.10 Ensure client layer tests pass
    - Run ONLY the 2-8 tests written in 1.1
    - Verify client initializes correctly
    - Verify API call structure is correct (can use mocked responses)
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 1.1 pass
- ELEVENLABS_API_KEY loads from config successfully
- ElevenLabsClient class initializes with correct base_url and hardcoded IDs
- create_outbound_call method builds correct payload structure
- Error handling catches httpx exceptions and API errors
- Retry logic executes with exponential backoff
- Comprehensive logging outputs at all stages

---

### Business Logic Layer

#### Task Group 2: Driver Violation Batch Call Function
**Dependencies:** Task Group 1

- [x] 2.0 Complete ElevenLabs batch call business logic
  - [x] 2.1 Write 2-8 focused tests for batch call function
    - Limit to 2-8 highly focused tests maximum
    - Test only critical function behaviors (e.g., phone normalization, single driver processing, prompt generation integration)
    - Skip exhaustive testing of all violation types and scenarios
    - Place tests in appropriate test directory
  - [x] 2.2 Create make_drivers_violation_batch_call_elevenlabs function in models/driver_data.py
    - Place after existing make_drivers_violation_batch_call function
    - Accept BatchCallRequest parameter
    - Add async def signature
    - Import elevenlabs_client from utils/elevenlabs_client
    - Add function docstring explaining single driver processing
  - [x] 2.3 Implement incoming payload logging
    - Print separator lines (100 equals signs)
    - Print section header: "INCOMING PAYLOAD - Full Request Received"
    - Log callType, timestamp, number of drivers
    - Use json.dumps with indent=2 for full payload structure
    - Follow exact logging pattern from make_drivers_violation_batch_call (line 1002-1030)
  - [x] 2.4 Extract and validate first driver from request
    - Check if request.drivers is empty, raise HTTPException 400 if no drivers
    - Get first driver: driver = request.drivers[0]
    - Log processing message with driver name and ID
    - Follow pattern from line 1033-1038 in driver_data.py
  - [x] 2.5 Implement phone number normalization to E.164 format
    - Strip non-digit characters: phone_digits = "".join(filter(str.isdigit, driver.phoneNumber))
    - Prepend +1 if doesn't start with "1": normalized_phone = f"+1{phone_digits}" or f"+{phone_digits}"
    - Log normalized phone number with separator lines
    - Follow exact pattern from line 1041-1042 in driver_data.py
  - [x] 2.6 Generate dynamic prompt using existing function
    - Call generate_enhanced_conversational_prompt with driver violations
    - Pass driver.violations.tripId to fetch trip data
    - Handle None trip_id gracefully
    - Extract prompt from returned dict: prompt_text = prompt_result.get("prompt", "")
    - Log prompt generation result
    - Reuse pattern from generate_prompt_for_driver function
  - [x] 2.7 Call ElevenLabs client with generated data
    - Prepare parameters: transfer_to, call_sid, dispatcher_name (hardcode defaults for now)
    - Call elevenlabs_client.create_outbound_call with normalized_phone, prompt_text, and parameters
    - Await response and parse conversation_id
    - Wrap in try/except for HTTPException and general Exception
  - [x] 2.8 Build and return success response
    - Return dict with message, timestamp, driver info (driverId, driverName, phoneNumber)
    - Include conversation_id from ElevenLabs response
    - Include callSid from ElevenLabs response
    - Include triggers_count for monitoring
    - Log success message with driver name
    - Follow response pattern from line 1086-1096 in driver_data.py
  - [x] 2.9 Add comprehensive error handling
    - Catch HTTPException and re-raise
    - Catch general Exception with traceback
    - Log errors with full traceback using logger.error
    - Raise HTTPException 500 with user-friendly message
    - Follow error handling pattern from line 1098-1107 in driver_data.py
  - [x] 2.10 Ensure business logic tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify phone normalization works correctly
    - Verify function processes first driver only
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- Function accepts BatchCallRequest and processes first driver
- Phone numbers normalize correctly to E.164 format
- Prompt generates dynamically from violations and trip data
- ElevenLabs client called with correct parameters
- Success response includes conversation_id and driver info
- Errors caught and logged with appropriate HTTPException responses

---

### API Endpoint Layer

#### Task Group 3: FastAPI Endpoint Implementation
**Dependencies:** Task Group 2

- [x] 3.0 Complete FastAPI endpoint for ElevenLabs calls
  - [x] 3.1 Write 2-8 focused tests for API endpoint
    - Limit to 2-8 highly focused tests maximum
    - Test only critical endpoint behaviors (e.g., request validation, successful call response, error response format)
    - Skip exhaustive testing of all payload variations
    - Place tests in appropriate test directory
  - [x] 3.2 Import new function in services/driver_data.py
    - Add make_drivers_violation_batch_call_elevenlabs to imports from models.driver_data
    - Verify BatchCallRequest already imported from models.vapi
    - Check existing router configuration (prefix="/driver_data", tags=["driver_data"])
  - [x] 3.3 Create new POST endpoint /driver_data/call-elevenlabs
    - Use @router.post("/call-elevenlabs") decorator
    - Define async def endpoint function
    - Accept request: BatchCallRequest parameter
    - Add descriptive docstring explaining ElevenLabs integration
  - [x] 3.4 Call batch call function and return response
    - Await make_drivers_violation_batch_call_elevenlabs(request)
    - Capture response dict
    - Return response directly (already formatted)
    - Wrap in try/except for proper error handling
  - [x] 3.5 Add endpoint-level error handling
    - Catch HTTPException and re-raise (preserves status codes)
    - Catch general Exception and return 500 with detail
    - Log endpoint errors using logger.error
    - Follow FastAPI error handling best practices
  - [x] 3.6 Add endpoint documentation
    - Add summary parameter to @router.post decorator
    - Add description explaining ElevenLabs vs VAPI endpoint
    - Document expected request structure
    - Document response structure with conversation_id
  - [x] 3.7 Verify endpoint registration in main.py
    - Check that driver_data router is included in main app
    - Verify router imports and include_router call exist
    - No changes needed if already registered (which it should be)
  - [x] 3.8 Ensure API endpoint tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify endpoint accepts BatchCallRequest
    - Verify endpoint returns proper response structure
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 3.1 pass
- New POST endpoint /driver_data/call-elevenlabs exists and is accessible
- Endpoint accepts BatchCallRequest validation
- Endpoint returns response with conversation_id and driver info
- Errors handled gracefully with appropriate status codes
- API documentation displays correctly in Swagger/ReDoc
- Existing /driver_data/call endpoint remains unchanged

---

### Testing and Documentation

#### Task Group 4: Integration Testing and Documentation
**Dependencies:** Task Groups 1-3

- [ ] 4.0 Review existing tests and document implementation
  - [ ] 4.1 Review tests from Task Groups 1-3
    - Review the 2-8 tests written by config/client engineer (Task 1.1)
    - Review the 2-8 tests written by business logic engineer (Task 2.1)
    - Review the 2-8 tests written by API engineer (Task 3.1)
    - Total existing tests: approximately 6-24 tests
  - [ ] 4.2 Analyze test coverage gaps for ElevenLabs integration only
    - Identify critical integration workflows that lack test coverage
    - Focus ONLY on gaps related to ElevenLabs integration feature
    - Do NOT assess entire application test coverage
    - Prioritize end-to-end call workflow over unit test gaps
  - [ ] 4.3 Write up to 10 additional strategic tests maximum (if needed)
    - Add maximum of 10 new tests to fill identified critical gaps
    - Focus on integration between client, business logic, and API endpoint
    - Test phone normalization edge cases (already has country code, missing digits)
    - Test prompt generation integration with violations
    - Test error propagation through layers
    - Do NOT write comprehensive coverage for all scenarios
    - Skip performance tests and load testing
  - [ ] 4.4 Create manual testing checklist document
    - Document test scenarios for manual verification
    - Include: successful call, phone number variations, error scenarios
    - Include API payload examples for Postman/curl testing
    - Document expected responses for each scenario
    - Place in agent-os/specs/elevenlabs-integration/planning/testing-checklist.md
  - [ ] 4.5 Update CLAUDE.md with ElevenLabs integration notes
    - Add section documenting ElevenLabs client location and purpose
    - Document new endpoint /driver_data/call-elevenlabs
    - Note independence from VAPI implementation
    - Add to "Key Integrations" section
    - Keep documentation concise and reference-focused
  - [ ] 4.6 Create implementation notes document
    - Document hardcoded agent_id and agent_phone_number_id values
    - Document retry configuration (max_retries=3, exponential backoff)
    - Document phone normalization approach
    - Note future enhancements (frontend configuration)
    - Place in agent-os/specs/elevenlabs-integration/planning/implementation-notes.md
  - [ ] 4.7 Run feature-specific tests only
    - Run ONLY tests related to ElevenLabs integration (tests from 1.1, 2.1, 3.1, and 4.3)
    - Expected total: approximately 16-34 tests maximum
    - Do NOT run the entire application test suite
    - Verify critical workflows pass (client creation, batch call, endpoint)
  - [ ] 4.8 Perform manual smoke testing
    - Activate virtualenv: source .venv/Scripts/activate
    - Start server: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    - Test endpoint with curl or Postman using valid BatchCallRequest
    - Verify conversation_id returned in response
    - Verify phone number normalization in logs
    - Test with invalid payload and verify error handling
  - [ ] 4.9 Verify logging output format
    - Check logs contain incoming payload section (with separators)
    - Check logs contain normalized phone number
    - Check logs contain API request/response details
    - Verify emoji indicators present for readability
    - Confirm no sensitive data logged (API keys masked)
  - [ ] 4.10 Document known limitations
    - Document single-driver processing limitation
    - Document hardcoded parameter defaults (transfer_to, call_sid, dispatcher_name)
    - Note webhook handling is out of scope
    - Note call status tracking is out of scope
    - Place in agent-os/specs/elevenlabs-integration/planning/limitations.md

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 16-34 tests total)
- Critical integration workflows for ElevenLabs feature are covered
- No more than 10 additional tests added when filling in testing gaps
- Manual testing checklist created and verified
- CLAUDE.md updated with ElevenLabs integration information
- Implementation notes and limitations documented
- Manual smoke test confirms endpoint works end-to-end
- Logging output follows consistent format with proper detail

---

## Execution Order

Recommended implementation sequence:
1. **Configuration and Client Setup** (Task Group 1) - Foundation layer with ElevenLabs client and configuration
2. **Business Logic Layer** (Task Group 2) - Core batch call function leveraging existing prompt generation
3. **API Endpoint Layer** (Task Group 3) - FastAPI endpoint exposing ElevenLabs functionality
4. **Integration Testing and Documentation** (Task Group 4) - Test gap analysis, manual testing, and documentation

---

## Technical Dependencies

### External Dependencies
- httpx (already in project) - for async HTTP client
- FastAPI (already in project) - for API endpoint
- Pydantic (already in project) - for settings and request validation

### Internal Dependencies
- config.py Settings class - for ELEVENLABS_API_KEY configuration
- models/vapi.py - for BatchCallRequest model (reused)
- models/driver_data.py - for generate_enhanced_conversational_prompt function
- helpers.logger - for consistent logging throughout implementation
- services/driver_data.py router - for new endpoint registration

### Environment Dependencies
- .env file with ELEVENLABS_API_KEY
- Virtual environment activation before testing
- Database connection (for trip data fetching in prompt generation)

---

## Testing Strategy

### Unit Testing Focus
- ElevenLabsClient initialization and configuration loading
- create_outbound_call method payload construction
- Phone number normalization edge cases
- Error handling for network failures and API errors
- Retry logic execution with exponential backoff

### Integration Testing Focus
- End-to-end flow from API endpoint to ElevenLabs API call
- Prompt generation integration with violation data
- Response structure validation with conversation_id
- Error propagation through all layers
- Logging consistency across client, business logic, and endpoint

### Manual Testing Scenarios
- Valid BatchCallRequest with single driver
- Phone numbers with various formats (with/without country code)
- Missing or invalid API key configuration
- Network timeout simulation
- Invalid violation data causing prompt generation failure

---

## Implementation Notes

### Code Reuse Strategy
- HTTP client pattern from VAPIClient (httpx.AsyncClient, async/await, timeouts)
- Error handling structure from VAPIClient (try/except, httpx exceptions)
- Logging pattern from VAPIClient (helpers.logger with emoji indicators)
- Phone normalization from make_drivers_violation_batch_call (filter and format)
- Payload logging from make_drivers_violation_batch_call (JSON dumps with separators)
- Prompt generation from generate_enhanced_conversational_prompt (existing function)

### Independence from VAPI
- Completely separate client class (no shared code with VAPIClient)
- Completely separate batch call function (no shared code with VAPI batch call)
- Separate endpoint (existing VAPI endpoint remains unchanged)
- Enables clean removal of VAPI implementation in future without affecting ElevenLabs

### Configuration Approach
- API key: Environment variable via Pydantic Settings (secure, configurable per environment)
- Agent ID and Phone Number ID: Hardcoded class variables (temporary, future enhancement for frontend config)
- Retry settings: Class constants (configurable without code changes)

### Error Handling Strategy
- Client layer: Catch httpx exceptions, validate status codes, log errors
- Business logic layer: Catch client errors, add context, raise HTTPException
- API endpoint layer: Catch HTTPException (preserve status), catch general Exception (500 status)
- All layers: Use helpers.logger for consistent error logging with traceback

---

## Future Enhancements (Out of Scope)

The following items are noted for future consideration but NOT included in this implementation:

- Make agent_id and agent_phone_number_id configurable from frontend interface
- Implement webhook handling for ElevenLabs call status updates
- Add call status tracking and retrieval functionality
- Process and store call transcriptions in database
- Update driver records based on call outcomes
- Support multi-driver batch processing (beyond single driver)
- Migrate existing VAPI endpoints to ElevenLabs
- Remove VAPI implementation entirely from codebase
- Performance benchmarking between VAPI and ElevenLabs
- Integration with call analytics and reporting systems
