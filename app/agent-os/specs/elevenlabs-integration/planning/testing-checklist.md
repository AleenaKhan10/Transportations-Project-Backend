# Manual Testing Checklist: ElevenLabs Integration

## Overview
This checklist provides manual test scenarios for verifying the ElevenLabs API integration for driver violation calls.

## Prerequisites
- [ ] Virtual environment activated
- [ ] Server running on localhost:8000
- [ ] Valid ELEVENLABS_API_KEY in .env
- [ ] Postman or curl available
- [ ] Access to server logs

## Test Scenarios

### 1. Successful Call - Standard Phone Number

**Request:**
```bash
curl -X POST "http://localhost:8000/driver_data/call-elevenlabs"   -H "Content-Type: application/json"   -d '{
    "callType": "violation",
    "timestamp": "2025-11-20T10:00:00Z",
    "drivers": [{
      "driverId": "DR001",
      "driverName": "John Doe",
      "phoneNumber": "4155551234",
      "violations": {
        "tripId": "TRIP123",
        "violationDetails": [{
          "type": "speeding",
          "description": "Exceeded speed limit by 15 mph"
        }]
      }
    }]
  }'
```

**Expected:** 200 OK with conversation_id and normalized phone +14155551234

**Verify:**
- [ ] Status 200
- [ ] Phone normalized to +14155551234
- [ ] conversation_id present
- [ ] triggers_count = 1
- [ ] Logs show incoming payload
- [ ] Logs show phone normalization
- [ ] Logs show API request/response

---

### 2. Phone with Country Code

**Phone:** "14155555678"
**Expected:** Normalized to +14155555678 (not +114155555678)

**Verify:**
- [ ] Correct normalization
- [ ] Logs show before/after

---

### 3. Phone with Special Characters

**Phone:** "(415) 555-9012"
**Expected:** Normalized to +14155559012

**Verify:**
- [ ] Special chars stripped
- [ ] Correct E.164 format

---

### 4. Multiple Violations

**Request:** Single driver with 3 violations

**Verify:**
- [ ] triggers_count = 3
- [ ] All violations in logs
- [ ] Prompt includes all violations

---

### 5. Multiple Drivers

**Request:** Array with 2 drivers

**Verify:**
- [ ] Only first driver processed
- [ ] Response shows first driver info
- [ ] Logs show "Number of Drivers: 2"
- [ ] Second driver ignored

---

### 6. Empty Drivers Array

**Request:** drivers: []

**Expected:** 400 Bad Request

**Verify:**
- [ ] Status 400
- [ ] Error: "No driver data provided"
- [ ] No API call made

---

### 7. Missing Required Fields

**Request:** Missing timestamp or phoneNumber

**Expected:** 422 Unprocessable Entity

**Verify:**
- [ ] Status 422
- [ ] Validation error details
- [ ] No API call made

---

### 8. Invalid API Key

**Setup:** Set invalid ELEVENLABS_API_KEY, restart server

**Expected:** 500 Internal Server Error

**Verify:**
- [ ] Status 500
- [ ] Error mentions authentication
- [ ] Logs show 401 from ElevenLabs
- [ ] Retry attempts logged (up to 3)

**Cleanup:** Restore valid key, restart

---

### 9. Logging Format Verification

**Test:** Run Scenario 1 and check logs

**Verify:**
- [ ] Separator lines (100 =)
- [ ] "INCOMING PAYLOAD" header
- [ ] Full JSON with indent
- [ ] "PHONE NUMBER NORMALIZATION" section
- [ ] "GENERATED PROMPT" section
- [ ] "ELEVENLABS API REQUEST PAYLOAD" section
- [ ] "ELEVENLABS API RESPONSE" section
- [ ] No API keys in logs

---

### 10. API Documentation

**Steps:**
1. Visit http://localhost:8000/docs
2. Find POST /driver_data/call-elevenlabs
3. Check summary and description
4. Try "Try it out" with valid payload
5. Visit http://localhost:8000/redoc
6. Verify same documentation

**Verify:**
- [ ] Endpoint visible in Swagger
- [ ] Summary correct
- [ ] Request/response schemas shown
- [ ] "Try it out" works
- [ ] ReDoc shows correctly

---

## Edge Cases to Test

- [ ] Phone: "+14155556789"
- [ ] Phone: "415-555-6789"
- [ ] Phone: "415.555.6789"
- [ ] Null violations
- [ ] Empty violationDetails
- [ ] Missing tripId

---

## Comparison with VAPI

**Test:** Send same payload to both endpoints

**Verify:**
- [ ] /driver_data/call still works
- [ ] /driver_data/call-elevenlabs works
- [ ] Response structures similar
- [ ] Both independent

---

## Summary

- [ ] All success scenarios work
- [ ] Phone normalization correct
- [ ] Error handling works
- [ ] Logging consistent
- [ ] Documentation complete
- [ ] VAPI unaffected
- [ ] No sensitive data logged

