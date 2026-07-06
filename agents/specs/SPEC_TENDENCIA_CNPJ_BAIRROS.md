# SPEC — Tendência CNPJ por Bairro (determinística, 3 anos)

> Criada 2026-07-05. Gancho competitivo: OndeAbrir mostra "378 aberturas / 242 fechamentos
> nos últimos anos" — sem janela definida, sem bairro, sem auditabilidade (ver
> `docs/produto/CONCORRENTE_ONDEABRIR.md`). Nós entregamos o mesmo insight com fonte
> determinística (RFB), janela explícita, quebra POR BAIRRO com score e red flag.

## 1. O que o usuário vê (linguagem de domínio)

No relatório (e teaser no mini):

- **Série 3 anos fechados + ano corrente**: aberturas × fechamentos × saldo de academias
  (CNAE 9313-1/00) na cidade, ano a ano — "2023: +29 / −39 (−10)".
- **Quadro comparativo por bairro** (top N bairros com movimento): aberturas, fechamentos,
  saldo no triênio, score da categoria no bairro.
- **Red flag automática**: o bairro com pior score e saldo negativo ganha selo
  "⚠️ bairro em retração — X fechamentos para Y aberturas desde AAAA".
- Rodapé de auditoria: "Fonte: CNPJ Aberto RFB, referência AAAA-MM, CNAE 9313-1/00,
  janela 01/AAAA–hoje" — reproduzível, ao contrário do "últimos anos" da concorrência.

## 2. Fonte e mudanças técnicas

Base: `tools/rfb_cnpj_fitness_loader.py` já extrai por estabelecimento: `bairro`,
`data_inicio_atividade`, `situacao_cadastral`, `data_situacao` (data da baixa), município.

1. **Loader (mudança obrigatória):** hoje filtra `situacao not in SITUACAO_ATIVA` e joga
   fora os baixados — sem eles não há série de fechamentos. Passar a persistir TAMBÉM
   situação 08 (baixada), com `data_situacao` como data do fechamento. Flag de coluna
   `situacao_cadastral` já existe no schema do loader; volume estimado ~2× o atual do CNAE.
2. **Agregação (nova, determinística — sem LLM):** módulo `tools/cnpj_tendencia.py`:
   - `serie_anual(cidade, uf, anos=3)` → [{ano, aberturas, fechamentos, saldo}] usando
     `data_inicio_atividade` (abertura) e `data_situacao` quando situação=08 (fechamento).
   - `quadro_bairros(cidade, uf, anos=3)` → por bairro normalizado: aberturas, fechamentos,
     saldo, ativos_hoje.
   - Normalização de bairro: campo RFB é texto livre → upper/trim/sem acento + tabela de
     sinônimos por cidade (reusar a normalização que o A0/geo já aplica; divergências não
     mapeadas caem em "OUTROS", nunca somem).
3. **Score da categoria por bairro:** reusar o score de bairro do motor quando o bairro já
   foi analisado (cache em `relatorio_outputs`/market store); para bairros sem análise,
   score proxy determinístico = f(saldo triênio, ativos/10k hab, renda do bairro) — fórmula
   fixa em `parametros_metodologia` (P-008: parâmetro no banco, não hardcode).
4. **Persistência:** nova coluna `relatorio_outputs.tendencia_cnpj_bairros jsonb`
   (migration própria, aditiva). Shape:
   `{ref_rfb, janela, serie_anual[], bairros[{bairro, aberturas, fechamentos, saldo, score, red_flag}], red_flag_bairro}`.
5. **Exibição:** A6 inclui bloco no markdown do relatório; `status_analise` expõe no
   `extras` o teaser: `tendencia: {saldo_3anos, red_flag_bairro_motivo}` (nome do bairro
   red-flag ABERTO — é dado público e gera "uau"; o quadro completo fica no pago).

## 3. Regras duras

- Zero número via LLM: agregação é SQL/pandas puro sobre o espelho RFB (auditável).
- Janela sempre explícita na saída (nunca "últimos anos").
- Fechamento = situação 08 com `data_situacao` na janela; situação 02 ativa; 03/04
  (suspensa/inapta) contam em métrica separada `zumbis`, não como fechamento.
- Red flag exige AMBOS: pior score E saldo negativo (evita difamar bairro pequeno com
  1 fechamento).
- MEI: o CNPJ Aberto cobre MEI com estabelecimento; documentar no rodapé que MEI sem
  estabelecimento declarado fica fora (a concorrência mistura sem avisar).

## 4. Aceitação

1. Fortaleza/CE retorna série 2023–2025+YTD com totais batendo com query manual no espelho.
2. Cocó aparece no quadro com os mesmos estabelecimentos do parque ativo já usado pelo A0.
3. Bairro red-flag muda quando a fórmula de score muda em `parametros_metodologia` (sem deploy).
4. Relatório antigo (sem a coluna) continua renderizando — campo ausente = bloco omitido.

## 5. Fora de escopo (registrar, não fazer agora)

- Comparação intermunicipal (ranking de cidades — é o "panorama" do OndeAbrir; fase 2).
- Projeção/tendência futura (já existe `demanda_futura` separada; não misturar).
