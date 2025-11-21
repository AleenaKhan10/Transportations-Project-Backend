# Frontend Implementation Guide - ElevenLabs Live Calls

## Backend API Endpoints - Status Confirmation

### ✅ **Available Endpoints**

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/driver_data/call-elevenlabs` | POST | Initiate call | ✅ **Working** |
| `/calls` | GET | List all calls (with filters) | ✅ **NEW** |
| `/calls/active` | GET | Get active calls only | ✅ **NEW** |
| `/calls/{call_sid}` | GET | Get call details | ✅ **NEW** |
| `/calls/{call_sid}/transcript` | GET | Get call transcript | ✅ **NEW** |
| `/calls/{call_sid}/full` | GET | Get call + transcript | ✅ **NEW** |
| `/driver_data/conversations/{conversation_id}/fetch` | POST | Manual fetch from ElevenLabs | ✅ **NEW** |
| `/webhooks/elevenlabs/transcription` | POST | Webhook for real-time transcripts | ✅ **Working** |

---

## Complete Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FRONTEND: Driver Triggers Page                           │
│  User selects driver → selects violations → clicks "Call Driver"            │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  POST /driver_data/call-elevenlabs                                           │
│  {                                                                            │
│    "callType": "violation",                                                  │
│    "timestamp": "2025-01-21T10:30:00Z",                                      │
│    "drivers": [{                                                             │
│      "driverId": "DRV123",                                                   │
│      "violations": {                                                         │
│        "violationDetails": [...]                                             │
│      }                                                                       │
│    }]                                                                        │
│  }                                                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKEND RESPONSE:                                                           │
│  {                                                                           │
│    "message": "Call initiated successfully",                                │
│    "conversation_id": "conv_1901kaj4pr...",                                 │
│    "call_sid": "EL_DRV123_1737456600000",                                   │
│    "driver": { ... }                                                        │
│  }                                                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FRONTEND: Switch to "Live Calls" View                                      │
│  → Start polling GET /calls/active every 3-5 seconds                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GET /calls/active                                                           │
│  Returns:                                                                    │
│  [                                                                           │
│    {                                                                         │
│      "call_sid": "EL_DRV123_...",                                           │
│      "conversation_id": "conv_...",                                         │
│      "driver_id": "DRV123",                                                 │
│      "status": "in_progress",                                               │
│      "call_start_time": "2025-01-21T10:30:00Z",                             │
│      "duration_seconds": 45                                                 │
│    }                                                                         │
│  ]                                                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  For each active call:                                                       │
│  GET /calls/{call_sid}/transcript                                           │
│  → Poll every 2-3 seconds for real-time updates                             │
│                                                                              │
│  Returns:                                                                    │
│  [                                                                           │
│    {                                                                         │
│      "role": "agent",                                                       │
│      "text": "Hey John, this is dispatch...",                               │
│      "timestamp": "2025-01-21T10:30:05Z",                                   │
│      "sequence_number": 1                                                   │
│    },                                                                        │
│    {                                                                         │
│      "role": "driver",                                                      │
│      "text": "Yeah, I have a few minutes",                                  │
│      "timestamp": "2025-01-21T10:30:08Z",                                   │
│      "sequence_number": 2                                                   │
│    }                                                                         │
│  ]                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  When call status changes to "completed":                                    │
│  → Stop polling for that call                                                │
│  → Optionally fetch full conversation with summary                           │
│  → POST /driver_data/conversations/{conversation_id}/fetch                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoint Details

### 1. **Initiate Call** (Already Working)

**Endpoint:** `POST /driver_data/call-elevenlabs`

**Request:**
```json
{
  "callType": "violation",
  "timestamp": "2025-01-21T10:30:00Z",
  "drivers": [
    {
      "driverId": "DRV123",
      "driverName": "John Smith",
      "phoneNumber": "+14155551234",
      "customRules": "Be polite",
      "violations": {
        "tripId": "TRIP456",
        "violationDetails": [
          {
            "type": "violation",
            "description": "Temperature not equal to set point"
          }
        ]
      }
    }
  ]
}
```

**Response:**
```json
{
  "message": "Call initiated successfully via ElevenLabs",
  "timestamp": "2025-01-21T10:30:00Z",
  "driver": {
    "driverId": "DRV123",
    "driverName": "John Smith",
    "phoneNumber": "+14155551234"
  },
  "call_sid": "EL_DRV123_1737456600000",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "callSid": "CA1234567890abcdef",
  "triggers_count": 2
}
```

---

### 2. **Get Active Calls** (New)

**Endpoint:** `GET /calls/active`

**Purpose:** Fetch all in-progress calls for the live view

**Response:**
```json
[
  {
    "call_sid": "EL_DRV123_1737456600000",
    "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
    "driver_id": "DRV123",
    "status": "in_progress",
    "call_start_time": "2025-01-21T10:30:00Z",
    "call_end_time": null,
    "duration_seconds": 45,
    "created_at": "2025-01-21T10:30:00Z",
    "updated_at": "2025-01-21T10:30:45Z"
  }
]
```

**Polling Strategy:**
- Poll every **3-5 seconds** while "Live Calls" view is active
- Stop polling when switching back to "Driver Triggers" view

---

### 3. **Get Call Transcript** (New)

**Endpoint:** `GET /calls/{call_sid}/transcript`

**Purpose:** Fetch real-time transcript for a specific call

**Query Parameters:**
- `limit` (optional): Maximum number of messages to return

**Response:**
```json
[
  {
    "role": "agent",
    "text": "Hey John, this is dispatch calling. Do you have a few minutes?",
    "timestamp": "2025-01-21T10:30:05Z",
    "sequence_number": 1
  },
  {
    "role": "driver",
    "text": "Yeah, I have a few minutes",
    "timestamp": "2025-01-21T10:30:08Z",
    "sequence_number": 2
  },
  {
    "role": "agent",
    "text": "I see your temp is at 45 degrees but it needs to be 35 degrees. What's going on?",
    "timestamp": "2025-01-21T10:30:12Z",
    "sequence_number": 3
  }
]
```

**Polling Strategy:**
- Poll every **2-3 seconds** for each active call
- Compare `sequence_number` to detect new messages
- Auto-scroll to latest message

---

### 4. **Get Call Details** (New)

**Endpoint:** `GET /calls/{call_sid}`

**Purpose:** Fetch call metadata (without transcript)

**Response:**
```json
{
  "call_sid": "EL_DRV123_1737456600000",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "driver_id": "DRV123",
  "status": "in_progress",
  "call_start_time": "2025-01-21T10:30:00Z",
  "call_end_time": null,
  "duration_seconds": 45,
  "created_at": "2025-01-21T10:30:00Z",
  "updated_at": "2025-01-21T10:30:45Z"
}
```

---

### 5. **Get Call with Full Transcript** (New)

**Endpoint:** `GET /calls/{call_sid}/full`

**Purpose:** Convenience endpoint that returns call + transcript in one request

**Response:**
```json
{
  "call_sid": "EL_DRV123_1737456600000",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "driver_id": "DRV123",
  "status": "in_progress",
  "call_start_time": "2025-01-21T10:30:00Z",
  "call_end_time": null,
  "duration_seconds": 45,
  "transcript": [
    {
      "role": "agent",
      "text": "Hey John...",
      "timestamp": "2025-01-21T10:30:05Z",
      "sequence_number": 1
    }
  ],
  "transcript_count": 15
}
```

---

### 6. **List All Calls** (New)

**Endpoint:** `GET /calls`

**Purpose:** List calls with optional filtering

**Query Parameters:**
- `status`: Filter by status (`in_progress`, `completed`, `failed`)
- `driver_id`: Filter by driver ID
- `limit`: Max results (default: 100, max: 500)

**Examples:**
- `GET /calls?status=completed&limit=50` - Get last 50 completed calls
- `GET /calls?driver_id=DRV123` - Get all calls for driver DRV123

**Response:** Same as `/calls/active`

---

### 7. **Fetch Conversation from ElevenLabs** (New)

**Endpoint:** `POST /driver_data/conversations/{conversation_id}/fetch`

**Purpose:** Manually fetch complete conversation data from ElevenLabs API

**Use Cases:**
- Webhook failed
- Need conversation summary
- Backfill missing data

**Response:**
```json
{
  "message": "Conversation data fetched and stored successfully",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV123_1737456600000",
  "call_updated": true,
  "call_status": "completed",
  "call_duration": 180,
  "transcriptions_added": 15,
  "transcriptions_total": 15,
  "conversation_data": {
    "conversation_id": "conv_...",
    "status": "done",
    "transcript": [...],
    "metadata": {
      "call_duration_secs": 180,
      "analysis": {
        "call_successful": true,
        "transcript_summary": "Driver confirmed temperature issue and will adjust setpoint..."
      }
    }
  }
}
```

---

## Frontend Implementation Steps

### **Phase 1: Create Services**

#### File: `src/services/elevenLabsCallService.ts` (NEW)

```typescript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface TranscriptMessage {
  role: 'agent' | 'driver';
  text: string;
  timestamp: string;
  sequence_number: number;
}

