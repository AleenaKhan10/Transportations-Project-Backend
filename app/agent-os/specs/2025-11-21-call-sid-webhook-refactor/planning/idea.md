# Raw Idea: Call SID Webhook Refactor

## User's Description

"In the implementation of above webhook and this API to create a call /call-elevenlabs/ we are creating call_sid while creating the call and ElevenLabs agent knows about that because we pass it in the variables. The agent should be able to call the webhook using that call_sid instead of conversation_id. What I want is to save the call_sid while doing the call and save conversation with webhook based on that variable."

## Context

- We have an existing call transcription webhook at POST /webhooks/elevenlabs/transcription
- We have an existing endpoint POST /driver_data/call-elevenlabs that creates calls
- Currently the system uses conversation_id as the primary identifier
- The user wants to refactor to use call_sid instead

## Key Points

1. **Current State**:
   - call_sid is generated during call creation
   - ElevenLabs agent receives call_sid in variables
   - Webhook currently uses conversation_id as primary identifier

2. **Desired State**:
   - Webhook should use call_sid instead of conversation_id
   - call_sid should be saved during call creation
   - Conversation data should be linked via call_sid

3. **Benefit**:
   - More consistent identifier across the system
   - ElevenLabs agent already has access to call_sid
   - Eliminates dependency on conversation_id
