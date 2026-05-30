---
description: Systematic debugging guide for any issue in the GymSite Intelligence stack. Follows root-cause analysis methodology.
---

# Workflow: /debug

Systematic debugging protocol.

## Steps

1. **Reproduce**
   - Get exact error message and stack trace
   - Identify environment (local/docker/prod)
   - Note recent changes (git log --oneline -5)

2. **Isolate**
   - Which module/file/line?
   - Which skill domain? (backend/frontend/pipeline/intel)
   - Can you reproduce with minimal data?

3. **Hypothesize**
   - List 3 possible causes
   - Rank by probability
   - Check logs for clues

4. **Test**
   - Add targeted logging (not print!)
   - Use debugger or inspect state
   - Create minimal reproduction script

5. **Fix**
   - Fix the ROOT cause, not the symptom
   - Add regression test
   - Verify fix doesn't break other features

6. **Document**
   - Update relevant docs if behavior changed
   - Add to `docs/KNOWN_ISSUES.md` if applicable

## Debug Commands

```bash
# Python stack trace with locals
python -c "import traceback; traceback.print_exc()"

# FastAPI endpoint test
curl -s http://localhost:8000/api/health | jq .

# Frontend network errors
# Open DevTools → Network → check failed requests

# ADK agent state inspection
python -c "import json; print(json.dumps(session.state, indent=2))"

# Database query inspection
psql $DATABASE_URL -c "SELECT * FROM oportunidades_prospeccao ORDER BY created_at DESC LIMIT 5"
```
