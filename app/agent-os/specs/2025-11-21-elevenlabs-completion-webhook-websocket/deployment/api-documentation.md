# ElevenLabs WebSocket API Documentation

## Overview

This document provides comprehensive API documentation for frontend developers implementing real-time call monitoring using WebSockets for ElevenLabs conversational AI calls.

**Features:**
- Real-time transcription streaming as calls progress
- Call completion notifications with analysis and metadata
- Support for monitoring multiple calls simultaneously
- JWT-based authentication
- Auto-detection of call identifiers (call_sid or conversation_id)

**Use Cases:**
- Live call monitoring dashboard
- Real-time transcription display
- Call completion notifications
- Driver violation call tracking

---

## WebSocket Connection

### Connection URL

```
ws://your-domain/ws/calls/transcriptions?token=YOUR_JWT_TOKEN
```

**For Production (HTTPS):**
```
wss://your-domain/ws/calls/transcriptions?token=YOUR_JWT_TOKEN
```

### Authentication

WebSocket connections require JWT authentication via query parameter:

**Query Parameter:**
- `token` (required): JWT access token obtained from login endpoint

**Why Query Parameter?**
WebSocket upgrade requests in browsers don't reliably support custom headers, so we use a query parameter for the JWT token instead of the `Authorization` header.

**Token Requirements:**
- Must be a valid JWT access token
- Token must not be expired (24-hour expiration by default)
- User associated with token must exist in the database

**Authentication Flow:**
1. Client obtains JWT token from `/auth/login` endpoint
2. Client initiates WebSocket connection with token in query parameter
3. Server validates token during WebSocket upgrade
4. Connection accepted if token valid, rejected with 403 if invalid

---

## Message Protocol

All messages use JSON format. Messages are distinguished by message type fields.

### Client -> Server Messages

Clients send messages to subscribe/unsubscribe from call updates.

#### 1. Subscribe Request

**Purpose:** Start receiving real-time updates for a specific call

**Format:**
```json
{
  "subscribe": "CALL_IDENTIFIER"
}
```

**Fields:**
- `subscribe` (string, required): Call identifier - can be either `call_sid` or `conversation_id`

**Call Identifier Types:**
- **call_sid**: Our generated identifier (format: `EL_{driverId}_{timestamp}`)
  - Example: `"EL_driver123_1732199700"`
- **conversation_id**: ElevenLabs identifier
  - Example: `"abc123xyz"`

**Server Processing:**
1. Auto-detects identifier type (call_sid vs conversation_id)
2. Looks up Call record in database
3. Validates Call exists
4. Adds connection to subscription registry
5. Responds with `subscription_confirmed` or `error` message

**Example:**
```json
{
  "subscribe": "EL_driver123_1732199700"
}
```

---

#### 2. Unsubscribe Request

**Purpose:** Stop receiving updates for a specific call

**Format:**
```json
{
  "unsubscribe": "CALL_IDENTIFIER"
}
```

**Fields:**
- `unsubscribe` (string, required): Call identifier to stop receiving updates for

**Example:**
```json
{
  "unsubscribe": "EL_driver123_1732199700"
}
```

---

### Server -> Client Messages

Server sends 6 types of messages identified by the `type` field.

#### 1. Subscription Confirmed

**Purpose:** Confirm successful subscription to a call

**Trigger:** Sent immediately after client subscribes to a call

**Format:**
```json
{
  "type": "subscription_confirmed",
  "identifier": "EL_driver123_1732199700",
  "call_sid": "EL_driver123_1732199700",
  "conversation_id": "abc123xyz",
  "status": "in_progress",
  "message": "Successfully subscribed to call updates"
}
```

