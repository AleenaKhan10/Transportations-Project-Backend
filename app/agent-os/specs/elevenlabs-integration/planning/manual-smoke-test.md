# Manual Smoke Test Guide

## Task 4.8: Smoke Testing

### Start Server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

### Test Valid Request
curl -X POST http://localhost:8000/driver_data/call-elevenlabs with valid payload

### Verify Response
- Status 200
- Phone normalized to +1 format
- conversation_id present

### Task 4.9: Verify Logging
Check logs for 5 sections:
1. INCOMING PAYLOAD
2. PHONE NORMALIZATION
3. GENERATED PROMPT
4. API REQUEST
5. API RESPONSE

All with 100-char separators
No API keys in logs
