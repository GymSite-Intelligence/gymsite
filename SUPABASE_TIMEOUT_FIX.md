"""
SUPABASE CONNECTION TIMEOUT FIX — Apply to api.py

The API container is failing POST requests to /api/relatorios because
Supabase httpx client times out at 5s default (too short for cloud SaaS).

THREE SOLUTIONS (pick one):

1. QUICK — Patch _supabase_client() function (inline timeout):
   Replace lines 52-62 with the code below.

2. ENV-BASED — Set timeout via .env:
   Add: SUPABASE_CLIENT_TIMEOUT=15

3. DOCKER-LEVEL — Increase container ulimits in docker-compose.yml:
   Add network tuning flags.

════════════════════════════════════════════════════════════════════════════
SOLUTION 1 (RECOMMENDED): Patch _supabase_client() timeout
════════════════════════════════════════════════════════════════════════════

In api.py, replace the _supabase_client() function (lines ~52-62):

OLD:
```python
def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="Supabase não configurado (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ausentes em .env)",
        )
    from supabase import create_client
    return create_client(url, key)
```

NEW:
```python
def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="Supabase não configurado (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ausentes em .env)",
        )
    from supabase import create_client
    import httpx
    
    # Timeout aumentado pra cloud latency (default 5s pode ser insuficiente em SaaS)
    timeout_sec = float(os.getenv("SUPABASE_CLIENT_TIMEOUT", "15.0"))
    timeout = httpx.Timeout(timeout_sec, connect=timeout_sec + 5)
    
    client = create_client(url, key)
    
    # Aplica timeout no httpx session interno
    if hasattr(client, 'postgrest') and hasattr(client.postgrest, 'session'):
        client.postgrest.session.timeout = timeout
    if hasattr(client, 'realtime') and hasattr(client.realtime, 'session'):
        client.realtime.session.timeout = timeout
    
    return client
```

════════════════════════════════════════════════════════════════════════════
SOLUTION 2: Use .env for timeout
════════════════════════════════════════════════════════════════════════════

In .env, add:
  SUPABASE_CLIENT_TIMEOUT=15

Then in _supabase_client():
  timeout_sec = float(os.getenv("SUPABASE_CLIENT_TIMEOUT", "15.0"))
  timeout = httpx.Timeout(timeout_sec, connect=timeout_sec + 5)
  # ... rest of code

════════════════════════════════════════════════════════════════════════════
SOLUTION 3: Increase Docker timeout
════════════════════════════════════════════════════════════════════════════

In docker-compose.yml, add `sysctls` to the api service:

  api:
    build: ...
    sysctls:
      - net.core.somaxconn=4096
      - net.ipv4.tcp_max_syn_backlog=4096
      - net.ipv4.ip_local_port_range=1024 65535

This increases TCP backlog and socket buffer sizes.

════════════════════════════════════════════════════════════════════════════
SOLUTION 4 (OPTIONAL): Add retry logic in api.py
════════════════════════════════════════════════════════════════════════════

Wrap Supabase calls in a retry decorator:

import time
from functools import wraps

def retry_supabase(max_retries=3, backoff_sec=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "timed out" in str(e).lower() and attempt < max_retries - 1:
                        logger.warning(f"Supabase timeout, retrying ({attempt+1}/{max_retries})...")
                        time.sleep(backoff_sec * (2 ** attempt))  # Exponential backoff
                        continue
                    raise
        return wrapper
    return decorator

# Usage:
@retry_supabase(max_retries=3, backoff_sec=2)
def create_relatorio_stub(...):
    sb = _supabase_client()
    # ... rest of code

════════════════════════════════════════════════════════════════════════════
QUICK FIX — Commands to apply right now:
════════════════════════════════════════════════════════════════════════════

1. Increase timeout inline (no code change needed if using env):

   docker exec -e SUPABASE_CLIENT_TIMEOUT=20 gymsite-api uvicorn api:app --host 0.0.0.0 --port 8000

2. Or rebuild container with updated .env:

   # Update .env with:
   SUPABASE_CLIENT_TIMEOUT=15

   # Rebuild:
   docker-compose up --build

3. Test the fix:

   curl -X POST http://localhost:8000/api/relatorios \\
     -H "Content-Type: application/json" \\
     -d '{
       "cidade": "Fortaleza",
       "bairro": "Lagoa",
       "area_m2_min": 100,
       "area_m2_max": 500,
       "tipo_negocio": "academia",
       "publico_alvo": "25-40"
     }'

════════════════════════════════════════════════════════════════════════════
ROOT CAUSE ANALYSIS:
════════════════════════════════════════════════════════════════════════════

Error: httpx.ConnectTimeout: timed out

Why it happens:
1. Container in Docker (network latency to Supabase cloud SaaS)
2. Default httpx timeout = 5 seconds
3. Cloud REST API roundtrip > 5s during peak hours or network jitter
4. Connection pooling not warmed up on first POST

Affected endpoints:
- POST /api/relatorios (create stub) — most common
- GET /api/relatorios (list, but cacheable)
- GET /api/relatorios/{id} (detail)
- Any endpoint that queries Supabase on first request

Root factors:
- Distance: container → Supabase datacenter (latency ~100-200ms)
- Cold connection pool: first request has handshake overhead
- Concurrent requests: multiple threads competing for connections
- Cloud provider rate-limiting: Supabase free tier may throttle
"""

# RECOMMENDED FIX TO APPLY NOW:

import httpx

def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="Supabase não configurado (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ausentes em .env)",
        )
    from supabase import create_client
    
    # Timeout aumentado pra cloud latency (default 5s → 15s)
    timeout_sec = float(os.getenv("SUPABASE_CLIENT_TIMEOUT", "15.0"))
    timeout = httpx.Timeout(timeout_sec, connect=timeout_sec + 5.0)
    
    client = create_client(url, key)
    
    # Aplica timeout no httpx session interno
    if hasattr(client, 'postgrest') and hasattr(client.postgrest, 'session'):
        client.postgrest.session.timeout = timeout
    if hasattr(client, 'realtime') and hasattr(client.realtime, 'session'):
        client.realtime.session.timeout = timeout
    
    logger.info(f"Supabase client initialized with {timeout_sec}s timeout")
    return client
