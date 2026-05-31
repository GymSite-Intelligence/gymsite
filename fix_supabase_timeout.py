#!/usr/bin/env python
"""
Quick fix: Patch api.py to increase Supabase timeout from 5s to 15s
This resolves httpx.ConnectTimeout errors on POST /api/relatorios
"""

import re
import sys
from pathlib import Path

API_FILE = Path("/app/api.py")

# Pattern to find the old _supabase_client function
OLD_PATTERN = r'''def _supabase_client\(\):
    url = os\.getenv\("SUPABASE_URL", ""\)\.strip\(\)
    key = os\.getenv\("SUPABASE_SERVICE_ROLE_KEY", ""\)\.strip\(\)
    if not url or not key:
        raise HTTPException\(
            status_code=500,
            detail="Supabase não configurado \(SUPABASE_URL \+ SUPABASE_SERVICE_ROLE_KEY ausentes em \.env\)",
        \)
    from supabase import create_client
    return create_client\(url, key\)'''

NEW_CODE = '''def _supabase_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=500,
            detail="Supabase não configurado (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY ausentes em .env)",
        )
    from supabase import create_client
    import httpx
    
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
    return client'''

if __name__ == "__main__":
    content = API_FILE.read_text(encoding="utf-8")
    
    # Simple pattern match for the function
    if "def _supabase_client():" in content:
        # Find the function boundaries and replace
        start = content.find("def _supabase_client():")
        end = content.find("\n\n_UUID_RE", start)  # Next function definition
        
        if start != -1 and end != -1:
            content = content[:start] + NEW_CODE + content[end:]
            API_FILE.write_text(content, encoding="utf-8")
            print("✓ Patched _supabase_client() with increased timeout (15s)")
            sys.exit(0)
    
    print("✗ Could not find _supabase_client() function in api.py")
    sys.exit(1)
