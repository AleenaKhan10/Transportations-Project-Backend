# Quick Start - WebSocket Testing

## Files Created

7 files have been created in the `tests/` directory:

```
tests/
├── websocket_test.js              # Full integration test (call + WebSocket)
├── websocket_simple_test.js       # Simple WebSocket connectivity test
├── package.json                   # Node.js dependencies
├── .env.example                   # Environment variables template
├── install_and_run.bat           # Windows automated installer/runner
├── README_WEBSOCKET_TEST.md      # Detailed documentation
├── TEST_GUIDE.md                 # Comprehensive testing guide
└── QUICK_START.md                # This file
```

## Installation (3 Steps)

### Step 1: Navigate to tests directory

```bash
cd tests
```

### Step 2: Install dependencies

```bash
npm install
```

### Step 3: Configure environment

```bash
# Copy example file
cp .env.example .env

# Edit .env with your credentials
# Required fields:
#   - TEST_USERNAME (your test user email)
#   - TEST_PASSWORD (your test user password)
#   - API_BASE_URL (default: http://localhost:8000)
#   - WS_BASE_URL (default: ws://localhost:8000)
```

## Running Tests

### Option 1: Full Test (Recommended)

Tests complete flow: Call initiation → Real-time WebSocket → Fetch conversation

```bash
npm test
```

**What it does**:
1. Authenticates user
2. Initiates ElevenLabs call
3. Connects to WebSocket
4. Receives transcriptions in real-time
5. Fetches complete conversation
6. Compares real-time vs fetched data

**Duration**: 2-10 minutes (depends on call length)

### Option 2: Simple WebSocket Test

Just tests WebSocket connectivity without initiating a call:

```bash
npm run test:simple
```

**What it does**:
1. Authenticates user
2. Connects to WebSocket
3. Waits for messages (any active call)

**Duration**: Instant (runs until Ctrl+C)

### Option 3: Monitor Existing Call

Subscribe to a specific call by call_sid:

```bash
npm run test:simple EL_driver123_1732199700
```

**What it does**:
1. Authenticates user
2. Connects to WebSocket
3. Subscribes to specific call
4. Displays real-time messages

**Duration**: Instant (runs until call completes or Ctrl+C)

## Windows Users

Double-click `install_and_run.bat` for automated setup and execution.

## What to Expect

### Successful Test Output

```
[AUTH] Authenticating user...
[AUTH] Authentication successful!

[CALL] Initiating ElevenLabs call...
[CALL] Call initiated successfully!

[WS] Connecting to WebSocket...
[WS] WebSocket connected successfully!
[WS_MSG] Subscription confirmed!

[WS_MSG] New transcription [agent]
   [0] AGENT: Hey John, this is dispatch calling...
[WS_MSG] New transcription [driver]
   [1] DRIVER: Yeah, sure. What's up?

... (more transcriptions) ...

[WS_MSG] Call completed with full data!
[FETCH] Conversation fetched successfully!
[COMPARE] SUCCESS: Counts match!

Real-time transcriptions received: 12
Fetched transcriptions: 12
Call completed: YES
```

## Testing Both Systems

This test verifies:

1. **Real-Time Transcription** (Backend → Database)
   - ElevenLabs webhooks received
   - Dialogue saved to database
   - Transcriptions stored correctly

2. **WebSocket Real-Time Updates** (Backend → Client)
   - WebSocket connection established
   - Subscriptions working
   - Messages broadcast in real-time
   - Clients receive updates

## Troubleshooting

### Issue: Authentication failed

```bash
# Check your .env file
cat .env

# Verify user exists in database
# Check backend logs
```

### Issue: WebSocket connection refused

```bash
# Verify backend is running
curl http://localhost:8000/

# Check WebSocket URL in .env
# Should be ws://localhost:8000 (not http://)
```

### Issue: No transcriptions received

```bash
# Wait longer (call may not have started yet)
# Check ElevenLabs webhook configuration
# Review backend logs for webhook errors
```

## Next Steps

1. Run the full test: `npm test`
2. Verify output matches expected results
3. Check database for saved transcriptions
4. Review [TEST_GUIDE.md](TEST_GUIDE.md) for detailed documentation
5. Integrate WebSocket into your frontend (see [FRONTEND_INTEGRATION_GUIDE.md](../agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/deployment/FRONTEND_INTEGRATION_GUIDE.md))

## Documentation

- **QUICK_START.md** (this file) - Get started in 5 minutes
- **TEST_GUIDE.md** - Comprehensive testing guide
- **README_WEBSOCKET_TEST.md** - Detailed API documentation

## Support

- Check logs: Backend server logs, test output
- Review documentation: TEST_GUIDE.md troubleshooting section
- Verify configuration: .env file, backend settings

---

**Ready to test?** Run `npm test` and watch the magic happen!
