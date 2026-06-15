# Inteligência Competitiva aplicada ao Mercado Fitness

> Tradução do módulo "[Inteligência Competitiva] Aprenda a mapear seus
> concorrentes e muito mais" (Janaina Rehder; caso original: Subway vs
> fast-food, dez/2015) para o domínio do GymSite Intelligence. Cada
> conceito do curso vira narrativa fitness + a ferramenta nossa que o
> operacionaliza. O curso descreve À MÃO o que o pipeline A0-A9 faz
> automatizado — este doc é a ponte metodológica (e munição de venda:
> "fazemos em 8 minutos o que consultoria faz em 6 semanas").

---

## Aula 1 — Analisando a concorrência → quem disputa o aluno

No fitness, "concorrência" não é a lista de pins do Google Maps — são as
academias que disputam o MESMO aluno (caso Wally do Cocó: 40 pins, ~15
tradicionais, 7 dissecadas). Análise estruturada = saber quem são, onde
estão, o que cobram, do que os alunos reclamam e quando lotam.

**GymSite:** tabela de concorrentes (A3a) com place_id, rating, pico 24h,
dores classificadas e planos×preços. Filtro semântico separa academia
tradicional de box/studio/arte marcial — com motivo de exclusão exibido.

## Aula 2 — Área de influência → o raio que importa

Área de influência de academia é pequena e cruel: o aluno não atravessa a
cidade pra treinar. A pergunta não é "quantas academias tem em Fortaleza"
— é "quantas o morador DESTE bairro alcança em 10 minutos".

**GymSite:** anéis competitivos (Motor v2 Apêndice D): NO_BAIRRO (peso
1.00), FRONTEIRA ≤2 km (0.50), REGIONAL (0.20). **FEITO (jun/2026):** a
classificação por anel funciona — `classificar_anel` casa NO_BAIRRO pelo
campo `bairro_concorrente` por CONTÉM ("Cocó" em "Lojas 2/3 - Cocó"); no
relatório real os 10 concorrentes de Cocó saem NO_BAIRRO=10 (antes
REGIONAL=9, por bug do campo). **PENDENTE (roadmap, não pronto):** (a) o
score ponderado por anel (`resumo_aneis.score_competitivo_ponderado`)
ainda NÃO alimenta o `score_concorrencia` — hoje o score vem da saturação
por CONTAGEM; (b) `dist_borda_km` é distância ao CENTRÓIDE (média dos
candidatos GeoScout), não à borda do polígono do bairro — falta o
polígono/grade; (c) flag `multiesporte` e lista per-competitor
(anel/porte/dist) são computadas mas ainda não exibidas no relatório. A
meta "Aldeota forte não mascara Cocó vazio" depende de (a).

## Aula 3 — Importância → prever movimento, não fotografar

O valor não é o retrato de hoje — é antecipar o movimento: quem vai
abrir, onde, antes da fachada existir.

**GymSite:** radar de futuros concorrentes = CNPJ/RFB (entrantes CNAE
9313-1 por bairro, 132.961 estabelecimentos carregados) + CNO (obras
fitness em andamento com área e endereço) + CAGED (saldo de empregos do
setor por município, Trilha 6). O dono vê a academia nova ANTES da obra
ficar pronta — é o "você à frente do seu concorrente" do slide.

## Aula 4 — Benefícios → oportunidade e risco com fonte

Oportunidade: bairro com demanda e anel NO_BAIRRO vazio. Risco: bairro
saturado, rede grande chegando (CNO/CNPJ), pico igual ao de todo mundo.
Decisão embasada = cada afirmação com fonte auditável (IBGE, Receita,
Places, anúncio) — nunca "achismo de consultor".

**GymSite:** veredito do relatório (aprovado/com ressalvas/reprovado) +
alertas financeiros + bairros alternativos ranqueados.

## Aula 5 — Entenda o concorrente → a ficha completa

Perfil, forma de atuação, presença. No fitness: modelo (low-cost rede /
independente premium / 24h), planos e preços, o que inclui, fidelidade,
dores recorrentes nos reviews, horário de lotação, porte.

**GymSite:** ficha por concorrente = planos×preços (grounding com fonte),
dores na taxonomia fechada (reviews de MENOR nota, não os 5 elogios da
Places), pico 24h (SearchAPI), contato, porte por nº de avaliações.

## Aula 6 — Diretos e indiretos → tradicional vs alternativas

Direto: academia tradicional disputando a mesma mensalidade. Indireto:
CrossFit box, studio de pilates, parque com calistenia, aulas online —
atendem a mesma necessidade ("me exercitar") por outro caminho. O filtro
que separa também REGISTRA: excluído não é invisível, é categorizado.

**GymSite:** seção "excluídos por filtro semântico" com motivo; flag
`multiesporte` pra quem é gym + natação/luta (VS Club mantido como flag,
não mais excluído — falso negativo morto no Motor v2; flag computada mas
ainda não exibida no relatório, jun/2026); parques ativos próximos como
polo de concorrência indireta
gratuita.

