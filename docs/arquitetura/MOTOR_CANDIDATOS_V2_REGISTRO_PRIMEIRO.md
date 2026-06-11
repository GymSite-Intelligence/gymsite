# Motor de Candidatos v2 — Registro Primeiro

> Spec de arquitetura. Decisão de 11/06/2026 (conversa Marcelo + análise do
> caso Pinto Bandeira, 499). Implementação entra na fila DEPOIS do pacote de
> metadados (spec F2 §7). Nada aqui altera o pipeline atual até lá.

## 1. O problema que motivou (caso real)

Relatório da Parquelândia (3b3ffcac) elegeu como top1 uma CASA no
Engenheiro Luciano Cavalcante — outro vetor da cidade — por R$ 9,90/m²
(70% abaixo do piso comercial; "1400 m² tot." = área de terreno, não
construída). Os 3 candidatos do relatório estavam fora de Parquelândia
(um em Maracanaú) e nada sinalizou isso. Causa raiz: o motor atual é
**anúncio-primeiro** — qualquer listing com área na faixa vira candidato,
e o mercado anunciado nem sempre tem estoque no bairro analisado.

## 2. A inversão (decisão)

**Base oficial primeiro, mercado depois.** A descoberta de candidatos parte
do registro público do território; A1 e A3 deixam de descobrir e passam a
VALIDAR. O dinheiro (matrícula ONR) só sai depois de três gates gratuitos
e por clique do usuário (P-003).

```
A0.5 BASE TERRITORIAL (agente novo)
  Fontes abertas do polígono do bairro:
    - IPTU Fortaleza (CSV no CKAN — confirmado em 11/06)
    - Áreas Edificadas por uso 2021-2024 (CSV no CKAN — confirmado)
    - Zoneamento/LUOS (mapas abertos da prefeitura)
    - CNO (obras por endereço — base já carregada)
    - Circunscrição ONR → cartório competente (integração existente)
  → universo de imóveis FÍSICOS do bairro
  GATE 1 (grátis): uso comercial/serviço + área edificada na faixa
                   + zona permite academia          ← lixo morre aqui
        ↓ sobreviventes
A1 GEOSCOUT (vira validador de ponto)
  Visibilidade, via, âncoras, Street View DESSES endereços
  GATE 2 (grátis): score mínimo de ponto
        ↓ qualificados
A3 LISTING HUNTER (vira casamento, não descoberta)
  Busca oferta de aluguel ATIVA para os endereços qualificados
  (ImovelWeb/OLX — scraping existente, agora dirigido por endereço)
  GATE 3: tem oferta ativa  → FINALISTA
          sem oferta        → VITRINE OFF-MARKET (opt-in do usuário)
        ↓ finalistas (3-5)
MATRÍCULA ONR (pago ~R$ 30-60, ação explícita do usuário — P-003)
  Dono (CPF/CNPJ), ônus (penhora/hipoteca/alienação), área averbada,
  valores históricos de transação
        ↓
CONTATO E DUE DILIGENCE (playbook)
  Dono PJ → cruza base RFB CNPJ (já carregada) → sócios e contato
  Etapa de imóvel ganha passos: matrícula no cartório competente
  (dados já em candidatos.cartorio), visita, zoneamento confirmado
```

## 3. O que cada camada entrega e custa

| Camada | Fonte | Custo | Entrega |
|---|---|---|---|
| Base territorial | IPTU CSV + Áreas Edificadas + LUOS + CNO (CKAN/abertos) | R$ 0 | imóveis físicos: inscrição, área edificada, uso, zona |
| Validação de ponto | Places/Street View (cotas existentes) | ~R$ 0 | qualidade do ponto comercial |
| Casamento de oferta | Scraping ImovelWeb/OLX existente | R$ 0 | disponibilidade real + preço pedido |
| Matrícula | ONR/SAEC | R$ 30-60/consulta | dono, ônus, área oficial, histórico |
| Contato | RFB CNPJ (base própria) | R$ 0 | sócios, telefone, e-mail de dono PJ |

Princípio de custo: **o aberto faz a peneira, o pago compra a chave, o
aberto de novo acha a porta.** Matrícula nunca é automática — botão
"Verificar matrícula (~R$ 50)" no candidato finalista.

## 4. Red flags (gate de elegibilidade)

Persistidas em `candidatos.red_flags JSONB` (nasce no pacote de metadados,
padrão P-008..P-010). Mínimo viável:

| Flag | Regra | Efeito |
|---|---|---|
| `fora_do_escopo` | bairro/município ≠ polígono da análise | desclassifica do top; só entra com aceite explícito |
| `tipo_incompativel` | Casa/Apartamento/Terreno para academia (ONR `tipo_imovel_codigo_onr` já gravado) | flag forte + alerta |
| `preco_suspeito` | R$/m² < 50% do piso comercial da cidade | alerta "área provavelmente de terreno" |
| `area_divergente` | área anunciada ≠ área edificada do IPTU (>30%) | alerta |
| `investigacao_fraca` | A4 confiança baixa/média | não pode ser top1 sem ressalva |

Check novo no A8: relatório com 100% dos candidatos `fora_do_escopo`
→ severidade ALTA ("nenhum imóvel na área analisada — estoque anunciado
zero; considere prospecção off-market").

## 5. Off-market (modo de exceção, opt-in)

Quando GATE 3 zera (caso Parquelândia): UI avisa "não há ofertas ativas no
bairro" e oferece prospecção off-market — imóveis físicos aprovados nos
gates 1-2, sem anúncio. Fluxo: matrícula (paga, clique) → dono → abordagem
direta. Nunca automático; é decisão comercial do usuário.

## 6. Dependências e fases

1. **Pré-requisito**: pacote de metadados (F2 §7) — `red_flags`,
   enriquecimento aberto e participações nascem no padrão novo.
2. **v2.0**: GATE de red flags no fluxo ATUAL (anúncio-primeiro) + check A8
   de escopo. Barato, mata o caso Pinto Bandeira sem reordenar o pipeline.
3. **v2.1**: A0.5 Base Territorial com IPTU/Áreas Edificadas de Fortaleza
   (bairro_renda_loader já previsto consome o mesmo CKAN) + A1/A3 dirigidos.
4. **v2.2**: botão de matrícula ONR no candidato + due diligence cartorial
   no playbook + cruzamento RFB para dono PJ.
5. **v2.3** (F4): conta ONR integrada com pagamento, automação opt-in.

Fallback permanente: município sem cadastro aberto → fluxo v2.0
(anúncio-primeiro com gates). A inversão é progressiva por cobertura de
dados, não big-bang.

## 7. Fora de escopo

- Raspar e-mail/contato de páginas de anúncio de terceiros (decisão ética
  mantida; contato nasce de matrícula + RFB, fontes oficiais).
- Envio de e-mail pela plataforma (F3, com infra própria de e-mail).
- Compra automática de certidões sem clique do usuário.
