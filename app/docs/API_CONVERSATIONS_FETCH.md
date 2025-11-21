# ElevenLabs Conversation Fetch API

## Endpoint Overview

**POST** `/driver_data/conversations/{conversation_id}/fetch`

Fetch complete conversation data from ElevenLabs API and update the database with call metadata and transcriptions.

---

## Purpose

This endpoint is used to:
- Retrieve complete conversation details from ElevenLabs API
- Update Call record with metadata (status, duration, timestamps)
- Store conversation transcript in CallTranscription table
- Useful for manual data retrieval, debugging, or backfilling missing data

---

## Authentication

This endpoint requires authentication. Include your auth token in the request headers:

```
Authorization: Bearer <your_token_here>
```

---

## URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `conversation_id` | string | Yes | ElevenLabs conversation identifier (format: `conv_xxxxx`) |

---

## Request

### Method
`POST`

### URL Structure
```
POST /driver_data/conversations/{conversation_id}/fetch
```

### Example Request
```bash
curl -X POST "https://your-api-domain.com/driver_data/conversations/conv_1901kaj4pr1penza6bbkscg6hgkc/fetch" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json"
```

### Request Body
**No request body required.** This endpoint only uses the `conversation_id` from the URL path.

---

## Response

### Success Response (200 OK)

