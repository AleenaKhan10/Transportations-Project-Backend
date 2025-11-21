# Deployment Checklist: ElevenLabs Completion Webhook and WebSocket Integration

## Overview

This checklist covers the deployment of two major features:
1. Post-call completion webhook (`POST /webhooks/elevenlabs/post-call`)
2. Real-time WebSocket system (`/ws/calls/transcriptions`)

**Key Components:**
- Database migration (6 new fields in Call model)
- Post-call webhook endpoint
- WebSocket connection manager
- WebSocket endpoint with JWT authentication
- WebSocket broadcasting from webhooks

---

## Pre-Deployment Checklist

### Code Review

- [ ] **All code changes reviewed and approved**
  - Review changes in models/call.py (new post-call metadata fields)
  - Review services/webhooks_elevenlabs.py (post-call webhook endpoint)
  - Review services/websocket_manager.py (connection manager)
  - Review services/websocket_calls.py (WebSocket endpoint)
  - Review models/websocket_messages.py (message models)
  - Review integration points in existing webhooks

- [ ] **All tests passing**
  - Run feature-specific tests (approximately 22-34 tests)
  - Verify no regressions in existing test suite
  - Review test coverage for critical paths

- [ ] **Documentation complete**
  - API documentation for frontend (api-documentation.md)
  - CLAUDE.md updated with new features
  - This deployment checklist reviewed

### Environment Preparation

- [ ] **Database backup created**
  - Create full backup of production database
  - Verify backup can be restored
  - Document backup location and timestamp

- [ ] **Migration tested in staging**
  - Run migration 006_add_post_call_metadata.py in staging
  - Verify all columns added successfully
  - Confirm existing Call records unaffected (NULL values)
  - Test rollback procedure

- [ ] **Environment variables configured**
  - ELEVENLABS_API_KEY present in production environment
  - SECRET_KEY configured for JWT authentication
  - Database credentials verified
  - All required environment variables present

- [ ] **Monitoring setup**
  - Sentry/GlitchTip configured for error tracking
  - Log aggregation enabled
  - Alerts configured for webhook failures
  - Alerts configured for WebSocket connection failures

---

## Deployment Steps

### Phase 1: Database Migration

**Timing:** Execute during low-traffic window

- [ ] **1.1 Run database migration**
  ```bash
  source .venv/Scripts/activate
  python run_migrations.py
  ```
  - Migration 006 adds 6 new columns to calls table
  - All columns nullable (backward compatible)
  - No data backfill required

- [ ] **1.2 Verify migration success**
  - Check migration logs for errors
  - Verify all 6 columns exist in calls table:
    - transcript_summary (Text)
    - call_duration_seconds (Integer)
    - cost (Double Precision)
    - call_successful (Boolean)
    - analysis_data (Text)
    - metadata_json (Text)
  - Confirm existing Call records have NULL for new fields

- [ ] **1.3 Test Call model methods**
  - Verify Call.update_post_call_data() can be called
  - Test with sample data
  - Verify database write succeeds

**Rollback:** If migration fails, run reverse migration to drop columns

---

### Phase 2: Code Deployment

- [ ] **2.1 Deploy new code to production**
  - Pull latest code from repository
  - Install dependencies (if any new ones)
  - Restart application servers
  - Verify application starts without errors

- [ ] **2.2 Verify deployment**
  - Check application logs for startup errors
  - Verify no exceptions during initialization
  - Confirm WebSocketConnectionManager initialized
  - Verify all routers registered

- [ ] **2.3 Test endpoints availability**
  - POST /webhooks/elevenlabs/post-call returns 400 for invalid payload (endpoint active)
  - WebSocket /ws/calls/transcriptions rejects connection without token (endpoint active)
  - Existing endpoints still functional

**Rollback:** If deployment fails, revert to previous code version and restart

---

### Phase 3: ElevenLabs Configuration

- [ ] **3.1 Configure post-call webhook in ElevenLabs dashboard**
  - Log in to ElevenLabs dashboard
  - Navigate to webhook configuration
  - Add post-call webhook URL: `https://your-production-domain/webhooks/elevenlabs/post-call`
  - Enable webhook delivery
  - Save configuration

- [ ] **3.2 Test webhook delivery**
  - Initiate test call via ElevenLabs
  - Wait for call completion
  - Verify post-call webhook received in logs
  - Check Call record updated with metadata
  - Verify no errors in webhook processing

- [ ] **3.3 Verify ElevenLabs retry mechanism**
  - Confirm ElevenLabs configured for retries (up to 10 attempts)
  - Test that non-200 responses trigger retry
  - Verify retry delay configured

**Rollback:** If webhook issues occur, disable webhook in ElevenLabs dashboard

---

### Phase 4: Post-Deployment Verification

#### Webhook Verification (30 minutes)

