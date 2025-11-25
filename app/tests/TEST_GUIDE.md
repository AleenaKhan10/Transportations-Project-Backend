# WebSocket Real-Time Transcription Testing Guide

This guide explains how to test both Real-Time Transcription and WebSocket Real-Time Updates for the ElevenLabs integration.

## What Gets Tested

### 1. Real-Time Transcription System
- ElevenLabs sends webhooks to `/webhooks/elevenlabs/transcription` during calls
- Backend saves dialogue turns to database (`call_transcriptions` table)
- Each transcription includes: speaker, message, timestamp, sequence number
- Verifies data persistence and integrity

### 2. WebSocket Real-Time Updates
- WebSocket endpoint: `/ws/calls/transcriptions?token=JWT`
- Client subscribes to specific calls using `call_sid` or `conversation_id`
- Server broadcasts messages in real-time:
  - `transcription` - Each dialogue turn as it happens
  - `call_status` - When call completes
  - `call_completed` - Full call data with analysis
- Verifies live message delivery and subscription management

## Files Created

### Test Scripts

1. **websocket_test.js** - Full integration test
   - Authenticates user
   - Initiates ElevenLabs call
   - Connects to WebSocket
   - Receives real-time transcriptions
   - Fetches conversation via REST API
   - Compares real-time vs fetched data
   - **Duration**: 2-10 minutes (depends on call length)

2. **websocket_simple_test.js** - Simple connectivity test
   - Quick WebSocket connection test
   - No call initiation (uses existing call_sid)
   - Just monitors messages
   - **Duration**: Instant (runs until stopped)

### Configuration Files

3. **package.json** - Node.js dependencies and scripts
   - Dependencies: `ws`, `node-fetch`
   - Scripts: `npm test`, `npm run test:simple`

4. **.env.example** - Environment variables template
   - API_BASE_URL, WS_BASE_URL
   - TEST_USERNAME, TEST_PASSWORD
   - TEST_PHONE_NUMBER

### Documentation

5. **README_WEBSOCKET_TEST.md** - Detailed documentation
   - Installation instructions
   - Usage examples
   - Expected output
   - Troubleshooting guide

6. **TEST_GUIDE.md** - This file
   - Overview of testing approach
   - Quick start guide

### Automation Scripts

7. **install_and_run.bat** - Windows batch script
   - Automated setup and execution
   - Checks Node.js installation
   - Installs dependencies
   - Creates .env from template
   - Runs the test

## Quick Start

### Option 1: Full Automated Test (Windows)

```bash
# Double-click install_and_run.bat or run:
install_and_run.bat
```

This will:
1. Check for Node.js
2. Install dependencies
3. Create .env file
4. Run the full test

### Option 2: Manual Setup (All Platforms)

```bash
# 1. Navigate to tests directory
cd tests

# 2. Install dependencies
npm install

# 3. Create .env file
cp .env.example .env

# 4. Edit .env with your credentials
# (Use your favorite text editor)

# 5. Run full test
npm test

# OR run simple WebSocket test
npm run test:simple CALL_SID_HERE
```

## Test Scenarios

### Scenario 1: End-to-End Test (Recommended First Time)

**Purpose**: Verify complete integration from call initiation to completion

**Command**:
```bash
npm test
```

**What happens**:
1. Authenticates with your test user
2. Initiates a real ElevenLabs call
3. Monitors the call in real-time via WebSocket
4. Receives transcriptions as they occur
5. Gets completion notification
6. Fetches complete conversation
7. Compares real-time vs fetched data

**Expected Duration**: 2-10 minutes (depends on call)

**Success Criteria**:
- Call initiated successfully
- WebSocket connected
- Transcriptions received in real-time
- Call completion messages received
- Conversation fetched successfully
- Real-time count matches fetched count

### Scenario 2: WebSocket Connectivity Test

**Purpose**: Quick test of WebSocket connection without initiating call

**Command**:
```bash
npm run test:simple
```

**What happens**:
1. Authenticates with your test user
2. Connects to WebSocket
3. Waits for messages
4. Displays any received messages

