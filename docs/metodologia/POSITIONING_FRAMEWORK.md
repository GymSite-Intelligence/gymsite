# Framework de Posicionamento GymSite — A9 PositioningStrategist

## Visão Geral

O **A9 PositioningStrategist** é um agente especializado do pipeline GymSite Intelligence que consome TODOS os outputs produzidos pelos agents A0–A6 e gera um **relatório estratégico de posicionamento** baseado no **Framework ERRC** (Eliminar, Reduzir, Aumentar, Criar).

Diferente dos agents anteriores que focam em **coleta de dados** (demografia, concorrência, financeiro), o A9 foca em **síntese estratégica**: transformar dados brutos em recomendações acionáveis de como a academia deve se posicionar no mercado.

---

## Onde o A9 se encaixa no pipeline

```
A0 (ContextBuilder)  →  A1 (GeoScout)  →  A2-A4 (Análise Paralela)
                                                          │
                                                          ▼
A5 (ContactHunter)  →  A6 (ReportConsolidator)  →  A9 (PositioningStrategist)
                                                          │
                                                          ▼
                                              relatorio_posicionamento (JSON + MD)
```

O A9 é o **último passo do pipeline** — ele recebe o "estado completo" do mercado e emite um veredito estratégico.

---

## Framework ERRC — O Modelo de Análise

O ERRC é uma matriz de 4 dimenses que orienta a academia a escapar do **oceano vermelho** (guerra de preços, competição genérica) e nadar no **oceano azul** (diferenciação real, sem concorrência direta).

### ELIMINAR — O que NÃO fazer

| Item | Por que eliminar | Impacto esperado |
|---|---|---|
| Competir por preço com low-cost (Smart Fit @ R$79) | Margem irrisória (10-15%), churn alto, dependência de volume massivo | Aumento de 200-300% na margem |
| Planos genéricos "tamanho único" | Não atende nenhum público bem, não justifica ticket premium | Diferenciação por segmento |
| Serviços que todos os concorrentes já oferecem | Zero vantagem competitiva, commodity | Foco em exclusividade |
| Marketing de "mais barato que a concorrência" | Corrida ao fundo, destrói marca | Posicionamento por valor |

### REDUZIR — O que tornar menor/enxuto

| Item | Padrão do mercado | O que reduzir para |
|---|---|---|
| Capacidade máxima | 500+ alunos (modelo low-cost) | 150-250 alunos (ocupação inteligente) |
| Dependência de comissão | 100% da motivação do vendedor | Mix: comissão + cultura + propósito |
| Complexidade operacional | 15+ funcionários, alta rotatividade | 5-8 funcionários multiskilled |
| CAC (Custo de Aquisição de Cliente) | R$ 200-400 (tráfego pago genérico) | R$ 80-150 (indicação + comunidade) |

### AUMENTAR — O que tornar superior

| Item | Padrão do mercado | O que aumentar para |
|---|---|---|
| Percepção de exclusividade | "Mais uma academia no bairro" | "A ÚNICA academia que oferece X" |
| Atendimento personalizado | Professor genérico, rotatividade alta | Professor fixo, acompanhamento 1:1 |
| Experiência do aluno (NPS) | NPS 20-40 (indústria fitness) | NPS 60-80 (benchmark premium) |
| Margem de lucro por aluno | R$ 15-25/aluno (low-cost) | R$ 80-150/aluno (premium) |

### CRIAR — O que NINGUÉM oferece ainda

| Inovação | Descrição | Potencial de ticket |
|---|---|---|
| **Ecossistema Wellness** | Treino + Nutrição + Recovery no mesmo plano | R$ 250-400 |
| **Silver Fitness (50+)** | Programas para idosos além de hidro genérica | R$ 200-300 |
| **Comunidade Fitness** | Eventos, desafios, grupos de afinidade, pertencimento | R$ 200-280 |
| **Tecnologia Real** | Personalização por IA, wearables, HRV, monitoramento | R$ 300-450 |
| **Integração Local** | Beach sports, outdoor, preparação para eventos | R$ 250-350 |

