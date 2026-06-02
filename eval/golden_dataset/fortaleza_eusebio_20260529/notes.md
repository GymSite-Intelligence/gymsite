# Golden Case: fortaleza_eusebio_20260529

## Identificação
- **UUID:** `02e42bad-2157-47f1-bdab-26d70c850f92`
- **ADK Run ID:** `rpt_1780081675`
- **Data Criação:** 2026-05-29T18:54:57.846629+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Fortaleza
- **Bairro:** Eusébio
- **UF:** CE
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO COM RESSALVAS
- **Score Top1:** 6.83
- **Score Bairro:** 6.83
- **Modelo Recomendado:** Mid Market
- **Saturação:** BAIXO
- **Candidatos (DB):** 0
- **Concorrentes (DB):** 8

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