**Fields:**
- `type` (string): Always `"subscription_confirmed"`
- `identifier` (string): Original identifier from subscribe request
- `call_sid` (string): Resolved call_sid from Call record
- `conversation_id` (string|null): Resolved conversation_id from Call record (may be null if call hasn't started yet)
- `status` (string): Current call status - `"in_progress"`, `"completed"`, or `"failed"`
- `message` (string): Human-readable confirmation message

---

#### 2. Unsubscribe Confirmed

**Purpose:** Confirm successful unsubscription from a call

**Trigger:** Sent immediately after client unsubscribes from a call

**Format:**
```json
{
  "type": "unsubscribe_confirmed",
  "identifier": "EL_driver123_1732199700",
  "message": "Successfully unsubscribed from call updates"
}
```

**Fields:**
- `type` (string): Always `"unsubscribe_confirmed"`
- `identifier` (string): Original identifier from unsubscribe request
- `message` (string): Human-readable confirmation message

---

#### 3. Transcription Message

**Purpose:** Real-time transcription update with dialogue text

**Trigger:** Sent immediately after transcription webhook saves new dialogue turn to database

**Format:**
```json
{
  "type": "transcription",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "transcription_id": 456,
  "sequence_number": 3,
  "speaker_type": "agent",
  "message_text": "Hello, how are you doing today?",
  "timestamp": "2025-11-21T15:30:45.123456Z"
}
```

**Fields:**
- `type` (string): Always `"transcription"`
- `conversation_id` (string): ElevenLabs conversation identifier
- `call_sid` (string): Our generated call identifier
- `transcription_id` (integer): Database ID of transcription record
- `sequence_number` (integer): Sequence number in conversation (for ordering messages)
- `speaker_type` (string): Speaker attribution - `"agent"` (AI) or `"driver"` (human)
- `message_text` (string): Dialogue text spoken during the call
- `timestamp` (string): ISO 8601 timestamp when message occurred (UTC timezone)

**Notes:**
- Messages arrive in real-time as the call progresses
- Use `sequence_number` to ensure correct ordering if messages arrive out of order
- `speaker_type` identifies who spoke (AI agent vs human driver)

---

#### 4. Call Status Message

**Purpose:** Immediate notification that call has completed or failed

**Trigger:** Sent immediately after post-call webhook updates Call status (first message in completion sequence)

**Format:**
```json
{
  "type": "call_status",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "status": "completed",
  "call_end_time": "2025-11-21T15:35:00.000000Z"
}
```

**Fields:**
- `type` (string): Always `"call_status"`
- `conversation_id` (string): ElevenLabs conversation identifier
- `call_sid` (string): Our generated call identifier
- `status` (string): New call status - `"completed"` or `"failed"`
- `call_end_time` (string|null): ISO 8601 timestamp when call ended (nullable)

**Notes:**
- This is the first message in the completion sequence
- Always followed by `call_completed` message with full data
- Use this for immediate UI updates (e.g., showing "Call Ended" badge)

---

#### 5. Call Completed Message

**Purpose:** Complete call data with analysis, metadata, and costs

**Trigger:** Sent immediately after `call_status` message (second message in completion sequence)

**Format:**
```json
{
  "type": "call_completed",
  "conversation_id": "abc123xyz",
  "call_sid": "EL_driver123_1732199700",
  "call_data": {
    "status": "completed",
    "driver_id": "driver123",
    "call_sid": "EL_driver123_1732199700",
    "conversation_id": "abc123xyz",
    "call_start_time": "2025-11-21T15:30:00.000000Z",
    "call_end_time": "2025-11-21T15:35:00.000000Z",
    "duration_seconds": 300,
    "transcript_summary": "Agent greeted the driver and confirmed delivery location. Driver acknowledged and agreed to proceed to the new destination.",
    "cost": 0.08,
    "call_successful": true,
    "analysis_data": {
      "call_successful": true,
      "transcript_summary": "Agent greeted the driver and confirmed delivery location. Driver acknowledged and agreed to proceed to the new destination.",
      "evaluation_results": {
        "criteria_1": "passed",
        "criteria_2": "passed"
      }
    },
    "metadata": {
      "call_duration_secs": 300,
      "cost": 0.08,
      "from_number": "+14155551234",
      "to_number": "+14155555678",
      "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
      "start_time_unix_secs": 1732199700
    }
  }
}
```

**Fields:**
- `type` (string): Always `"call_completed"`
- `conversation_id` (string): ElevenLabs conversation identifier
- `call_sid` (string): Our generated call identifier
- `call_data` (object): Full Call record data with all metadata

**call_data Object Fields:**
- `status` (string): Final call status - `"completed"` or `"failed"`
- `driver_id` (string|null): Driver identifier (nullable if lookup failed)
- `call_sid` (string): Our generated call identifier
- `conversation_id` (string): ElevenLabs conversation identifier
- `call_start_time` (string): ISO 8601 timestamp when call started
- `call_end_time` (string|null): ISO 8601 timestamp when call ended
- `duration_seconds` (integer|null): Duration of call in seconds
- `transcript_summary` (string|null): AI-generated summary of conversation
- `cost` (float|null): Call cost in USD (e.g., `0.08` = $0.08)
- `call_successful` (boolean|null): Whether call achieved its goal (from AI analysis)
- `analysis_data` (object|null): Full analysis results from ElevenLabs
- `metadata` (object|null): Full metadata from ElevenLabs (phone numbers, timestamps, etc.)

**Notes:**
- This is the second message in the completion sequence
- Contains all information needed for call analytics and reporting
- Client automatically unsubscribed after this message (subscription cleaned up)

---

#### 6. Error Message

**Purpose:** Notify client of errors during operations

**Trigger:** Sent when operations fail or invalid requests received

**Format:**
```json
{
  "type": "error",
  "message": "Call not found for identifier: invalid_id_123",
  "code": "CALL_NOT_FOUND"
}
```

**Fields:**
- `type` (string): Always `"error"`
- `message` (string): Human-readable error description
- `code` (string|null): Optional error code for programmatic handling

**Common Error Codes:**
- `CALL_NOT_FOUND`: Identifier doesn't match any Call record
- `INVALID_IDENTIFIER`: Malformed identifier format
- `AUTHENTICATION_FAILED`: JWT token invalid or expired
- `SUBSCRIPTION_FAILED`: Failed to subscribe to call updates
- `INVALID_MESSAGE_FORMAT`: Client message doesn't match expected schema

---

## Subscription Flow

### Typical Connection Lifecycle

```
1. Client connects with JWT token
   ws://domain/ws/calls/transcriptions?token=JWT_TOKEN

2. Server accepts connection (or rejects if invalid token)

3. Client subscribes to a call
   -> {"subscribe": "EL_driver123_1732199700"}

4. Server confirms subscription
   <- {"type": "subscription_confirmed", ...}

5. Client receives real-time transcriptions
   <- {"type": "transcription", "message_text": "...", ...}
   <- {"type": "transcription", "message_text": "...", ...}
   <- {"type": "transcription", "message_text": "...", ...}

6. Call completes, server sends completion messages
   <- {"type": "call_status", "status": "completed", ...}
   <- {"type": "call_completed", "call_data": {...}, ...}

7. Client unsubscribes (optional - auto-unsubscribed after completion)
   -> {"unsubscribe": "EL_driver123_1732199700"}

8. Server confirms unsubscription
   <- {"type": "unsubscribe_confirmed", ...}

9. Client closes connection
```

### Multiple Call Subscriptions

Clients can subscribe to multiple calls on a single connection:

```
1. Client connects

2. Subscribe to call A
   -> {"subscribe": "EL_driverA_1732199700"}
   <- {"type": "subscription_confirmed", ...}

3. Subscribe to call B
   -> {"subscribe": "EL_driverB_1732199800"}
   <- {"type": "subscription_confirmed", ...}

4. Receive updates for both calls
   <- {"type": "transcription", "call_sid": "EL_driverA_...", ...}
   <- {"type": "transcription", "call_sid": "EL_driverB_...", ...}
   <- {"type": "transcription", "call_sid": "EL_driverA_...", ...}

5. Calls complete independently
   <- {"type": "call_status", "call_sid": "EL_driverA_...", ...}
   <- {"type": "call_completed", "call_sid": "EL_driverA_...", ...}
   <- {"type": "call_status", "call_sid": "EL_driverB_...", ...}
   <- {"type": "call_completed", "call_sid": "EL_driverB_...", ...}
```

**Key Points:**
- Single WebSocket connection can monitor multiple calls
- Messages include `call_sid` and `conversation_id` to identify which call they belong to
- Each call auto-unsubscribes after completion
- No explicit unsubscribe needed (but supported)

---

## Error Handling

### Connection Errors

**Invalid JWT Token:**
- **Status:** Connection rejected with HTTP 403 Forbidden
- **Cause:** Token is invalid, expired, or user doesn't exist
- **Solution:** Re-authenticate to get new token

**Connection Timeout:**
- **Cause:** Network issues or server unavailability
- **Solution:** Implement exponential backoff reconnection strategy

### Subscription Errors

**Call Not Found:**
```json
{
  "type": "error",
  "message": "Call not found for identifier: invalid_id_123",
  "code": "CALL_NOT_FOUND"
}
```
- **Cause:** Identifier doesn't match any Call record
- **Solution:** Verify identifier is correct, call may not have been initiated yet

**Invalid Identifier:**
```json
{
  "type": "error",
  "message": "Invalid identifier format",
  "code": "INVALID_IDENTIFIER"
}
```
- **Cause:** Identifier is malformed or empty
- **Solution:** Ensure identifier is non-empty string

### Message Parse Errors

**Invalid Message Format:**
```json
{
  "type": "error",
  "message": "Invalid message format",
  "code": "INVALID_MESSAGE_FORMAT"
}
```
- **Cause:** Client sent message that doesn't match expected schema
- **Solution:** Verify message format matches documented schemas

### Graceful Degradation

**Best Practices:**
1. Always handle `error` message type
2. Display error messages to users when appropriate
3. Implement reconnection logic for disconnections
4. Fall back to polling REST endpoints if WebSocket unavailable
5. Log errors for debugging

---

## Example Code

### JavaScript (Browser)

```javascript
class CallMonitor {
  constructor(apiDomain, jwtToken) {
    this.apiDomain = apiDomain;
    this.jwtToken = jwtToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    // Use wss:// for HTTPS domains, ws:// for HTTP
    const protocol = this.apiDomain.startsWith('https') ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${this.apiDomain}/ws/calls/transcriptions?token=${this.jwtToken}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.handleReconnect();
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'subscription_confirmed':
        console.log('Subscribed to call:', message.call_sid);
        this.onSubscriptionConfirmed(message);
        break;

      case 'transcription':
        console.log(`[${message.speaker_type}]: ${message.message_text}`);
        this.onTranscription(message);
        break;

      case 'call_status':
        console.log('Call status changed:', message.status);
        this.onCallStatus(message);
        break;

      case 'call_completed':
        console.log('Call completed with data:', message.call_data);
        this.onCallCompleted(message);
        break;

      case 'unsubscribe_confirmed':
        console.log('Unsubscribed from call:', message.identifier);
        this.onUnsubscribeConfirmed(message);
        break;

      case 'error':
        console.error('Error:', message.message, message.code);
        this.onError(message);
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  subscribe(callIdentifier) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ subscribe: callIdentifier }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  unsubscribe(callIdentifier) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ unsubscribe: callIdentifier }));
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // Override these methods in your implementation
  onSubscriptionConfirmed(message) {}
  onTranscription(message) {}
  onCallStatus(message) {}
  onCallCompleted(message) {}
  onUnsubscribeConfirmed(message) {}
  onError(message) {}
}

// Usage Example
const monitor = new CallMonitor('your-domain.com', 'YOUR_JWT_TOKEN');

// Override handlers
monitor.onSubscriptionConfirmed = (message) => {
  console.log('Successfully subscribed:', message);
  // Update UI to show "Monitoring call..."
};

monitor.onTranscription = (message) => {
  // Add transcription to UI
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${message.speaker_type}`;
  messageDiv.innerHTML = `
    <strong>${message.speaker_type}:</strong> ${message.message_text}
    <span class="timestamp">${new Date(message.timestamp).toLocaleTimeString()}</span>
  `;
  document.getElementById('transcription-container').appendChild(messageDiv);
};

