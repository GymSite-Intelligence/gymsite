---
description: Generate a complete viability report (PDF) for a target city/bairro using the A0–A6 agent pipeline.
---

# Workflow: /report

Generate a full viability report with PDF output.

## Prerequisites

- `GEMINI_API_KEY` configured
- City/bairro defined
- Area range defined (min/max m²)

## Steps

1. **Collect inputs**
   - City, UF, bairro (optional)
   - Area range, ticket faixa, modelo (low/mid/premium)
   - Tamanho preset (PP, P, M, G, GG)

2. **Validate Google Maps API key** // turbo
   ```python
   from tools.maps_health import check_google_maps
   result = check_google_maps()
   assert result["ok"], f"Maps API failed: {result}"
   ```

3. **Execute A0–A6 pipeline**
   - Create session with inputs
   - Run Runner with root agent
   - Capture final state and PDF path

4. **Validate report**
   - Check PDF exists in `artifacts/`
   - Verify file size > 10KB
   - Open and check first page renders correctly

5. **Store metadata**
   - Insert record in `relatorios` table
   - Link PDF URL in `pdf_url` column

## Output

- PDF file: `artifacts/gymsite-relatorio-{cidade}-{uuid}.pdf`
- Database record with full pipeline state