- [ ] **4.1 Monitor post-call webhook receipts**
  - Watch logs for incoming POST /webhooks/elevenlabs/post-call requests
  - Verify 200 OK responses for valid payloads
  - Check Call records updated with metadata
  - Confirm no 500 errors

- [ ] **4.2 Verify post-call data storage**
  - Query database for recent completed calls
  - Verify post-call fields populated:
    - transcript_summary not NULL
    - call_duration_seconds matches expected range
    - cost is reasonable value
    - call_successful is boolean
    - analysis_data is valid JSON
    - metadata_json is valid JSON
  - Confirm call_end_time populated

- [ ] **4.3 Test failure scenarios**
  - Send invalid webhook payload (should return 400)
  - Send webhook with non-existent conversation_id (should return 404)
  - Verify error logging works
  - Confirm errors sent to Sentry/GlitchTip

#### WebSocket Verification (30 minutes)

- [ ] **4.4 Test WebSocket connection**
  - Connect WebSocket client with valid JWT token
  - Verify connection accepted
  - Check connection logged in server logs
  - Confirm WebSocketConnectionManager tracking connection

- [ ] **4.5 Test subscription flow**
  - Send subscribe message with call_sid
  - Verify subscription_confirmed message received
  - Check call details in confirmation
  - Test subscribe with conversation_id
  - Verify both work correctly

- [ ] **4.6 Test real-time transcription broadcast**
  - Subscribe to active call
  - Trigger transcription webhook (simulated or real call)
  - Verify transcription message received in WebSocket
  - Check message format matches specification
  - Confirm speaker_type, message_text, sequence_number present

- [ ] **4.7 Test call completion broadcast**
  - Subscribe to active call
  - Trigger post-call webhook (simulated or wait for real call)
  - Verify call_status message received first
  - Verify call_completed message received second
  - Check message order maintained
  - Confirm full call_data present in completed message

- [ ] **4.8 Test multiple client subscriptions**
  - Connect 2-3 WebSocket clients
  - Subscribe all to same call
  - Trigger transcription webhook
  - Verify all clients receive same message
  - Check no duplicate deliveries per client

- [ ] **4.9 Test authentication failures**
  - Attempt WebSocket connection without token (should reject)
  - Attempt connection with expired token (should reject)
  - Attempt connection with invalid token (should reject)
  - Verify error responses appropriate

- [ ] **4.10 Test graceful disconnection**
  - Connect WebSocket client
  - Subscribe to call
  - Disconnect client
  - Verify connection cleaned up in logs
  - Confirm subscriptions removed
  - Check no memory leaks

#### Integration Verification (30 minutes)

- [ ] **4.11 End-to-end call flow**
  - Initiate real ElevenLabs call via POST /driver_data/call-elevenlabs
  - Subscribe WebSocket client to call using call_sid
  - Verify subscription_confirmed received
  - Monitor transcription messages during call
  - Wait for call completion
  - Verify call_status message received
  - Verify call_completed message received with full data
  - Check Call record in database has all metadata
  - Confirm transcriptions stored in database

