# Deployment Summary: ElevenLabs Completion Webhook and WebSocket Integration

**Deployment Date:** Ready for deployment
**Feature Branch:** `feature/elevenlabs-completion-webhook-websocket`
**Target Environment:** Staging -> Production
**Migration Required:** Yes (Migration 006)

---

## Executive Summary

This deployment completes the ElevenLabs conversational AI integration by adding:

1. **Post-Call Completion Webhook** - Receives call completion data from ElevenLabs and stores metadata (summary, cost, duration, analysis)
2. **Real-Time WebSocket System** - Enables live streaming of transcriptions and call completion events to frontend clients

**Key Benefits:**
- Real-time call monitoring for dispatchers
- Complete call metadata tracking (cost, duration, success indicators)
- No more polling - push-based updates via WebSocket
- Enhanced user experience with instant transcription display

**Testing Status:**
- 32 tests written and passing
- All feature-specific tests passing (100% success rate)
- Integration tests cover end-to-end workflows
- Ready for staging deployment

---

## Files Changed/Created

### Modified Files

1. **models/call.py**
   - Added 6 new post-call metadata fields (all nullable)
   - Added `update_post_call_data()` class method
   - Changes: Lines 63-71 (new fields), Lines 292-350 (new method)

2. **services/webhooks_elevenlabs.py**
   - Added post-call webhook endpoint: `POST /webhooks/elevenlabs/post-call`
   - Added 5 new Pydantic models for webhook payloads
   - Integrated WebSocket broadcasting in transcription webhook (now async)
   - Integrated WebSocket broadcasting in post-call webhook
   - Changes: ~400 lines added (models, endpoint, integration)

3. **main.py**
   - Registered websocket_calls_router
   - Changes: Lines 45-46 (import and registration)

4. **run_migrations.py**
   - Added migration_006 to migration sequence
   - Changes: Added migration import and execution call

5. **CLAUDE.md**
   - Updated ElevenLabs Call Workflow section with new features
   - Documented post-call webhook and WebSocket endpoints
   - Changes: Lines 75-150 (expanded documentation)

### New Files Created

#### Core Implementation

1. **migrations/006_add_post_call_metadata.py**
   - Database migration to add 6 new columns to calls table
   - All columns nullable for backward compatibility
   - Includes upgrade() and downgrade() methods
   - Size: 171 lines

2. **services/websocket_manager.py**
   - WebSocketConnectionManager class for connection management
   - In-memory subscription tracking
   - Broadcast methods for transcriptions and completions
   - Size: 350+ lines

3. **services/websocket_calls.py**
   - WebSocket endpoint: `/ws/calls/transcriptions`
   - JWT authentication via query parameter
   - Subscription/unsubscribe message handling
   - Size: 250+ lines

4. **models/websocket_messages.py**
   - 8 Pydantic models for WebSocket messages
   - Client-to-server: SubscribeMessage, UnsubscribeMessage
   - Server-to-client: 6 message types
   - Size: 180+ lines

#### Tests

5. **tests/models/test_call_post_data.py**
   - 4 tests for Call.update_post_call_data() method
   - Tests: happy path, not found, partial data, status update

6. **tests/services/test_webhooks_post_call.py**
   - 6 tests for post-call webhook endpoint
   - Tests: valid payloads, errors (400/404/500), timestamp conversion

7. **tests/services/test_websocket_manager.py**
   - 6 tests for WebSocketConnectionManager
   - Tests: connect, disconnect, subscribe, broadcast

8. **tests/models/test_websocket_messages.py**
   - 3 tests for WebSocket message models
   - Tests: parsing, serialization, validation

9. **tests/services/test_websocket_endpoint.py**
   - 5 tests for WebSocket endpoint
   - Tests: authentication, subscribe/unsubscribe, error handling

10. **tests/integration/test_transcription_broadcast.py**
    - 3 tests for transcription webhook -> WebSocket broadcast
    - Tests: happy path, no subscribers, broadcast failures

