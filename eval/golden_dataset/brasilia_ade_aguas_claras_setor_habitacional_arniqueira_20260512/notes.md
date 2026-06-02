# Golden Case: brasilia_ade_aguas_claras_setor_habitacional_arniqueira_20260512

## Identificação
- **UUID:** `21bd2ccb-4536-4c09-b2a7-a5e6cd831b99`
- **ADK Run ID:** `rpt_1778544751`
- **Data Criação:** 2026-05-12T00:09:01.094461+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Brasília
- **Bairro:** ADE Águas Claras - Setor Habitacional Arniqueira
- **UF:** 
- **Área:** 1000-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO
- **Score Top1:** 8.83
- **Score Bairro:** 8.83
- **Modelo Recomendado:** Low Cost
- **Saturação:** BAIXO
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 0

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