monitor.onCallCompleted = (message) => {
  // Display call completion summary
  const data = message.call_data;
  alert(`Call completed!\nDuration: ${data.duration_seconds}s\nCost: $${data.cost}\nSummary: ${data.transcript_summary}`);
};

monitor.onError = (message) => {
  // Display error to user
  alert(`Error: ${message.message}`);
};

// Connect and subscribe
monitor.connect();

// After connection is open, subscribe to a call
setTimeout(() => {
  monitor.subscribe('EL_driver123_1732199700');
}, 1000);
```

---

### Python (asyncio + websockets)

```python
import asyncio
import websockets
import json
from typing import Callable, Dict, Any

class CallMonitor:
    def __init__(self, api_domain: str, jwt_token: str):
        self.api_domain = api_domain
        self.jwt_token = jwt_token
        self.ws = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

        # Event handlers
        self.on_subscription_confirmed = None
        self.on_transcription = None
        self.on_call_status = None
        self.on_call_completed = None
        self.on_unsubscribe_confirmed = None
        self.on_error = None

    async def connect(self):
        """Establish WebSocket connection."""
        # Use wss:// for HTTPS domains, ws:// for HTTP
        protocol = 'wss' if self.api_domain.startswith('https') else 'ws'
        ws_url = f"{protocol}://{self.api_domain}/ws/calls/transcriptions?token={self.jwt_token}"

        try:
            self.ws = await websockets.connect(ws_url)
            print("WebSocket connected")
            self.reconnect_attempts = 0

            # Start message handler
            await self.handle_messages()

        except Exception as e:
            print(f"Connection error: {e}")
            await self.handle_reconnect()

    async def handle_messages(self):
        """Listen for and handle incoming messages."""
        try:
            async for message_str in self.ws:
                message = json.loads(message_str)
                await self.process_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            await self.handle_reconnect()
        except Exception as e:
            print(f"Error handling messages: {e}")

    async def process_message(self, message: Dict[str, Any]):
        """Process incoming message based on type."""
        message_type = message.get('type')

        if message_type == 'subscription_confirmed':
            print(f"Subscribed to call: {message.get('call_sid')}")
            if self.on_subscription_confirmed:
                await self.on_subscription_confirmed(message)

        elif message_type == 'transcription':
            speaker = message.get('speaker_type')
            text = message.get('message_text')
            print(f"[{speaker}]: {text}")
            if self.on_transcription:
                await self.on_transcription(message)

        elif message_type == 'call_status':
            print(f"Call status changed: {message.get('status')}")
            if self.on_call_status:
                await self.on_call_status(message)

        elif message_type == 'call_completed':
            print(f"Call completed with data: {message.get('call_data')}")
            if self.on_call_completed:
                await self.on_call_completed(message)

        elif message_type == 'unsubscribe_confirmed':
            print(f"Unsubscribed from call: {message.get('identifier')}")
            if self.on_unsubscribe_confirmed:
                await self.on_unsubscribe_confirmed(message)

        elif message_type == 'error':
            print(f"Error: {message.get('message')} (code: {message.get('code')})")
            if self.on_error:
                await self.on_error(message)

        else:
            print(f"Unknown message type: {message_type}")

    async def subscribe(self, call_identifier: str):
        """Subscribe to a call's updates."""
        if self.ws and not self.ws.closed:
            await self.ws.send(json.dumps({"subscribe": call_identifier}))
        else:
            print("WebSocket not connected")

    async def unsubscribe(self, call_identifier: str):
        """Unsubscribe from a call's updates."""
        if self.ws and not self.ws.closed:
            await self.ws.send(json.dumps({"unsubscribe": call_identifier}))

    async def handle_reconnect(self):
        """Handle reconnection with exponential backoff."""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(2 ** self.reconnect_attempts, 30)
            print(f"Reconnecting in {delay}s (attempt {self.reconnect_attempts})")
            await asyncio.sleep(delay)
            await self.connect()
        else:
            print("Max reconnection attempts reached")

    async def disconnect(self):
        """Close WebSocket connection."""
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.ws = None


