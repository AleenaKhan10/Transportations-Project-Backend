# WebSocket Database Polling - Fallback Mechanism

## Overview

Added database polling as a **fallback mechanism** to ensure WebSocket clients always receive transcriptions, even when webhook broadcasts fail or are missed.

## Use Cases

1. **Local Development**: Testing locally while ElevenLabs webhooks hit production server
2. **Network Issues**: Temporary connection problems that cause missed webhook broadcasts
3. **Race Conditions**: Transcriptions saved before client subscribes
4. **Reliability**: Extra safety net for mission-critical real-time updates

## How It Works

### Architecture

```
Client Subscribes
    ↓
Send Existing Transcriptions (initial load)
    ↓
Start Background Polling Task (every 5 seconds)
    ↓
┌─────────────────────────────┐
│ Webhook Broadcast (Primary) │ ← ElevenLabs sends transcription webhook
│  - Immediate delivery        │
│  - Updates sequence tracker  │
└─────────────────────────────┘
           OR (fallback)
┌─────────────────────────────┐
│ Database Polling (Fallback) │ ← Polls every 5 seconds
│  - Checks for missed items   │
│  - Only sends new ones       │
│  - Updates sequence tracker  │
└─────────────────────────────┘
    ↓
Client Receives Transcription (no duplicates)
```

### Sequence Tracking

Each connection tracks the last sequence number sent for each call:

```python
last_sequence_sent = {
    "connection_uuid_123": {
        "EL_driver_456": 16,  # Last sequence sent for this call
        "EL_driver_789": 8
    },
    "connection_uuid_456": {
        "EL_driver_456": 16
    }
}
```

### Polling Logic

Every 5 seconds, for each subscribed call:

1. **Get last sequence sent**: `last_seq = last_sequence_sent[conn_id][call_sid]`
2. **Fetch new transcriptions**: `WHERE sequence_number > last_seq`
3. **Send new transcriptions**: Only ones not yet sent
4. **Update tracker**: `last_sequence_sent[conn_id][call_sid] = latest_seq`

## Implementation Details

### Files Modified

1. **[services/websocket_manager.py](services/websocket_manager.py)**
   - Added `last_sequence_sent` tracker
   - Added `poll_new_transcriptions()` method
   - Updated `broadcast_transcription()` to track sequences
   - Updated `disconnect()` to cleanup tracker

2. **[services/websocket_calls.py](services/websocket_calls.py)**
   - Added `poll_for_updates()` background task
   - Updated subscription handler to track sequences on initial send
   - Added task cancellation on disconnect

3. **[models/call_transcription.py](models/call_transcription.py)**
   - Added `get_by_call_sid()` method

### Configuration

```python
# Polling interval (in websocket_calls.py)
POLL_INTERVAL_SECONDS = 5  # Poll every 5 seconds
```

**Adjust this value based on your needs:**
- Lower (2-3s) = More responsive, more DB load
- Higher (10-15s) = Less DB load, slightly delayed updates

## Benefits

1. **No Duplicates**: Sequence tracking prevents sending same transcription twice
2. **Efficient**: Only fetches transcriptions newer than last sent
3. **Resilient**: Continues even if one poll iteration fails
4. **Transparent**: Clients receive transcriptions identically whether from webhook or poll
5. **Backward Compatible**: Existing webhook broadcasts still work as primary mechanism

## Performance Considerations

### Database Load

- **Queries per connection**: 1 query every 5 seconds per subscribed call
- **Example**: 10 active connections × 1 call each = 10 queries every 5 seconds = 2 QPS
- **Optimization**: Queries only run when call is `in_progress`, auto-cleanup on `completed`

### Network Load

- **Minimal**: Only sends transcriptions that weren't already broadcast
- **Best case**: 0 messages (webhooks working perfectly)
- **Worst case**: All transcriptions sent via polling (same as webhook broadcast)

## Testing

### Test Scenario 1: Local + Production Mismatch

```javascript
// Connect to localhost while webhooks hit production
const ws = new WebSocket('ws://localhost:8000/ws/calls/transcriptions?token=...');

// Result: Polling will fetch transcriptions from shared database
// Client receives all transcriptions within 5 seconds of being saved
```

### Test Scenario 2: Production (Webhooks Working)

```javascript
// Connect to production where webhooks are delivered
const ws = new WebSocket('wss://production.com/ws/calls/transcriptions?token=...');

// Result: Webhooks deliver immediately, polling finds no new data (no duplicates)
```

### Test Scenario 3: Subscribe to Ongoing Call

```javascript
// Subscribe to call that's already in progress with 10 transcriptions
ws.send(JSON.stringify({subscribe: 'EL_call_123'}));

// Result:
// 1. Receives all 10 existing transcriptions immediately
// 2. Receives transcription #11 via webhook (or polling if webhook fails)
// 3. No duplicates
```

## Monitoring

Look for these log messages:

```
# When polling starts
Starting polling task for connection: {uuid}

# When polling finds new data
Poll found {count} new transcriptions - call_sid: {sid}, last_sequence: {seq}
Poll completed - sent {count} new transcriptions to connection: {uuid}

# When polling is cancelled
Polling task cancelled for connection: {uuid}
```

## Disabling Polling

If you want to disable polling (e.g., in production where webhooks work perfectly):

```python
# In websocket_calls.py
POLL_INTERVAL_SECONDS = 0  # Disable polling

# Or comment out the polling task creation:
# polling_task = asyncio.create_task(poll_for_updates(connection_id))
```

## Future Enhancements

1. **Adaptive Polling**: Slow down polling when no new data found
2. **Metrics**: Track webhook vs polling delivery ratio
3. **Redis Pub/Sub**: For multi-instance deployments
4. **Configurable**: Make POLL_INTERVAL_SECONDS environment variable
