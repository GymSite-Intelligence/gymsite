# Add-on — Raio-X de Marketing dos Concorrentes (Instagram Competitive Intelligence)

> **Produto de enriquecimento por crédito**, FORA do pipeline base do relatório.
> Encaixa no `MODELO_NEGOCIO.md` como add-on da Fase 2 (créditos / pay-per-use):
> o usuário compra "1 crédito" e recebe um raio-X de como os concorrentes do bairro
> usam o Instagram — para **não reinventar a roda** no próprio marketing.

## 1. Por que existe (a dor)

O relatório base diz QUEM são os concorrentes e o que cobram. Não diz **como eles
vencem no digital**. O dono de academia novo não sabe: que formato posta? com que
frequência? o que engaja na praça? Hoje ele chuta — copia genérico do "guru do
Instagram". Este add-on entrega o que **comprovadamente funciona NO BAIRRO dele**,
medido nos concorrentes reais.

## 2. Fonte de dados (validada)

SearchAPI `engine=instagram_profile` (já é infra do projeto — `tools/instagram_profile.py`).
Por concorrente, retorna (smoke real, academiamaxforma, latência ~2s):
- **Perfil:** followers, following, posts (total), bio, is_business, link externo.
- **Posts (12 recentes):** `caption`, `likes`, `comments`, `type` (foto/vídeo/carrossel),
  `iso_date`, `location`, hashtags (na caption), permalink.

Custo: ~1 chamada/concorrente × ~10 = **~$0,05-0,10 por add-on**. Margem altíssima.
Latência: paralelo (`gather`) ~5s — roda **on-demand**, não trava o pipeline.

## 3. O que o add-on analisa (5 dimensões)

| Dimensão | Como mede | Saída pro usuário |
|----------|-----------|-------------------|
| **Modelo de conteúdo** | distribuição de `type` (reels/carrossel/foto) por concorrente | "Na praça, 60% reels — quem só posta foto fica pra trás" |
| **Cadência** | frequência via `iso_date` (posts/semana) | "Líder posta 5×/semana; mediana do bairro 2×" |
| **Engajamento por formato** | (likes+comments)/followers por `type` | "Carrossel engaja 3× mais que foto aqui" |
| **Temas que engajam** | hashtags + palavras-chave da `caption` dos top-posts | "Top posts: desafio 30 dias, antes/depois, aluno destaque" |
| **Presença digital (score)** | índice composto → ranking | "Concorrente X domina (score 82); 3 estão parados (brecha)" |

### Score de presença digital (determinístico, auditável)
```
score_digital = w1·log(followers) + w2·taxa_engajamento + w3·cadencia + w4·consistencia
```
Pesos via `param()` (recalibráveis). Cruzado entre TODOS os concorrentes → ranking +
percentil. Sem LLM inventando — número derivado dos posts reais.

## 4. Entregável "não reinvente a roda" (o playbook)

Saída final = **playbook de marketing da praça**, ex.:
> **O que funciona no Cocó (medido em 8 concorrentes):**
> - Formato campeão: **Reels** (engaja 4× mais que foto). Max Forma (94k) posta 60% reels.
> - Cadência mínima pra competir: **3-4 posts/semana** (abaixo disso, invisível).
> - Temas que mais engajam: desafios, antes/depois, bastidores de treino.
> - **Brecha:** nenhum concorrente forte faz conteúdo de **nutrição/recovery** — seu
>   diferencial de serviço (ver ERRC) também é uma brecha de conteúdo.
> - Benchmark de meta: para entrar no top 3 da praça, mirar taxa de engajamento ≥ X%.

Cruza com a ERRC (gaps de serviço) → o gap de SERVIÇO vira gap de CONTEÚDO.

## 5. Encaixe no MODELO_NEGOCIO

- **NÃO é core.** O relatório base responde "devo abrir?" (viabilidade). Este add-on
  responde "como me comunico?" (marketing de execução). Produto separado.
- **Cobrança:** add-on por crédito (Fase 2 do roadmap de monetização). Sugestão:
  **1 crédito de add-on** = raio-X de IG de 1 praça. Ou incluso no tier **Rede**.
- **Por que add-on e não grátis:** custo SearchAPI extra + valor de marketing alto
  percebido (consultor de mkt cobraria isso à parte). Margem ótima.
- **ICP que mais valoriza:** consultor fitness (revende) + dono de rede (já tem o
  produto, quer bater o concorrente no digital).

## 6. Arquitetura (off-pipeline, on-demand)

- Endpoint/job dedicado: `POST /api/relatorios/{id}/addon/ig-marketing` (debita crédito).
- Lê os concorrentes já mapeados do relatório (`competidores`), roda SearchAPI IG em
  paralelo, calcula scores, grava em tabela própria (`addon_ig_marketing`) + gera o
  playbook. NÃO altera o pipeline do relatório base.
- Determinístico (BaseAgent-style): scores em Python; só a redação do playbook usa LLM
  (uma chamada curta, skill de mkt).

## 7. Pendências pra fechar

- [ ] Validar taxa de cobertura: % de concorrentes com IG público encontrável.
- [ ] Definir peso do score (`param()`) com 2-3 praças piloto.
- [ ] Preço do crédito do add-on (entra nas entrevistas de willingness-to-pay, Fase 0).
- [ ] Skill de redação do playbook de mkt (curta, data-tied — não genérica).

---

*Referência de enquadramento de marketing IG: pilares de conteúdo, mix de formato,
cadência, taxa de engajamento, estratégia de hashtag. Toda a análise é derivada dos
posts REAIS dos concorrentes — zero conselho genérico.*
