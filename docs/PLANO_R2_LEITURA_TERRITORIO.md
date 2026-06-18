# Plano de Implementacao — R2: Leitura do territorio (sintese do heatmap via Gemini)

> Status: proposta (aguardando validacao). ROI alto / esforco baixo.
> Origem: docs/PLANO_MAPAS_GEOSEEKER.md (iniciativa R2).

## 1. O que entrega (linguagem natural)

O mapa de mercado ja tem o heatmap (manchas de saturacao / transicao / oceano
azul), mas hoje **mostra sem explicar** — quem olha interpreta as cores sozinho.
R2 adiciona um **paragrafo curto, gerado pela IA, que traduz o mapa em
recomendacao de negocio**: "regiao X saturada no centro, faixa de transicao a
leste com baixa concorrencia e densidade crescente — vale investigar". Faz o
mapa "falar" para qualquer pessoa, em segundos.

## 2. Por que o esforco e baixo (o que JA existe)

- Cliente Gemini resiliente pronto: `tools/_genai_client.py` expoe
  `build_genai_client()` e
  `generate_content_resilient(client, *, model, contents, config=None,
  max_retries=3, base_delay=4.0)` (retry + backoff + resource-exhausted).
- Padrao de saida estruturada (JSON Schema) ja usado nos agentes a0..a9.
- Dados do heatmap ja existem no frontend: hook `useRelatoriosNoMapa` +
  `GoogleMapOceano` (pins, oceano, viewport, filtros cidade/veredito).
- Camada de mapas e endpoints `/api/maps/*` ja montados em `api.py`.

## 3. Gap atual

- O heatmap nao tem nenhuma sintese textual; nao ha endpoint que receba o
  recorte visivel (bbox/filtros/contagens por oceano) e devolva uma leitura.
- Nao ha componente de UI para exibir essa leitura ao lado do mapa.

## 4. Arquitetura proposta

Fluxo: Frontend (recorte atual do mapa) -> Backend (`/api/maps/territorio-read`)
-> Gemini (JSON estruturado) -> Frontend (card "Leitura do territorio").

### Backend
1. Novo endpoint `GET/POST /api/maps/territorio-read` em `api.py` que recebe um
   **resumo agregado** do recorte (nao dados crus): cidade, bbox/viewport,
   contagem por oceano (vermelho/transicao/azul), top bairros e vereditos.
2. Novo modulo `tools/territorio_read_tool.py`:
   - monta `contents` (prompt) a partir do resumo;
   - chama `generate_content_resilient` com `config` exigindo JSON:
     `{ titulo, leitura, recomendacao, confianca }`;
   - cache por hash do resumo (TTL curto, ex.: 1h) para nao repagar a mesma vista;
   - fallback estatico ("Leitura indisponivel no momento") em erro/timeout.
3. Modelo Gemini: `gemini-2.5-flash` (custo baixo; mesmo dos agentes leves).

### Frontend
4. Hook `useTerritorioRead({ cidade, bbox, counts })` que chama o endpoint
   (debounce ao mover/filtrar o mapa) — so dispara em interacao do usuario.
5. Componente `LeituraTerritorio` (card lateral/rodape do mapa em
   `MapaRelatoriosPage.tsx`) exibindo titulo + leitura + recomendacao + selo de
   confianca; com estados loading/erro.

## 5. Contrato de dados (saida do Gemini)

```
{
  "titulo": "string curta",
  "leitura": "2-4 frases lendo o territorio visivel",
  "recomendacao": "1 frase acionavel",
  "confianca": "alta | media | baixa"
}
```

Regras de prompt: usar SOMENTE o resumo fornecido; nao inventar bairros/numeros
fora do recorte; citar entidades por nome completo na 1a mencao.

## 6. Guard-rails de custo e qualidade

- Debounce + cache por recorte: evita 1 chamada por pixel de pan/zoom.
- So gera sob interacao (nao em background/polling).
- JSON Schema obriga formato; parse defensivo com fallback.
- Disclaimer fixo: "leitura assistida por IA sobre os dados do recorte".

## 7. Riscos e mitigacoes

- **Alucinacao**: restringir prompt ao resumo + schema; nao passar dados crus.
- **Latencia**: `flash` + cache; UI com skeleton.
- **Custo**: cache por hash do recorte + debounce; modelo barato.
- **Privacidade**: enviar agregados, nao listas de PII.

## 8. Definicao de pronto (DoD)

- [ ] `/api/maps/territorio-read` responde JSON valido para um recorte.
- [ ] `territorio_read_tool` com cache + fallback (sem excecao em erro).
- [ ] `LeituraTerritorio` renderiza no `MapaRelatoriosPage` com loading/erro.
- [ ] Debounce evita chamadas em excesso ao mover o mapa.
- [ ] Texto so referencia dados do recorte (validado em 2-3 cidades).

## 9. Estimativa

- Backend (endpoint + tool + cache): ~1 dia.
- Frontend (hook + card + estados): ~0,5 a 1 dia.
- Custo recorrente: baixo (flash + cache + debounce).

## 10. Dependencia com R1

Independentes. Podem rodar em paralelo. Sugestao de ordem: R1 primeiro
(impacto visual imediato no PDF do cliente), R2 em seguida.

---
_Chave Gemini / billing sao configurados manualmente no Google Cloud / AI
Studio — fora do escopo de automacao._
