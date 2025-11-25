/**
 * Simple WebSocket Connection Test
 *
 * This lightweight script tests WebSocket connectivity without initiating a new call.
 * Useful for:
 * - Testing WebSocket authentication
 * - Subscribing to an existing call
 * - Verifying WebSocket messages are being received
 *
 * Usage:
 * 1. For existing call: node websocket_simple_test.js CALL_SID
 * 2. For monitoring only: node websocket_simple_test.js (waits for any call)
 */

const WebSocket = require('ws');
const fetch = require('node-fetch');

// Load environment variables from .env file
require('dotenv').config();

// Configuration
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.WS_BASE_URL || 'ws://localhost:8000';

const TEST_USER = {
    username: process.env.TEST_USERNAME || 'test@example.com',
    password: process.env.TEST_PASSWORD || 'testpassword123'
};

// Get call_sid from command line argument
const CALL_SID = process.argv[2];

let authToken = null;
let ws = null;
let messageCount = 0;

// Utility
function log(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
    if (data) {
        console.log(JSON.stringify(data, null, 2));
    }
}

// Authenticate
async function authenticate() {
    log('Authenticating...');

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
            username: TEST_USER.username,
            password: TEST_USER.password
        })
    });

    if (!response.ok) {
        throw new Error(`Auth failed: ${response.status}`);
    }

    const data = await response.json();
    authToken = data.access_token;
    log('Authenticated successfully', {
        username: TEST_USER.username,
        token_length: authToken.length
    });
}

// Connect WebSocket
function connectWebSocket() {
    return new Promise((resolve, reject) => {
        log('Connecting to WebSocket...');

        const wsUrl = `${WS_BASE_URL}/ws/calls/transcriptions?token=${authToken}`;
        ws = new WebSocket(wsUrl);

        ws.on('open', () => {
            log('WebSocket connected!');

            if (CALL_SID) {
                log(`Subscribing to call: ${CALL_SID}`);
                ws.send(JSON.stringify({ subscribe: CALL_SID }));
            } else {
                log('No call_sid provided - waiting for manual subscription or messages');
            }

            resolve();
        });

        ws.on('message', (data) => {
            messageCount++;
            const message = JSON.parse(data);

            console.log('\n' + '='.repeat(60));
            log(`Message #${messageCount} - Type: ${message.type}`);

            switch (message.type) {
                case 'subscription_confirmed':
                    console.log(`Call SID: ${message.call_sid}`);
                    console.log(`Conversation ID: ${message.conversation_id}`);
                    console.log(`Status: ${message.status}`);
                    break;

                case 'transcription':
                    console.log(`Sequence: ${message.sequence_number}`);
                    console.log(`Speaker: ${message.speaker_type.toUpperCase()}`);
                    console.log(`Message: ${message.message_text}`);
                    console.log(`Timestamp: ${message.timestamp}`);
                    break;

                case 'call_status':
                    console.log(`Status: ${message.status}`);
                    console.log(`End Time: ${message.call_end_time}`);
                    break;

                case 'call_completed':
                    console.log(`Duration: ${message.call_data.duration_seconds}s`);
                    console.log(`Cost: $${message.call_data.cost}`);
                    console.log(`Successful: ${message.call_data.call_successful}`);
                    console.log(`Summary: ${message.call_data.transcript_summary}`);
                    break;

                case 'error':
                    console.log(`Error: ${message.message}`);
                    console.log(`Code: ${message.code}`);
                    break;

                default:
                    console.log('Full message:', message);
            }

            console.log('='.repeat(60));
        });

        ws.on('error', (error) => {
            log('WebSocket error!', { error: error.message });
            reject(error);
        });

        ws.on('close', (code, reason) => {
            log('WebSocket closed', { code, reason: reason.toString() });
            log(`Total messages received: ${messageCount}`);
        });
    });
}

// Main
async function main() {
    console.log('\n' + '='.repeat(60));
    console.log('  Simple WebSocket Connection Test');
    console.log('='.repeat(60));

    if (CALL_SID) {
        console.log(`Testing with call_sid: ${CALL_SID}`);
    } else {
        console.log('No call_sid provided - will listen for all messages');
        console.log('Usage: node websocket_simple_test.js CALL_SID');
    }

    console.log('='.repeat(60) + '\n');

    try {
        await authenticate();
        await connectWebSocket();

        log('WebSocket connection active. Press Ctrl+C to exit.');

        // Keep process alive
        process.stdin.resume();

    } catch (error) {
        console.error('Test failed:', error.message);
        process.exit(1);
    }
}

// Graceful shutdown
process.on('SIGINT', () => {
    log('Shutting down...');
    if (ws && ws.readyState === WebSocket.OPEN) {
        if (CALL_SID) {
            ws.send(JSON.stringify({ unsubscribe: CALL_SID }));
        }
        ws.close();
    }
    setTimeout(() => process.exit(0), 500);
});

main();
