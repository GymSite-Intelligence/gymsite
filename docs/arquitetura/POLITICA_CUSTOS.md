# Política de Custos e Orçamento

> Regras de cálculo, alertas de desvio e comportamento do sistema quando o custo real diverge do planejado.

---

## 1. Fonte do Custo Planejado

O custo planejado de cada tarefa pode vir de **3 fontes**, em ordem de prioridade:

### 1.1. Relatório de Viabilidade (A4 — FinancialEstimator)
**Prioridade:** 1 (mais confiável)

Quando o relatório A4 gera cenários financeiros, ele detalha:
- CAPEX total (equipamentos, obra, tecnologia)
- OPEX mensal (aluguel, folha, energia, marketing)
- Custos de entrada (franquia, legal, imobiliário)

O `playbook_generator.py` mapeia esses valores para tarefas específicas.

**Exemplo:**
```
Relatório A4:
  capex_equipamentos: R$ 450.000
  capex_obra: R$ 280.000
  capex_tecnologia: R$ 35.000
  entrada_franquia: R$ 80.000
  opex_aluguel_mes: R$ 12.000

Playbook:
  Tarefa "Comprar aparelhos de musculação" → R$ 280.000 (60% do capex_equip)
  Tarefa "Comprar equipamentos cardio" → R$ 120.000 (27%)
  Tarefa "Comprar acessórios" → R$ 50.000 (13%)
```

### 1.2. Benchmark Histórico
**Prioridade:** 2

Se o relatório não tem dados suficientes (ex: usuário pulou A4), o sistema usa média de projetos anteriores no mesmo estado/cidade.

```sql
SELECT AVG(custo_real) 
FROM tarefas 
WHERE categoria = 'EQUIPAMENTOS' 
  AND tipo_negocio = 'academia'
  AND uf = 'PB'
  AND deleted_at IS NULL;
```

### 1.3. Template Base (Fallback)
**Prioridade:** 3

Se não há relatório nem benchmark, usa valor default do template.

```python
TEMPLATE_DEFAULTS = {
    "EQUIPAMENTOS": {
        "academia": {"custo_planejado_default": 400000},
        "crossfit_box": {"custo_planejado_default": 120000},
        "studio_pilates": {"custo_planejado_default": 180000},
        "studio_funcional": {"custo_planejado_default": 80000},
    },
    # ... etc
}
```

---

## 2. Hierarquia de Orçamento

### 2.1. Níveis

```
ORÇAMENTO TOTAL DO PROJETO
├── Orçamento por Categoria (IMOB, LEGAL, OBRAS, EQUIP, TECN, RH, MARK, FIN, OPER)
│   ├── Orçamento por Tarefa
│   │   └── Custo Planejado (da tarefa)
│   │   └── Custo Real (informado pelo usuário ao concluir)
│   └── Soma das tarefas = Orçamento da categoria
└── Soma das categorias = Orçamento total
```

### 2.2. Regra de Consistência

A soma dos custos planejados das tarefas deve ser **igual ou muito próxima** do CAPEX total do relatório (se existir). Se houver divergência > 5%, o sistema alerta:

> "A soma dos custos planejados (R$ 1.150.000) difere do CAPEX do relatório (R$ 1.200.000) em R$ 50.000. Revisar tarefas de [categoria]."

---

## 3. Thresholds de Alerta de Desvio

### 3.1. Por Tarefa

| Desvio | Cor | Badge | Comportamento |
|--------|-----|-------|---------------|
| Até 10% acima | 🟡 Amarelo | "Levemente acima" | Visível no card. Sem alerta proativo. |
| 10% a 25% acima | 🟠 Laranja | "Acima do planejado" | Toast no momento do registro. Sugestão: "Revisar orçamento da categoria [X]." |
| Acima de 25% | 🔴 Vermelho | "Muito acima do planejado" | Modal de alerta. Sugestão da IA: "Quer que eu reavalie as demais tarefas desta categoria?" |
| Abaixo de -20% | 🔵 Azul | "Abaixo do planejado" | Apenas informativo. Pode ser economia real ou esquecimento de registrar item. |

### 3.2. Por Categoria

| Desvio Acumulado | Comportamento |
|-----------------|---------------|
| Até 15% acima | Badge na categoria. |
| 15% a 30% acima | Alerta no dashboard: "Categoria [X] está Y% acima do orçamento." |
| Acima de 30% | Alerta crítico + sugestão IA: "Com base no desvio, seu CAPEX total pode estourar em R$ Z. Quer ajustar?" |

