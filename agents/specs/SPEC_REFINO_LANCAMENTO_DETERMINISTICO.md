# SPEC — Refino determinístico da Janela de Entrada (lançamentos T+24)

> Criada 2026-07-07. Gatilho: auditoria Gemini leu unidades/plantas/PREÇOS reais dos
> lançamentos (Like = 88 unidades, não nossas 129 do proxy; BS Rubi R$ 2,2–3,8 mi)
> indo direto às páginas — nosso refino atual (refino_lancamento_tools) usa grounding
> LLM (Vertex), só nas top 5 POR ÁREA, e só sobrescreve o proxy com match cep+número.
> Resultado: quase tudo fica no proxy e o preço do imóvel nem é capturado.

## 1. Onde o script atual falha (diagnóstico no código)

1. `demanda_futura_detalhada(top_n=5)` ordena por ÁREA → obra pequena (Like) nunca é
   refinada; o proxy área÷75 inventa unidades.
2. Refino é grounding LLM (custo → top_n baixo; não-determinístico → gate rígido);
   o gate ALTA-confiança (cep+número) raramente bate → proxy vence quase sempre.
3. PREÇO do lançamento não existe no schema — e é o melhor preditor de aderência
   (BS Rubi R$ 2,2mi+ = morador com academia própria; Sensia R$ 417k = alvo Mid).

## 2. Desenho — camada determinística ANTES do grounding (receita da #9)

`tools/lancamento_fetcher.py`, mesmo esqueleto do agregadores_fetcher:

1. **Descoberta** (SearchAPI, cache disco, 1× por obra): `"<nome-lançamento>" <bairro>
   <cidade>` com `site:` nos alvos em ordem de prioridade: site da construtora
   (fonte primária), apto.vc, expoimovel, meusensia/mrv/vivamood (páginas de produto).
   Validação `_nome_casa` (anti-falso-positivo).
2. **Fetch httpx + parsers regex sobre texto** (páginas de lançamento são SSR/SEO
   por natureza — precisam ser indexáveis pra vender):
   - unidades: r"(\d{2,4})\s*(unidades|aptos|apartamentos|residências)"
   - plantas: r"(\d{2,3})\s*(?:m²|m2)\s*(?:a|à|e)\s*(\d{2,3})\s*m" → min/max
   - preço: r"R\$\s*([\d.,]+)(?:\s*(?:a|até)\s*R\$\s*([\d.,]+))?" com sanidade
     3×10⁵–10⁸ (imóvel, não mensalidade)
   - entrega: r"(entrega|previsão)[^.]{0,40}(20\d{2})"
   - amenidade fitness: keywords existentes (_AMENIDADE_FITNESS)
3. **Refina TODAS as obras residenciais** (não top 5) — httpx é barato; grounding LLM
   vira FALLBACK só pra quem a camada determinística não resolveu (inverte a ordem).
4. **Campos novos na obra**: `ticket_imovel {min, max, fonte, url}` +
   `unidades_fonte: "pagina_lancamento"` (badge `real` no PDF já existe).
5. **Aderência v2**: planta média continua a régua-base; `ticket_imovel` REBAIXA
   (≥ R$ 1,5 mi ⇒ BAIXA mesmo com planta média) e CONFIRMA (≤ R$ 600k ⇒ ALTA).
   Régua explícita na nota do PDF (regra do carimbo).
6. Rótulo por CAMPO, não por linha: unidades podem ser `real` e preço `proxy` —
   cada valor carrega sua fonte.

## 3. Aceitação (caso Cocó, contra a auditoria Gemini)

1. Like Residencial: 88 unidades com fonte pagina_lancamento (não 129 do proxy).
2. BS Rubi: ticket_imovel ≥ R$ 2,2 mi capturado → aderência BAIXA por preço.
3. Sensia: ~R$ 417k → ALTA confirmada por preço + planta.
4. Zero chamada LLM quando a página resolve; grounding só no resto (log conta quantos).
5. Segunda rodada do bairro: cache, zero busca nova.

## 4. Fora de escopo

Corretores/WhatsApp (lead C já tem fluxo próprio); portais com preço só via JS;
alterar a cadeia financeira (captura/receita) — só a QUALIDADE dos insumos.
