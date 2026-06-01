# Security Policy

## Vulnerability Disclosure

If you discover a security vulnerability, please email: security@vectracargo.com.br

Do not create public GitHub issues for security vulnerabilities.

## Incident Log

### 2026-06-01: Exposed Google Distance Matrix API Key

**Status:** REMEDIATED ✅

- **Discovery Date:** 2026-06-01
- **Exposure Date:** 2026-05-30 03:18:06 UTC
- **Exposed Credential:** Google Distance Matrix API Key
- **Duration:** ~2 hours
- **Root Cause:** Accidental commit to .env.example in public repository

**Actions Taken:**
- ✅ API Key rotated and deleted from GCP (2026-06-01T11:23:17Z)
- ✅ Removed from git history using git filter-repo
- ✅ Enabled GitHub Secret scanning
- ✅ Enabled GitHub Push protection
- ✅ Team training on credential management

**Restrictions on Exposed Key:**
- Limited to Google Maps APIs only
- No billing permissions
- No unrestricted access

## Best Practices

- Never commit .env files to version control
- Use GitHub Secret scanning and Push protection
- Rotate credentials immediately upon exposure
- Maintain audit logs of all deployments
