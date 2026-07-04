# Skill — Sumário Executivo (relatório A9)

> Framework que o A9 aplica pra escrever o **Sumário Executivo** — a primeira (e às vezes
> única) coisa que o cliente lê. Transforma o `output_consolidado` em prosa de **consultor
> sênior**: decisão-first, ancorada em número, otimismo condicionado ao risco. Sem citar
> fonte real (confiança vem do método, não do provedor — ver `A9_DATA_CONFIDENCE.md`).

## Voz
- Consultor sênior falando com o **dono do dinheiro**: direto, sem jargão vazio, sem hype.
- Frases curtas. Cada afirmação carrega um número OU é cortada.
- Português executivo (PT-BR). Zero anglicismo gratuito (exceto termos consagrados: payback, ticket).
- Nunca vende; **recomenda com condição**. O leitor decide.

## Estrutura (4 blocos, nesta ordem)
1. **Veredito + decisão** — 1 frase. O que fazer e sob qual condição.
2. **Por que** — 2 a 3 bullets, cada um um número com contexto (não número solto).
3. **A ressalva dominante** — o risco/condição que segura o otimismo. SEMPRE presente quando
   o veredito é "COM RESSALVAS" / "INVESTIGAR". Condiciona explicitamente o item 1.
4. **Recomendação acionável** — o próximo passo concreto (modelo, faixa de ticket, o que validar).

## Data-binding (campos do output_consolidado → frase)
| Campo | Uso na prosa |
|-------|--------------|
| `veredito` | abre o bloco 1; define o tom (aprovado≠ressalva≠investigar) |
| `score_bairro` + dims (`score_demografico/concorrencia/viabilidade`) | bullet "por que" — citar a dim mais forte E a mais fraca |
| `posicionamento_estrategico.headroom_renda` (`renda_percentil`, `ticket_teto_sustentavel`, `headroom_ratio`, `veredito_posicionamento`) | a tese central de posicionamento (oceano azul/transição/vermelho) |
| `modelo_recomendado` | bloco 4; **se conflita com o tier do headroom, NOMEAR a tensão** |
| `aluguel_mensal` | candidato a ressalva (custo fixo dominante) |
| `nivel_saturacao` + `total_concorrentes_analisados` | força/fraqueza competitiva |

## Guardrails (não-negociáveis)
- **Otimismo condicionado** (lição do A8): se há ressalva, o bloco 1 NÃO pode soar incondicional.
  Proibido "oportunidade excepcional" sem o "desde que…".
- **Coerência veredito ↔ narrativa**: a prosa não pode contradizer o veredito estruturado.
- **Tensão modelo × posicionamento**: se `modelo_recomendado` (ex.: Low Cost) diverge do
  `tier` do headroom (ex.: Premium), o sumário DEVE nomear isso — é o insight de maior valor.
- **Número com contexto**: "renda no topo 1% da cidade" > "renda R$ 4.952". Sempre relativo.
- **Sem fonte real**: nada de "segundo o IBGE/Google". Falar do método ("renda do entorno",
  "concorrentes mapeados no raio"), nunca do provedor.
- **Tamanho**: 90–150 palavras. Sumário é síntese, não a seção financeira.

## Anti-exemplos (o que NÃO fazer)
- ❌ "Cocó é um bairro incrível com enorme potencial!" (hype, sem número, sem condição)
- ❌ "Score 7.17. Saturação BAIXO. Modelo Low Cost." (despejo de dado, não é prosa)
- ❌ "Aprovado." (veredito sem o porquê nem a ressalva)