11. **tests/integration/test_completion_broadcast.py**
    - 4 tests for post-call webhook -> WebSocket broadcast
    - Tests: happy path, two-message sequence, no subscribers

#### Documentation

12. **agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/deployment/deployment-checklist.md**
    - Comprehensive deployment checklist
    - Pre-deployment, deployment, verification, rollback procedures
    - Size: 477 lines

13. **agent-os/specs/2025-11-21-elevenlabs-completion-webhook-websocket/deployment/api-documentation.md**
    - Frontend API documentation
    - WebSocket protocol, message types, examples
    - Size: 500+ lines

---

## Database Schema Changes

### Migration 006: Add Post-Call Metadata Fields

**Migration File:** `migrations/006_add_post_call_metadata.py`

**Changes to `dev.calls` table:**

| Column Name            | Type             | Nullable | Description                                           |
|------------------------|------------------|----------|-------------------------------------------------------|
| transcript_summary     | TEXT             | Yes      | Summary of call conversation from ElevenLabs analysis |
| call_duration_seconds  | INTEGER          | Yes      | Duration of call in seconds from metadata             |
| cost                   | DOUBLE PRECISION | Yes      | Cost of call in dollars from ElevenLabs billing       |
| call_successful        | BOOLEAN          | Yes      | Boolean flag indicating if call was successful        |
| analysis_data          | TEXT             | Yes      | JSON string of full analysis results                  |
| metadata_json          | TEXT             | Yes      | JSON string of full metadata from webhook             |

**Backward Compatibility:**
- All columns nullable - existing records unaffected
- No data backfill required
- Application continues to work during migration
- Rollback safe - columns can be dropped without data loss

**Migration Commands:**

**Staging:**
```bash
cd c:/Users/CodingCops/Desktop/Projects/learning/agy-backend/app
source .venv/Scripts/activate
python run_migrations.py
```

**Production:**
```bash
cd /path/to/app
source .venv/bin/activate  # Linux/production
python run_migrations.py
```

**Verification:**
```sql
-- Check columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'dev'
AND table_name = 'calls'
AND column_name IN (
    'transcript_summary',
    'call_duration_seconds',
    'cost',
    'call_successful',
    'analysis_data',
    'metadata_json'
);

-- Verify existing records have NULL values
SELECT COUNT(*) as total_calls,
       COUNT(transcript_summary) as with_summary
FROM dev.calls;
```

**Rollback (if needed):**
```sql
ALTER TABLE dev.calls
DROP COLUMN IF EXISTS transcript_summary,
DROP COLUMN IF EXISTS call_duration_seconds,
DROP COLUMN IF EXISTS cost,
DROP COLUMN IF EXISTS call_successful,
DROP COLUMN IF EXISTS analysis_data,
DROP COLUMN IF EXISTS metadata_json;
```

---

## Deployment Steps

### Step 1: Staging Deployment

#### 1.1 Database Migration (Staging)

```bash
# Connect to staging server
ssh user@staging-server

# Navigate to application directory
cd /path/to/app

# Activate virtual environment
source .venv/bin/activate

# Run migration
python run_migrations.py

# Verify migration success
# Check logs for "Migration 006: Completed successfully"
```

**Verification:**
```bash
# Check database columns
psql -d your_database -c "
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'dev' AND table_name = 'calls'
AND column_name LIKE '%call_%' OR column_name LIKE '%transcript_%'
OR column_name LIKE '%analysis_%' OR column_name LIKE '%metadata_%'
OR column_name LIKE '%cost%';
"
```

#### 1.2 Code Deployment (Staging)

