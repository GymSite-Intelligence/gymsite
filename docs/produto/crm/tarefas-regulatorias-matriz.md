# Matriz de tarefas regulatórias — CRM (estudo)

**Data:** 2026-09-05  
**Status:** estudo aprovado — **sem seed no banco nesta onda**  
**Próxima onda:** importar linhas determinísticas em `backend/services/execucao/playbook_templates.py` / `playbook_generator.py`

## Regras de geração

| Regra | Valor |
|---|---|
| Invenção de requisito | **Proibido** — sem LLM; só linhas desta matriz |
| Flags de entrada | `precisa_lanchonete` (bool), `precisa_obra` (bool) |
| Baseline legal | Federal + referências nacionais; município/UF podem exigir mais |
| Categorias CRM | `LEGAL` ou `OBRAS` (códigos canônicos do playbook) |
| Seed DB / gerar-plano | **Fora de escopo** nesta onda |

### Pseudocódigo (próxima onda)

```text
tasks = VIGILANCIA_BASE
if precisa_lanchonete: tasks += VIGILANCIA_LANCHONETE
if precisa_obra:
  tasks += ARQUITETO_OBRA
  tasks += ENGENHEIRO_OBRA
```

---

## 1. Vigilância Sanitária — academia (base)

Sempre incluídas para unidade de atividade física / academias.

| # | Gatilho | Docs / atos (baseline nacional) | Título tarefa CRM | Checklist | Cat. | Notas UF / município |
|---|---------|-----------------------------------|-------------------|-----------|------|----------------------|
| VS-01 | `always` (academia) | **Lei 8.080/1990** (SUS); **Lei 6.437/1977** (infrações sanitárias); **RDC ANVISA 50/2002** (requisitos sanitários gerais — referência histórica para serviços); **Portaria MS 2.095/1997** (procedimentos operacionais) | Montar dossiê para licença sanitária da academia | Levantar checklist oficial no portal da VS municipal; reunir CNPJ + contrato social + contrato locação; planta baixa com fluxo e áreas (vestiários, banheiros, salão); comprovante de abastecimento de água potável; descarte de efluentes conforme rede/local | LEGAL | Protocolo, taxas e formulário variam por município. Confirmar se exige **DAM** (Documento de Arrecadação Municipal) ou sistema estadual (ex.: **SIVISA** em SP). |
| VS-02 | `always` | **RDC ANVISA 216/2004** (Boas Práticas — referência para POPs); **Portaria MS 2.095/1997** | Elaborar e implementar POPs da academia | POP limpeza e desinfecção (salão, vestiários, equipamentos); POP gestão de resíduos; POP controle de pragas; POP higiene de colaboradores; POP manejo de acidentes com fluidos; treinar equipe e registrar presença | LEGAL | Município pode exigir modelo próprio de POP ou lista fechada de documentos. |
| VS-03 | `always` | **Lei 6.437/1977**; contrato de **Dedetização / Controle Integrado de Pragas** | Contratar controle de pragas e guardar laudos | Contratar empresa registrada; definir periodicidade; arquivar laudos/certificados de aplicação; manter registro de ocorrências | LEGAL | Alguns municípios exigem laudo **≤ 30 dias** antes da vistoria. |
| VS-04 | `always` | **Portaria MS 518/2004** (qualidade da água); **RDC ANVISA 275/2002** (piscinas — se houver) | Comprovar água potável e condições de piscina | Exigir laudo/atestado de potabilidade (rede ou poço artesiano regularizado); se piscina: cloro/pH, fluxo de banho, POP específico | LEGAL | Poço artesiano exige outorga/laudo ambiental em vários estados. Piscina nem sempre existe — omitir checklist de piscina se `tem_piscina=false` (flag futura). |
| VS-05 | `always` | **Lei 12.305/2010** (PNRS); **CONAMA 275/2001** (resíduos de serviços de saúde — se aplicável a materiais perfurocortantes em estúdio/clínica acoplada) | Organizar gestão de resíduos | Mapear pontos de coleta; contratar coleta licenciada; separar recicláveis comuns; identificar resíduos especiais (perfurocortantes só se serviço clínico) | LEGAL | Coleta seletiva e frequência definidas localmente. |
| VS-06 | `always` | Licença sanitária municipal (ato local) | Agendar vistoria e obter licença sanitária | Protocolar dossiê; pagar taxas; corrigir apontamentos de vistoria; obter certificado/licença com validade; renovar calendário | LEGAL | Validade típica 1–2 anos; renovação pode ser simplificada. |