---

## Mapeamento de Serviços — Os 16 Serviços Obrigatórios

O A9 mapeia a oferta de cada concorrente em **16 serviços** e calcula a penetração (0-10) de cada um. Serviços com penetração < 3 em TODOS os concorrentes são classificados como **GAPs**.

```
┌─────────────────────────────┬────────┬────────┬────────┬────────┐
│ Serviço                     │Conc. A │Conc. B │Conc. C │  GAP?  │
├─────────────────────────────┼────────┼────────┼────────┼────────┤
│ Musculação                  │   10   │   10   │    9   │   ❌   │
│ Treino Funcional/HIIT       │    8   │    6   │    5   │   ❌   │
│ Aulas de Dança              │    7   │    5   │    4   │   ❌   │
│ Spinning                    │    8   │    7   │    5   │   ❌   │
│ Artes Marciais              │    6   │    4   │    3   │   ❌   │
│ Yoga/Pilates                │    5   │    6   │    2   │   ❌   │
│ Crossfit/Cross Training     │    6   │    5   │    3   │   ❌   │
│ Natação/Hidroginástica      │    4   │    3   │    1   │   ⚠️   │
│ Nutrição (consultoria)      │    2   │    1   │    0   │   ✅   │ ← GAP
│ Avaliação Física (PAR-Q)    │    5   │    4   │    2   │   ❌   │
│ App/Monitoramento Digital   │    3   │    4   │    2   │   ⚠️   │
│ Aulas Personalizadas (PT)   │    4   │    3   │    2   │   ⚠️   │
│ Recovery/Fisioterapia       │    1   │    0   │    0   │   ✅   │ ← GAP
│ Comunidade/Eventos          │    2   │    1   │    1   │   ✅   │ ← GAP
│ Aulas para Idosos (50+)     │    1   │    2   │    0   │   ✅   │ ← GAP
│ Beach Tennis/Esportes Praia │    0   │    1   │    0   │   ✅   │ ← GAP
└─────────────────────────────┴────────┴────────┴────────┴────────┘

Legenda: ✅ = GAP (penetração < 3 em todos) | ⚠️ = Quase GAP | ❌ = Saturado
```

---

## Veredito de Posicionamento

O A9 classifica cada análise em um de três vereditos:

### 🟢 OCEANO AZUL
**Condições:** Renda alta do bairro + baixa concorrência de premium + 3+ GAPs identificados + break-even viável com < 200 alunos.

**Recomendação:** Abrir como boutique/nicho. Ticket R$ 200-400. Capacidade 150-250 alunos. Foco em 1-2 GAPs principais.

**Exemplos:** Eusébio (CE) — renda per capita maior do estado, Smart Fit ainda chegando, zero oferta premium.

### 🟡 TRANSICAO
**Condições:** Renda média-alta + concorrência moderada + 1-2 GAPs + break-even viável com 200-350 alunos.

**Recomendação:** Diferenciar por serviço, não por preço. Ticket R$ 150-220. Capacidade 250-400 alunos. Foco em conveniência e experiência.

**Exemplos:** Aldeota (Fortaleza) — Top Up e Gaviões presentes, mas oferta genérica.

### 🔴 VERMELHO
**Condições:** Renda baixa + alta densidade de low-cost + 0-1 GAPs + break-even exige > 400 alunos.

**Recomendação:** NÃO abrir aqui. Ou, se abrir, usar modelo de volume com margem < 20% e aceitar alta competição.

**Exemplos:** Bairros com 3+ Smart Fit e renda média < 2 salários mínimos.

---

## Estrutura de Output (JSON Canônico)

