# Complete ElevenLabs Integration Guide for Frontend Developers

## Table of Contents
1. [Overview](#overview)
2. [Complete Flow Diagram](#complete-flow-diagram)
3. [Part 1: Call Initialization](#part-1-call-initialization)
4. [Part 2: Real-Time Transcription (Automatic)](#part-2-real-time-transcription-automatic)
5. [Part 3: Call Completion (Automatic)](#part-3-call-completion-automatic)
6. [Part 4: Conversation Fetching](#part-4-conversation-fetching)
7. [Part 5: WebSocket Real-Time Updates](#part-5-websocket-real-time-updates)
8. [Complete End-to-End Example](#complete-end-to-end-example)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)

---

## Overview

The ElevenLabs integration provides a complete conversational AI system for calling drivers about violations and receiving real-time transcriptions. The system consists of 5 interconnected parts:

- **Part 1**: Initiate driver calls via API
- **Part 2**: Automatic real-time transcription storage (backend-only, triggers WebSocket)
- **Part 3**: Automatic call completion tracking (backend-only, triggers WebSocket)
- **Part 4**: Fetch complete conversation history on demand
- **Part 5**: Receive real-time updates via WebSocket

**Key Features:**
- Proactive call tracking (records created before API call)
- Real-time transcription streaming via WebSocket
- Call completion notifications
- Complete conversation history retrieval
- Support for both `call_sid` (our ID) and `conversation_id` (ElevenLabs ID)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND APPLICATION                             │
└──────────┬──────────────────────────────────────┬──────────────────────┘
           │                                      │
           │ 1. POST /driver_data/call-elevenlabs │ 5. WebSocket Connection
           │    (Initiate Call)                   │    ws://domain/ws/calls/transcriptions?token=JWT
           │                                      │
           v                                      v
┌────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API SERVER                              │
│                                                                        │
│  ┌──────────────────┐     ┌────────────────────────────────────────┐ │
│  │ Call Record      │     │ WebSocket Connection Manager           │ │
│  │ Created          │     │ - Manages active connections           │ │
│  │ (call_sid, NULL  │     │ - Handles subscriptions                │ │
│  │  conversation_id)│     │ - Broadcasts to clients                │ │
│  └──────┬───────────┘     └────────────────────────────────────────┘ │
│         │                                                              │
│         v                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ ElevenLabs API Call                                              │ │
│  │ - Sends prompt & phone number                                    │ │
│  │ - Returns conversation_id                                        │ │
│  │ - Updates Call record with conversation_id                       │ │
│  └──────┬───────────────────────────────────────────────────────────┘ │
└─────────┼─────────────────────────────────────────────────────────────┘
          │
          │ 2. Call Initiated
          v
┌─────────────────────────────────────────────────────────────────────────┐
│                      ELEVENLABS PLATFORM                                │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Conversational AI Agent                                         │  │
│  │ - Calls driver's phone                                          │  │
│  │ - Conducts natural conversation                                 │  │
│  │ - Follows provided prompt                                       │  │
│  └──────┬─────────────────────────────┬────────────────────────────┘  │
└─────────┼─────────────────────────────┼───────────────────────────────┘
          │                             │
          │ 3. During Call:             │ 4. After Call Ends:
          │ POST /webhooks/             │ POST /webhooks/
          │ elevenlabs/transcription    │ elevenlabs/post-call
          │ (for each dialogue turn)    │ (once, with full metadata)
          │                             │
          v                             v
┌────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API SERVER                              │
│                                                                        │
│  Part 2: Transcription Webhook          Part 3: Post-Call Webhook     │
│  ┌────────────────────────┐             ┌─────────────────────────┐  │
│  │ - Receives dialogue    │             │ - Receives completion   │  │
│  │ - Saves to database    │             │ - Updates Call status   │  │
│  │ - Broadcasts via WS ───┼─────────────┼─> - Stores metadata     │  │
│  └────────────────────────┘             │ - Broadcasts via WS     │  │
│                                         └─────────────────────────┘  │
│                                                                        │
│  Part 5: WebSocket Broadcasting                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Real-Time Messages:                                            │  │
│  │ - transcription: Each dialogue turn                            │  │
│  │ - call_status: Call completed notification                     │  │
│  │ - call_completed: Full call data + metadata                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
└────────┬───────────────────────────────────────────────────────────────┘
         │
         │ WebSocket messages pushed in real-time
         v
┌─────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND APPLICATION                             │
│  - Receives real-time transcriptions                                   │
│  - Displays conversation as it happens                                 │
│  - Notified when call completes                                        │
│  - Can fetch full history via Part 4 if needed                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Call Initialization

**Purpose**: Initiate a driver call with violations/reminders

**Endpoint**: `POST /driver_data/call-elevenlabs`

**Authentication**: Required (JWT Bearer token)

### Request Format

```bash
curl -X POST 'https://your-domain.com/driver_data/call-elevenlabs' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -d '{
  "callType": "violation",
  "timestamp": "2025-11-21T15:30:00Z",
  "drivers": [
    {
      "driverId": "DRV_12345",
      "driverName": "John Smith",
      "phoneNumber": "+12192002824",
      "customRules": "Be extra polite, driver is stressed",
      "violations": {
        "tripId": "TRIP_78910",
        "violationDetails": [
          {
            "type": "violation",
            "description": "Your temp is at 45 degrees Fahrenheit but needs to be 38 degrees Fahrenheit"
          },
          {
            "type": "reminder",
            "description": "Please send loaded trailer pictures when you get a chance"
          }
        ]
      }
    }
  ]
}'
```

### Request Body Schema

```typescript
interface BatchCallRequest {
  callType: string;                    // e.g., "violation"
  timestamp: string;                   // ISO 8601 format
  drivers: DriverData[];               // Array, but only first driver is processed
}

interface DriverData {
  driverId: string;                    // Unique driver identifier
  driverName: string;                  // Full name for personalization
  phoneNumber: string;                 // Will be normalized to E.164 format
  customRules?: string;                // Optional special instructions for AI
  violations: ViolationData;
}

interface ViolationData {
  tripId: string;                      // Current trip ID
  violationDetails: ViolationDetail[];
}

interface ViolationDetail {
  type: "violation" | "reminder";     // Type of issue
  description: string;                 // What to discuss with driver
}
```

### Success Response (200 OK)

```json
{
  "message": "Call initiated successfully via ElevenLabs",
  "timestamp": "2025-11-21T15:30:00Z",
  "driver": {
    "driverId": "DRV_12345",
    "driverName": "John Smith",
    "phoneNumber": "+12192002824"
  },
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "callSid": "CA4746caaf456d7c2db1574b7d1f211f6a",
  "triggers_count": 2
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `call_sid` | string | **Our internal call identifier** - Use this for tracking and WebSocket subscription |
| `conversation_id` | string | ElevenLabs conversation identifier - Used for fetching complete conversation |
| `callSid` | string | Twilio call SID from ElevenLabs (phone system identifier) |
| `triggers_count` | number | Number of violations/reminders being discussed |

### Error Responses

**400 Bad Request - No driver data**
```json
{
  "detail": "No driver data provided"
}
```

**500 Internal Server Error - Call failed**
```json
{
  "detail": "Failed to initiate ElevenLabs call: Connection timeout"
}
```

### Important Notes

1. **Only First Driver Processed**: Although `drivers` is an array, only the first driver is processed per request
2. **Phone Number Normalization**: Phone numbers are automatically converted to E.164 format (+1XXXXXXXXXX)
3. **Proactive Call Tracking**: A Call record is created in the database BEFORE the ElevenLabs API call
4. **call_sid vs conversation_id**:
   - `call_sid`: Our identifier, generated immediately, use for WebSocket subscriptions
   - `conversation_id`: ElevenLabs identifier, received after API call succeeds
5. **Prompt Generation**: The backend automatically generates a conversational prompt based on violations and driver data

### What Happens Behind the Scenes

1. **Step 1**: Call record created with `call_sid`, status=IN_PROGRESS, conversation_id=NULL
2. **Step 2**: Dynamic prompt generated using violations and trip data
3. **Step 3**: ElevenLabs API called with prompt and phone number
4. **Step 4**: Call record updated with `conversation_id` from ElevenLabs response
5. **Step 5**: If API call fails, Call status updated to FAILED (record preserved for audit trail)

---

## Part 2: Real-Time Transcription (Automatic)

**Purpose**: Automatically receive and store conversation transcriptions as the call progresses

**Endpoint**: `POST /webhooks/elevenlabs/transcription` (Backend-only, ElevenLabs calls this)

**Flow**: ElevenLabs → Backend Webhook → Database → WebSocket Broadcast → Frontend

### What Happens Automatically

1. **During the call**, after each dialogue turn (agent speaks, user responds), ElevenLabs sends a webhook to our backend
2. **Backend receives** the transcription data with call_sid, speaker, message, sequence number
3. **Backend saves** the transcription to the database (`call_transcriptions` table)
4. **Backend broadcasts** the transcription to any subscribed WebSocket clients in real-time
5. **Frontend receives** the transcription via WebSocket (if subscribed) - see Part 5

### Webhook Payload Example (For Reference)

```json
{
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "speaker": "user",
  "message": "Yeah, I'll adjust the temperature right now",
  "timestamp": "2025-11-21T15:32:15.000Z"
}
```

### Transcription Storage

Each transcription is stored with:
- `conversation_id` (foreign key to Call)
- `speaker_type` (AGENT or DRIVER)
- `message_text` (what was said)
- `timestamp` (when it was said)
- `sequence_number` (order in conversation)
- `transcription_id` (unique ID)

### WebSocket Message Broadcast

When a transcription is saved, the following message is broadcast to subscribed clients:

```json
{
  "type": "transcription",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "transcription_id": 42,
  "sequence_number": 5,
  "speaker_type": "driver",
  "message_text": "Yeah, I'll adjust the temperature right now",
  "timestamp": "2025-11-21T15:32:15.000Z"
}
```

### Frontend Action Required

**Subscribe to WebSocket** (Part 5) to receive these transcriptions in real-time and display them in your UI.

---

## Part 3: Call Completion (Automatic)

**Purpose**: Automatically receive and store call completion metadata when call ends

**Endpoint**: `POST /webhooks/elevenlabs/post-call` (Backend-only, ElevenLabs calls this)

**Flow**: ElevenLabs → Backend Webhook → Database → WebSocket Broadcast → Frontend

### What Happens Automatically

1. **When the call ends**, ElevenLabs sends a post-call webhook with complete call metadata
2. **Backend receives** the completion data including:
   - Call duration, cost, success indicator
   - AI-generated transcript summary
   - Complete analysis results
3. **Backend updates** the Call record:
   - Status changed to COMPLETED
   - Metadata fields populated (summary, duration, cost, analysis)
4. **Backend broadcasts** TWO messages to subscribed WebSocket clients:
   - **Message 1**: Status update (call completed)
   - **Message 2**: Full call data with all metadata
5. **Frontend receives** both messages via WebSocket (if subscribed) - see Part 5

### Webhook Payload Types

ElevenLabs sends one of two webhook types:

#### Type 1: Post-Call Transcription (Successful Call)

```json
{
  "type": "post_call_transcription",
  "event_timestamp": 1732156800,
  "data": {
    "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
    "status": "done",
    "metadata": {
      "call_duration_secs": 145,
      "cost": 0.08,
      "phone_call": {
        "direction": "outbound",
        "agent_number": "+12196541187",
        "external_number": "+12192002824"
      }
    },
    "analysis": {
      "call_successful": "success",
      "transcript_summary": "Driver acknowledged temperature issue and agreed to adjust immediately. Confirmed receipt of load picture reminder."
    }
  }
}
```

#### Type 2: Call Initiation Failure

```json
{
  "type": "call_initiation_failure",
  "event_timestamp": 1732156800,
  "data": {
    "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
    "metadata": {
      "error": "Phone number unreachable"
    }
  }
}
```

### Call Metadata Stored

The following metadata is extracted and stored in the Call record:

| Field | Type | Description |
|-------|------|-------------|
| `transcript_summary` | Text | AI-generated summary of conversation |
| `call_duration_seconds` | Integer | Duration in seconds (e.g., 145) |
| `cost` | Float | Call cost in dollars (e.g., 0.08) |
| `call_successful` | Boolean | Whether call achieved its purpose |
| `analysis_data` | JSON | Complete analysis object from ElevenLabs |
| `metadata_json` | JSON | Complete metadata object from ElevenLabs |
| `status` | Enum | Updated to COMPLETED or FAILED |
| `call_end_time` | DateTime | When the call ended |

### WebSocket Messages Broadcast

**Message 1: Call Status Update**

```json
{
  "type": "call_status",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "status": "completed",
  "call_end_time": "2025-11-21T15:32:25.000Z"
}
```

**Message 2: Full Call Data** (sent immediately after Message 1)

```json
{
  "type": "call_completed",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "call_data": {
    "driver_id": "DRV_12345",
    "call_start_time": "2025-11-21T15:30:00.000Z",
    "call_end_time": "2025-11-21T15:32:25.000Z",
    "call_duration_seconds": 145,
    "cost": 0.08,
    "call_successful": true,
    "transcript_summary": "Driver acknowledged temperature issue and agreed to adjust immediately.",
    "status": "completed",
    "analysis": {
      "call_successful": "success",
      "transcript_summary": "Driver acknowledged temperature issue...",
      "evaluation_criteria_results": {},
      "data_collection_results": {}
    },
    "metadata": {
      "call_duration_secs": 145,
      "cost": 0.08,
      "phone_call": {
        "direction": "outbound",
        "agent_number": "+12196541187",
        "external_number": "+12192002824"
      }
    }
  }
}
```

### Frontend Action Required

**Subscribe to WebSocket** (Part 5) to receive call completion notifications and display final summary/results in your UI.

---

## Part 4: Conversation Fetching

**Purpose**: Fetch complete conversation history on demand (for reviewing past calls)

**Endpoint**: `POST /conversations/{conversation_id}/fetch`

**Authentication**: Required (JWT Bearer token)

**Use Cases**:
- Review past calls
- Debug issues
- Backfill missing data
- Display complete conversation history

### Request Format

```bash
curl -X POST 'https://your-domain.com/driver_data/conversations/conv_1901kaj4pr1penza6bbkscg6hgkc/fetch' \
  -H 'Authorization: Bearer YOUR_JWT_TOKEN' \
  -H 'Content-Type: application/json'
```

### Request Parameters

| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `conversation_id` | URL path | string | Yes | ElevenLabs conversation identifier |

**Note**: No request body required. The `conversation_id` in the URL is sufficient.

### Success Response (200 OK)

```json
{
  "message": "Conversation data fetched and stored successfully",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "call_updated": true,
  "call_status": "COMPLETED",
  "call_duration": 145,
  "transcriptions_added": 12,
  "transcriptions_total": 12,
  "conversation_data": {
    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
    "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
    "status": "done",
    "transcript": [
      {
        "role": "agent",
        "message": "Hey John, this is dispatch calling. Do you have a few minutes to chat about your trip?",
        "time_in_call_secs": 0
      },
      {
        "role": "user",
        "message": "Yeah, sure. What's up?",
        "time_in_call_secs": 4
      },
      {
        "role": "agent",
        "message": "I noticed your temp is at 45 degrees Fahrenheit but needs to be 38 degrees. What's going on with that?",
        "time_in_call_secs": 8
      },
      {
        "role": "user",
        "message": "Oh yeah, I'll adjust it right now. Thanks for catching that.",
        "time_in_call_secs": 15
      }
    ],
    "metadata": {
      "start_time_unix_secs": 1732156680,
      "call_duration_secs": 145,
      "cost": 0.08,
      "phone_call": {
        "direction": "outbound",
        "agent_number": "+12196541187",
        "external_number": "+12192002824",
        "type": "twilio"
      },
      "termination_reason": "Call ended by remote party"
    },
    "analysis": {
      "call_successful": "success",
      "transcript_summary": "Driver acknowledged temperature issue and agreed to adjust immediately. Confirmed receipt of load picture reminder.",
      "call_summary_title": "Temperature Adjustment Confirmed"
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | string | ElevenLabs conversation identifier |
| `call_sid` | string | Our internal call identifier |
| `call_updated` | boolean | Whether Call record was updated |
| `call_status` | string | Current call status (COMPLETED, FAILED, etc.) |
| `call_duration` | integer | Duration in seconds |
| `transcriptions_added` | integer | Number of NEW transcriptions added (0 if already fetched) |
| `transcriptions_total` | integer | Total transcriptions for this conversation |
| `conversation_data` | object | Complete conversation data from ElevenLabs |

### Conversation Data Structure

```typescript
interface ConversationData {
  agent_id: string;
  conversation_id: string;
  status: "done" | "in_progress";
  transcript: TranscriptTurn[];
  metadata: ConversationMetadata;
  analysis: ConversationAnalysis;
}

interface TranscriptTurn {
  role: "agent" | "user";
  message: string;
  time_in_call_secs: number;
  tool_calls?: any[];
  tool_results?: any[];
  llm_usage?: any;
  interrupted?: boolean;
}

interface ConversationMetadata {
  start_time_unix_secs: number;
  call_duration_secs: number;
  cost: number;
  phone_call: {
    direction: "outbound" | "inbound";
    agent_number: string;
    external_number: string;
    type: string;
  };
  termination_reason: string;
}

interface ConversationAnalysis {
  call_successful: "success" | "failure" | string;
  transcript_summary: string;
  call_summary_title: string;
  evaluation_criteria_results?: any;
  data_collection_results?: any;
}
```

### Error Responses

**404 Not Found - Conversation not found in ElevenLabs**
```json
{
  "detail": "Conversation conv_xxxxx not found in ElevenLabs"
}
```

**404 Not Found - Call record not found**
```json
{
  "detail": "Call record not found for conversation conv_xxxxx"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Failed to fetch conversation data: Connection timeout"
}
```

### Important Notes

1. **Idempotent**: Safe to call multiple times - won't create duplicate transcriptions
2. **Backfill Friendly**: Useful for filling gaps if real-time webhooks were missed
3. **Complete History**: Returns ENTIRE conversation, not just new data
4. **Large Response**: Can be 10KB-100KB+ for long conversations
5. **Use for Historical Review**: Best for reviewing past calls, not real-time monitoring (use WebSocket for that)

---

## Part 5: WebSocket Real-Time Updates

**Purpose**: Receive real-time transcriptions and call updates as they happen

**Endpoint**: `ws://your-domain.com/ws/calls/transcriptions` (or `wss://` for production)

**Authentication**: JWT token via query parameter

**Use Cases**:
- Display live conversation as it happens
- Show real-time call progress
- Notify users when calls complete
- Monitor multiple active calls simultaneously

### Connection Flow

```
1. Frontend connects to WebSocket with JWT token
2. Backend validates token and accepts connection
3. Frontend subscribes to specific call(s) by call_sid or conversation_id
4. Backend confirms subscription
5. Frontend receives real-time messages as call progresses
6. Frontend unsubscribes when done (optional)
7. Connection closes gracefully
```

### WebSocket URL Format

```
ws://your-domain.com/ws/calls/transcriptions?token=YOUR_JWT_TOKEN
```

**Production (SSL):**
```
wss://your-domain.com/ws/calls/transcriptions?token=YOUR_JWT_TOKEN
```

### Authentication

**Important**: WebSocket doesn't easily support headers, so JWT token is passed as a **query parameter**.

```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const ws = new WebSocket(`wss://your-domain.com/ws/calls/transcriptions?token=${token}`);
```

### Message Types

#### Client → Server Messages

**1. Subscribe to a Call**

Subscribe using either `call_sid` (preferred) or `conversation_id`:

```json
{
  "subscribe": "EL_DRV_12345_2025-11-21T15:30:00Z"
}
```

OR

```json
{
  "subscribe": "conv_1901kaj4pr1penza6bbkscg6hgkc"
}
```

**2. Unsubscribe from a Call**

```json
{
  "unsubscribe": "EL_DRV_12345_2025-11-21T15:30:00Z"
}
```

#### Server → Client Messages

**1. Subscription Confirmed**

```json
{
  "type": "subscription_confirmed",
  "identifier": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "status": "in_progress"
}
```

**2. Unsubscribe Confirmed**

```json
{
  "type": "unsubscribe_confirmed",
  "identifier": "EL_DRV_12345_2025-11-21T15:30:00Z"
}
```

**3. Transcription (Real-Time Dialogue)**

Received during the call, after each dialogue turn:

```json
{
  "type": "transcription",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "transcription_id": 42,
  "sequence_number": 5,
  "speaker_type": "driver",
  "message_text": "Yeah, I'll adjust the temperature right now",
  "timestamp": "2025-11-21T15:32:15.000Z"
}
```

**4. Call Status Update**

Received when call completes (first of two messages):

```json
{
  "type": "call_status",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "status": "completed",
  "call_end_time": "2025-11-21T15:32:25.000Z"
}
```

**5. Call Completed (Full Data)**

Received immediately after call_status (second of two messages):

```json
{
  "type": "call_completed",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_12345_2025-11-21T15:30:00Z",
  "call_data": {
    "driver_id": "DRV_12345",
    "call_start_time": "2025-11-21T15:30:00.000Z",
    "call_end_time": "2025-11-21T15:32:25.000Z",
    "call_duration_seconds": 145,
    "cost": 0.08,
    "call_successful": true,
    "transcript_summary": "Driver acknowledged temperature issue and agreed to adjust immediately.",
    "status": "completed"
  }
}
```

**6. Error Message**

```json
{
  "type": "error",
  "message": "Call not found",
  "code": "CALL_NOT_FOUND"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `CALL_NOT_FOUND` | The call_sid or conversation_id doesn't exist |
| `INVALID_IDENTIFIER` | The identifier format is invalid |
| `INVALID_MESSAGE` | The message format is invalid |
| `AUTHENTICATION_FAILED` | JWT token is invalid or expired |

### JavaScript/Browser Example

```javascript
class CallMonitor {
  constructor(baseUrl, authToken) {
    this.baseUrl = baseUrl;
    this.authToken = authToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = `${this.baseUrl}/ws/calls/transcriptions?token=${this.authToken}`;
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

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.attemptReconnect();
    };
  }

  handleMessage(message) {
    switch (message.type) {
      case 'subscription_confirmed':
        console.log(`Subscribed to call: ${message.call_sid}`);
        this.onSubscriptionConfirmed(message);
        break;

      case 'transcription':
        console.log(`New transcription: ${message.speaker_type}: ${message.message_text}`);
        this.onTranscription(message);
        break;

      case 'call_status':
        console.log(`Call status: ${message.status}`);
        this.onCallStatus(message);
        break;

      case 'call_completed':
        console.log('Call completed with full data');
        this.onCallCompleted(message);
        break;

      case 'error':
        console.error(`Error: ${message.message} (${message.code})`);
        this.onError(message);
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  subscribeToCall(callSidOrConversationId) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        subscribe: callSidOrConversationId
      }));
    } else {
      console.error('WebSocket not connected');
    }
  }

  unsubscribeFromCall(callSidOrConversationId) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        unsubscribe: callSidOrConversationId
      }));
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
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
  onSubscriptionConfirmed(message) { }
  onTranscription(message) { }
  onCallStatus(message) { }
  onCallCompleted(message) { }
  onError(message) { }
}

// Usage
const monitor = new CallMonitor('wss://your-domain.com', 'your-jwt-token');

// Override handlers
monitor.onTranscription = (message) => {
  // Update UI with new transcription
  const transcriptDiv = document.getElementById('transcript');
  const entry = document.createElement('div');
  entry.className = message.speaker_type === 'agent' ? 'agent-message' : 'driver-message';
  entry.textContent = `${message.speaker_type}: ${message.message_text}`;
  transcriptDiv.appendChild(entry);
};

monitor.onCallCompleted = (message) => {
  // Show call summary
  alert(`Call completed! Summary: ${message.call_data.transcript_summary}`);
};

// Connect and subscribe
monitor.connect();

// After connection opens, subscribe to a call
setTimeout(() => {
  monitor.subscribeToCall('EL_DRV_12345_2025-11-21T15:30:00Z');
}, 1000);
```

### React Hook Example

```typescript
import { useEffect, useRef, useState } from 'react';

interface Transcription {
  transcription_id: number;
  sequence_number: number;
  speaker_type: 'agent' | 'driver';
  message_text: string;
  timestamp: string;
}

interface CallData {
  driver_id: string;
  call_duration_seconds: number;
  cost: number;
  call_successful: boolean;
  transcript_summary: string;
  status: string;
}

export function useCallMonitor(callSidOrConversationId: string, authToken: string) {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [callStatus, setCallStatus] = useState<string>('connecting');
  const [callData, setCallData] = useState<CallData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = `wss://your-domain.com/ws/calls/transcriptions?token=${authToken}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      // Subscribe to the call
      ws.send(JSON.stringify({ subscribe: callSidOrConversationId }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'subscription_confirmed':
          setCallStatus(message.status || 'in_progress');
          break;

        case 'transcription':
          setTranscriptions((prev) => [...prev, {
            transcription_id: message.transcription_id,
            sequence_number: message.sequence_number,
            speaker_type: message.speaker_type,
            message_text: message.message_text,
            timestamp: message.timestamp
          }]);
          break;

        case 'call_status':
          setCallStatus(message.status);
          break;

        case 'call_completed':
          setCallData(message.call_data);
          setCallStatus('completed');
          break;

        case 'error':
          setError(message.message);
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error');
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setCallStatus('disconnected');
    };

    // Cleanup on unmount
    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ unsubscribe: callSidOrConversationId }));
        ws.close();
      }
    };
  }, [callSidOrConversationId, authToken]);

  return {
    transcriptions,
    callStatus,
    callData,
    error,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  };
}

// Usage in component
function CallMonitorComponent({ callSid, authToken }) {
  const { transcriptions, callStatus, callData, error } = useCallMonitor(callSid, authToken);

  return (
    <div>
      <h2>Call Status: {callStatus}</h2>
      {error && <div className="error">{error}</div>}

      <div className="transcriptions">
        {transcriptions.map((t) => (
          <div key={t.transcription_id} className={t.speaker_type}>
            <strong>{t.speaker_type}:</strong> {t.message_text}
          </div>
        ))}
      </div>

      {callData && (
        <div className="call-summary">
          <h3>Call Completed</h3>
          <p>Duration: {callData.call_duration_seconds}s</p>
          <p>Cost: ${callData.cost.toFixed(2)}</p>
          <p>Summary: {callData.transcript_summary}</p>
        </div>
      )}
    </div>
  );
}
```

### Python Example (asyncio)

```python
import asyncio
import websockets
import json

async def monitor_call(call_sid, auth_token):
    """Monitor a call via WebSocket"""
    uri = f"wss://your-domain.com/ws/calls/transcriptions?token={auth_token}"

    async with websockets.connect(uri) as websocket:
        print("WebSocket connected")

        # Subscribe to the call
        await websocket.send(json.dumps({"subscribe": call_sid}))

        try:
            async for message in websocket:
                data = json.loads(message)

                if data["type"] == "subscription_confirmed":
                    print(f"Subscribed to call: {data['call_sid']}")

                elif data["type"] == "transcription":
                    print(f"{data['speaker_type']}: {data['message_text']}")

                elif data["type"] == "call_status":
                    print(f"Call status: {data['status']}")

                elif data["type"] == "call_completed":
                    print(f"Call completed!")
                    print(f"Summary: {data['call_data']['transcript_summary']}")
                    print(f"Duration: {data['call_data']['call_duration_seconds']}s")
                    print(f"Cost: ${data['call_data']['cost']}")
                    break

                elif data["type"] == "error":
                    print(f"Error: {data['message']} ({data.get('code', 'UNKNOWN')})")

        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")

# Usage
asyncio.run(monitor_call("EL_DRV_12345_2025-11-21T15:30:00Z", "your-jwt-token"))
```

### Important Notes

1. **Token in Query Parameter**: Unlike REST APIs that use `Authorization` header, WebSocket requires token in query string
2. **Auto-Detection**: You can subscribe using either `call_sid` (our ID) or `conversation_id` (ElevenLabs ID) - backend auto-detects
3. **Multiple Subscriptions**: You can subscribe to multiple calls on the same connection
4. **Two-Message Completion**: When a call completes, you receive TWO messages:
   - `call_status` (quick notification)
   - `call_completed` (full data with summary and metadata)
5. **Client-Side Reconnection**: If connection drops, implement exponential backoff reconnection on the client side
6. **Heartbeat**: WebSocket connection stays alive - no manual ping/pong required
7. **Message Order**: Transcriptions arrive in sequence order, guaranteed

---

## Complete End-to-End Example

### Scenario: Monitor a Driver Call from Start to Finish

```javascript
// Step 1: Initiate the call
async function initiateDriverCall() {
  const response = await fetch('https://your-domain.com/driver_data/call-elevenlabs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
    body: JSON.stringify({
      callType: 'violation',
      timestamp: new Date().toISOString(),
      drivers: [{
        driverId: 'DRV_12345',
        driverName: 'John Smith',
        phoneNumber: '+12192002824',
        customRules: '',
        violations: {
          tripId: 'TRIP_78910',
          violationDetails: [
            {
              type: 'violation',
              description: 'Your temp is at 45 degrees but needs to be 38 degrees'
            }
          ]
        }
      }]
    })
  });

  const data = await response.json();
  console.log('Call initiated:', data);

  return {
    callSid: data.call_sid,
    conversationId: data.conversation_id
  };
}

// Step 2: Connect to WebSocket and subscribe
function monitorCall(callSid, authToken) {
  const ws = new WebSocket(`wss://your-domain.com/ws/calls/transcriptions?token=${authToken}`);

  const transcriptions = [];

  ws.onopen = () => {
    console.log('WebSocket connected');
    // Subscribe to the call we just initiated
    ws.send(JSON.stringify({ subscribe: callSid }));
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
      case 'subscription_confirmed':
        console.log('✓ Subscribed to call');
        updateUI({ status: 'Call in progress...' });
        break;

      case 'transcription':
        // Real-time transcription received
        transcriptions.push(message);
        updateUI({
          newTranscription: {
            speaker: message.speaker_type,
            text: message.message_text,
            time: message.timestamp
          }
        });
        break;

      case 'call_status':
        // Call completed notification
        console.log('Call completed');
        updateUI({ status: 'Call completed' });
        break;

      case 'call_completed':
        // Full call data received
        console.log('Call data:', message.call_data);
        updateUI({
          summary: message.call_data.transcript_summary,
          duration: message.call_data.call_duration_seconds,
          cost: message.call_data.cost,
          successful: message.call_data.call_successful
        });

        // Optionally fetch complete history
        fetchCompleteHistory(message.conversation_id);
        break;

      case 'error':
        console.error('Error:', message.message);
        updateUI({ error: message.message });
        break;
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket closed');
  };

  return ws;
}

// Step 3 (Optional): Fetch complete history
async function fetchCompleteHistory(conversationId) {
  const response = await fetch(
    `https://your-domain.com/driver_data/conversations/${conversationId}/fetch`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    }
  );

  const data = await response.json();
  console.log('Complete conversation:', data.conversation_data);

  // Display full transcript
  displayFullTranscript(data.conversation_data.transcript);
}

// Complete flow
async function completeFlow() {
  const authToken = 'your-jwt-token';

  try {
    // 1. Initiate call
    const { callSid, conversationId } = await initiateDriverCall();
    console.log(`Call initiated: ${callSid}`);

    // 2. Monitor in real-time
    const ws = monitorCall(callSid, authToken);

    // WebSocket will automatically receive:
    // - Real-time transcriptions (Part 2)
    // - Call completion notification (Part 3)
    // - Full call data with metadata (Part 3)

    // 3. (Optional) After call completes, fetch full history
    // This happens automatically in the 'call_completed' handler above

  } catch (error) {
    console.error('Error:', error);
  }
}

// Helper function to update UI (implement based on your framework)
function updateUI(updates) {
  if (updates.status) {
    document.getElementById('call-status').textContent = updates.status;
  }

  if (updates.newTranscription) {
    const transcript = document.getElementById('transcript');
    const entry = document.createElement('div');
    entry.className = updates.newTranscription.speaker;
    entry.innerHTML = `
      <strong>${updates.newTranscription.speaker}:</strong>
      ${updates.newTranscription.text}
      <span class="time">${new Date(updates.newTranscription.time).toLocaleTimeString()}</span>
    `;
    transcript.appendChild(entry);
    transcript.scrollTop = transcript.scrollHeight;
  }

  if (updates.summary) {
    document.getElementById('call-summary').textContent = updates.summary;
    document.getElementById('call-duration').textContent = `${updates.duration}s`;
    document.getElementById('call-cost').textContent = `$${updates.cost.toFixed(2)}`;
    document.getElementById('call-success').textContent = updates.successful ? 'Yes' : 'No';
  }

  if (updates.error) {
    document.getElementById('error-message').textContent = updates.error;
  }
}
```

### Timeline of Events

```
T+0s:   [Frontend] POST /driver_data/call-elevenlabs
T+0.5s: [Backend] Call record created (status=IN_PROGRESS, conversation_id=NULL)
T+1s:   [Backend] ElevenLabs API called
T+1.5s: [Backend] Call record updated (conversation_id set)
T+2s:   [Frontend] Receives response with call_sid and conversation_id
T+2.5s: [Frontend] Opens WebSocket connection
T+3s:   [Frontend] Sends subscribe message with call_sid
T+3.5s: [Backend] Confirms subscription
T+4s:   [ElevenLabs] Call connects to driver
T+5s:   [ElevenLabs] Agent speaks
T+8s:   [ElevenLabs] → Webhook Part 2: Transcription (agent dialogue)
T+8.1s: [Backend] Saves transcription, broadcasts via WebSocket
T+8.2s: [Frontend] Receives transcription message
T+10s:  [ElevenLabs] Driver responds
T+12s:  [ElevenLabs] → Webhook Part 2: Transcription (driver dialogue)
T+12.1s:[Backend] Saves transcription, broadcasts via WebSocket
T+12.2s:[Frontend] Receives transcription message
... (conversation continues) ...
T+145s: [ElevenLabs] Call ends
T+146s: [ElevenLabs] → Webhook Part 3: Post-call completion
T+146.1s:[Backend] Updates Call (status=COMPLETED, metadata stored)
T+146.2s:[Backend] Broadcasts call_status message
T+146.3s:[Backend] Broadcasts call_completed message (full data)
T+146.4s:[Frontend] Receives both messages, displays summary
```

---

## Error Handling

### API Errors (Part 1, Part 4)

```javascript
async function handleApiCall() {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 400:
          console.error('Bad request:', error.detail);
          // Show user-friendly error message
          break;

        case 401:
          console.error('Unauthorized');
          // Redirect to login
          break;

        case 404:
          console.error('Not found:', error.detail);
          // Show "Call not found" message
          break;

        case 500:
          console.error('Server error:', error.detail);
          // Show "Something went wrong" message
          // Retry with exponential backoff
          break;
      }

      throw new Error(error.detail || 'API call failed');
    }

    return await response.json();

  } catch (error) {
    console.error('Network error:', error);
    // Handle network failures
    throw error;
  }
}
```

### WebSocket Errors (Part 5)

```javascript
class RobustWebSocket {
  constructor(url, authToken) {
    this.url = url;
    this.authToken = authToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    try {
      this.ws = new WebSocket(`${this.url}?token=${this.authToken}`);

      this.ws.onopen = () => {
        console.log('Connected');
        this.reconnectAttempts = 0;
        this.onConnected();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError(error);
      };

      this.ws.onclose = (event) => {
        console.log(`Connection closed: ${event.code} ${event.reason}`);
        this.handleDisconnect(event);
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      this.handleDisconnect();
    }
  }

  handleMessage(message) {
    if (message.type === 'error') {
      switch (message.code) {
        case 'AUTHENTICATION_FAILED':
          // Token expired, refresh and reconnect
          this.refreshTokenAndReconnect();
          break;

        case 'CALL_NOT_FOUND':
          // Call doesn't exist
          this.onCallNotFound(message);
          break;

        case 'INVALID_MESSAGE':
          // Malformed message sent
          console.error('Invalid message format');
          break;
      }
    } else {
      // Normal message processing
      this.onMessage(message);
    }
  }

  handleDisconnect(event) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      this.onMaxReconnectAttemptsReached();
    }
  }

  async refreshTokenAndReconnect() {
    try {
      const newToken = await this.refreshToken();
      this.authToken = newToken;
      this.reconnectAttempts = 0;
      this.connect();
    } catch (error) {
      console.error('Failed to refresh token:', error);
      this.onAuthenticationFailed();
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
      throw new Error('WebSocket not connected');
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  // Override these methods
  onConnected() {}
  onMessage(message) {}
  onError(error) {}
  onCallNotFound(message) {}
  onAuthenticationFailed() {}
  onMaxReconnectAttemptsReached() {}
  async refreshToken() {
    // Implement token refresh logic
    throw new Error('Not implemented');
  }
}
```

### Common Error Scenarios

| Scenario | Handling Strategy |
|----------|-------------------|
| Token expired during call | Refresh token, reconnect WebSocket, resubscribe to call |
| Network interruption | Exponential backoff reconnection (1s, 2s, 4s, 8s, 16s) |
| Call not found | Check call_sid/conversation_id, fetch from Part 4 if needed |
| WebSocket message parse error | Log error, skip message, continue processing |
| API call timeout | Retry with exponential backoff (max 3 retries) |
| Invalid phone number | Validate format before sending (E.164: +1XXXXXXXXXX) |
| No violations provided | Validate request payload before sending |
| Call creation succeeds but ElevenLabs fails | Call record exists with status=FAILED, retry safe |

---

## Best Practices

### 1. Use call_sid for Everything

```javascript
// After initiating call, store call_sid
const { call_sid, conversation_id } = await initiateCall();

// Use call_sid for WebSocket subscription (preferred)
ws.send(JSON.stringify({ subscribe: call_sid }));

// Only use conversation_id for Part 4 (fetching history)
await fetch(`/conversations/${conversation_id}/fetch`);
```

**Why**: `call_sid` is generated immediately and is our internal identifier. It's always available, even if ElevenLabs API call fails.

### 2. Subscribe to WebSocket Before Call Completes

```javascript
// GOOD: Subscribe immediately after call initiation
const { call_sid } = await initiateCall();
const ws = connectWebSocket(authToken);
ws.onopen = () => {
  ws.send(JSON.stringify({ subscribe: call_sid }));
};

// BAD: Subscribing too late might miss transcriptions
await initiateCall();
await sleep(30000); // Don't do this!
const ws = connectWebSocket(authToken); // Might miss messages
```

### 3. Handle Reconnections Gracefully

```javascript
class PersistentMonitor {
  constructor(callSid, authToken) {
    this.callSid = callSid;
    this.authToken = authToken;
    this.subscriptions = new Set([callSid]);
  }

  onConnect() {
    // Resubscribe to all calls after reconnection
    for (const callSid of this.subscriptions) {
      this.ws.send(JSON.stringify({ subscribe: callSid }));
    }
  }

  addSubscription(callSid) {
    this.subscriptions.add(callSid);
    if (this.isConnected()) {
      this.ws.send(JSON.stringify({ subscribe: callSid }));
    }
  }
}
```

### 4. Validate Data Before Sending

```javascript
function validateCallRequest(request) {
  if (!request.drivers || request.drivers.length === 0) {
    throw new Error('No driver data provided');
  }

  const driver = request.drivers[0];

  // Validate phone number format
  const phoneRegex = /^\+?1?\d{10}$/;
  if (!phoneRegex.test(driver.phoneNumber.replace(/[^\d+]/g, ''))) {
    throw new Error('Invalid phone number format');
  }

  // Validate violations
  if (!driver.violations || !driver.violations.violationDetails || driver.violations.violationDetails.length === 0) {
    throw new Error('No violations provided');
  }

  return true;
}
```

### 5. Cache Call Data Locally

```javascript
class CallCache {
  constructor() {
    this.calls = new Map();
  }

  addCall(callSid, data) {
    this.calls.set(callSid, {
      ...data,
      transcriptions: [],
      status: 'in_progress',
      lastUpdated: Date.now()
    });
  }

  addTranscription(callSid, transcription) {
    const call = this.calls.get(callSid);
    if (call) {
      call.transcriptions.push(transcription);
      call.lastUpdated = Date.now();
    }
  }

  updateStatus(callSid, status, metadata) {
    const call = this.calls.get(callSid);
    if (call) {
      call.status = status;
      call.metadata = metadata;
      call.lastUpdated = Date.now();
    }
  }

  getCall(callSid) {
    return this.calls.get(callSid);
  }
}
```

### 6. Monitor Multiple Calls Efficiently

```javascript
class MultiCallMonitor {
  constructor(authToken) {
    this.authToken = authToken;
    this.ws = null;
    this.activeCalls = new Map();
  }

  connect() {
    this.ws = new WebSocket(`wss://your-domain.com/ws/calls/transcriptions?token=${this.authToken}`);

    this.ws.onopen = () => {
      // Resubscribe to all active calls
      for (const callSid of this.activeCalls.keys()) {
        this.ws.send(JSON.stringify({ subscribe: callSid }));
      }
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      const callSid = message.call_sid;

      if (this.activeCalls.has(callSid)) {
        const handler = this.activeCalls.get(callSid);
        handler(message);
      }
    };
  }

  monitorCall(callSid, handler) {
    this.activeCalls.set(callSid, handler);

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ subscribe: callSid }));
    }
  }

  stopMonitoring(callSid) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ unsubscribe: callSid }));
    }
    this.activeCalls.delete(callSid);
  }
}

