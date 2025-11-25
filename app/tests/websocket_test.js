/**
 * WebSocket Real-Time Transcription Test
 *
 * This script tests the complete ElevenLabs integration:
 * 1. Authenticates and obtains JWT token
 * 2. Initiates a driver call via ElevenLabs
 * 3. Connects to WebSocket for real-time updates
 * 4. Receives real-time transcriptions as they occur
 * 5. Fetches complete conversation history
 * 6. Compares real-time vs fetched data
 *
 * Requirements:
 * - npm install ws node-fetch
 * - Backend server running on localhost:8000 (or configure API_BASE_URL)
 * - Valid user credentials in .env or hardcoded
 * - ElevenLabs API credentials configured in backend
 */

const WebSocket = require('ws');
const fetch = require('node-fetch');

// Load environment variables from .env file
require('dotenv').config();

// ============================================================================
// Configuration
// ============================================================================

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.WS_BASE_URL || 'ws://localhost:8000';

// Test credentials (replace with your actual test user)
const TEST_USER = {
    username: process.env.TEST_USERNAME || 'test@example.com',
    password: process.env.TEST_PASSWORD || 'testpassword123'
};

// Test driver data (using real driver from production database)
const TEST_DRIVER = {
    driverId: 'DRV_1753320481164',
    driverName: 'Alina Khan',
    phoneNumber: '+12192002824', // Normalized from (219)200-2824
    customRules: 'This is a test call - be brief and polite',
    violations: {
        tripId: 'TEST_TRIP_001',
        violationDetails: [
            {
                type: 'violation',
                description: 'Temperature is at 45 degrees but needs to be 38 degrees'
            },
            {
                type: 'reminder',
                description: 'Please send loaded trailer pictures'
            }
        ]
    }
};

// ============================================================================
// Global State
// ============================================================================

let authToken = null;
let callSid = null;
let conversationId = null;
let ws = null;
let receivedTranscriptions = [];
let fetchedTranscriptions = [];
let callCompleted = false;

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Pretty print log messages with timestamps
 */
function log(section, message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`\n[$[timestamp}] [${section}] ${message}`);
    if (data) {
        console.log(JSON.stringify(data, null, 2));
    }
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================================
// Step 1: Authentication
// ============================================================================