# Usage Example
async def main():
    monitor = CallMonitor('your-domain.com', 'YOUR_JWT_TOKEN')

    # Define event handlers
    async def handle_transcription(message):
        speaker = message['speaker_type']
        text = message['message_text']
        timestamp = message['timestamp']
        print(f"[{timestamp}] {speaker}: {text}")
        # Update your UI or database here

    async def handle_call_completed(message):
        data = message['call_data']
        print(f"Call Completed:")
        print(f"  Duration: {data['duration_seconds']}s")
        print(f"  Cost: ${data['cost']}")
        print(f"  Summary: {data['transcript_summary']}")
        # Process completion data

    # Set handlers
    monitor.on_transcription = handle_transcription
    monitor.on_call_completed = handle_call_completed

    # Connect
    await monitor.connect()

    # Subscribe to a call
    await asyncio.sleep(1)  # Wait for connection
    await monitor.subscribe('EL_driver123_1732199700')

    # Keep connection alive
    await asyncio.sleep(300)  # Monitor for 5 minutes

    # Cleanup
    await monitor.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Best Practices

### Connection Management

1. **Implement Reconnection Logic:**
   - Use exponential backoff (1s, 2s, 4s, 8s, 16s, 30s max)
   - Limit reconnection attempts to avoid infinite loops
   - Re-subscribe to calls after reconnection