## Aula 7 — Distribuição dos players → mapa, não lista

Como as redes se distribuem pela cidade: Smart Fit nas âncoras de varejo,
independentes grandes em avenida de bairro, studios em sala comercial.
Distribuição revela estratégia — e revela o buraco.

**GymSite:** mapa do relatório (Google Maps com pins por tipo) + market
atlas municipal + distribuição por bairro na tabela de reviews.

## Aula 8 — Quantitativo + Qualitativo → o quanto e o porquê

Quantitativo: nº de academias por anel, preços, pico, avaliações, m².
Qualitativo: POR QUE a Smart Fit do Papicu perde aluno (ar-condicionado
quebrado após 20h — review real), por que o Gaviões lota às 19h.
Número sem porquê é tabela; porquê sem número é opinião.

**GymSite:** pico (quanto) + dores classificadas com quote (porquê) na
MESMA tabela. ERRC do A9 nasce do cruzamento: eliminar a dor comum,
elevar o que ninguém entrega.

## Aula 9 — O caso Subway traduzido: a Smart Fit é a Subway do fitness

O caso central do curso, espelhado no nosso mercado:

| Insight Subway (2015) | Tradução fitness (2026) | Ferramenta GymSite |
|---|---|---|
| Concorrentes em shopping; Subway na rua, posto, estacionamento — loja menor | Mesmo "fast-food fitness", perfis de ponto distintos: Smart Fit em âncora de varejo, independente em avenida de bairro, studio em sala — cada `tipo_negocio` tem ponto ideal próprio | slot `tipo_negocio` + faixa de área por preset + âncoras no relatório |
| 49% no Sudeste = dispersão maior que concorrentes | Rede que dispersa primeiro captura interior/Nordeste sem briga — Smart Fit: 984 clubes BR, +161/ano, 47% das aberturas | CNPJ por UF/município: presença de cada rede; radar de entrantes |
| Municípios COM concorrente e SEM Subway = alvo; 80% deles <100k hab | Bairro com demanda comprovada (concorrente lotado) e anel NO_BAIRRO sem academia tradicional = oceano azul local; cidade média sem rede grande = oportunidade de franquia | anéis + pico do concorrente + Censo/setor censitário (Trilha 6) |
| Capital / litoral / interior — renda e comportamento distintos | Bairro de orla (Bessa!) ≠ bairro de escritório (Aldeota) ≠ bairro residencial (Cocó): renda, horário de pico e modelo viável mudam | ADH/UDH renda intraurbana + RAIS (pop. diurna) + Censo (residente) |
| População flutuante: Bombinhas, 600 mil turistas/ano, loja nº 500 | Demanda de academia = residente (Censo) + trabalhador diurno (RAIS) + flutuante (turismo na orla, hospital, universidade) — bairro "pequeno" no Censo pode ser gigante de dia | conceito formal no score de demanda do Motor v2; polos geradores já capturam hospital/universidade |
| Subway cresceu 11% a.a. vs 4,5% dos concorrentes | Velocidade de expansão por rede = quem está acelerando AGORA (aberturas CNPJ/ano por rede na cidade) — antecipa pressão competitiva | série temporal de entrantes CNPJ por rede/município |
| Qualitativo atrelado ao negócio: metragem menor permitiu crescer rápido | Modelo enxuto (300-500 m², low-cost, 24h sem recepção) abre onde full-service não para em pé — análise de viabilidade muda por modelo | cenários financeiros por preset de área + benchmark CVM (Smart Fit listada) |

## Conceito novo a formalizar: população flutuante no score de demanda

Única peça do curso que ainda NÃO temos formalizada. Demanda real do
bairro = residente + diurna + flutuante:

- **Residente** — Censo 2022 por setor censitário (Trilha 6, Tier A)
- **Diurna** — RAIS: vínculos formais por bairro/CNAE (Trilha 6, Tier A)
- **Flutuante** — proxies: polos geradores (hospital, universidade,
  shopping — já coletados), atratividade turística (orla), pico dos
  concorrentes como validação comportamental

→ Registrar no Motor v2 como terceiro componente do score de demanda,
mesma esteira dos anéis (geometria compartilhada). Caso Bessa é o piloto
natural: bairro de orla com fluxo que o Censo não enxerga.

## Resumo executivo da tradução

O curso ensina a fazer manualmente, com dados de 2015, o que o GymSite
entrega em 8 minutos com dados vivos: mapear quem disputa o aluno
(anéis), entender cada concorrente por dentro (dores+planos+pico),
prever quem vem (CNPJ+CNO), e achar o buraco onde a demanda existe e a
oferta não (oceano azul local). A peça que o curso acrescenta ao nosso
modelo é a população flutuante — formalizada acima como item do Motor v2.