async function authenticate() {
    log('AUTH', 'Authenticating user...');

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                username: TEST_USER.username,
                password: TEST_USER.password
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Authentication failed: ${response.status} - ${error}`);
        }

        const data = await response.json();
        authToken = data.access_token;

        log('AUTH', 'Authentication successful!', {
            username: TEST_USER.username,
            token_prefix: authToken.substring(0, 20) + '...'
        });

        return authToken;
    } catch (error) {
        log('AUTH', 'Authentication failed!', { error: error.message });
        throw error;
    }
}

// ============================================================================
// Step 2: Initiate Call
// ============================================================================

async function initiateCall() {
    log('CALL', 'Initiating ElevenLabs call...');

    try {
        const response = await fetch(`${API_BASE_URL}/driver_data/call-elevenlabs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                callType: 'violation',
                timestamp: new Date().toISOString(),
                drivers: [TEST_DRIVER]
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Call initiation failed: ${response.status} - ${JSON.stringify(error)}`);
        }

        const data = await response.json();
        callSid = data.call_sid;
        conversationId = data.conversation_id;

        log('CALL', 'Call initiated successfully!', {
            call_sid: callSid,
            conversation_id: conversationId,
            driver: data.driver,
            triggers_count: data.triggers_count
        });

        return data;
    } catch (error) {
        log('CALL', 'Call initiation failed!', { error: error.message });
        throw error;
    }
}

// ============================================================================
// Step 3: WebSocket Connection & Subscription
// ============================================================================

async function connectWebSocket() {
    log('WS', 'Connecting to WebSocket...');

    return new Promise((resolve, reject) => {
        try {
            const wsUrl = `${WS_BASE_URL}/ws/calls/transcriptions?token=${authToken}`;
            ws = new WebSocket(wsUrl);

            ws.on('open', () => {
                log('WS', 'WebSocket connected successfully!');

                // Subscribe to the call
                log('WS', `Subscribing to call: ${callSid}`);
                ws.send(JSON.stringify({ subscribe: callSid }));
            });

            ws.on('message', (data) => {
                handleWebSocketMessage(data);
            });

            ws.on('error', (error) => {
                log('WS', 'WebSocket error!', { error: error.message });
                reject(error);
            });

            ws.on('close', (code, reason) => {
                log('WS', 'WebSocket closed', { code, reason: reason.toString() });
            });

            // Resolve after connection is established
            ws.once('open', resolve);

        } catch (error) {
            log('WS', 'WebSocket connection failed!', { error: error.message });
            reject(error);
        }
    });
}

// ============================================================================
// Step 4: Handle WebSocket Messages
// ============================================================================

function handleWebSocketMessage(data) {
    try {
        const message = JSON.parse(data);

        switch (message.type) {
            case 'subscription_confirmed':
                log('WS_MSG', 'Subscription confirmed!', {
                    call_sid: message.call_sid,
                    conversation_id: message.conversation_id,
                    status: message.status
                });
                break;

            case 'transcription':
                log('WS_MSG', `New transcription [${message.speaker_type}]`, {
                    sequence: message.sequence_number,
                    message: message.message_text,
                    timestamp: message.timestamp
                });

                // Store received transcription
                receivedTranscriptions.push({
                    id: message.transcription_id,
                    sequence: message.sequence_number,
                    speaker: message.speaker_type,
                    text: message.message_text,
                    timestamp: message.timestamp
                });

                // Display in readable format
                console.log(`   [${message.sequence_number}] ${message.speaker_type.toUpperCase()}: ${message.message_text}`);
                break;

            case 'call_status':
                log('WS_MSG', 'Call status update!', {
                    status: message.status,
                    call_end_time: message.call_end_time
                });
                break;

            case 'call_completed':
                log('WS_MSG', 'Call completed with full data!', {
                    duration: message.call_data.duration_seconds,
                    cost: message.call_data.cost,
                    successful: message.call_data.call_successful,
                    summary: message.call_data.transcript_summary
                });
                callCompleted = true;

                // Trigger conversation fetch after brief delay
                setTimeout(() => fetchConversation(), 2000);
                break;

            case 'unsubscribe_confirmed':
                log('WS_MSG', 'Unsubscribe confirmed!', {
                    identifier: message.identifier
                });
                break;

            case 'error':
                log('WS_MSG', 'Error received!', {
                    message: message.message,
                    code: message.code
                });
                break;

            default:
                log('WS_MSG', 'Unknown message type', message);
        }
    } catch (error) {
        log('WS_MSG', 'Failed to parse message', { error: error.message, data: data.toString() });
    }
}

// ============================================================================
// Step 5: Fetch Conversation History
// ============================================================================

async function fetchConversation() {
    log('FETCH', 'Fetching complete conversation history...');

    try {
        const response = await fetch(
            `${API_BASE_URL}/driver_data/conversations/${conversationId}/fetch`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Fetch failed: ${response.status} - ${JSON.stringify(error)}`);
        }

        const data = await response.json();

        log('FETCH', 'Conversation fetched successfully!', {
            call_sid: data.call_sid,
            conversation_id: data.conversation_id,
            call_status: data.call_status,
            call_duration: data.call_duration,
            transcriptions_added: data.transcriptions_added,
            transcriptions_total: data.transcriptions_total
        });

        // Store fetched transcriptions
        if (data.conversation_data && data.conversation_data.transcript) {
            fetchedTranscriptions = data.conversation_data.transcript.map((turn, index) => ({
                sequence: index,
                speaker: turn.role === 'agent' ? 'agent' : 'driver',
                text: turn.message,
                time_in_call: turn.time_in_call_secs
            }));

            log('FETCH', 'Transcript turns:', {
                count: fetchedTranscriptions.length,
                turns: fetchedTranscriptions
            });
        }

        // Compare real-time vs fetched
        compareResults();

        return data;
    } catch (error) {
        log('FETCH', 'Conversation fetch failed!', { error: error.message });
        throw error;
    }
}

// ============================================================================
// Step 6: Compare Results
// ============================================================================

