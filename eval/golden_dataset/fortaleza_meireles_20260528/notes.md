# Golden Case: fortaleza_meireles_20260528

## Identificação
- **UUID:** `cccb77b5-58e4-405a-9c07-b81deaafb315`
- **ADK Run ID:** `rpt_1779994017`
- **Data Criação:** 2026-05-28T18:34:12.961156+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Fortaleza
- **Bairro:** Meireles
- **UF:** CE
- **Área:** 800-1500 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** m
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** APROVADO
- **Score Top1:** 8.17
- **Score Bairro:** 8.17
- **Modelo Recomendado:** Mid Market
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