2. **Handle Connection Lifecycle:**
   - Always close connections gracefully when done
   - Clean up event listeners on disconnect
   - Implement connection timeout monitoring

3. **Token Refresh:**
   - Monitor token expiration
   - Refresh token before expiration
   - Reconnect with new token if connection rejected

### Message Handling

1. **Always Validate Message Types:**
   - Check `type` field before processing
   - Handle unknown message types gracefully
   - Log unexpected messages for debugging

2. **Use Identifiers Correctly:**
   - Store both `call_sid` and `conversation_id` from messages
   - Use `call_sid` as primary identifier (always present)
   - Use `conversation_id` when interacting with ElevenLabs API

3. **Handle Sequence Numbers:**
   - Store `sequence_number` from transcription messages
   - Sort messages by sequence if they arrive out of order
   - Use sequence for message ordering in UI

### Error Handling

1. **Display User-Friendly Errors:**
   - Show clear error messages to users
   - Don't expose technical details
   - Provide actionable guidance

2. **Implement Fallbacks:**
   - Fall back to polling REST endpoints if WebSocket fails
   - Cache messages during brief disconnections
   - Notify users when real-time updates unavailable

3. **Log Errors:**
   - Log all errors for debugging
   - Include connection ID, timestamp, and context
   - Send critical errors to monitoring service