function compareResults() {
    log('COMPARE', 'Comparing real-time vs fetched transcriptions...');

    console.log('\n=== REAL-TIME TRANSCRIPTIONS (WebSocket) ===');
    console.log(`Total received: ${receivedTranscriptions.length}`);
    receivedTranscriptions.forEach(t => {
        console.log(`  [${t.sequence}] ${t.speaker}: ${t.text}`);
    });

    console.log('\n=== FETCHED TRANSCRIPTIONS (REST API) ===');
    console.log(`Total fetched: ${fetchedTranscriptions.length}`);
    fetchedTranscriptions.forEach(t => {
        console.log(`  [${t.sequence}] ${t.speaker}: ${t.text}`);
    });

    // Verify counts match
    if (receivedTranscriptions.length === fetchedTranscriptions.length) {
        log('COMPARE', 'SUCCESS: Counts match!', {
            real_time_count: receivedTranscriptions.length,
            fetched_count: fetchedTranscriptions.length
        });
    } else {
        log('COMPARE', 'WARNING: Counts do not match!', {
            real_time_count: receivedTranscriptions.length,
            fetched_count: fetchedTranscriptions.length,
            difference: Math.abs(receivedTranscriptions.length - fetchedTranscriptions.length)
        });
    }

    // Compare content
    let matchingMessages = 0;
    for (let i = 0; i < Math.min(receivedTranscriptions.length, fetchedTranscriptions.length); i++) {
        const rtMsg = receivedTranscriptions[i];
        const fetchedMsg = fetchedTranscriptions[i];

        if (rtMsg.speaker === fetchedMsg.speaker && rtMsg.text === fetchedMsg.text) {
            matchingMessages++;
        } else {
            log('COMPARE', `Mismatch at sequence ${i}`, {
                real_time: { speaker: rtMsg.speaker, text: rtMsg.text },
                fetched: { speaker: fetchedMsg.speaker, text: fetchedMsg.text }
            });
        }
    }

    log('COMPARE', 'Content comparison complete!', {
        total_compared: Math.min(receivedTranscriptions.length, fetchedTranscriptions.length),
        matching: matchingMessages,
        accuracy: `${(matchingMessages / Math.min(receivedTranscriptions.length, fetchedTranscriptions.length) * 100).toFixed(2)}%`
    });
}

// ============================================================================
// Main Test Flow
// ============================================================================

async function runTest() {
    console.log('\n' + '='.repeat(80));
    console.log('  WebSocket Real-Time Transcription Test');
    console.log('='.repeat(80));

    try {
        // Step 1: Authenticate
        await authenticate();

        // Step 2: Initiate Call
        await initiateCall();

        // Step 3: Connect WebSocket
        await connectWebSocket();

        log('TEST', 'Test setup complete! Waiting for call to complete...');
        log('TEST', 'The call is now in progress. You will see real-time transcriptions below.');
        log('TEST', 'This may take several minutes depending on call duration.');

        // Wait for call to complete (or timeout after 10 minutes)
        const timeout = 10 * 60 * 1000; // 10 minutes
        const startTime = Date.now();

        while (!callCompleted && (Date.now() - startTime) < timeout) {
            await sleep(1000);
        }

        if (!callCompleted) {
            log('TEST', 'WARNING: Call did not complete within timeout period');
            log('TEST', 'Manually fetching conversation...');
            await fetchConversation();
        }

        // Wait a bit for comparison to complete
        await sleep(3000);

        // Final summary
        console.log('\n' + '='.repeat(80));
        console.log('  TEST SUMMARY');
        console.log('='.repeat(80));
        console.log(`Call SID: ${callSid}`);
        console.log(`Conversation ID: ${conversationId}`);
        console.log(`Real-time transcriptions received: ${receivedTranscriptions.length}`);
        console.log(`Fetched transcriptions: ${fetchedTranscriptions.length}`);
        console.log(`Call completed: ${callCompleted ? 'YES' : 'NO'}`);
        console.log('='.repeat(80));

        // Cleanup
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ unsubscribe: callSid }));
            ws.close();
        }

        log('TEST', 'Test completed successfully!');
        process.exit(0);

    } catch (error) {
        log('TEST', 'Test failed!', {
            error: error.message,
            stack: error.stack
        });

        // Cleanup on error
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
        }

        process.exit(1);
    }
}

// ============================================================================
// Run Test
// ============================================================================

// Handle graceful shutdown
process.on('SIGINT', () => {
    log('TEST', 'Received SIGINT, shutting down...');
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }
    process.exit(0);
});

// Run the test
runTest().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
});
