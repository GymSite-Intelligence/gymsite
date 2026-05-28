# PDF de relatório — GymSite Intelligence

## O que o produto pode entregar

| Capacidade | Print do browser (atual) | PDF Python (`pdf/`) |
|------------|--------------------------|---------------------|
| Layout fixo A4 | Depende do Chrome | Sim |
| Capa + veredito | Parcial (com sidebar) | Sim |
| Scores com gráfico de barras | Não | Sim |
| CAPEX empilhado (3 modelos) | Não | Sim |
| Lucro por cenário | Não | Sim |
| Tabelas candidatos / concorrentes | Sim | Sim, paginadas |
| Resumo + posicionamento (texto longo) | Sim | Sim, com quebra |
| Street View / mapas | Sim (se carregar) | Fase 2 (imagem URL) |
| Popular times heatmap | Sim | Fase 2 |
| Marca Vectra (header/footer) | Não | Sim (paleta navy/teal) |

## Três opções de modelagem (`layout`)

### 1. `classic` (padrão produto)

Relatório completo para decisor e operação comercial.

1. Capa (bairro, veredito, scores resumo)
2. Scores regionais + gráfico
3. Resumo executivo
4. Contexto de mercado (A0)
5. Top 3 candidatos (tabela + motivos)
6. Viabilidade 3 cenários (tabela + gráficos CAPEX e lucro)
7. Concorrentes (amostra até 12)
8. Posicionamento, bairros alternativos, alertas

**Quando usar:** entrega ao cliente, arquivo definitivo, impressão.

### 2. `executive`

2–4 páginas: capa, scores, resumo, financeiro mid, candidatos, alertas críticos.

**Quando usar:** e-mail para sócio, pré-reunião, WhatsApp.

### 3. `data_room`

Ênfase em tabelas e números (financeiro + concorrência + candidatos + mercado), menos narrativa.

**Quando usar:** due diligence, anexo a planilha, investidor.

## Stack implementada

| Camada | Tecnologia | Motivo |
|--------|------------|--------|
| Motor | **ReportLab** | Controle de páginas, tabelas, header/footer |
| Gráficos | **Matplotlib** (Agg) | Barras horizontais, CAPEX stacked, lucro |
| Dados | `pdf/adapters.py` | Payload `GET /api/relatorios/{id}` → `RelatorioPdfModel` |

### Alternativas (não implementadas ainda)

| Opção | Prós | Contras |
|-------|------|---------|
| **WeasyPrint** (HTML+CSS) | Parecido com o viewer web | Dependências Cairo no Docker |
| **Playwright PDF** | Pixel-perfect com React | Pesado, precisa Chromium no API |
| **Typst / LaTeX** | Tipografia premium | Curva de template |

Recomendação: manter **ReportLab** como fonte da verdade; opcionalmente HTML→PDF no futuro para parity visual com o frontend.

## API

```http
GET /api/relatorios/{id}/pdf?layout=classic
```

Resposta: `application/pdf` com `Content-Disposition: attachment`.

## CLI / teste local

```bash
pip install reportlab matplotlib
python tools/generate_pdf_sample.py
# → artifacts/gymsite-relatorio-sample.pdf
```

Com mock:

```bash
python tools/generate_pdf_sample.py --mock frontend/src/mocks/relatorios/rpt_1778468764.json
```

## Roadmap gráfico (fase 2)

- [ ] Mini heatmap popular times (matplotlib imshow)
- [ ] Thumbnail Street View (fetch + embed, respeitar quota Maps)
- [ ] Composição parque CNPJ (pizza por segmento)
- [ ] Série aberturas anual (barras por ano)
- [ ] QR code para link do viewer online

## Frontend

O botão **PDF** na listagem deve chamar a API (`VITE_API_BASE`) e baixar o blob — não mais `window.print()`.

Fallback: manter link “Imprimir página” no viewer para quem quiser preview rápido.
