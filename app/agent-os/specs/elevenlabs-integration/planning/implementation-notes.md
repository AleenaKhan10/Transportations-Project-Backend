# Implementation Notes: ElevenLabs Integration

## Hardcoded Configuration

**Agent ID:** agent_5501k9czkv3qepy815bm59nt04qk
**Phone Number ID:** phnum_8401k9ndc950ewza733y8thmpbrx
**Location:** utils/elevenlabs_client.py (lines 17-18)

**Future:** Move to database config with admin UI

## Retry Configuration

**MAX_RETRIES:** 3
**Backoff:** Exponential (2^attempt seconds = 2s, 4s)
**Total Max Wait:** 6 seconds
**Location:** utils/elevenlabs_client.py (line 21)

## Default Parameters

**Location:** models/driver_data.py (lines 1225-1227)
- transfer_to: +18005551234
- call_sid: EL_{driverId}_{timestamp}
- dispatcher_name: AGY Dispatcher

**Future:** Load from settings, use UUID, pull from auth session

## Phone Normalization

**Location:** models/driver_data.py (lines 1173-1174)

Strips non-digits, prepends +1 if needed:
- 4155551234 → +14155551234
- 14155551234 → +14155551234
- (415) 555-1234 → +14155551234

**Limitation:** US-only, no validation
**Future:** Use phonenumbers library, international support

## Prompt Generation

Reuses generate_enhanced_conversational_prompt:
1. Fetch trip data (get_trip_data_for_violations)
2. Convert ViolationDetail format
3. Generate prompt with context
4. Handle None trip_id gracefully

## Error Handling

**Layer 1 (Client):** httpx exceptions, retry logic
**Layer 2 (Business Logic):** Add context, HTTPException
**Layer 3 (Endpoint):** Preserve status codes, 500 fallback

**Retry:** Timeout/network errors only
**No Retry:** 4xx/5xx API responses

## Logging

Five sections with 100-char separators:
1. INCOMING PAYLOAD
2. PHONE NORMALIZATION  
3. GENERATED PROMPT
4. API REQUEST
5. API RESPONSE

**Security:** No API keys logged

## Response Structure

**Success (200):**
- message, timestamp, driver, conversation_id, callSid, triggers_count

**Errors:**
- 400: No driver data
- 422: Validation errors  
- 500: Call failed

## VAPI Independence

**Separate:** Client, batch function, endpoint
**Shared:** Models, prompt generation, logging
**Goal:** Clean VAPI removal later

## Performance

- Normal: 500-2000ms
- With retries: up to +12s
- DB queries: <100ms

## Testing

- 22 automated tests (7 + 8 + 7)
- 10 manual scenarios
- Comprehensive coverage

## Dependencies

**External:** ElevenLabs API, httpx
**Internal:** config, models, helpers.logger
**Env:** ELEVENLABS_API_KEY, DB_* variables

## Future Roadmap

1. Frontend config UI
2. Webhook handling
3. Multi-driver processing
4. Analytics
5. VAPI deprecation
