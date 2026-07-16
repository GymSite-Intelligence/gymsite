# Auditoria de Tools — Processo Canônico

> Adotado jul/2026. Governança de **não conformidade em `tools/`** (custo API, fonte errada, fallback abusivo, tool mal composta).
> **Pai:** [`auditoria-conformidade.md`](auditoria-conformidade.md) (ciclo global). Este arquivo = trilho **Tools**.
> Complementa: [`pipeline-fontes-deterministicas.md`](pipeline-fontes-deterministicas.md) · [`conferencia-fontes-pipeline.md`](conferencia-fontes-pipeline.md) · P-000.
> Diagrama: [`auditoria-tools.mmd`](auditoria-tools.mmd).

## Quando abre uma auditoria

- Ledger (`relatorio_api_calls`) com SKU dual / custo anomalamente alto
- Tool viola SearchAPI-primário ou misturam jobs (POI ≠ listing ≠ aluguel)
- Mesmo sintoma em ≥2 relatórios
- Fix superficial falhou (ex.: “SearchAPI falhou” sem 5 Whys)
- Feedback produto: relatório lento / número sem carimbo / Places no caminho crítico

## Papéis

| Papel | Quem | Faz |
|---|---|---|
| **Author** | quem achou o sintoma (agente ou humano) | Draft: evidência + 5 Whys + `.mmd` |
| **Reviewer** | dono metodologia / pipeline | confere causa raiz vs regras de fonte; `request changes` ou avança |
| **Approver** | dono produto ou tech lead | approve → Act-on, ou reject |
| **Reviewer Lead** | default Marcelo se Reviewer não assigned | SLA Submitted |

## Estados e SLA

| Estado | SLA | Notificar se pending |
|---|---|---|
| **Draft** | 2 dias | Author se >1 dia |
| **Submitted** | 1 dia | Reviewer Lead se >1 dia |
| **Reviewed** | 3 dias | Approver se >2 dias |
| **Approved** | imediato | Author — pode Act-on / merge / Cloud Run |
| **Rejected** | imediato | Author — fecha com motivo |

Transições: ver `auditoria-tools.mmd`.

## Artefatos obrigatórios por estado

### Draft (Author)

1. Sintoma mensurável (ex.: relatório UUID + agregação `tool_name`/`api_sku`)
2. **5 Porquês** até causa raiz (não parar em “API falhou”)
3. Diagrama `.mmd` ao lado da tool ou em `docs/metodologia/`
4. Hipótese: tool mal composta? engine errado? fallback trata `[]` = erro?

### Submitted

- Pacote acima completo; Author marca pronto pra Reviewer
- Checklist pré-leitura: `pipeline-fontes-deterministicas` + `conferencia-fontes-pipeline`

### Reviewed (Reviewer)

- Concorda / discorda da causa raiz
- Mapeia ações: Act-on mínimo vs redesign
- Ou **request changes** → volta Draft

### Approved (Approver)

- Act-on: código + testes + (se `tools/`) Cloud Run API+worker
- Atualizar PIPELINE_AGENTES / data_lineage se fonte mudar
- Critério de Done: ledger ou teste prova que o sintoma sumiu

### Rejected

- Motivo escrito; opcional ticket “não agora”
- Não merge de “fix cosmético” que não ataca a raiz

## Encaixe com regras já existentes

```
sintoma (custo/fonte/latência)
    → Auditoria Tools (este processo)
        → 5 Whys + .mmd
        → Review vs conferencia-fontes / SearchAPI-primário
        → Approved = P-000 Act-on (código mínimo + teste + deploy)
```

Auditoria **não** substitui checklist pré-merge do pipeline — **precede** quando o merge já passou e produção / ledger prova regressão, ou quando o Author quer mudar a tool antes do PR.

## Caso — `buscar_imoveis_texto` (jul/2026)

| Campo | Valor |
|---|---|
| Estado | **Approved** (Act-on merged no código — aguarda deploy Cloud Run) |
| Sintoma | Cocó `c908…` · dual SKU SearchAPI+Places · ~R$2,53 em `buscar_imoveis_texto` |
| 5 Whys | [`tools/maps_tools_5whys_imoveis.mmd`](../../tools/maps_tools_5whys_imoveis.mmd) |
| Causa raiz | Tool misturou polo/POI + listing; Maps Local vazio ≠ outage; fallback Places em `[]` |
| Act-on feito | (1) Places só se SearchAPI `None` (2) A1 removeu queries listing — cascata já em `_fetch_listings_como_candidatos` (3) teste `empty_nao_fallback_places` |
| Done prod | dual SKU some no próximo relatório pós-Cloud Run |