**Expected Duration**: Instant (runs until Ctrl+C)

**Use Cases**:
- Test WebSocket authentication
- Monitor active calls
- Debug connection issues

### Scenario 3: Monitor Existing Call

**Purpose**: Subscribe to an already-running call

**Command**:
```bash
npm run test:simple EL_driver123_1732199700
```

**What happens**:
1. Authenticates with your test user
2. Connects to WebSocket
3. Subscribes to specific call_sid
4. Receives real-time updates for that call

**Expected Duration**: Instant (runs until call completes or Ctrl+C)

**Use Cases**:
- Monitor calls initiated from frontend
- Test subscription to existing calls
- Debug specific call issues

## Environment Variables

Create `.env` file with these variables:

```env
# Backend API URL
API_BASE_URL=http://localhost:8000

# WebSocket URL (ws:// for HTTP, wss:// for HTTPS)
WS_BASE_URL=ws://localhost:8000

# Test user credentials (must exist in your database)
TEST_USERNAME=test@example.com
TEST_PASSWORD=testpassword123

# Phone number for test calls (E.164 format: +1XXXXXXXXXX)
TEST_PHONE_NUMBER=+12192002824
```

### Production Testing

For testing against production:

```env
API_BASE_URL=https://your-domain.com
WS_BASE_URL=wss://your-domain.com
TEST_USERNAME=your-prod-test-user@example.com
TEST_PASSWORD=your-prod-test-password
```

## Expected Output

### Successful Full Test

```
================================================================================
  WebSocket Real-Time Transcription Test
================================================================================

[2025-11-22T10:30:00.000Z] [AUTH] Authenticating user...
[2025-11-22T10:30:01.000Z] [AUTH] Authentication successful!

[2025-11-22T10:30:01.500Z] [CALL] Initiating ElevenLabs call...
[2025-11-22T10:30:02.000Z] [CALL] Call initiated successfully!
{
  "call_sid": "EL_TEST_DRIVER_001_1732276200",
  "conversation_id": "conv_abc123xyz"
}

[2025-11-22T10:30:02.500Z] [WS] Connecting to WebSocket...
[2025-11-22T10:30:03.000Z] [WS] WebSocket connected successfully!
[2025-11-22T10:30:03.200Z] [WS_MSG] Subscription confirmed!

[2025-11-22T10:30:15.000Z] [WS_MSG] New transcription [agent]
   [0] AGENT: Hey John, this is dispatch calling...

[2025-11-22T10:30:20.000Z] [WS_MSG] New transcription [driver]
   [1] DRIVER: Yeah, sure. What's up?

... (more transcriptions) ...

[2025-11-22T10:32:00.000Z] [WS_MSG] Call completed with full data!

[2025-11-22T10:32:03.000Z] [FETCH] Conversation fetched successfully!

[2025-11-22T10:32:05.000Z] [COMPARE] SUCCESS: Counts match!
{
  "real_time_count": 12,
  "fetched_count": 12,
  "accuracy": "100.00%"
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

### Successful Simple Test

```
============================================================
  Simple WebSocket Connection Test
============================================================
Testing with call_sid: EL_driver123_1732199700
============================================================

[2025-11-22T10:30:00.000Z] Authenticating...
[2025-11-22T10:30:01.000Z] Authenticated successfully

[2025-11-22T10:30:02.000Z] Connecting to WebSocket...
[2025-11-22T10:30:02.500Z] WebSocket connected!
[2025-11-22T10:30:02.600Z] Subscribing to call: EL_driver123_1732199700

============================================================
[2025-11-22T10:30:03.000Z] Message #1 - Type: subscription_confirmed
Call SID: EL_driver123_1732199700
Conversation ID: conv_abc123xyz
Status: in_progress
============================================================

============================================================
[2025-11-22T10:30:15.000Z] Message #2 - Type: transcription
Sequence: 0
Speaker: AGENT
Message: Hey John, this is dispatch calling...
Timestamp: 2025-11-22T10:30:15.000Z
============================================================

