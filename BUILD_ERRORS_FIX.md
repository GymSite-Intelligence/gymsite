# 🐛 Build Errors Analysis & Fixes — GymSite Intelligence

## 📊 Error Summary

### **Error 1: supabase_vector_marce — Restarting (0)**
```
ERROR: Listing currently running containers failed.
error=HyperLegacyError { ... NetworkUnreachable, message: "Network unreachable" }
```
**Root Cause:** Vector container cannot reach Docker daemon (socket access missing)

**Impact:** Logs not flowing to Logflare (analytics disrupted, but non-critical)

**Fix:** Mount Docker socket in docker-compose.yml

---

### **Error 2: supabase_edge_runtime_marce — Exited (255)**
```
Status: Exited (255)
```
**Root Cause:** Network config issue or Edge Runtime initialization failure

**Impact:** Supabase Edge Functions unavailable (if used)

**Fix:** Restart or adjust network settings

---

### **Error 3: RedisQueue timeout — "Timeout reading from redis:6379"**
```json
{
  "level": "ERROR",
  "message": "RedisQueue error: Timeout reading from redis:6379",
  "funcName": "start_worker",
  "lineno": 63
}
```
**Root Cause:** Redis connection pool exhaustion OR `brpop()` timeout during blocking read

**Impact:** Async jobs (pipeline, prospecting) accumulate in queue, not processed

**Fix:** Increase timeout, add connection pooling, or disable queue if unused

---

## 🔧 Fixes

### **Fix 1: Mount Docker Socket for Vector**

Edit `docker-compose.yml`:

```yaml
services:
  supabase_vector_marce:
    image: public.ecr.aws/supabase/vector:0.53.0-alpine
    container_name: supabase_vector_marce
    environment:
      LOGFLARE_API_KEY: ${LOGFLARE_API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # ← ADD THIS
    # ... rest of config
```

This allows Vector to query Docker daemon for logs.

---

### **Fix 2: Restart Edge Runtime**

```bash
docker restart supabase_edge_runtime_marce

# Wait 30 seconds then check
sleep 30
docker logs supabase_edge_runtime_marce | tail -5
```

If still failing, rebuild:
```bash
docker-compose -f supabase/docker-compose.yml down
docker-compose -f supabase/docker-compose.yml up -d supabase_edge_runtime_marce
```

---

### **Fix 3: Fix RedisQueue Timeout**

**Option A: Increase timeout (RECOMMENDED)**

In `/app/tools/redis_queue.py`, line ~45:

```python
# OLD:
result = await r.brpop(QUEUE_KEY, timeout=5)

# NEW:
result = await r.brpop(QUEUE_KEY, timeout=30)  # 30 sec timeout
```

**Option B: Fix timeout in redis_client.py**

```python
# Add connection pool config
async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_pool = redis.from_url(
            url,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
            connection_pool_kwargs={
                "max_connections": 10,
                "retry_on_timeout": True,
                "socket_connect_timeout": 10.0,
                "socket_read_timeout": 30.0,
                "socket_write_timeout": 30.0,
            }
        )
    return _redis_pool
```

**Option C: Disable RedisQueue if not used**

In `api.py`, comment out:

```python
# Disable Redis queue if not critical for pipeline
# queue = RedisQueue(gymsite_worker, concurrency=2)
# await queue.start_worker()
```

And use FastAPI's built-in `BackgroundTasks` instead:

```python
@app.post("/api/relatorios")
async def create_relatorio(
    payload: NovoRelatorioInput,
    background_tasks: BackgroundTasks,  # ← Use this
):
    background_tasks.add_task(_run_pipeline_async_wrapper, relatorio_id, payload)
```

---

## 📝 Step-by-Step Fix Instructions

### **1. Fix Vector (Supabase Logging)**

```bash
# Edit docker-compose.yml (for Supabase Vector)
# Add volume: /var/run/docker.sock:/var/run/docker.sock
# Then restart:

docker-compose down supabase_vector_marce
docker-compose up -d supabase_vector_marce

# Verify (should NOT show "Restarting"):
docker ps | findstr "vector"
```

### **2. Restart Edge Runtime**

```bash
docker restart supabase_edge_runtime_marce
sleep 30
docker logs supabase_edge_runtime_marce
```

### **3. Fix RedisQueue Timeout**

Edit inside container or rebuild:

```bash
docker exec -it gymsite-api nano /app/tools/redis_queue.py
# Change line 45: timeout=5 → timeout=30
# Save (Ctrl+X → y → Enter)

# Restart API
docker restart gymsite-api
```

Or apply patch programmatically:

```bash
docker exec gymsite-api sed -i 's/timeout=5/timeout=30/g' /app/tools/redis_queue.py
docker restart gymsite-api
```

### **4. Verify All Services**

```bash
docker ps -a | findstr "vector\|edge-runtime\|redis\|gymsite-api"
docker logs gymsite-api --tail 20
docker exec gymsite-api python -c "import redis; print(redis.Redis(host='redis', port=6379).ping())"
```

---

## 📋 Full docker-compose.yml Supabase Vector Section

```yaml
  supabase_vector_marce:
    image: public.ecr.aws/supabase/vector:0.53.0-alpine
    container_name: supabase_vector_marce
    restart: unless-stopped
    environment:
      LOGFLARE_API_KEY: ${LOGFLARE_API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # ← FIX 1
      - ./supabase/vector.yaml:/etc/vector/vector.yaml:ro
    # Logging destination (Logflare)
    logging:
      driver: json-file
      options:
        max-size: 100m
        max-file: "3"
```

---

## 🎯 Quick Fix Script

Save as `fix_errors.sh`:

```bash
#!/bin/bash

echo "🐛 Fixing GymSite build errors..."

# Fix 1: Update docker-compose.yml for Vector
echo "1️⃣  Mounting Docker socket for Vector..."
docker-compose down supabase_vector_marce
docker-compose up -d supabase_vector_marce

# Fix 2: Restart Edge Runtime
echo "2️⃣  Restarting Edge Runtime..."
docker restart supabase_edge_runtime_marce
sleep 30

# Fix 3: Patch RedisQueue timeout
echo "3️⃣  Fixing RedisQueue timeout..."
docker exec gymsite-api sed -i 's/timeout=5/timeout=30/g' /app/tools/redis_queue.py
docker restart gymsite-api

# Verify
echo "4️⃣  Verifying services..."
docker ps -a | grep -E "vector|edge-runtime|redis|gymsite-api"
echo ""
echo "✅ Fixes applied. Check docker ps output above."
```

---

## 🚨 Additional Warnings

### **Red Flags**
- ⚠️ Vector in restart loop — might cascade to entire Supabase
- ⚠️ Redis timeouts — will block pipeline executions
- ⚠️ Edge Runtime down — if any Edge Functions in use

### **Non-Critical Issues**
- ✅ Vector logs not flowing → Observability degraded but app works
- ✅ Edge Runtime down → OK if not used by API

---

## 📞 Next Steps

1. **Apply Fix 1:** Mount Docker socket
2. **Apply Fix 2:** Restart Edge Runtime
3. **Apply Fix 3:** Increase Redis timeout to 30s
4. **Verify:** `docker ps` shows all healthy
5. **Test:** `curl http://localhost:8000/health`

Run these fixes now and report back if errors persist!
