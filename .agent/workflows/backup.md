---
description: Create a full backup of the project — database, artifacts, cache, and configuration. Stores backups with timestamps.
---

# Workflow: /backup

Create a comprehensive backup of all project assets.

## Steps

1. **Create backup directory** // turbo
   ```bash
   BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
   mkdir -p "$BACKUP_DIR"
   echo "Backup dir: $BACKUP_DIR"
   ```

2. **Backup database**
   ```bash
   pg_dump $DATABASE_URL > "$BACKUP_DIR/db_full.sql"
   echo "Database backup complete"
   ```

3. **Backup artifacts (PDFs, reports)**
   ```bash
   cp -r artifacts/ "$BACKUP_DIR/artifacts/"
   echo "Artifacts backup complete"
   ```

4. **Backup cache**
   ```bash
   cp -r metrics/cache/ "$BACKUP_DIR/cache/"
   cp -r competitor_cache/ "$BACKUP_DIR/competitor_cache/"
   echo "Cache backup complete"
   ```

5. **Backup configuration**
   ```bash
   cp .env.example "$BACKUP_DIR/"
   cp docker-compose.yml "$BACKUP_DIR/"
   cp pyproject.toml "$BACKUP_DIR/"
   echo "Config backup complete"
   ```

6. **Generate manifest**
   ```bash
   cat > "$BACKUP_DIR/manifest.json" <<EOF
   {
     "timestamp": "$(date -Iseconds)",
     "files": {
       "database": "db_full.sql",
       "artifacts": "artifacts/",
       "cache": "cache/",
       "competitor_cache": "competitor_cache/"
     },
     "size_mb": $(du -sm "$BACKUP_DIR" | cut -f1)
   }
   EOF
   ```

7. **Verify backup**
   ```bash
   du -sh "$BACKUP_DIR"
   ls -la "$BACKUP_DIR"
   ```

## Restore

```bash
# Restore database
psql $DATABASE_URL < backups/20260529_120000/db_full.sql

# Restore artifacts
cp -r backups/20260529_120000/artifacts/* artifacts/
```

## Safety

- ⚠️ Backups include sensitive data — store securely
- ⚠️ `.env` with real keys is NOT backed up (use `.env.example` only)
- ⚠️ Verify backup integrity before considering it complete