... (continues until Ctrl+C) ...
```

## Troubleshooting

### Common Issues

#### 1. Authentication Failed

**Error**: `Authentication failed: 401`

**Solutions**:
- Verify TEST_USERNAME and TEST_PASSWORD in .env
- Ensure user exists in database
- Check database connection in backend

#### 2. WebSocket Connection Refused

**Error**: `WebSocket error: Connection refused`

**Solutions**:
- Verify backend is running
- Check WS_BASE_URL is correct
- Ensure WebSocket endpoint is enabled
- Check firewall rules

#### 3. No Transcriptions Received

**Issue**: WebSocket connected but no messages

**Solutions**:
- Wait longer (call may not have started)
- Check ElevenLabs webhook configuration
- Verify backend webhook endpoint is accessible
- Review backend logs for webhook errors

#### 4. Call Initiation Failed

**Error**: `Call initiation failed: 500`

**Solutions**:
- Check ElevenLabs API credentials in backend
- Verify phone number is in E.164 format
- Review backend logs for detailed errors
- Check ElevenLabs API quota/limits

#### 5. Dependency Installation Failed

**Error**: `npm install` fails

**Solutions**:
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and package-lock.json
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

### Debug Mode

Enable more verbose logging:

```bash
# Set debug environment variable (Linux/Mac)
DEBUG=* npm test

# Windows
set DEBUG=*
npm test
```

## Architecture Diagram

```
┌─────────────────┐
│   Test Script   │
│  (Node.js)      │
└────────┬────────┘
         │
         ├─── (1) POST /auth/login
         │    └─── Get JWT Token
         │
         ├─── (2) POST /driver_data/call-elevenlabs
         │    └─── Initiate Call → call_sid, conversation_id
         │
         ├─── (3) WebSocket Connection
         │    ws://domain/ws/calls/transcriptions?token=JWT
         │    │
         │    ├─── Send: {"subscribe": "call_sid"}
         │    ├─── Receive: subscription_confirmed
         │    ├─── Receive: transcription (multiple)
         │    ├─── Receive: call_status
         │    └─── Receive: call_completed
         │
         └─── (4) POST /driver_data/conversations/{id}/fetch
              └─── Fetch Complete History → Compare with Real-time
```

## Integration Points

This test validates:

1. **Authentication Flow**
   - JWT token generation
   - Token validation in WebSocket
   - [logic/auth/security.py](../logic/auth/security.py)

2. **Call Initiation**
   - Driver call endpoint
   - ElevenLabs API integration
   - [services/driver_data.py](../services/driver_data.py)
   - [utils/elevenlabs_client.py](../utils/elevenlabs_client.py)

3. **WebSocket System**
   - Connection management
   - Subscription handling
   - Message broadcasting
   - [services/websocket_manager.py](../services/websocket_manager.py)

4. **Webhook Processing**
   - Transcription webhook
   - Post-call webhook
   - Database storage
   - [services/webhooks_elevenlabs.py](../services/webhooks_elevenlabs.py)

5. **Data Persistence**
   - Call records
   - Transcription storage
   - [models/call.py](../models/call.py)
   - [models/call_transcription.py](../models/call_transcription.py)

## Next Steps

After successful testing:

1. **Frontend Integration**
   - Use the same WebSocket pattern in your frontend
   - Reference: [FRONTEND_INTEGRATION_GUIDE.md](../agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/deployment/FRONTEND_INTEGRATION_GUIDE.md)

2. **Production Deployment**
   - Configure production WebSocket URL (wss://)
   - Set up ElevenLabs webhook URLs
   - Test with production credentials

3. **Monitoring**
   - Monitor WebSocket connections
   - Track message delivery rates
   - Set up alerts for failures

## Support

For issues or questions:

1. Check backend logs: `tail -f app.log`
2. Review ElevenLabs dashboard for webhook status
3. Check database for call records: `SELECT * FROM calls WHERE call_sid = 'EL_...'`
4. Review this guide's troubleshooting section

## License

MIT