- [ ] **4.12 Verify webhook-WebSocket independence**
  - Disconnect all WebSocket clients
  - Trigger transcription webhook
  - Verify webhook returns 200 OK (no subscribers doesn't fail)
  - Trigger post-call webhook
  - Verify webhook returns 200 OK
  - Check Call record still updated correctly

- [ ] **4.13 Test concurrent operations**
  - Start multiple calls simultaneously
  - Subscribe to multiple calls on single WebSocket connection
  - Verify messages delivered correctly
  - Check no message mixing between calls
  - Confirm call_sid/conversation_id identify messages correctly

---

### Phase 5: Monitoring Setup

- [ ] **5.1 Configure Sentry alerts**
  - Alert on POST /webhooks/elevenlabs/post-call 5xx errors
  - Alert on WebSocket connection failures
  - Alert on database errors in webhooks
  - Alert on ElevenLabs API call failures

- [ ] **5.2 Set up log monitoring**
  - Monitor for "WebSocket connection established" logs
  - Monitor for "WebSocket connection disconnected" logs
  - Monitor for "Broadcast completed" logs
  - Monitor for webhook receipt logs
  - Set up dashboard for connection counts

- [ ] **5.3 Configure metrics collection**
  - Track active WebSocket connections count
  - Track webhook receipt rate
  - Track webhook error rate
  - Track Call completion rate
  - Track average call duration and cost

- [ ] **5.4 Document monitoring locations**
  - Document where to view logs
  - Document Sentry project URL
  - Document metrics dashboard URL
  - Share access with team

---

## Post-Deployment Monitoring (24-48 hours)

### First 24 Hours

- [ ] **Monitor continuously for first 2-4 hours**
  - Check for any error spikes
  - Verify webhook deliveries working
  - Monitor WebSocket connection stability
  - Watch for memory leaks or resource issues

- [ ] **Review error logs regularly**
  - Check Sentry for new error types
  - Review application logs for warnings
  - Investigate any unexpected errors
  - Document and fix issues promptly

- [ ] **Monitor database performance**
  - Check query performance for new fields
  - Verify indexes being used
  - Monitor database connection pool
  - Check for slow queries

- [ ] **Collect user feedback**
  - Ask frontend team about WebSocket reliability
  - Check for any reported issues
  - Gather performance feedback
  - Document improvement suggestions

### 24-48 Hours Post-Deployment

- [ ] **Review metrics and analytics**
  - Analyze webhook receipt success rate
  - Check WebSocket connection stability
  - Review average call duration and costs
  - Compare against expected values

- [ ] **Performance tuning (if needed)**
  - Adjust connection timeouts if needed
  - Optimize database queries if slow
  - Tune WebSocket broadcast performance
  - Address any bottlenecks

- [ ] **Documentation updates**
  - Document any issues encountered
  - Update runbooks with lessons learned
  - Add troubleshooting tips
  - Share knowledge with team

---

## Rollback Procedures

### Rollback: WebSocket Issues

**Symptoms:**
- WebSocket connections failing
- Messages not being delivered
- High error rates in broadcasts

**Actions:**
1. WebSocket endpoint can be disabled without affecting core functionality
2. Frontend falls back to polling `/calls/{call_sid}/transcript` endpoint
3. Webhook processing continues to save data to database
4. Fix WebSocket issue in development
5. Re-deploy and re-test
6. Re-enable WebSocket for frontend

**Data Loss:** None - all data persists to database

---

### Rollback: Post-Call Webhook Issues

**Symptoms:**
- High error rates in post-call webhook
- Call records not being updated
- Database errors

**Actions:**
1. Disable webhook in ElevenLabs dashboard immediately
2. Calls continue to work but completion data not stored
3. Investigate issue in logs
4. Fix issue and deploy patch
5. Re-enable webhook in ElevenLabs
6. Lost completion data can be fetched via `/conversations/{conversation_id}/fetch` endpoint

**Data Loss:** Minimal - can backfill using conversation fetch endpoint

---

### Rollback: Database Migration Issues

**Symptoms:**
- Migration fails during execution
- Application can't start after migration
- Database errors accessing new fields

**Actions:**
1. **Stop application immediately**
2. **Rollback migration:**
   ```sql
   -- Run in production database
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS transcript_summary;
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS call_duration_seconds;
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS cost;
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS call_successful;
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS analysis_data;
   ALTER TABLE dev.calls DROP COLUMN IF EXISTS metadata_json;
   ```
3. **Redeploy previous code version**
4. **Restart application**
5. **Verify application working**
6. **Investigate migration issue in staging**
7. **Fix and re-attempt migration**

**Data Loss:** None - rollback removes empty columns only

---

### Rollback: Code Deployment Issues

**Symptoms:**
- Application won't start
- High error rates after deployment
- Critical functionality broken

**Actions:**
1. **Revert to previous code version immediately:**
   ```bash
   git checkout <previous-commit-hash>
   ```
2. **Restart application**
3. **Verify application working**
4. **Database migration remains (backward compatible)**
5. **Investigate issue in staging**
6. **Fix and re-deploy**

**Data Loss:** None - new fields remain NULL until re-deployment

---

## Success Criteria

Deployment considered successful when:

- [ ] **Database migration completed** without errors
- [ ] **All new endpoints accessible** and returning expected responses
- [ ] **Post-call webhooks being received** from ElevenLabs
- [ ] **Call records being updated** with post-call metadata
- [ ] **WebSocket connections working** with JWT authentication
- [ ] **Subscriptions working** for both call_sid and conversation_id
- [ ] **Real-time transcriptions broadcasting** to subscribed clients
- [ ] **Call completion broadcasting** with two-message sequence
- [ ] **No critical errors** in logs or Sentry
- [ ] **No performance degradation** in existing functionality
- [ ] **Monitoring and alerts configured** and functional
- [ ] **Zero data loss** during deployment process

---

## Contact Information

**On-Call Engineer:** [Name/Contact]

**Backend Team Lead:** [Name/Contact]

**DevOps Contact:** [Name/Contact]

**Escalation Path:** [Details]

---

## Deployment Sign-Off

**Deployed By:** _______________  **Date:** ___________  **Time:** __________

**Verified By:** _______________  **Date:** ___________  **Time:** __________

**Production Stable:** [ ] Yes  [ ] No  **Confirmed By:** _______________

---

## Notes

Use this space to document any issues, observations, or deviations from the checklist during deployment:

```
[Add deployment notes here]
```
