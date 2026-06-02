# Golden Case: fortaleza_cidade_inteira_20260527

## Identificação
- **UUID:** `6fda525a-1dc4-4ce7-aa22-21e1a6fe1356`
- **ADK Run ID:** `rpt_1779840928`
- **Data Criação:** 2026-05-27T00:13:19.180457+00:00
- **Pipeline Version:** 1.5
- **Status:** done

## Input
- **Cidade:** Fortaleza
- **Bairro:** (cidade inteira)
- **UF:** CE
- **Área:** 250-400 m²
- **Público:** 25-40
- **Tipo Negócio:** academia
- **Tamanho Preset:** pp
- **Gênero Alvo:** misto

## Output Esperado (ground truth Supabase)
- **Veredito:** INVESTIGAR MAIS
- **Score Top1:** 5.33
- **Score Bairro:** 5.33
- **Modelo Recomendado:** Nenhum
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

- **Veredito negativo:** não existe `REPROVADO` no Supabase (jun/2026); este caso usa `INVESTIGAR MAIS` (score 5.33) como proxy.
- **Modo cidade inteira:** bairro `(cidade inteira)` — útil para eval de agregação municipal vs. raio.
- **Modelo Nenhum:** pipeline concluiu sem modelo recomendado claro — documentar no eval estrutural futuro.

## Aprovação
- [ ] Veredito correto
- [ ] Score dentro da faixa esperada
- [ ] Modelo recomendado faz sentido
- [ ] Campos críticos validados
- [ ] Notas do curador preenchidas