---

## 2. Vigilância Sanitária — branch `precisa_lanchonete`

Incluir **somente se** `precisa_lanchonete = true` (bar, café, lanchonete, venda de alimentos preparados ou embalados no local).

| # | Gatilho | Docs / atos (baseline nacional) | Título tarefa CRM | Checklist | Cat. | Notas UF / município |
|---|---------|-----------------------------------|-------------------|-----------|------|----------------------|
| VS-L01 | `precisa_lanchonete` | **RDC ANVISA 216/2004** (BPF); **RDC ANVISA 275/2002** (alimentos preparados); **Lei 1.283/1950** + **Decreto 6.871/2009** (rotulagem quando aplicável) | Montar dossiê sanitário da área de alimentos | Separar fluxo limpo/sujo na planta; listar equipamentos (geladeira, fogão, bancada inox); definir responsável técnico se exigido; cardápio e origem dos insumos | LEGAL | Município pode classificar como **Baixo / Médio / Alto risco** — muda documentação. |
| VS-L02 | `precisa_lanchonete` | **RDC ANVISA 216/2004** | POPs específicos de manipulação de alimentos | POP recebimento de matérias-primas; POP higienização de utensílios; POP controle de temperatura; POP higiene pessoal manipuladores; POP rastreabilidade e recall | LEGAL | Manipuladores podem precisar **atestado de saúde** e carteira de manipulador (curso municipal/estadual). |
| VS-L03 | `precisa_lanchonete` | **RDC ANVISA 275/2002**; **Instrução Normativa MAPA 60/2019** (SIF/SIP — se produtos de origem animal industrializados) | Regularizar manipuladores e fornecedores | Exigir curso/atestado dos manipuladores; NF de fornecedores; armazenamento refrigerado conforme ficha técnica | LEGAL | Venda de produtos industrializados fechados (barra, whey) costuma simplificar vs. cozinha quente. |
| VS-L04 | `precisa_lanchonete` | Licença sanitária de estabelecimento de alimentos (ato local) | Vistoria VS — lanchonete | Agendar vistoria da área de alimentos; corrigir não conformidades; obter licença ou anexo à licença da academia | LEGAL | Pode exigir **projeto sanitário** separado ou RT (nutricionista/farmacêutico/biomédico) conforme porte. |

---

## 3. Arquiteto — `precisa_obra`

Incluir **somente se** `precisa_obra = true` (adaptação, reforma, obra nova, mudança de layout com impacto legal).

| # | Gatilho | Docs / atos (baseline nacional) | Título tarefa CRM | Checklist | Cat. | Notas UF / município |
|---|---------|-----------------------------------|-------------------|-----------|------|----------------------|
| AR-01 | `precisa_obra` | **Lei 5.194/1966** (exercício profissional); **Resolução CAU** (ART/RRT de projeto) | Contratar arquiteto e registrar ART/RRT de projeto | Proposta e contrato; levantamento do imóvel; registro ART/RRT no CAU/CREA conforme escopo | OBRAS | Obra em área histórica ou shopping pode exigir aprovação adicional. |
| AR-02 | `precisa_obra` | **NBR 9050/2020** (acessibilidade); **Lei 13.146/2015** (Estatuto da Pessoa com Deficiência) | Projeto arquitetônico com acessibilidade | Rotas acessíveis; banheiro PCD; sinalização tátil/visual; vagas reservadas quando aplicável | OBRAS | Prefeitura pode exigir **Termo de Conclusão de Obra** assinado por responsável técnico. |
| AR-03 | `precisa_obra` | **Lei 5.194/1966**; **Código de Obras** municipal | Submeter projeto à prefeitura (Alvará de construção/reforma) | Protocolo digital ou presencial; taxas; plantas, cortes, quadro de áreas; cronograma de obra | OBRAS | **Alvará de construção** vs. **comunicação de obra pequena** — regra municipal. |
| AR-04 | `precisa_obra` | Inputs para **AVCB/CLCB** (Corpo de Bombeiros estadual) | Entregar plantas e memorial para PCI | Planta de layout com rotas de fuga; sinalização; extintores; iluminação de emergência; hidrantes/sprinkler se exigido | OBRAS | Memorial entregue ao engenheiro de incêndio / bombeiros — ver seção Engenheiro. |
| AR-05 | `precisa_obra` | **Lei 5.194/1966** (acompanhamento) | Acompanhamento de obra e conformidade | Visitas periódicas; registro fotográfico; conferência de materiais; ART/RRT de execução se aplicável | OBRAS | Reforma em imóvel locado: alinhar escopo com contrato de locação. |