### Performance

1. **Manage Subscriptions:**
   - Only subscribe to calls currently being monitored
   - Unsubscribe when user navigates away
   - Limit number of simultaneous subscriptions (max 10-20)

2. **Update UI Efficiently:**
   - Batch UI updates for transcriptions
   - Use virtual scrolling for long transcription lists
   - Debounce rapid updates

3. **Memory Management:**
   - Clean up old messages from memory
   - Limit transcription history in memory (keep last 100-200 messages)
   - Use pagination for historical data

---

## Troubleshooting

### Connection Refused

**Symptoms:**
- WebSocket connection fails immediately
- Error: "Connection refused" or HTTP 403

**Causes:**
- Invalid JWT token
- Expired token
- Network connectivity issues
- Server unavailable

**Solutions:**
1. Verify token is valid and not expired
2. Re-authenticate to get fresh token
3. Check network connectivity
4. Verify server is running and accessible

---

### Messages Not Received

**Symptoms:**
- Connection successful but no messages received
- Subscription confirmed but no transcriptions

**Causes:**
- Not subscribed to any calls
- Call hasn't started yet
- Call already completed
- Network issues causing message loss

**Solutions:**
1. Verify subscription request sent and confirmed
2. Check call status (may be completed already)
3. Verify call_sid/conversation_id is correct
4. Check network for packet loss

---

### Duplicate Messages

**Symptoms:**
- Same transcription received multiple times

**Causes:**
- Multiple subscriptions to same call
- Reconnection without unsubscribing first
- Client-side duplicate processing

**Solutions:**
1. Track received `transcription_id` values
2. De-duplicate messages by `transcription_id`
3. Unsubscribe before reconnecting
4. Use Set/Map for message tracking

---

## Security Considerations

### Token Security

1. **Never Log Tokens:**
   - Don't log JWT tokens in console or logs
   - Mask tokens in error messages
   - Use secure storage for tokens

2. **Token Rotation:**
   - Implement token refresh mechanism
   - Rotate tokens before expiration
   - Invalidate old tokens on logout

3. **HTTPS/WSS Only in Production:**
   - Always use WSS (WebSocket Secure) in production
   - Never use WS over unencrypted HTTP in production
   - Validate SSL certificates

### Connection Security

1. **Validate Server Certificate:**
   - Verify SSL certificate in production
   - Reject self-signed certificates
   - Use certificate pinning for mobile apps

2. **Rate Limiting:**
   - Implement client-side rate limiting for subscribe/unsubscribe
   - Avoid rapid reconnection attempts
   - Respect server rate limits

3. **Data Privacy:**
   - Treat all call data as sensitive
   - Don't cache transcriptions insecurely
   - Clear data on logout

---

## API Versioning

**Current Version:** 1.0

This is the initial version of the WebSocket API. Future versions will maintain backward compatibility where possible.

**Breaking Changes:**
- Will be announced with migration guide
- Old version supported for 6 months after new version release
- Versioning via URL path (e.g., `/ws/v2/calls/transcriptions`)

---

## Support

For questions or issues:
1. Check this documentation first
2. Review server logs for error details
3. Contact backend team with:
   - Connection URL used
   - JWT token prefix (first 10 characters only)
   - Error messages received
   - Steps to reproduce

---

## Changelog

### Version 1.0 (2025-11-21)
- Initial release
- WebSocket endpoint for real-time call monitoring
- Support for transcription streaming
- Support for call completion notifications
- JWT authentication via query parameter
- Auto-detection of call identifiers (call_sid and conversation_id)
- Support for multiple call subscriptions per connection
