# Malha de bairros IBGE (Censo 2022) — Spec C

Espelho **local** para runtime. Relatório **não** baixa FTP por request.

## Layout

| Path | Role |
|------|------|
| `fixtures/coco_ce.geojson` | Fixture committed (tests) |
| `{UF}.gpkg` | GeoPackage por UF (gitignored) — via `scripts/batch/ingest_ibge_bairros_uf.py` |

## Download oficial

FTP IBGE (exemplo CE):

`https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/gpkg/UF/`

Cobertura: ~17,5k bairros; **não** inclui TO/DF na malha típica.

## Git

Ignore `*.gpkg` / arquivos grandes. Mantém `fixtures/` + este README.