```bash
# Pull latest code
git fetch origin
git checkout feature/elevenlabs-completion-webhook-websocket
git pull origin feature/elevenlabs-completion-webhook-websocket

# Install any new dependencies (if applicable)
pip install -r requirements.txt

# Restart application
# Method depends on your deployment setup:
# Option 1: systemd
sudo systemctl restart agy-backend

# Option 2: Docker
docker-compose restart app

# Option 3: Cloud Run (automatic on deploy)
gcloud run deploy agy-backend --source .

# Verify application started
curl https://staging-domain/health
# Or check application logs
tail -f /var/log/agy-backend/app.log
```

#### 1.3 Configure ElevenLabs Webhook (Staging)

1. Log in to ElevenLabs dashboard: https://elevenlabs.io/app/conversational-ai
2. Navigate to your agent configuration
3. Go to Webhooks section
4. Add new webhook:
   - **Name:** Post-Call Completion (Staging)
   - **URL:** `https://staging-domain/webhooks/elevenlabs/post-call`
   - **Event Type:** `post_call_transcription`, `call_initiation_failure`
   - **Enabled:** Yes
5. Save configuration
6. Note: Existing transcription webhook should already be configured

#### 1.4 Smoke Test (Staging)

**Test 1: Post-Call Webhook**
```bash
# Initiate a test call via your staging application
curl -X POST https://staging-domain/driver_data/call-elevenlabs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "driver_ids": ["test_driver_123"],
    "violation_types": ["speeding"]
  }'

# Wait for call to complete (2-5 minutes)

# Check logs for webhook receipt
tail -f /var/log/agy-backend/app.log | grep "post-call"

# Verify Call record updated
psql -d your_database -c "
SELECT call_sid, conversation_id, status, transcript_summary, cost, call_successful
FROM dev.calls
WHERE call_sid LIKE 'EL_test_driver_123%'
ORDER BY created_at DESC LIMIT 1;
"
```

**Test 2: WebSocket Connection**
```javascript
// Use browser console or Node.js script
const token = "YOUR_JWT_TOKEN";
const ws = new WebSocket(`wss://staging-domain/ws/calls/transcriptions?token=${token}`);

ws.onopen = () => {
    console.log("Connected!");
    // Subscribe to a call
    ws.send(JSON.stringify({subscribe: "EL_test_driver_123_1732199700"}));
};

ws.onmessage = (event) => {
    console.log("Message received:", JSON.parse(event.data));
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};
```

**Test 3: Real-Time Transcription**
```bash
# Start WebSocket connection (from browser or script above)
# Initiate a test call
# Watch WebSocket messages arrive in real-time as call progresses
# Verify transcription messages appear
# Verify call_status and call_completed messages appear when call ends
```

**Expected Results:**
- Migration completes without errors
- Application starts successfully
- Post-call webhook receives data from ElevenLabs
- Call record updated with metadata
- WebSocket connections accepted with valid token
- Subscriptions work with both call_sid and conversation_id
- Real-time messages delivered during call
- Call completion messages delivered (status + data)

---

### Step 2: Production Deployment

**Timing:** Schedule during low-traffic window (e.g., 2-4 AM local time)

#### 2.1 Pre-Deployment Checklist

- [ ] All staging tests passed
- [ ] Staging environment stable for 24+ hours
- [ ] Database backup created and verified
- [ ] Deployment team on standby
- [ ] Rollback plan reviewed and understood
- [ ] ElevenLabs support contacted (optional, for high-volume)
- [ ] Monitoring dashboards open and ready

#### 2.2 Database Migration (Production)

**IMPORTANT:** Backup database first!

```bash
# Create database backup
pg_dump -h DB_HOST -U DB_USER -d DB_NAME > backup_pre_migration_006_$(date +%Y%m%d_%H%M%S).sql

# Verify backup created
ls -lh backup_pre_migration_006_*.sql

# Run migration
cd /path/to/app
source .venv/bin/activate
python run_migrations.py

