# Golden Case: altamira_altamira_20260529

## Identificação
- **UUID:** `8aa99904-4681-4cbc-a7db-a2bf1d2298a9`
- **ADK Run ID:** `rpt_1780032397`
- **Data Criação:** 2026-05-29T05:02:11.863606+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Altamira
- **Bairro:** Altamira
- **UF:** PA
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO COM RESSALVAS
- **Score Top1:** 6.11
- **Score Bairro:** 6.11
- **Modelo Recomendado:** Low Cost
- **Saturação:** MEDIO
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 10

## Campos Críticos (devem bater exatamente)
- `veredito`
- `score_top1_candidato`
- `modelo_recomendado`
- `nivel_saturacao`

## Campos com Tolerância
- `score_top1_candidato`: ±50%
- `aluguel_mensal`: ±10%

## Notas do Curador
<!-- Preencha: por que este caso é ground truth -->


## Aprovação
- [ ] Veredito correto
- [ ] Score dentro da faixa esperada
- [ ] Modelo recomendado faz sentido
- [ ] Campos críticos validados
- [ ] Notas do curador preenchidas