export interface Call {
  call_sid: string;
  conversation_id: string | null;
  driver_id: string | null;
  status: 'in_progress' | 'completed' | 'failed';
  call_start_time: string;
  call_end_time: string | null;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface CallWithTranscript extends Call {
  transcript: TranscriptMessage[];
  transcript_count: number;
}

class ElevenLabsCallService {
  /**
   * Fetch all active (in-progress) calls
   */
  async fetchActiveCalls(): Promise<Call[]> {
    const response = await axios.get(`${API_BASE_URL}/calls/active`);
    return response.data;
  }

  /**
   * Fetch call details by call_sid
   */
  async fetchCallDetails(call_sid: string): Promise<Call> {
    const response = await axios.get(`${API_BASE_URL}/calls/${call_sid}`);
    return response.data;
  }

  /**
   * Fetch real-time transcript for a call
   */
  async fetchTranscript(call_sid: string): Promise<TranscriptMessage[]> {
    const response = await axios.get(`${API_BASE_URL}/calls/${call_sid}/transcript`);
    return response.data;
  }

  /**
   * Fetch call with full transcript (convenience method)
   */
  async fetchCallWithTranscript(call_sid: string): Promise<CallWithTranscript> {
    const response = await axios.get(`${API_BASE_URL}/calls/${call_sid}/full`);
    return response.data;
  }