# Watch logs carefully
# Expected output: "Migration 006: Completed successfully"
```

**If migration fails:**
- DO NOT PROCEED
- Rollback immediately
- Investigate issue in staging
- Contact database administrator if needed

#### 2.3 Code Deployment (Production)

```bash
# Method 1: Git deployment
git fetch origin
git checkout feature/elevenlabs-completion-webhook-websocket
git pull origin feature/elevenlabs-completion-webhook-websocket

# Method 2: Cloud Run deployment
gcloud run deploy agy-backend \
  --source . \
  --region YOUR_REGION \
  --project YOUR_PROJECT

# Method 3: Docker deployment
docker pull your-registry/agy-backend:latest
docker-compose up -d

# Restart application
sudo systemctl restart agy-backend

# Verify application health
curl https://production-domain/health

# Check startup logs
tail -f /var/log/agy-backend/app.log
# Look for:
# - "Application startup complete"
# - "WebSocketConnectionManager initialized"
# - No error stack traces
```

#### 2.4 Configure ElevenLabs Webhook (Production)

1. Log in to ElevenLabs dashboard
2. Navigate to agent configuration
3. Add production webhook:
   - **URL:** `https://production-domain/webhooks/elevenlabs/post-call`
   - **Enabled:** Yes
4. Test webhook delivery:
   - ElevenLabs may have a "Test Webhook" button
   - Or initiate a real test call
5. Monitor logs for webhook receipt

#### 2.5 Verification (Production)

**Monitor for 1-2 hours continuously:**

```bash
# Terminal 1: Watch application logs
tail -f /var/log/agy-backend/app.log

# Terminal 2: Watch webhook receipts
tail -f /var/log/agy-backend/app.log | grep "webhooks/elevenlabs"

# Terminal 3: Monitor errors
tail -f /var/log/agy-backend/app.log | grep -E "ERROR|CRITICAL"
```

**Check Sentry/GlitchTip:**
- Open Sentry dashboard
- Watch for new error types
- Investigate any 5xx errors immediately

**Database Verification:**
```sql
-- Check recent calls have post-call data
SELECT
    call_sid,
    status,
    transcript_summary IS NOT NULL as has_summary,
    cost,
    call_successful,
    call_end_time
FROM dev.calls
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 10;

-- Check WebSocket activity (via logs)
-- No direct database tracking for WebSocket connections
```

**Frontend Verification:**
- Contact frontend team to test WebSocket connections
- Verify real-time transcriptions appearing in UI
- Check call completion notifications working
- Gather feedback on performance

---

## ElevenLabs Configuration

### Webhook URLs

**Staging:**
- Transcription: `https://staging-domain/webhooks/elevenlabs/transcription` (existing)
- Post-Call: `https://staging-domain/webhooks/elevenlabs/post-call` (NEW)

**Production:**
- Transcription: `https://production-domain/webhooks/elevenlabs/transcription` (existing)
- Post-Call: `https://production-domain/webhooks/elevenlabs/post-call` (NEW)

### Webhook Configuration Steps

1. **Access ElevenLabs Dashboard:**
   - URL: https://elevenlabs.io/app/conversational-ai
   - Log in with production credentials

2. **Navigate to Agent Settings:**
   - Select your production agent
   - Go to "Webhooks" or "Integrations" section

3. **Add Post-Call Webhook:**
   - Click "Add Webhook" or "New Webhook"
   - Name: "Post-Call Completion"
   - URL: Your production URL
   - Events: Select `post_call_transcription` and `call_initiation_failure`
   - Authentication: None (handled by app logic)
   - Retry Policy: Enable (up to 10 retries recommended)

4. **Test Webhook:**
   - Use ElevenLabs test feature if available
   - Or initiate a real test call
   - Verify webhook receipt in application logs

5. **Monitor Webhook Health:**
   - ElevenLabs dashboard shows webhook delivery status
   - Check delivery success rate (should be >99%)
   - Investigate any failed deliveries

### Webhook Retry Configuration

