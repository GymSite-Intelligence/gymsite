# Preview para aprovação (canônico)

> Adotada 2026-08-06 · reforço PDF 2026-08-07. **Toda** mudança que o humano vê **ou** que define um gate de produto (PDF, UI, saída de gate CLI) exige **preview** antes de pedir “ok / merge / commit”.

## Gate

Não pedir aprovação de Wave/PR sem:

1. Gerar artefato de preview no repo
2. **Abrir o preview no browser** (default do SO ou aba visível) — Marcelo aprova olhando, não lendo path no chat
3. Caminho explícito na mensagem
4. Antes/depois curto quando for mudança de rótulo/copy

Sem preview aberto → entrega incompleta (mesmo com testes verdes).

## PDF / relatório (obrigatório)

Mudança em `pdf/html_builder.py`, template Jinja, WeasyPrint ou seção do relatório:

| Exigência | Regra |
|---|---|
| Fonte do HTML | **`gerar_html(RelatorioPdfModel(...))`** — mesmo pipeline do PDF de produção |
| Proibido | Stub “micro tabela” / mock solto que **não** passa pelo builder |
| Conteúdo | Seções relevantes **no layout do relatório** (capa/contexto + demografia + seção nova + vizinhas se o fluxo mudar) |
| Objetivo | Marcelo aprova a **versão final do PDF** (como o cliente vê), não um rascunho isolado |
| Abrir | Sempre `Start-Process` / browser no arquivo gerado ao fechar a wave |
| Copy | Ver também `leitura-executiva-pdf.md` — prosa por tópico, sem jargão `pool`/`pen.` |

Arquivo: `docs/superpowers/previews/YYYY-MM-DD-<tema>.html` = dump do `gerar_html` (ou export Weasy→HTML equivalente).

## Onde guardar

| Tipo | Pasta / padrão |
|---|---|
| PDF / Jinja | `docs/superpowers/previews/YYYY-MM-DD-<tema>.html` via **`gerar_html`** |
| UI / tela | screenshot em `docs/superpowers/previews/` **ou** HTML isolado do componente |
| Gate / ops (sem UI) | HTML com saída do comando (FAIL atual + OK esperado) |
| Spec / design | link do preview na spec ou no plano (Wave) |

Nome: data + tema curto. Ex.: `2026-08-07-absorcao-w2a.html`.

## Quando aplica

- Waves que mexem em `pdf/html_builder.py`, templates Jinja, WeasyPrint
- Front: cards, labels, carimbos, demografia, mercado
- Qualquer copy visível ao usuário final no relatório
- **Ops / gates sem UI:** preview da saída do comando (pass/fail) — ex. CUB gate

## Quando NÃO exige preview

- Só docs/runbook **sem** mudar comportamento executável
- Só teste unitário sem UI/PDF **e** sem novo gate CLI de produto

## Relação com outras regras

| Regra | Papel |
|---|---|
| `spec-self-review.md` | Spec completa + `## Self-review` |
| **este arquivo** | Preview **depois** da implementação · **abrir** · **antes** do ok humano |
| P-000 § evidência visual front | Continua válido; este rule generaliza pra PDF + gates |

## Checklist do agente

1. Implementar mudança
2. Gerar preview:
   - **PDF** → `gerar_html(...)` → gravar em `docs/superpowers/previews/`
   - UI → screenshot / HTML do componente
   - Gate/ops → HTML com saída do comando
3. **Abrir o arquivo no browser**
4. Na resposta: path + 2–3 linhas do que mudou
5. Só então perguntar aprovação / commit
