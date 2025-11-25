# WebSocket Real-Time Transcription Test

This Node.js script tests the complete ElevenLabs integration for real-time call transcription and WebSocket updates.

## What This Test Does

The test verifies that both systems are working correctly:

1. **Real-Time Transcription** - ElevenLabs webhooks saving dialogue to database
2. **WebSocket Real-Time Updates** - Live broadcast of transcriptions to connected clients

### Test Flow

```
1. Authenticate user and get JWT token
2. Initiate ElevenLabs call via POST /driver_data/call-elevenlabs
3. Connect to WebSocket endpoint with JWT token
4. Subscribe to the call using call_sid
5. Receive real-time transcriptions as call progresses (WebSocket messages)
6. Wait for call to complete
7. Fetch complete conversation history via REST API
8. Compare real-time vs fetched transcriptions
9. Display summary and results
```

## Prerequisites

1. **Backend server running** on `localhost:8000` (or configure API_BASE_URL)
2. **ElevenLabs API credentials** configured in backend
3. **Valid test user** in the database
4. **Test phone number** that can receive calls (for actual call testing)
5. **Node.js** installed (version 14+)

## Installation

1. Navigate to the tests directory:
```bash
cd tests
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Edit `.env` with your configuration:
```env
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000
TEST_USERNAME=your-test-user@example.com
TEST_PASSWORD=your-test-password
TEST_PHONE_NUMBER=+1234567890
```

## Running the Test

### Full Test (Actual Call)
This will initiate a real ElevenLabs call to the test phone number:

```bash
npm test
```

or

```bash
node websocket_test.js
```

### Expected Output

```
================================================================================
  WebSocket Real-Time Transcription Test
================================================================================

[2025-11-22T10:30:00.000Z] [AUTH] Authenticating user...
{
  "username": "test@example.com",
  "token_prefix": "eyJhbGciOiJIUzI1NiI..."
}

[2025-11-22T10:30:01.000Z] [CALL] Initiating ElevenLabs call...
{
  "call_sid": "EL_TEST_DRIVER_001_1732276200",
  "conversation_id": "conv_abc123xyz",
  "driver": {
    "driverId": "TEST_DRIVER_001",
    "driverName": "John Test Driver"
  }
}

[2025-11-22T10:30:02.000Z] [WS] Connecting to WebSocket...
[2025-11-22T10:30:02.500Z] [WS] WebSocket connected successfully!
[2025-11-22T10:30:02.600Z] [WS_MSG] Subscription confirmed!

[2025-11-22T10:30:15.000Z] [WS_MSG] New transcription [agent]
   [0] AGENT: Hey John, this is dispatch calling. Do you have a few minutes?

[2025-11-22T10:30:20.000Z] [WS_MSG] New transcription [driver]
   [1] DRIVER: Yeah, sure. What's up?

[2025-11-22T10:30:25.000Z] [WS_MSG] New transcription [agent]
   [2] AGENT: I noticed your temperature is at 45 degrees but needs to be 38...

... (more transcriptions as call progresses) ...

[2025-11-22T10:32:00.000Z] [WS_MSG] Call status update!
{
  "status": "completed",
  "call_end_time": "2025-11-22T10:32:00.000Z"
}

[2025-11-22T10:32:01.000Z] [WS_MSG] Call completed with full data!
{
  "duration": 120,
  "cost": 0.08,
  "successful": true,
  "summary": "Driver acknowledged temperature issue..."
}

[2025-11-22T10:32:03.000Z] [FETCH] Fetching complete conversation history...
[2025-11-22T10:32:04.000Z] [FETCH] Conversation fetched successfully!

[2025-11-22T10:32:04.500Z] [COMPARE] Comparing real-time vs fetched transcriptions...

=== REAL-TIME TRANSCRIPTIONS (WebSocket) ===
Total received: 12
  [0] agent: Hey John, this is dispatch calling...
  [1] driver: Yeah, sure. What's up?
  ...

=== FETCHED TRANSCRIPTIONS (REST API) ===
Total fetched: 12
  [0] agent: Hey John, this is dispatch calling...
  [1] driver: Yeah, sure. What's up?
  ...