ElevenLabs automatically retries failed webhooks. Ensure:
- Retry attempts: 10 (maximum)
- Retry delay: Exponential backoff (1s, 2s, 4s, 8s, etc.)
- Timeout: 30 seconds per attempt

**Important:** Application MUST return non-200 status codes for errors to trigger retries:
- 400 Bad Request: Invalid payload (won't retry)
- 404 Not Found: Call not found (will retry - may resolve after delay)
- 500 Internal Server Error: Database/processing error (will retry)

---

## Monitoring and Verification

### Key Metrics to Monitor

**Post-Call Webhook:**
- Request rate (calls/hour)
- Success rate (should be >99%)
- Error rate by status code (400/404/500)
- Average processing time (<200ms typical)
- Database write latency

**WebSocket Connections:**
- Active connection count
- New connections per minute
- Disconnections per minute
- Average connection duration
- Message broadcast rate
- Failed broadcast attempts

**Database:**
- Query performance for new fields
- Storage growth rate
- Connection pool utilization
- Migration impact on performance

### Monitoring Commands

**Check Active WebSocket Connections:**
```bash
# Count connections from logs (example)
grep "WebSocket connection established" /var/log/agy-backend/app.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

**Check Webhook Receipt Rate:**
```bash
# Count post-call webhooks received today
grep "POST /webhooks/elevenlabs/post-call" /var/log/agy-backend/app.log | \
  grep "$(date +%Y-%m-%d)" | wc -l
```

**Check Error Rates:**
```bash
# Count 5xx errors in last hour
grep -E "HTTP/1.1\" 5[0-9]{2}" /var/log/agy-backend/app.log | \
  grep "$(date +%Y-%m-%d %H)" | wc -l
```

### Sentry Alert Configuration

**Create alerts for:**

1. **High Error Rate Alert**
   - Condition: Error count > 10 in 5 minutes
   - Channels: Email, Slack, PagerDuty
   - Priority: High

2. **Post-Call Webhook Failure**
   - Condition: 5xx errors on `/webhooks/elevenlabs/post-call`
   - Channels: Email, Slack
   - Priority: Medium

3. **WebSocket Connection Failure**
   - Condition: WebSocket errors > 5 in 1 minute
   - Channels: Email, Slack
   - Priority: Medium

4. **Database Write Failure**
   - Condition: `update_post_call_data` errors
   - Channels: Email, Slack, PagerDuty
   - Priority: High

---

## Rollback Procedures

### Scenario 1: WebSocket Issues Only

**Symptoms:**
- WebSocket connections failing
- High error rates in WebSocket logs
- Frontend reports connection problems

**Impact:** Low - Core functionality unaffected

**Rollback Steps:**
1. No code rollback needed
2. Frontend switches to polling mode
3. Webhook processing continues normally
4. Fix issue in development
5. Re-deploy WebSocket fix only

**Data Loss:** None

---

### Scenario 2: Post-Call Webhook Issues

**Symptoms:**
- High 5xx error rates on post-call webhook
- Call records not being updated
- Database errors

**Impact:** Medium - Call metadata not stored

**Rollback Steps:**
1. Disable webhook in ElevenLabs dashboard immediately
2. Application continues to work normally
3. Investigate issue in logs
4. Fix and re-deploy
5. Re-enable webhook
6. Backfill missing data using conversation fetch endpoint

**Data Loss:** Minimal - can be recovered

**Backfill Command:**
```bash
# Fetch missing call data from ElevenLabs API
# For each call missing metadata:
curl https://production-domain/conversations/{conversation_id}/fetch \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Scenario 3: Migration Failure

**Symptoms:**
- Migration script errors
- Database connection errors
- Application won't start

**Impact:** High - Application down

**Rollback Steps:**

```bash
# 1. Stop application immediately
sudo systemctl stop agy-backend

# 2. Restore database backup
psql -h DB_HOST -U DB_USER -d DB_NAME < backup_pre_migration_006_TIMESTAMP.sql

# 3. Rollback code to previous version
git checkout main
# or
git checkout previous-release-tag

# 4. Restart application
sudo systemctl start agy-backend

# 5. Verify application working
curl https://production-domain/health

# 6. Monitor logs
tail -f /var/log/agy-backend/app.log
```

**Data Loss:** None if backup restored successfully

---

### Scenario 4: Code Deployment Issues

**Symptoms:**
- Application won't start
- High error rates immediately after deployment
- Critical endpoints broken

**Impact:** High - Application impaired or down

**Rollback Steps:**

```bash
# 1. Revert to previous code version
git checkout main  # or previous stable tag

# 2. Restart application
sudo systemctl restart agy-backend

# 3. Verify application working
curl https://production-domain/health

# 4. Check core functionality
curl https://production-domain/driver_data/call-elevenlabs \
  -H "Authorization: Bearer TOKEN" \
  -X POST -d '{"driver_ids": ["test"]}'

# 5. Note: Database migration remains (backward compatible)
# New fields will just be NULL until re-deployment
```

**Data Loss:** None

---

## Testing in Staging

### Test Checklist

- [ ] **Database Migration**
  - [ ] Migration runs without errors
  - [ ] All 6 columns added to calls table
  - [ ] Existing records unaffected
  - [ ] Can rollback migration successfully

- [ ] **Post-Call Webhook**
  - [ ] Webhook endpoint accessible
  - [ ] Valid payloads processed (200 OK)
  - [ ] Invalid payloads rejected (400 Bad Request)
  - [ ] Non-existent calls return 404
  - [ ] Call records updated with metadata
  - [ ] JSON fields properly formatted

- [ ] **WebSocket Connection**
  - [ ] Connects with valid JWT token (via query param)
  - [ ] Rejects invalid/expired tokens
  - [ ] Connection tracked in logs
  - [ ] Graceful disconnection

- [ ] **WebSocket Subscription**
  - [ ] Subscribe with call_sid works
  - [ ] Subscribe with conversation_id works
  - [ ] Invalid identifier returns error
  - [ ] Subscription confirmation received
  - [ ] Can subscribe to multiple calls

- [ ] **Real-Time Broadcasting**
  - [ ] Transcription messages delivered
  - [ ] Call status messages delivered
  - [ ] Call completed messages delivered
  - [ ] Message order correct (status before data)
  - [ ] Multiple clients receive same message

- [ ] **Integration Testing**
  - [ ] Complete call flow: initiate -> transcribe -> complete
  - [ ] WebSocket receives all events
  - [ ] Database updated correctly
  - [ ] No errors in logs

---

## Success Criteria

Deployment is successful when:

- [x] All 32 tests passing (verified before deployment)
- [ ] Database migration completed without errors
- [ ] Application starts successfully in production
- [ ] Post-call webhook receiving data from ElevenLabs
- [ ] Call records being updated with metadata
- [ ] WebSocket connections working with authentication
- [ ] Real-time transcriptions broadcasting to clients
- [ ] Call completion messages broadcasting correctly
- [ ] No critical errors in Sentry
- [ ] No performance degradation
- [ ] Frontend team confirms functionality working
- [ ] Zero data loss during deployment
- [ ] Production stable for 24+ hours

---

## Post-Deployment Monitoring

### First 2 Hours (Continuous Monitoring)

**Actions:**
- Keep terminal windows open with log tails
- Monitor Sentry dashboard continuously
- Watch for error spikes
- Check WebSocket connection counts
- Verify webhook deliveries

**Red Flags:**
- Error rate >1% on webhooks
- WebSocket connections failing
- Database query slowdowns
- Memory usage increasing
- 5xx errors in logs

**Response:**
- Investigate immediately
- Prepare for rollback if needed
- Contact team if unclear

---

### First 24 Hours (Regular Checks)

**Every 2-4 hours:**
- Check Sentry for new errors
- Review application logs
- Verify webhook success rate
- Check database performance
- Monitor WebSocket stability

**Gather feedback:**
- Contact frontend team
- Ask dispatchers about UI performance
- Check for user-reported issues
- Document any problems

---

### 24-48 Hours Post-Deployment

**Final verification:**
- Review all metrics and analytics
- Compare to baseline (pre-deployment)
- Check for any anomalies
- Verify data integrity

**Performance tuning (if needed):**
- Adjust WebSocket timeouts
- Optimize database queries
- Fine-tune broadcast logic
- Address any bottlenecks

**Documentation:**
- Document issues encountered
- Update runbooks with lessons learned
- Share knowledge with team
- Archive deployment notes

---

## Contact Information

**Deployment Lead:** [Your Name/Contact]
**Backend Team:** [Team Contact]
**DevOps/Infrastructure:** [DevOps Contact]
**Database Administrator:** [DBA Contact]
**ElevenLabs Support:** support@elevenlabs.io

**Emergency Contacts:**
- On-Call Engineer: [Phone/Slack]
- Team Lead: [Phone/Slack]
- CTO: [Phone] (critical issues only)

---

## Reference Documentation

**Related Documentation:**
- Detailed Deployment Checklist: `deployment/deployment-checklist.md`
- Frontend API Documentation: `deployment/api-documentation.md`
- Feature Specification: `spec.md`
- Task Breakdown: `tasks.md`
- Implementation Notes: `IMPLEMENTATION_SUMMARY_TASK_*.md`

**External Documentation:**
- ElevenLabs Webhook Documentation: https://elevenlabs.io/docs/api-reference/webhooks
- ElevenLabs Conversational AI: https://elevenlabs.io/docs/conversational-ai
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/

---

## Appendix: Quick Reference Commands

### Check Application Status
```bash
# Health check
curl https://production-domain/health

# Check logs
tail -f /var/log/agy-backend/app.log

# Check process
ps aux | grep python | grep main.py
```

### Database Queries
```sql
-- Check recent calls with metadata
SELECT call_sid, status, transcript_summary, cost, call_successful
FROM dev.calls
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Count calls by status
SELECT status, COUNT(*)
FROM dev.calls
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status;

-- Check metadata population rate
SELECT
    COUNT(*) as total_calls,
    COUNT(transcript_summary) as with_summary,
    ROUND(100.0 * COUNT(transcript_summary) / COUNT(*), 2) as percentage
FROM dev.calls
WHERE created_at > NOW() - INTERVAL '24 hours'
AND status = 'completed';
```

### WebSocket Testing (JavaScript)
```javascript
// Quick WebSocket test
const token = "YOUR_JWT_TOKEN";
const ws = new WebSocket(`wss://production-domain/ws/calls/transcriptions?token=${token}`);

ws.onopen = () => console.log("Connected!");
ws.onmessage = (e) => console.log("Message:", JSON.parse(e.data));
ws.onerror = (e) => console.error("Error:", e);

// Subscribe to a call
ws.send(JSON.stringify({subscribe: "CALL_SID_HERE"}));
```

### Webhook Testing
```bash
# Test post-call webhook with curl
curl -X POST https://production-domain/webhooks/elevenlabs/post-call \
  -H "Content-Type: application/json" \
  -d '{
    "type": "post_call_transcription",
    "event_timestamp": 1732200000,
    "data": {
      "conversation_id": "test_conv_123",
      "status": "done",
      "metadata": {
        "call_duration_secs": 120,
        "cost": 0.05
      },
      "analysis": {
        "call_successful": true,
        "transcript_summary": "Test call completed successfully"
      }
    }
  }'
```

---

**Deployment Summary Version:** 1.0
**Last Updated:** 2025-11-21
**Document Status:** Ready for deployment
