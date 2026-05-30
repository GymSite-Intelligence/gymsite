---
description: Run the CNPJ×CNO prospecting engine for a city. Disables cache, executes pipeline, and validates results.
---

# Workflow: /prospect

Execute a complete prospecting run for a target city.

## Prerequisites

- `GOOGLE_MAPS_API_KEY` configured
- `SUPABASE_*` credentials valid
- CNO CSV data available in `db/cno_data/`

## Steps

1. **Validate inputs**
   - Confirm city name and UF (default: Fortaleza/CE)
   - Verify CNO data exists for the city

2. **Clear prospecting cache** // turbo
   ```bash
   rm -rf metrics/cache/prospeccao_* 2>/dev/null; echo "Cache cleared"
   ```

3. **Run engine**
   ```bash
   python -m prospecting.engine --cidade="FORTALEZA" --uf="CE" --dias=90
   ```

4. **Validate output**
   - Check `oportunidades_prospeccao` table has new records
   - Verify `score_match` values are between 0.0–1.0
   - Confirm `status` = 'novo' for all new records

5. **Generate summary**
   - Count total oportunidades created
   - List top 5 by score_match
   - Identify any errors in `metrics/api_calls_pipeline.csv`

## Safety Checks

- ⚠️ This creates DB records — do NOT run on production without confirmation
- ⚠️ Google Maps API calls incur costs — verify quota before large runs