---

## 4. Engenheiro — MEP / AVCB / estrutura

Incluir **somente se** `precisa_obra = true`. Subconjuntos podem ser omitidos na implementação se flags futuras existirem (`precisa_estrutura`, `precisa_mep`, `precisa_avcb`); nesta matriz, obra completa assume os três eixos.

| # | Gatilho | Docs / atos (baseline nacional) | Título tarefa CRM | Checklist | Cat. | Notas UF / município |
|---|---------|-----------------------------------|-------------------|-----------|------|----------------------|
| EN-01 | `precisa_obra` + estrutura | **NBR 6118/2023** (concreto); **Lei 5.194/1966** | Projeto estrutural e ART/RRT | Análise de cargas (equipamentos suspensos/rigs); reforço se necessário; ART/RRT estrutural | OBRAS | Crossfit/rigs no teto exigem laudo estrutural frequente. |
| EN-02 | `precisa_obra` + MEP | **NBR 5410/2004** (instalações elétricas); **NBR 5626/2020** (água fria) | Projetos elétrico e hidráulico | Quadro de cargas; circuitos dedicados cardio/ar-condicionado; dimensionamento hidráulico vestiários/chuveiros | OBRAS | Concessionária de energia pode exigir **parecer de demanda** ou obra na rede. |
| EN-03 | `precisa_obra` + MEP | **NBR 16401/2008** (ar-condicionado) | Projeto de climatização / exaustão | Carga térmica; exaustão vestiários; manutenção de filtros documentada | OBRAS | Áreas de grupo (spinning) podem exigir taxa de renovação de ar local. |
| EN-04 | `precisa_obra` + AVCB | **Lei 13.425/2017**; **Decreto estadual do Corpo de Bombeiros** (ex.: **Decreto SP 63.911/2018** — referência; usar decreto vigente da UF) | Projeto de Prevenção e Combate a Incêndio (PCI) | Elaborar PCI; ART/RRT; submeter ao CB estadual; executar sinalização e extintores conforme projeto | LEGAL | Categorização de risco varia por UF (CLCB vs AVCB vs certificado digital). |
| EN-05 | `precisa_obra` + AVCB | Decreto CB estadual | Obter AVCB / CLCB / certificado do Corpo de Bombeiros | Agendar vistoria do CB; corrigir pendências; arquivar certificado com validade | LEGAL | Renovação periódica; obra sem certificado impede alvará em muitos municípios. |
| EN-06 | `precisa_obra` | **NR-10** (segurança em instalações elétricas — operação) | Laudos e testes de comissionamento MEP | Teste de continuidade/aterramento; pressurização hidráulica; entrega de **as built** | OBRAS | Laudo **SPDA** (para-raios) se exigido pelo CB ou altura do imóvel. |
| EN-07 | `precisa_obra` | **Lei 5.194/1966** | ART/RRT de execução e encerramento técnico | Registrar ART/RRT de execução; laudo de conformidade; suporte ao **habite-se** / **certidão de conclusão** | OBRAS | Habite-se pode ser exigido mesmo para reforma de grande porte. |

---

## 5. Mapeamento resumido → playbook (próxima onda)

| Papel | Linhas | Flag | Categorias |
|---|---|---|---|
| Vigilância — academia | VS-01 … VS-06 | sempre | LEGAL |
| Vigilância — lanchonete | VS-L01 … VS-L04 | `precisa_lanchonete` | LEGAL |
| Arquiteto | AR-01 … AR-05 | `precisa_obra` | OBRAS |
| Engenheiro | EN-01 … EN-07 | `precisa_obra` | OBRAS + LEGAL (AVCB) |

**Contagem determinística:** 6 + 4 + 5 + 7 = **22 tarefas** no pior caso (todas as flags verdadeiras).

---

## 6. Explicitamente fora desta onda

- Seed de templates no Supabase / `playbook_templates` table
- Chamada LLM no `playbook_generator.py` para inventar licenças
- Consulta automática a portal de prefeitura (fase posterior)
- Flags adicionais (`tem_piscina`, `precisa_estrutura`, etc.) — documentadas como extensão futura

---

## Referências internas

- Design: `docs/superpowers/specs/2026-09-05-app-logado-crm-shell-capex-design.md` (PR6)
- Categorias CRM: `docs/arquitetura/CATEGORIAS_TAREFAS.md`
- Templates atuais (fallback LLM): `backend/services/execucao/playbook_templates.py`