```json
{
  "message": "Conversation data fetched and stored successfully",
  "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
  "call_sid": "EL_DRV_1753320481164_2025-11-21T02:12:51.469Z",
  "call_updated": true,
  "call_status": "COMPLETED",
  "call_duration": 234,
  "transcriptions_added": 25,
  "transcriptions_total": 25,
  "conversation_data": {
    "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
    "conversation_id": "conv_1901kaj4pr1penza6bbkscg6hgkc",
    "status": "done",
    "user_id": null,
    "branch_id": null,
    "transcript": [
      {
        "role": "user",
        "agent_metadata": null,
        "message": "Hello?",
        "multivoice_message": null,
        "tool_calls": [],
        "tool_results": [],
        "feedback": null,
        "llm_override": null,
        "time_in_call_secs": 9,
        "conversation_turn_metrics": {
          "metrics": {
            "convai_asr_trailing_service_latency": {
              "elapsed_time": 0.025111063998338068
            }
          }
        },
        "rag_retrieval_info": null,
        "llm_usage": null,
        "interrupted": false,
        "original_message": null,
        "source_medium": "audio"
      },
      {
        "role": "agent",
        "agent_metadata": {
          "agent_id": "agent_5501k9czkv3qepy815bm59nt04qk",
          "branch_id": null,
          "workflow_node_id": null
        },
        "message": "Hello? How can I help you today?",
        "multivoice_message": null,
        "tool_calls": [],
        "tool_results": [],
        "feedback": null,
        "llm_override": null,
        "time_in_call_secs": 11,
        "conversation_turn_metrics": {
          "metrics": {
            "convai_llm_service_ttf_sentence": {
              "elapsed_time": 0.11392616599914618
            },
            "convai_llm_service_ttfb": {
              "elapsed_time": 0.10164229799920577
            },
            "convai_llm_service_tt_last_sentence": {
              "elapsed_time": 0.113907871000265
            },
            "convai_tts_service_ttfb": {
              "elapsed_time": 0.3959559530012484
            }
          }
        },
        "rag_retrieval_info": null,
        "llm_usage": {
          "model_usage": {
            "glm-45-air-fp8": {
              "input": {
                "tokens": 10390,
                "price": 0.0091432
              },
              "input_cache_read": {
                "tokens": 0,
                "price": 0
              },
              "input_cache_write": {
                "tokens": 0,
                "price": 0
              },
              "output_total": {
                "tokens": 65,
                "price": 0.0008449999999999999
              }
            }
          }
        },
        "interrupted": false,
        "original_message": null,
        "source_medium": null
      }
    ],
    "metadata": {
      "start_time_unix_secs": 1763692996,
      "accepted_time_unix_secs": 1763692996,
      "call_duration_secs": 234,
      "cost": 2925,
      "deletion_settings": {
        "deletion_time_unix_secs": null,
        "deleted_logs_at_time_unix_secs": null,
        "deleted_audio_at_time_unix_secs": null,
        "deleted_transcript_at_time_unix_secs": null,
        "delete_transcript_and_pii": false,
        "delete_audio": false
      },
      "feedback": {
        "type": null,
        "overall_score": null,
        "likes": 0,
        "dislikes": 0,
        "rating": null,
        "comment": null
      },
      "phone_call": {
        "direction": "outbound",
        "phone_number_id": "phnum_8401k9ndc950ewza733y8thmpbrx",
        "agent_number": "+12196541187",
        "external_number": "+12192002824",
        "type": "twilio",
        "stream_sid": "MZ296b22cbf5fe6b1cb2d9e0fe86409818",
        "call_sid": "CA4746caaf456d7c2db1574b7d1f211f6a"
      },
      "termination_reason": "Call ended by remote party",
      "error": null,
      "warnings": [],
      "main_language": "en"
    },
    "analysis": {
      "evaluation_criteria_results": {},
      "data_collection_results": {},
      "call_successful": "success",
      "transcript_summary": "Summary of the conversation...",
      "call_summary_title": "Call Title"
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Success message |
| `conversation_id` | string | ElevenLabs conversation identifier |
| `call_sid` | string | Our internal call tracking ID |
| `call_updated` | boolean | Whether the Call record was successfully updated |
| `call_status` | string | Updated call status (`COMPLETED`, `FAILED`, etc.) |
| `call_duration` | integer | Call duration in seconds |
| `transcriptions_added` | integer | Number of new transcriptions added to database |
| `transcriptions_total` | integer | Total transcriptions for this conversation |
| `conversation_data` | object | Complete conversation data from ElevenLabs (see structure below) |

---

## Conversation Data Structure

The `conversation_data` object contains the complete conversation details from ElevenLabs:

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | ElevenLabs agent identifier |
| `conversation_id` | string | ElevenLabs conversation identifier |
| `status` | string | Conversation status (`done`, `in_progress`, etc.) |
| `user_id` | string \| null | Associated user ID (if any) |
| `branch_id` | string \| null | Branch identifier (if using workflows) |
| `transcript` | array | Array of conversation turns (see below) |
| `metadata` | object | Call metadata including timing, cost, phone details |
| `analysis` | object | AI-generated call analysis and summary |
| `conversation_initiation_client_data` | object | Initial configuration and dynamic variables |

### Transcript Array

Each item in the `transcript` array represents a turn in the conversation:

```typescript
interface TranscriptTurn {
  role: "user" | "agent";
  agent_metadata: {
    agent_id: string;
    branch_id: string | null;
    workflow_node_id: string | null;
  } | null;
  message: string;
  multivoice_message: any | null;
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
  feedback: any | null;
  llm_override: any | null;
  time_in_call_secs: number;
  conversation_turn_metrics: {
    metrics: {
      [key: string]: {
        elapsed_time: number;
      };
    };
  } | null;
  rag_retrieval_info: any | null;
  llm_usage: {
    model_usage: {
      [modelName: string]: {
        input: { tokens: number; price: number };
        input_cache_read: { tokens: number; price: number };
        input_cache_write: { tokens: number; price: number };
        output_total: { tokens: number; price: number };
      };
    };
  } | null;
  interrupted: boolean;
  original_message: string | null;
  source_medium: "audio" | null;
}
```

### Metadata Object

```typescript
interface Metadata {
  start_time_unix_secs: number;
  accepted_time_unix_secs: number;
  call_duration_secs: number;
  cost: number;
  deletion_settings: {
    deletion_time_unix_secs: number | null;
    deleted_logs_at_time_unix_secs: number | null;
    deleted_audio_at_time_unix_secs: number | null;
    deleted_transcript_at_time_unix_secs: number | null;
    delete_transcript_and_pii: boolean;
    delete_audio: boolean;
  };
  feedback: {
    type: string | null;
    overall_score: number | null;
    likes: number;
    dislikes: number;
    rating: number | null;
    comment: string | null;
  };
  phone_call: {
    direction: "outbound" | "inbound";
    phone_number_id: string;
    agent_number: string;
    external_number: string;
    type: "twilio";
    stream_sid: string;
    call_sid: string;
  };
  termination_reason: string;
  error: string | null;
  warnings: string[];
  main_language: string;
}
```

### Analysis Object

```typescript
interface Analysis {
  evaluation_criteria_results: Record<string, any>;
  data_collection_results: Record<string, any>;
  call_successful: "success" | "failure" | string;
  transcript_summary: string;
  call_summary_title: string;
}
```

---

## Error Responses

### 404 Not Found - Conversation Not Found

```json
{
  "detail": "Conversation conv_xxxxx not found in ElevenLabs"
}
```

### 404 Not Found - Call Record Not Found

```json
{
  "detail": "Call record not found for conversation conv_xxxxx"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to fetch conversation data: <error message>"
}
```

---

## Usage Notes

1. **Idempotent Operation**: The endpoint checks for existing transcriptions and skips storage if transcriptions already exist for this conversation_id, preventing duplicates.

2. **Automatic Status Update**: The endpoint automatically updates the Call status in the database based on the `call_successful` field from ElevenLabs analysis:
   - `"success"` -> `COMPLETED`
   - Other values -> `FAILED`

3. **Timestamp Calculation**: Message timestamps are calculated by adding `time_in_call_secs` to the call start time from metadata.

4. **Speaker Type Mapping**:
   - `role: "agent"` -> `SpeakerType.AGENT`
   - `role: "user"` -> `SpeakerType.DRIVER`

5. **Sequence Numbers**: Transcriptions are stored with sequence numbers (1-indexed) to maintain conversation order.

---

## Example Frontend Integration

### Using Fetch API

```javascript
async function fetchConversation(conversationId, authToken) {
  try {
    const response = await fetch(
      `https://your-api-domain.com/driver_data/conversations/${conversationId}/fetch`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('Conversation fetched:', data);
    return data;
  } catch (error) {
    console.error('Error fetching conversation:', error);
    throw error;
  }
}

// Usage
const conversationId = 'conv_1901kaj4pr1penza6bbkscg6hgkc';
const authToken = 'your_auth_token';
fetchConversation(conversationId, authToken)
  .then(data => {
    console.log('Call duration:', data.call_duration);
    console.log('Transcriptions added:', data.transcriptions_added);
    console.log('Full transcript:', data.conversation_data.transcript);
  });
```

### Using Axios

```javascript
import axios from 'axios';

async function fetchConversation(conversationId, authToken) {
  try {
    const response = await axios.post(
      `https://your-api-domain.com/driver_data/conversations/${conversationId}/fetch`,
      {},
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );

    return response.data;
  } catch (error) {
    console.error('Error fetching conversation:', error.response?.data || error.message);
    throw error;
  }
}
```

### React Hook Example

```typescript
import { useState } from 'react';

interface ConversationFetchResponse {
  message: string;
  conversation_id: string;
  call_sid: string;
  call_updated: boolean;
  call_status: string;
  call_duration: number;
  transcriptions_added: number;
  transcriptions_total: number;
  conversation_data: any;
}

export function useFetchConversation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ConversationFetchResponse | null>(null);

  const fetchConversation = async (conversationId: string, authToken: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `https://your-api-domain.com/driver_data/conversations/${conversationId}/fetch`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch conversation');
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { fetchConversation, loading, error, data };
}
```

---

## Common Use Cases

### 1. Manual Data Retrieval
Fetch conversation data after a call completes to display in the UI:

```javascript
// After call completes, fetch full conversation
const callData = await fetchConversation(conversationId, token);
displayTranscript(callData.conversation_data.transcript);
```

### 2. Debugging Failed Calls
Retrieve conversation data to debug why a call failed:

```javascript
const result = await fetchConversation(conversationId, token);
if (result.call_status === 'FAILED') {
  console.log('Failure reason:', result.conversation_data.metadata.termination_reason);
  console.log('Errors:', result.conversation_data.metadata.error);
}
```

### 3. Backfilling Missing Data
If transcriptions are missing from the database, use this endpoint to retrieve and store them:

```javascript
const result = await fetchConversation(conversationId, token);
console.log(`Added ${result.transcriptions_added} missing transcriptions`);
```

### 4. Call Analysis Display
Display AI-generated call analysis to users:

```javascript
const result = await fetchConversation(conversationId, token);
const analysis = result.conversation_data.analysis;
console.log('Call summary:', analysis.transcript_summary);
console.log('Call successful:', analysis.call_successful);
```

---

## Related Endpoints

- **POST /driver_data/call-elevenlabs** - Initiate a new ElevenLabs call
- **POST /webhooks/elevenlabs/transcription** - Webhook for receiving real-time transcriptions
- **GET /driver_data/{driver_id}** - Get driver information

---

## Notes for Frontend Developers

1. **No Payload Required**: This is a POST endpoint but requires no request body. Only the conversation_id in the URL is needed.

2. **Large Response**: The `conversation_data` object can be quite large (10KB - 100KB+), especially for long conversations. Consider implementing pagination or lazy loading for the transcript display.

3. **Duplicate Protection**: The endpoint automatically prevents duplicate transcriptions. If you call it multiple times with the same conversation_id, `transcriptions_added` will be 0 on subsequent calls.

4. **Timestamps**: All timestamps in the response are in UTC. Convert to local timezone in your frontend as needed.

5. **Tool Calls**: The transcript may include `tool_calls` and `tool_results` arrays. These represent automated actions the AI agent performed during the call (e.g., webhook calls).

6. **Interrupted Messages**: Some agent messages have `interrupted: true` and an `original_message` field. This indicates the driver interrupted the agent mid-sentence.

7. **LLM Metrics**: Each agent turn includes detailed `llm_usage` metrics for cost tracking and `conversation_turn_metrics` for performance monitoring.

---

## Testing

### Test with cURL

```bash
# Test successful fetch
curl -X POST "http://localhost:8000/driver_data/conversations/conv_1901kaj4pr1penza6bbkscg6hgkc/fetch" \
  -H "Authorization: Bearer your_token_here"

# Test with invalid conversation_id
curl -X POST "http://localhost:8000/driver_data/conversations/conv_invalid/fetch" \
  -H "Authorization: Bearer your_token_here"
```

### Expected Test Scenarios

| Scenario | Expected Outcome |
|----------|-----------------|
| Valid conversation_id, first fetch | 200 OK, transcriptions_added > 0 |
| Valid conversation_id, second fetch | 200 OK, transcriptions_added = 0 |
| Invalid conversation_id | 404 Not Found |
| Conversation exists but no Call record | 404 Not Found |
| Network error with ElevenLabs | 500 Internal Server Error |

---

## Support

For questions or issues with this API endpoint, contact the backend development team or refer to:
- [CLAUDE.md](../CLAUDE.md) - Project architecture overview
- [ElevenLabs API Documentation](https://elevenlabs.io/docs) - ElevenLabs API reference
- [Call Model](../models/call.py) - Call database model
- [CallTranscription Model](../models/call_transcription.py) - Transcription database model
