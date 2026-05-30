---
description: Perform a comprehensive code review on the current changes or a specific file/PR. Checks types, security, performance, and style.
---

# Workflow: /review

Code review with automated + manual checks.

## Steps

1. **Type check** // turbo
   ```bash
   pyrefly check . 2>&1 | head -20
   cd frontend && npm run lint 2>&1 | head -20
   ```

2. **Security scan**
   - Check for hardcoded secrets (regex: `api[_-]?key`, `password`, `secret`)
   - Verify no `eval()` or `exec()` with user input
   - Check SQL injection vectors (f-strings in queries)

3. **Performance check**
   - Identify N+1 queries (loops with DB calls)
   - Check for missing indexes in new queries
   - Verify no synchronous I/O in async functions

4. **Style review**
   - Functions ≤30 lines?
   - Type hints present?
   - Docstrings for public APIs?
   - No `print()` / `console.log()`?

5. **Generate report**
   - List all issues found
   - Categorize: CRITICAL / WARNING / NIT
   - Suggest fixes with code examples
