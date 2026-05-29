# Operação FipeZap — GymSite Intelligence

## O que é

Base de dados mensal do **Índice FipeZap** (residencial + comercial) armazenada no Supabase e consultada pelo A4 FinancialEstimator como **Tier 1.5** de precificação de aluguel.

| Tier | Fonte | Quando entra |
|---|---|---|
| 1 | Search Grounding (Gemini + web ao vivo) | Sempre que retorna dados |
| **1.5** | **FipeZap (dados oficiais mensais)** | **Quando Tier 1 falha** |
| 2 | Benchmark ACAD hardcoded | Fallback final |

---

## Frequência de atualização

- **Publicação FIPE:** mensal, entre o **dia 5 e 10** de cada mês
- **Link estável do Excel:** `https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx`
- **Processo recomendado:** executar o loader entre o dia 10 e 15 de cada mês

---

## Como atualizar (passo a passo)

### 1. Aplicar a migration (primeira vez apenas)

Abra o **SQL Editor** do Supabase Dashboard e execute o conteúdo de:

```
db/migrations/20260527_fipezap_indices.sql
```

Isso cria:
- Tabela `fipezap_indices`
- View `v_fipezap_ultimo` (lookup rápido pro A4)
- Índices e RLS

### 2. Baixar o Excel do FipeZap

Opção A — automática:
```powershell
python tools/fipezap_loader.py --download --dry-run
```

Opção B — manual:
1. Acesse https://www.fipe.org.br/pt-br/indices/fipezap/
2. Clique em "Clique aqui para fazer download da planilha em formato Excel"
3. Salve em `docs/fipezap-serieshistoricas.xlsx`

### 3. Carregar no banco

```powershell
python tools/fipezap_loader.py --file docs/fipezap-serieshistoricas.xlsx
```

Para validar antes de gravar:
```powershell
python tools/fipezap_loader.py --file docs/fipezap-serieshistoricas.xlsx --dry-run
```

Processamento típico:
- **~56 cidades**
- **~18.000 registros**
- **~2-3 minutos**

### 4. Verificar se o A4 está usando

Gere um relatório para uma cidade coberta (ex: São Paulo) e verifique o campo `fonte_aluguel` no output. Deve aparecer algo como:

```json
"fonte_aluguel": "FipeZap Comercial (2025-04-01)"
```

Se a cidade não tiver índice comercial direto (ex: Fortaleza), o A4 usa o residencial como proxy:

```json
"fonte_aluguel": "FipeZap Residencial proxy ×1.35 (2025-04-01)"
```

---

## Cobertura de cidades

### Comercial (salas/conjuntos até 200 m²)
São Paulo, Rio de Janeiro, Belo Horizonte, Porto Alegre, Curitiba, Florianópolis, Brasília, Salvador, Campinas, Niterói.

### Residencial (apartamentos prontos)
56 cidades, incluindo 22 capitais. Lista completa nas abas do Excel.

---

## Arquitetura

```
FipeZap site (Excel mensal)
    ↓
tools/fipezap_loader.py  (parse + upsert)
    ↓
Supabase — fipezap_indices
    ↓
tools/fipezap_tools.py   (lookup)
    ↓
tools/financial_tools.py (Tier 1.5 no A4)
```

---

## Agendamento automático (opcional)

### Windows Task Scheduler
```powershell
# Rodar dia 12 de cada mês às 09:00
schtasks /create /tn "GymSite_FipeZap_Update" `
  /tr "python C:\Users\marce\gymsite_intelligence\tools\fipezap_loader.py --download" `
  /sc monthly /d 12 /st 09:00
```

### Linux/Mac crontab
```bash
# Dia 12, 09:00
0 9 12 * * cd /home/marce/gymsite_intelligence && python tools/fipezap_loader.py --download >> /var/log/fipezap.log 2>&1
```

---

## Troubleshooting

| Problema | Causa provável | Solução |
|---|---|---|
| "Tabela não encontrada" | Migration não aplicada | Rodar SQL no Supabase Dashboard |
| "Nenhum registro extraído" | Mudança no layout do Excel | Verificar se COL_MAPPING no loader ainda bate com as colunas |
| Encoding estranho nos nomes | Console Windows | Os dados internos estão corretos; é só exibição |
| Download retorna 403 | Cloudflare bloqueou | Baixar manualmente pelo navegador |

---

## Comparação: benchmarks antigos vs FipeZap real (jan/2025)

| Cidade | Benchmark projeto | FipeZap comercial | Diferença |
|---|---|---|---|
| São Paulo | R$ 85/m² | R$ 54,86/m² | -35% |
| Rio de Janeiro | R$ 75/m² | R$ 45,17/m² | -40% |
| Curitiba | R$ 55/m² | R$ 37,28/m² | -32% |
| Brasília | R$ 65/m² | R$ 35,56/m² | -45% |
| Fortaleza | R$ 35/m² | R$ ~29/m² (proxy res) | -17% |

> **Impacto:** o Tier 2 (hardcoded) estava inflacionando alugueis em 30-45%. Com o FipeZap como Tier 1.5, o A4 agora ancora em dados reis de mercado antes de cair no fallback.
