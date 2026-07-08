# Guia de prompts do pipeline — princípios destilados e APLICADOS

> Destilado em 2026-07-06 do `Guia de Engenharia de Prompt Eficaz.pdf` (mesma pasta).
> Regra de leitura: princípio genérico só vale aqui se vier com o exemplo NOSSO
> (A3b/A6/A9, consultores da landing, curador RAG). O PDF fica como fonte; este .md
> é o que se consulta ao escrever/revisar prompt no GymSite.

## Regra ZERO (da casa — acima do guia)

**Número, score e veredito NUNCA vêm do LLM.** O LLM narra, classifica texto e organiza;
quem calcula é tool determinística (`parametros_metodologia` + código). O guia não cobre
isso porque é decisão nossa de produto — e é a que mais protege o relatório.
Evidência: resumo executivo do A6 é montado determinístico e SOBRESCREVE o do LLM
(que narrava densidade errada); gaps do ERRC idem (`_gaps_reais` sobrepõe o chute).

## Os 4 pilares, com exemplo nosso

| Pilar | Ruim (real, já nos mordeu) | Bom (como fazemos/devemos fazer) |
|---|---|---|
| Clareza | "analise os concorrentes" | "classifique CADA review em UMA categoria do catálogo `dores`; sem categoria nova" |
| Contexto | prompt sem o state → LLM inventa concorrente | injetar o bloco do state delimitado + "responda APENAS com base no bloco acima" |
| Formato | "retorne um JSON" → vinha com fence ```json (A3b, bug real — `_parse_state_intel` teve que aprender a limpar) | "retorne SOMENTE o objeto JSON, sem markdown, sem fence, começando por `{`" |
| Restrições | "não invente dados" (negativa aberta — o guia mostra que é fraca) | "cada afirmação deve citar o campo de origem do bloco; afirmação sem campo = omitir" |

## Específico do Gemini (nosso pipeline A0–A9 roda Gemini)

1. **Contexto grande PRIMEIRO, instrução na ÚLTIMA linha.** Com state gigante (33k+
   tokens de histórico que já medimos no DemoAnalyst), a tarefa e as restrições vão no
   FIM do prompt — senão o modelo perde a instrução no meio do material. Revisar os
   macro-prompts do A3b/A6 com essa lente.
2. **Temperatura 1.0 (default) em tarefa de raciocínio.** Não "baixar pra ficar
   determinístico" — abaixo de 1.0 o Gemini degrada e repete tokens. Determinismo aqui
   vem das TOOLS, não da temperatura.
3. **Direcionamento positivo > proibição genérica.** "Use somente os campos do bloco
   <dados>" funciona; "não faça suposições" não.

## Abstenção RAG (consultores da landing + curador)

Todo prompt que consulta o Vertex AI Search (agente de Mercado, Técnico, etc.) leva a
permissão de abstenção explícita: **"se a informação não está no material recuperado,
responda que não está disponível — não complete com conhecimento geral"**. É a defesa
nº 1 contra alucinação factual na degustação pública (e proteção reputacional: o
visitante está nos testando).

## Modelos deliberativos (Claude headless da narração / futuros)

- NÃO incluir "pense passo a passo" nem few-shot extenso — em modelo com raciocínio
  nativo isso DEGRADA (paradoxo documentado no guia).
- Onde pagamos token de pensamento (narração fluente do resumo), vale o padrão
  Chain-of-Draft: instruir rascunho interno curto ("etapas de no máximo 5 palavras") —
  mesma acurácia, fração do custo/latência.
- Claude: delimitar dados com tags XML (`<dados>...</dados>`) — é o formato que a
  família foi treinada pra respeitar.

## O pipeline JÁ usa as técnicas avançadas do guia (nomear pra não desmontar)

- **Prompt chaining** = o próprio A0→A9 (cada agente recebe SÓ o state que precisa).
- **Validação adversária** = A8 Validator (critica o trabalho dos outros antes de fechar)
  + a trinca de auditores externos (OndeAbrir/Gemini/nós) no nível de produto.
- **Template universal** (`# IDENTIDADE / # CONTEXTO / # TAREFA / # REGRAS / # FORMATO`)
  = padrão da casa para toda persona nova — exemplo vivo: `curador_rag_mercado.md`.

## Checklist de revisão de prompt (colar no PR que mexer em prompt)

- [ ] Instrução/restrições na última seção (Gemini) ou tags XML (Claude)?
- [ ] Formato de saída à prova de fence (`somente o objeto JSON, começando por {`)?
- [ ] Restrições positivas (o que FAZER com o dado) em vez de negativas abertas?
- [ ] Abstenção explícita se consulta RAG/material delimitado?
- [ ] Nenhum número/veredito pedido ao LLM que uma tool deveria calcular?
- [ ] Categoria interna (snake_case) proibida na saída voltada a cliente?
