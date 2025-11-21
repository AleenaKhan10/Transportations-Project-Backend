# Rollback Procedures: Call SID Webhook Refactor

## When to Rollback

Execute rollback if:
- High error rates detected (>5% increase)
- Webhooks consistently failing
- Database performance degraded significantly
- Two-step lookup causing timeouts
- Data integrity issues detected
- Critical production issues preventing operations

## Rollback Decision Matrix

| Issue Type | Severity | Rollback Recommended | Alternative |
|-----------|----------|---------------------|-------------|
| Code errors | High | Yes | Quick fix if simple |
| Database slow queries | Medium | Maybe | Add indexes first |
| Webhook failures | High | Yes | Check configuration |
| Migration failures | Critical | Yes | Must rollback |
| Feature bugs | Low | No | Fix forward |

## Rollback Steps

### Step 1: Assess Current State

```bash
# Check how many calls have been created with new workflow
SELECT COUNT(*) FROM dev.calls WHERE conversation_id IS NULL;

# Check if any webhooks are still being processed
# Review logs for in-flight requests
```

Document findings:
- [ ] Number of calls in progress
- [ ] Number of calls with NULL conversation_id
- [ ] Current webhook processing rate
- [ ] Error rates and types

### Step 2: Stop New Calls (Optional)

If critical issue, temporarily disable call creation:

```python
# Add feature flag or maintenance mode
# Route calls through old system temporarily
```

- [ ] New calls stopped if needed
- [ ] Users notified of temporary maintenance
- [ ] Alternative process in place

### Step 3: Rollback ElevenLabs Webhook Configuration

**Priority: HIGH - Do this first to stop webhook errors**

Update webhook back to conversation_id format:

```bash
curl -X PUT "https://api.elevenlabs.io/v1/webhooks/{webhook_id}" \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhooks/elevenlabs/transcription",
    "events": ["conversation.dialogue.completed"],
    "payload": {
      "conversation_id": "{{conversation_id}}",
      "speaker": "{{speaker}}",
      "message": "{{message}}",
      "timestamp": "{{timestamp}}"
    }
  }'
```

- [ ] Webhook configuration reverted
- [ ] Verify webhook sends conversation_id
- [ ] Test webhook with single call
- [ ] Monitor webhook success rate

### Step 4: Rollback Code Deployment

```bash
# Option A: Revert to specific commit
git log --oneline -10  # Find previous stable commit
git checkout <previous-commit-hash>

# Option B: Revert to main branch
git checkout main
git pull origin main

# Redeploy application
# (Use your deployment process)

# Restart application
sudo systemctl restart agy-backend  # Or your restart command
```

- [ ] Code reverted to previous version
- [ ] Application deployed successfully
- [ ] Application started without errors
- [ ] Monitor logs for startup issues

### Step 5: Verify Code Rollback

```bash
# Test that old workflow works
curl -X POST "https://your-domain.com/webhooks/elevenlabs/transcription" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv_123",
    "speaker": "agent",
    "message": "Test message",
    "timestamp": "2025-11-21T10:00:00Z"
  }'
```

- [ ] Webhook accepts conversation_id again
- [ ] Old workflow functions correctly
- [ ] No errors in application logs

### Step 6: Database Rollback (If Needed)

**WARNING: Only rollback database if absolutely necessary**

#### Limitations
- Migration 004 rollback will FAIL if any Call records have NULL conversation_id
- Migrations cannot rollback if new calls were created with new schema
- Data created with new schema may be lost

#### Before Rollback
```sql
-- Check for NULL conversation_id records
SELECT COUNT(*) FROM dev.calls WHERE conversation_id IS NULL;

-- If count > 0, you MUST populate conversation_id or delete these records before rollback
-- Option 1: Delete records with NULL conversation_id (DESTRUCTIVE)
DELETE FROM dev.calls WHERE conversation_id IS NULL;

-- Option 2: Set dummy conversation_id values
UPDATE dev.calls
SET conversation_id = CONCAT('ROLLBACK_', call_sid)
WHERE conversation_id IS NULL;
```

#### Execute Rollback (Reverse Order)
```bash
# Migration 004 rollback - Make conversation_id non-nullable
python migrations/004_make_conversation_id_nullable.py downgrade

# Migration 003 rollback - Remove constraints and indexes
python migrations/003_add_call_sid_constraints.py downgrade

# Migration 002 rollback - Clear call_sid values
python migrations/002_backfill_call_sid.py downgrade

# Migration 001 rollback - Drop call_sid column
python migrations/001_add_call_sid_column.py downgrade
```

- [ ] All migrations rolled back successfully
- [ ] Verify database schema reverted
- [ ] Check for any orphaned data
- [ ] Verify indexes removed

### Step 7: Post-Rollback Verification

#### Test Old Workflow
```bash
# Create test call with old system
# Verify Call record created on first webhook (old behavior)
# Verify transcriptions saved correctly
```

- [ ] Old workflow works end-to-end
- [ ] Webhooks process successfully
- [ ] Transcriptions saved correctly
- [ ] No errors in logs

#### Monitor Metrics
- [ ] Error rates returned to normal
- [ ] Response times acceptable
- [ ] Database performance restored
- [ ] Webhook success rate >95%

### Step 8: Document Issues

Create incident report:

```markdown
# Rollback Incident Report

**Date**: [Date]
**Time**: [Time]
**Duration**: [Duration]

## Issue Summary
[Description of what went wrong]

## Root Cause
[Analysis of why it failed]

## Rollback Steps Taken
1. [Step 1]
2. [Step 2]
...

## Data Impact
- Calls affected: [Number]
- Data lost: [Yes/No + details]
- Duration of outage: [Duration]

## Lessons Learned
[What we learned]

## Corrective Actions
[What needs to be fixed before retry]
```

- [ ] Incident report created
- [ ] Root cause identified
- [ ] Corrective actions defined
- [ ] Team notified

## Rollback Time Estimates

| Step | Estimated Duration |
|------|-------------------|
| Assess current state | 10-15 minutes |
| Rollback webhook config | 5-10 minutes |
| Rollback code | 15-20 minutes |
| Verify code rollback | 10-15 minutes |
| Database rollback (if needed) | 30-45 minutes |
| Post-rollback verification | 30-60 minutes |
| **Total** | **1.5-3 hours** |

## Partial Rollback Options

### Option 1: Rollback Only Webhook (Keep Code/Database)
If issue is only with webhook configuration:
- Revert webhook to conversation_id format
- Keep new code deployed
- Keep database migrations
- Fix webhook issue and redeploy webhook config only

### Option 2: Rollback Code (Keep Database)
If issue is in code but not database:
- Revert code deployment
- Keep database migrations
- Keep call_sid field (unused but harmless)
- Fix code and redeploy

### Option 3: Full Rollback (Everything)
If critical database or data integrity issue:
- Rollback webhook
- Rollback code
- Rollback database migrations
- Start over after fixing issues

## Prevention for Next Deployment

- [ ] More extensive staging testing
- [ ] Gradual rollout (canary deployment)
- [ ] Better monitoring/alerting
- [ ] Feature flags for gradual enablement
- [ ] Backup/restore procedures tested
- [ ] Communication plan for team
- [ ] Rollback rehearsal

## Emergency Contacts

**On-Call Engineer**: [Contact]
**Database Admin**: [Contact]
**Team Lead**: [Contact]
**ElevenLabs Support**: [Contact]

## Notes

- Always prioritize data integrity over feature completion
- Document all decisions during rollback
- Communicate status to stakeholders
- Don't rush - careful rollback prevents further issues
- Keep calm and follow the plan
