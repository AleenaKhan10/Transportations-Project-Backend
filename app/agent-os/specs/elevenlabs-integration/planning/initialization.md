# Spec Initialization: ElevenLabs Integration

## Feature Description
Implement a service layer for ElevenLabs API to replace the current VAPI implementation. Create a new function similar to `make_drivers_violation_batch_call` that uses ElevenLabs API for outbound calls.

## Key Requirements
1. Create a new service layer/client for ElevenLabs API integration
2. Implement a function similar to `make_drivers_violation_batch_call` but using ElevenLabs instead of VAPI
3. Keep the existing `make_drivers_violation_batch_call` function intact (don't remove it)
4. Replace usage of `make_drivers_violation_batch_call` with the new ElevenLabs implementation

## Technical Details from User
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

## Context from Codebase
- This is part of the critical VAPI → ElevenLabs migration (Phase 1 of product roadmap)
- Current VAPI implementation exists in `utils/vapi_client.py`
- Function `make_drivers_violation_batch_call` currently uses VAPI for driver calls
- Project uses FastAPI backend with Python, PostgreSQL database
- Configuration managed through Pydantic Settings in `config.py`

## Initialization Date
2025-11-20

## Status
Requirements gathering phase