```json
{
  "framework_errc": {
    "eliminar": ["item 1", "item 2", "item 3", "item 4"],
    "reduzir": ["item 1", "item 2", "item 3", "item 4"],
    "aumentar": ["item 1", "item 2", "item 3", "item 4"],
    "criar": ["item 1", "item 2", "item 3", "item 4"]
  },
  "mapa_servicos": [
    {
      "concorrente": "Nome da Academia",
      "servicos": {
        "musculacao": 9,
        "treino_funcional": 6,
        "aulas_danca": 5,
        "spinning": 4,
        "artes_marciais": 3,
        "yoga_pilates": 2,
        "crossfit": 3,
        "natacao_hidro": 1,
        "nutricao": 0,
        "avaliacao_fisica": 4,
        "app_digital": 2,
        "aulas_personalizadas": 2,
        "recovery": 0,
        "comunidade_eventos": 1,
        "aulas_idosos": 0,
        "beach_tennis": 0
      }
    }
  ],
  "gaps_identificados": [
    {
      "gap": "Nutrição integrada + recovery",
      "descricao": "Nenhum concorrente oferece ecossistema wellness completo",
      "potencial_ticket": "R$ 250–350",
      "dificuldade_implementacao": "Média"
    }
  ],
  "recomendacao_ticket": {
    "ticket_recomendado": 249,
    "ticket_minimo": 199,
    "ticket_maximo": 299,
    "justificativa": "Baseado na renda média do bairro (R$ X), ausência de oferta premium, e cenário de break-even",
    "comparativo_mercado": {
      "smart_fit": 79,
      "selfit": 99,
      "top_up": 149,
      "gavioes": 169,
      "recomendado": 249
    }
  },
  "veredito_posicionamento": "OCEANO_AZUL",
  "justificativa_veredito": "O bairro tem renda alta, crescimento populacional acelerado, e zero oferta de serviços premium.",
  "markdown": "# Relatório de Posicionamento Estratégico\n\n..."
}
```

---

## Como usar o A9 no projeto

### 1. Copiar o arquivo para o projeto

```bash
cp agents/a9_positioning_strategist.py /caminho/do/projeto/agents/
```

### 2. Aplicar o patch no agent.py

Siga as instruções em `agent_py_patch.md` para modificar `gymsite_intelligence/agent.py`.

### 3. Executar o pipeline completo

O A9 é executado automaticamente como último passo do pipeline. Não requer ação manual — ele consome o state produzido por A0-A6.

### 4. Acessar o output

```python
# Após execução do pipeline
posicionamento = state["relatorio_posicionamento"]

# Acessar componentes específicos
errc = posicionamento["framework_errc"]
gaps = posicionamento["gaps_identificados"]
ticket = posicionamento["recomendacao_ticket"]["ticket_recomendado"]
veredito = posicionamento["veredito_posicionamento"]
markdown = posicionamento["markdown"]

# Ou acessar o markdown diretamente
markdown = state["relatorio_posicionamento_md"]
```

---

## Integração com o frontend

O output do A9 pode ser consumido pelo frontend do GymSite para renderizar:

- **Dashboard de Posicionamento** com as 4 dimensões do ERRC
- **Mapa de Serviços** visual (radar ou heatmap) mostrando penetração por concorrente
- **Cards de GAPs** destacando as 5 oportunidades principais
- **Comparativo de Preços** mostrando onde o ticket recomendado se posiciona vs concorrência
- **Badge de Veredito** (Oceano Azul / Transição / Vermelho) com cor correspondente

---

## Próximos passos (roadmap A9)

1. **v1.0** (atual) — Análise estática baseada nos dados do pipeline A0-A6
2. **v1.1** — Integração com dados históricos (tendência de preços ao longo do tempo)
3. **v1.2** — Recomendação automática de modelo de negócio (boutique vs nicho vs premium)
4. **v1.3** — Simulação "what-if" ("e se eu cobrasse R$ 300 em vez de R$ 250?")
5. **v1.4** — Benchmark entre múltiplos bairros (comparativo lado a lado)