[2025-11-22T10:32:05.000Z] [COMPARE] SUCCESS: Counts match!
{
  "real_time_count": 12,
  "fetched_count": 12
}

================================================================================
  TEST SUMMARY
================================================================================
Call SID: EL_TEST_DRIVER_001_1732276200
Conversation ID: conv_abc123xyz
Real-time transcriptions received: 12
Fetched transcriptions: 12
Call completed: YES
================================================================================
```

## Test Results Interpretation

### Success Indicators

- **Authentication successful** - JWT token obtained
- **Call initiated successfully** - call_sid and conversation_id received
- **WebSocket connected** - Connection established
- **Subscription confirmed** - Subscribed to call updates
- **Transcriptions received in real-time** - Messages appear as call progresses
- **Call status update received** - Call completion notification
- **Call completed message received** - Full call data with metadata
- **Conversation fetched** - REST API returns complete history
- **Counts match** - Real-time count equals fetched count
- **Content matches** - Messages are identical

### Failure Scenarios

1. **Authentication failed**
   - Check TEST_USERNAME and TEST_PASSWORD in .env
   - Verify user exists in database

2. **Call initiation failed**
   - Check ElevenLabs API credentials in backend
   - Verify phone number is in E.164 format (+1XXXXXXXXXX)
   - Check backend logs for detailed errors

3. **WebSocket connection failed**
   - Verify backend is running on correct port
   - Check JWT token is valid
   - Ensure WebSocket endpoint is accessible

4. **No transcriptions received**
   - Call may not have started yet (wait longer)
   - Check ElevenLabs webhook configuration
   - Verify backend webhook endpoint is accessible from ElevenLabs

5. **Counts don't match**
   - Some transcriptions may have been lost
   - Check for network issues
   - Review backend logs for webhook failures

## Troubleshooting

### Test Phone Number Issues

If you don't want to use a real phone number:

1. Use ElevenLabs test mode (if available)
2. Configure a test agent with shorter timeouts
3. Use ngrok to expose local backend for webhook testing

### Backend Not Receiving Webhooks

1. Check ElevenLabs webhook URL configuration
2. Verify ngrok or public URL is accessible
3. Check firewall rules
4. Review backend logs for incoming webhook requests

### WebSocket Disconnects

1. Check for connection timeouts (increase timeout if needed)
2. Verify JWT token hasn't expired
3. Check backend logs for disconnection reasons
4. Ensure backend WebSocket implementation is stable

### Test Hangs/Timeout

The test waits up to 10 minutes for call completion. If call takes longer:

1. Increase timeout in websocket_test.js (line 434)
2. Manually interrupt (Ctrl+C) and check partial results
3. Reduce call complexity (fewer violations)

## Customization

### Modify Test Data

Edit the TEST_DRIVER object in websocket_test.js:

```javascript
const TEST_DRIVER = {
    driverId: 'YOUR_DRIVER_ID',
    driverName: 'Your Driver Name',
    phoneNumber: '+1XXXXXXXXXX',
    customRules: 'Your custom instructions',
    violations: {
        tripId: 'YOUR_TRIP_ID',
        violationDetails: [
            {
                type: 'violation',
                description: 'Your violation description'
            }
        ]
    }
};
```

### Adjust Timeout

Change the timeout value (default 10 minutes):

```javascript
const timeout = 5 * 60 * 1000; // 5 minutes
```

### Add More Logging

Enable debug logging by adding console.log statements in handleWebSocketMessage():

```javascript
case 'transcription':
    console.log('DEBUG: Raw transcription message:', message);
    // ... rest of code
```

## Architecture Reference

This test validates the complete flow documented in:

- **Frontend Integration Guide**: `agent-os/specs/.../FRONTEND_INTEGRATION_GUIDE.md`
- **API Documentation**: `agent-os/specs/.../api-documentation.md`
- **WebSocket Manager**: `services/websocket_manager.py`
- **WebSocket Messages**: `models/websocket_messages.py`
- **Transcription Webhook**: `services/webhooks_elevenlabs.py`

## Dependencies

- **ws** (^8.14.2) - WebSocket client for Node.js
- **node-fetch** (^2.7.0) - Fetch API for Node.js (HTTP requests)
- **dotenv** (^16.3.1) - Environment variable management (optional)

## License

MIT
