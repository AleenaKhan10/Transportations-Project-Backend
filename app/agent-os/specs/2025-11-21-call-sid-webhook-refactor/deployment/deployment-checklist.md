# Deployment Checklist: Call SID Webhook Refactor

## Pre-Deployment

### Database Migrations
- [ ] Review all 4 migration files
- [ ] Test migrations in development environment
- [ ] Verify backfill logic handles NULL driver_id correctly
- [ ] Document expected migration duration
- [ ] Create database backup before migrations

### Code Review
- [ ] Review all model changes (Call model)
- [ ] Review all helper function changes (transcription_helpers.py)
- [ ] Review webhook endpoint changes (webhooks_elevenlabs.py)
- [ ] Review call creation workflow changes (driver_data.py)
- [ ] Verify all tests pass (approximately 18-42 tests)

### Testing
- [ ] Run all migration tests
- [ ] Run all model tests
- [ ] Run all helper function tests
- [ ] Run all endpoint tests
- [ ] Run all integration tests
- [ ] Verify test coverage for critical paths

## Staging Deployment

### Step 1: Run Migrations (Low-Traffic Period)
```bash
# Connect to staging database
# Run migrations in order:
python migrations/001_add_call_sid_column.py
python migrations/002_backfill_call_sid.py
python migrations/003_add_call_sid_constraints.py
python migrations/004_make_conversation_id_nullable.py
```

- [ ] Migration 001 completed successfully
- [ ] Migration 002 completed - verify backfill count
- [ ] Migration 003 completed - verify indexes created
- [ ] Migration 004 completed - conversation_id now nullable
- [ ] Verify database schema changes

### Step 2: Deploy Code to Staging
```bash
# Deploy updated code
git checkout feature/call-sid-webhook-refactor
git pull origin feature/call-sid-webhook-refactor
# Restart application
```

- [ ] Code deployed successfully
- [ ] Application starts without errors
- [ ] Check logs for startup errors

### Step 3: Test in Staging
- [ ] Create test call using POST /driver_data/call-elevenlabs
- [ ] Verify Call record created BEFORE ElevenLabs API call
- [ ] Verify Call record has call_sid populated
- [ ] Verify Call record has conversation_id=NULL initially
- [ ] Verify conversation_id populated after successful API call
- [ ] Send test webhook with call_sid
- [ ] Verify transcription saved successfully
- [ ] Test webhook with invalid call_sid (should return 400)
- [ ] Test webhook with NULL conversation_id (should return 400)
- [ ] Verify two-step lookup performance acceptable

## Production Deployment

### Step 4: Production Database Migrations
**IMPORTANT: Schedule during low-traffic period**

Recommended time: 2-4 AM local time

```bash
# Connect to production database
# Run migrations in order:
python migrations/001_add_call_sid_column.py
python migrations/002_backfill_call_sid.py
python migrations/003_add_call_sid_constraints.py
python migrations/004_make_conversation_id_nullable.py
```

- [ ] Migration 001 completed successfully
- [ ] Migration 002 completed - record backfill count
- [ ] Migration 003 completed - verify indexes created
- [ ] Migration 004 completed - conversation_id now nullable
- [ ] Verify all existing calls have call_sid
- [ ] Check database performance after index creation

### Step 5: Production Code Deployment
```bash
# Deploy to production
git checkout feature/call-sid-webhook-refactor
git pull origin feature/call-sid-webhook-refactor
# Deploy using your deployment process
# Restart application
```

- [ ] Code deployed successfully
- [ ] Application starts without errors
- [ ] Monitor logs for errors (5-10 minutes)

### Step 6: Update ElevenLabs Webhook Configuration
**IMPORTANT: Only after code deployment succeeds**

Update webhook payload to send call_sid instead of conversation_id:

```json
{
  "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
  "events": ["conversation.dialogue.completed"],
  "payload": {
    "call_sid": "{{call_sid}}",
    "speaker": "{{speaker}}",
    "message": "{{message}}",
    "timestamp": "{{timestamp}}"
  }
}
```

- [ ] Webhook configuration updated in ElevenLabs dashboard/API
- [ ] Test webhook with single test call
- [ ] Verify webhook receives call_sid correctly
- [ ] Verify transcription saved successfully

## Post-Deployment Verification

### Monitor First 10-20 Production Calls
- [ ] Call records created before API calls
- [ ] Call records have call_sid populated
- [ ] conversation_id populated after API success
- [ ] Webhooks receive call_sid correctly
- [ ] Transcriptions saved successfully
- [ ] Two-step lookup works correctly
- [ ] No increase in error rates
- [ ] Response times acceptable

### Database Verification
- [ ] Check index usage with EXPLAIN queries
- [ ] Verify unique constraints working
- [ ] Verify backfilled records work correctly
- [ ] Monitor database performance metrics
- [ ] Check for any slow queries

### Error Monitoring
- [ ] Check Sentry/GlitchTip for errors
- [ ] Review application logs for warnings
- [ ] Monitor webhook failure rates
- [ ] Check database connection pool metrics

## Rollback Procedures

### If Issues Detected

#### Rollback Code (if code issues)
```bash
# Revert to previous version
git checkout main
git pull origin main
# Redeploy previous version
# Restart application
```

#### Rollback Webhook Configuration
Update ElevenLabs webhook back to conversation_id:

```json
{
  "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
  "events": ["conversation.dialogue.completed"],
  "payload": {
    "conversation_id": "{{conversation_id}}",
    "speaker": "{{speaker}}",
    "message": "{{message}}",
    "timestamp": "{{timestamp}}"
  }
}
```

#### Rollback Database (if database issues)
**WARNING: Migration 004 rollback may fail if NULL conversation_id values exist**

```bash
# Rollback migrations in reverse order
python migrations/004_make_conversation_id_nullable.py downgrade
python migrations/003_add_call_sid_constraints.py downgrade
python migrations/002_backfill_call_sid.py downgrade
python migrations/001_add_call_sid_column.py downgrade
```

- [ ] Verify rollback completed successfully
- [ ] Verify application works with old code
- [ ] Document issues for investigation

## Success Criteria

- [ ] All migrations completed successfully
- [ ] Code deployed without errors
- [ ] ElevenLabs webhook updated successfully
- [ ] First 10-20 production calls work correctly
- [ ] No increase in error rates
- [ ] Response times within acceptable range
- [ ] Database indexes being used
- [ ] Two-step lookup performs well
- [ ] Backfilled records work correctly
- [ ] Audit trail complete for all calls (including failures)

## Post-Deployment Tasks

- [ ] Document any issues encountered
- [ ] Update runbook with new workflow
- [ ] Update monitoring dashboards if needed
- [ ] Schedule cleanup of old monitoring for conversation_id-only workflow
- [ ] Update team documentation
- [ ] Conduct team walkthrough of new workflow

## Timeline Estimate

- **Staging Deployment**: 1-2 hours
- **Production Migration**: 30-60 minutes (depends on database size)
- **Production Code Deployment**: 15-30 minutes
- **Webhook Configuration**: 10-15 minutes
- **Post-Deployment Monitoring**: 2-4 hours
- **Total**: Approximately 4-8 hours

## Contact Information

**On-Call Support**: [Your on-call schedule]
**Database Admin**: [DBA contact]
**ElevenLabs Support**: [ElevenLabs contact]

## Notes

- Migrations should be run during low-traffic period
- Keep database backup ready
- Monitor closely for first hour after deployment
- Document any unexpected behavior
- Have rollback plan ready before starting