### 3.3. Por Projeto (Total)

| Desvio Total | Comportamento |
|-------------|---------------|
| Até 10% acima | Considerado normal. Sem alerta. |
| 10% a 20% acima | Banner amarelo no topo: "Projeto X% acima do CAPEX planejado." |
| Acima de 20% | Banner vermelho + notificação: "Seu investimento total pode ultrapassar o previsto no relatório. Recomendamos revisão financeira." |

---

## 4. Registro de Custo Real

### 4.1. Quando registrar?

**Obrigatório:** Tarefas com `custo_planejado > R$ 10.000`
**Opcional:** Tarefas menores (usuário pode registrar, mas não é obrigado)

### 4.2. Como registrar?

Ao marcar tarefa como CONCLUIDA, o sistema pergunta:

```
🎉 Tarefa "Instalar piso vinílico" concluída!

Quanto você gastou de fato?
[ R$ ____________ ]

Se não souber exato, pode deixar em branco.
[ Salvar e continuar ]
```

### 4.3. Anexos de comprovante

Usuário pode anexar nota fiscal, recibo, contrato. O anexo é vinculado à tarefa e conta no storage do projeto.

---

## 5. Cálculos em Runtime

### 5.1. Fórmulas

```python
# Por tarefa
desvio_tarefa = ((custo_real - custo_planejado) / custo_planejado) * 100

# Por categoria
custo_planejado_categoria = sum(t.custo_planejado for t in tarefas if t.categoria == CAT)
custo_real_categoria = sum(t.custo_real for t in tarefas if t.categoria == CAT and t.status == 'CONCLUIDA')
desvio_categoria = ((custo_real_categoria - custo_planejado_categoria) / custo_planejado_categoria) * 100

# Por projeto
custo_planejado_total = sum(t.custo_planejado for t in todas_tarefas)
custo_real_total = sum(t.custo_real for t in todas_tarefas if t.status == 'CONCLUIDA')
desvio_total = ((custo_real_total - custo_planejado_total) / custo_planejado_total) * 100

# Progresso financeiro
progresso_financeiro = (custo_real_total / custo_planejado_total) * 100
# Nota: pode passar de 100% se houver desvio positivo
```

### 5.2. Cache

Cálculos pesados (soma de 200+ tarefas) são recalculados:
- **Síncrono:** ao concluir uma tarefa (atualiza na mesma transação)
- **Assíncrono:** a cada 5 minutos se houver múltiplas atualizações em lote
- **Frontend:** usa React Query com staleTime de 30s

---

## 6. Moeda e Precisão

| Aspecto | Regra |
|---------|-------|
| Moeda | BRL (Real Brasileiro) |
| Armazenamento | Centavos (integer no banco). Ex: R$ 1.250,00 = 125000 |
| Display | `R$ 1.250,00` (formatCurrency) |
| Arredondamento | 2 casas decimais no display. Nunca arredondar no cálculo antes do display. |
| Impostos | Não incluir impostos no custo planejado a menos que o relatório A4 já os incorpore. Custo real deve ser líquido (o que saiu da conta). |

---

## 7. Decisões

| Código | Decisão |
|--------|---------|
| **CST-001** | Custo planejado prioritariamente do relatório A4. Fallback: benchmark. Último recurso: template default. |
| **CST-002** | Desvio de até 10% é aceitável sem alerta. Mercado de construção e equipamentos tem variação natural. |
| **CST-003** | Custo real obrigatório apenas para tarefas > R$ 10.000. Evita micromanagement. |
| **CST-004** | Custo real pode ser informado depois da conclusão (até 7 dias). Se não informado, sistema usa custo planejado como proxy para cálculo de progresso, mas marca como "estimado". |
| **CST-005** | Anexos de comprovante são opcionais, mas incentivados (gamificação: "Projeto auditável" badge). |
| **CST-006** | Alertas de desvio não bloqueiam o usuário. São informativos e consultivos. |

---

## 8. Checklist

- [x] Definir 3 fontes de custo planejado (relatório, benchmark, template)
- [x] Definir hierarquia de orçamento (tarefa → categoria → total)
- [x] Definir thresholds de alerta (10% amarelo, 25% vermelho)
- [x] Definir quando custo real é obrigatório (> R$ 10.000)
- [x] Documentar fórmulas de cálculo
- [x] Definir moeda e precisão
- [x] Documentar decisões (CST-001 a CST-006)