// Usage
const monitor = new MultiCallMonitor(authToken);
monitor.connect();

// Monitor multiple calls
monitor.monitorCall('call_sid_1', (message) => {
  console.log('Call 1:', message);
});

monitor.monitorCall('call_sid_2', (message) => {
  console.log('Call 2:', message);
});
```

### 7. Implement Proper Cleanup

```javascript
useEffect(() => {
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    ws.send(JSON.stringify({ subscribe: callSid }));
  };

  // ... message handlers ...

  // Cleanup on unmount
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      // Unsubscribe before closing
      ws.send(JSON.stringify({ unsubscribe: callSid }));
      ws.close(1000, 'Component unmounting');
    }
  };
}, [callSid, authToken]);
```

### 8. Rate Limit API Calls

```javascript
class RateLimiter {
  constructor(maxCalls, perMs) {
    this.maxCalls = maxCalls;
    this.perMs = perMs;
    this.calls = [];
  }

  async acquire() {
    const now = Date.now();
    this.calls = this.calls.filter(t => t > now - this.perMs);

    if (this.calls.length >= this.maxCalls) {
      const oldestCall = Math.min(...this.calls);
      const waitTime = oldestCall + this.perMs - now;
      await new Promise(resolve => setTimeout(resolve, waitTime));
      return this.acquire();
    }

    this.calls.push(now);
  }
}

