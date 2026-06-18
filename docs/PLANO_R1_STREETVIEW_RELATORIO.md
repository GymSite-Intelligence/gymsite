# Plano de Implementacao — R1: Street View como evidencia no relatorio (A6/A9 + PDF)

> Status: proposta (aguardando validacao). ROI alto / esforco baixo.
> Origem: docs/PLANO_MAPAS_GEOSEEKER.md (iniciativa R1).

## 1. O que entrega (linguagem natural)

Hoje o relatorio mostra numeros e veredito sobre cada endereco-ancora, mas o
cliente nao "ve" o lugar. R1 insere a **foto de rua (Google Street View)** do
ponto analisado ao lado do dado — fachada, vizinhanca, movimento — tornando o
relatorio concreto e mais convincente. Vale para a tela do relatorio (A6/A9) e
para o PDF entregue ao cliente.

## 2. Por que o esforco e baixo (o que JA existe)

- Endpoint backend pronto: `GET /api/maps/street-view` em `api.py` (lat/lng,
  w/h), com chave SERVER separada e cache (`tools/maps_street_view.py`,
  `tools/maps_tools.py`).
- O payload do relatorio **ja carrega** `street_view_url` + `lat`/`lng` por
  local (visto em `frontend/src/mocks/relatorios/*.json` e no golden dataset).
- Frontend ja sabe montar a imagem: `components/domain/CandidatoCard.tsx`
  constroi `/api/maps/street-view?lat=..&lng=..` a partir das coordenadas.
- Auditoria (`docs/AUDITORIA_360.md`, item B2) confirma: a rota existe mas esta
  **orfã** — definida e nao consumida. R1 e exatamente "ligar o fio".

## 3. Gap atual

- No PDF (`pdf/builder.py`) a secao `_candidatos_section` NAO renderiza a
  imagem; o modelo `CandidatoPdf` (`pdf/models.py`) tem `endereco` mas **nao**
  tem `lat`/`lng` nem `street_view_url` (o adapter nao propaga esse campo).
- Na tela (A6/A9) o `street_view_url` existe no dado mas nao e exibido de forma
  consistente fora do CandidatoCard.

## 4. Mudancas propostas (arquivos e passos)

### Backend / PDF (entrega principal)
1. `pdf/models.py` — adicionar a `CandidatoPdf` (e onde fizer sentido) os campos
   opcionais: `lat: float | None = None`, `lng: float | None = None`,
   `street_view_url: str | None = None`, `street_view_path: str | None = None`.
2. `pdf/adapters.py` — propagar `lat`/`lng`/`street_view_url` do JSON do
   relatorio para o `CandidatoPdf` (o dado ja vem do pipeline).
3. `pdf/builder.py` — novo helper `_street_view_path(lat, lng)` que:
   - reaproveita o tool/cache de Street View para baixar a imagem 1x e salvar
     em disco (cache local, igual `_logo_path`/`_heatmap_path`);
   - retorna `None` em qualquer falha (defensivo — nunca quebra o PDF).
4. `pdf/builder.py` — em `_candidatos_section` (e variantes bala/executive),
   inserir um `Image` pequeno (ex.: 6cm x 3,75cm, ratio 16:10) por candidato
   quando houver imagem; com legenda "Vista da rua — {endereco}".
5. Guard de custo: limitar a N candidatos com foto (ex.: top 3) para nao
   estourar chamadas; reusar cache (TTL ja existe).

### Frontend (A6/A9 — opcional, menor)
6. Garantir que a view do relatorio exiba `street_view_url` (reaproveitar a
   logica do `CandidatoCard`) tambem na secao de candidatos do A6/A9.

## 5. Contrato de dados

```
CandidatoPdf {
  endereco: str
  lat?: float
  lng?: float
  street_view_url?: str   // ex: /api/maps/street-view?lat=..&lng=..&w=640&h=400
  street_view_path?: str  // caminho local apos download (preenchido no build)
}
```

## 6. Riscos e mitigacoes

- **Sem cobertura Street View** no ponto: Google devolve placeholder cinza.
  Mitigar: tratar 404/zero-result e simplesmente nao renderizar a imagem.
- **Custo por imagem**: limitar a top-N + cache (ja existe TTL 12h).
- **Quebra do PDF**: todos os helpers retornam `None` em erro (padrao defensivo
  ja adotado em `_logo_path`/`_heatmap_path`).
- **Chave**: usar SEMPRE o proxy server; nunca expor a chave no PDF/cliente.

## 7. Definicao de pronto (DoD)

- [ ] `CandidatoPdf` carrega `street_view_url`/coords; adapter propaga.
- [ ] `_candidatos_section` renderiza a foto quando disponivel, com legenda.
- [ ] PDF gera normalmente quando a foto falta/erra (sem excecao).
- [ ] Top-N respeitado; cache reutilizado (sem chamadas duplicadas).
- [ ] Smoke test do PDF (`PdfSmokePage`/script de smoke) passa.

## 8. Estimativa

- Backend/PDF: ~0,5 a 1 dia. Frontend opcional: ~0,5 dia.
- Custo recorrente: marginal (cache + limite top-N).

---
_Pre-req de credenciais/billing (chave SERVER Street View) e responsabilidade
manual no Google Cloud — fora do escopo de automacao._