  /**
   * Fetch conversation from ElevenLabs API (manual fetch)
   */
  async fetchConversationFromElevenLabs(conversation_id: string): Promise<any> {
    const response = await axios.post(
      `${API_BASE_URL}/driver_data/conversations/${conversation_id}/fetch`
    );
    return response.data;
  }

  /**
   * List all calls with optional filters
   */
  async listCalls(params?: {
    status?: 'in_progress' | 'completed' | 'failed';
    driver_id?: string;
    limit?: number;
  }): Promise<Call[]> {
    const response = await axios.get(`${API_BASE_URL}/calls`, { params });
    return response.data;
  }
}

export const elevenLabsCallService = new ElevenLabsCallService();
```

---

### **Phase 2: Create Custom Hooks**

#### File: `src/hooks/useElevenLabsCalls.ts` (NEW)

```typescript
import { useState, useEffect, useCallback } from 'react';
import { elevenLabsCallService, Call } from '../services/elevenLabsCallService';

export const useElevenLabsCalls = (enabled: boolean = true, pollInterval: number = 5000) => {
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveCalls = useCallback(async () => {
    if (!enabled) return;

    try {
      setLoading(true);
      setError(null);
      const activeCalls = await elevenLabsCallService.fetchActiveCalls();
      setCalls(activeCalls);
    } catch (err: any) {
      console.error('Error fetching active calls:', err);
      setError(err.message || 'Failed to fetch active calls');
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;

    // Initial fetch
    fetchActiveCalls();

    // Set up polling
    const interval = setInterval(() => {
      fetchActiveCalls();
    }, pollInterval);

    return () => clearInterval(interval);
  }, [enabled, pollInterval, fetchActiveCalls]);

  return { calls, loading, error, refetch: fetchActiveCalls };
};
```

#### File: `src/hooks/useCallTranscript.ts` (NEW)

```typescript
import { useState, useEffect, useCallback } from 'react';
import { elevenLabsCallService, TranscriptMessage } from '../services/elevenLabsCallService';

export const useCallTranscript = (call_sid: string | null, pollInterval: number = 3000) => {
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTranscript = useCallback(async () => {
    if (!call_sid) return;

    try {
      setLoading(true);
      setError(null);
      const messages = await elevenLabsCallService.fetchTranscript(call_sid);
      setTranscript(messages);
    } catch (err: any) {
      console.error('Error fetching transcript:', err);
      setError(err.message || 'Failed to fetch transcript');
    } finally {
      setLoading(false);
    }
  }, [call_sid]);

  useEffect(() => {
    if (!call_sid) return;

    // Initial fetch
    fetchTranscript();

    // Set up polling
    const interval = setInterval(() => {
      fetchTranscript();
    }, pollInterval);

    return () => clearInterval(interval);
  }, [call_sid, pollInterval, fetchTranscript]);

  return { transcript, loading, error, refetch: fetchTranscript };
};
```

---

### **Phase 3: Update Driver_Violations.tsx**

#### Replace Fake Data with Real Data

**Current code (lines 399-540):**
```typescript
// Remove fakeCallsLiveData
```

**New code:**
```typescript
import { useElevenLabsCalls } from '../hooks/useElevenLabsCalls';
import { useCallTranscript } from '../hooks/useCallTranscript';

// Inside component
const { calls: liveCallsData, loading: callsLoading } = useElevenLabsCalls(
  activeTab === 'liveCalls', // Only poll when Live Calls tab is active
  5000 // Poll every 5 seconds
);

// For each call in the live view
{liveCallsData.map((call) => (
  <CallCard
    key={call.call_sid}
    call={call}
    transcript={/* use useCallTranscript hook */}
  />
))}
```

#### Create CallCard Component

**File:** `src/components/CallCard.tsx` (NEW)

```typescript
import React, { useState, useEffect, useRef } from 'react';
import { useCallTranscript } from '../hooks/useCallTranscript';
import { Call } from '../services/elevenLabsCallService';

interface CallCardProps {
  call: Call;
}

export const CallCard: React.FC<CallCardProps> = ({ call }) => {
  const [expanded, setExpanded] = useState(false);
  const [muted, setMuted] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Fetch real-time transcript
  const { transcript, loading } = useCallTranscript(
    call.call_sid,
    3000 // Poll every 3 seconds
  );

  // Auto-scroll to latest message
  useEffect(() => {
    if (expanded && transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [transcript, expanded]);

  return (
    <div className="call-card">
      {/* Call header */}
      <div className="call-header">
        <div>
          <h3>Driver: {call.driver_id}</h3>
          <span className={`status ${call.status}`}>{call.status}</span>
        </div>
        <div className="actions">
          <button onClick={() => setMuted(!muted)}>
            {muted ? 'Unmute' : 'Mute'}
          </button>
          <button onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Collapse' : 'Expand'}
          </button>
        </div>
      </div>

      {/* Transcript */}
      {expanded && (
        <div className="transcript">
          {transcript.map((msg) => (
            <div key={msg.sequence_number} className={`message ${msg.role}`}>
              <strong>{msg.role === 'agent' ? 'Agent' : 'Driver'}:</strong>
              <p>{msg.text}</p>
              <span className="timestamp">{new Date(msg.timestamp).toLocaleTimeString()}</span>
            </div>
          ))}
          <div ref={transcriptEndRef} />
        </div>
      )}
    </div>
  );
};
```

---

### **Phase 4: Handle Call Completion**

When a call's status changes to `completed`:

```typescript
useEffect(() => {
  liveCallsData.forEach((call) => {
    if (call.status === 'completed' && call.conversation_id) {
      // Optionally fetch summary
      elevenLabsCallService
        .fetchConversationFromElevenLabs(call.conversation_id)
        .then((data) => {
          const summary = data.conversation_data?.metadata?.analysis?.transcript_summary;
          // Display summary in modal or notification
          console.log('Call summary:', summary);
        });
    }
  });
}, [liveCallsData]);
```

---

## Summary of Changes

### ✅ **Backend (Completed)**
1. Created `/calls` service with 6 new endpoints
2. Registered router in `main.py`
3. All endpoints tested and ready

### 📋 **Frontend (To Do)**
1. Create `elevenLabsCallService.ts`
2. Create `useElevenLabsCalls` hook
3. Create `useCallTranscript` hook
4. Update `Driver_Violations.tsx` to use real data
5. Create `CallCard` component
6. Add call completion handling

---

## Testing Checklist

- [ ] Call initiation works (`POST /driver_data/call-elevenlabs`)
- [ ] Active calls appear in live view (`GET /calls/active`)
- [ ] Transcript updates in real-time (`GET /calls/{call_sid}/transcript`)
- [ ] Polling stops when switching tabs
- [ ] Completed calls show summary
- [ ] Mute/unmute works
- [ ] Expand/collapse transcript works
- [ ] Auto-scroll works

---

## Next Steps

1. **Implement frontend services and hooks** (Phase 1-2)
2. **Update Driver_Violations.tsx** (Phase 3)
3. **Test with real ElevenLabs calls** (Phase 4)
4. **Add error handling and loading states**
5. **Implement call summary modal**

---

## Questions?

All backend endpoints are ready and documented. The frontend team can now implement the real-time polling and display logic using the provided services and hooks.

**Backend Base URL:** `http://localhost:8000` (or your production URL)

**Authentication:** Add JWT token to requests if required (check existing API calls for auth pattern)
