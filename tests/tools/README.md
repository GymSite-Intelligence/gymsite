# tests/tools — pytest offline

Testes unitários/smoke para tools determinísticas. **Sem rede.** Não confundir com scan HTTP (`tools/security_audit` contra prod).

## Verifier canônico (Superpowers + P-000)

```powershell
.\scripts\verify-tools-tests.ps1
```

Equivalente:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/tools/ -v --tb=short
```

## Matriz

| Teste | Módulo | Invariante |
|-------|--------|------------|
| `test_listing_candidato_normalize.py` | `listing_candidato_normalize` | Filtro cidade, área, coordenadas |
| `test_candidato_viabilidade_rank.py` | `candidato_viabilidade_rank` | Rank sem `price_raw`; payback norm |
| `test_a6_top3_mrlr_md.py` | `a6_report_consolidator` | MD top3 com carimbo MRLR |
| `test_security_audit_smoke.py` | `security_audit` | Registry, config gymsite, mocks |

## Documentação Superpowers

- Spec: [`docs/superpowers/specs/2026-08-26-tests-tools-verification-design.md`](../../docs/superpowers/specs/2026-08-26-tests-tools-verification-design.md)
- Plan: [`docs/superpowers/plans/2026-08-26-tests-tools-verification.md`](../../docs/superpowers/plans/2026-08-26-tests-tools-verification.md)
- Preview evidência: [`docs/superpowers/previews/2026-08-26-tests-tools-matrix.html`](../../docs/superpowers/previews/2026-08-26-tests-tools-matrix.html)