// Usage: Max 10 calls per minute
const limiter = new RateLimiter(10, 60000);

async function initiateCall(data) {
  await limiter.acquire();
  return fetch('/driver_data/call-elevenlabs', { ... });
}
```

### 9. Log Important Events

```javascript
const logger = {
  info: (message, data) => {
    console.log(`[INFO] ${new Date().toISOString()} - ${message}`, data);
  },
  error: (message, error) => {
    console.error(`[ERROR] ${new Date().toISOString()} - ${message}`, error);
    // Send to error tracking service (e.g., Sentry)
  },
  callEvent: (event, callSid, data) => {
    console.log(`[CALL_EVENT] ${event} - ${callSid}`, data);
    // Send to analytics
  }
};

// Usage
logger.callEvent('INITIATED', callSid, { driverId, phoneNumber });
logger.callEvent('TRANSCRIPTION_RECEIVED', callSid, { sequence: 5 });
logger.callEvent('COMPLETED', callSid, { duration, cost });
```

### 10. Test with Mock Data

```javascript
// Mock WebSocket for testing
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;

    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.();
      this.simulateMessages();
    }, 100);
  }

  send(data) {
    const message = JSON.parse(data);
    console.log('Mock WS sent:', message);

    if (message.subscribe) {
      setTimeout(() => {
        this.onmessage?.({
          data: JSON.stringify({
            type: 'subscription_confirmed',
            call_sid: message.subscribe,
            status: 'in_progress'
          })
        });
      }, 50);
    }
  }

  simulateMessages() {
    // Simulate transcriptions
    const messages = [
      { type: 'transcription', speaker_type: 'agent', message_text: 'Hey John...' },
      { type: 'transcription', speaker_type: 'driver', message_text: 'Yeah...' },
      { type: 'call_status', status: 'completed' },
      { type: 'call_completed', call_data: { /* ... */ } }
    ];

    messages.forEach((msg, index) => {
      setTimeout(() => {
        this.onmessage?.({ data: JSON.stringify(msg) });
      }, 1000 * (index + 1));
    });
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }
}
```

---

## Summary

This integration provides a complete real-time conversational AI system:

1. **Part 1**: Initiate calls with violations/reminders → Receive `call_sid` and `conversation_id`
2. **Part 2**: Automatic transcription storage → Real-time broadcasts via WebSocket
3. **Part 3**: Automatic call completion tracking → Status + metadata broadcasts via WebSocket
4. **Part 4**: On-demand conversation fetching → Complete history retrieval
5. **Part 5**: WebSocket subscriptions → Real-time monitoring of active calls

**Key Identifiers:**
- `call_sid`: Our internal ID, use for WebSocket subscriptions
- `conversation_id`: ElevenLabs ID, use for fetching complete history

**Recommended Flow:**
1. Initiate call → Get `call_sid`
2. Connect WebSocket → Subscribe with `call_sid`
3. Receive real-time transcriptions as call progresses
4. Receive completion notification when call ends
5. (Optional) Fetch complete history using `conversation_id`

For questions or issues, refer to:
- API Documentation: `/deployment/api-documentation.md`
- Deployment Checklist: `/deployment/deployment-checklist.md`
- Backend Documentation: `CLAUDE.md`
