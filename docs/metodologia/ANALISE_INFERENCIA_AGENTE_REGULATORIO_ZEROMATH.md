# Análise — Motor de Inferência do Agente Regulatório × Zero Math AI

> Escopo: **Agente Regulatório** (`agents_site` / persona `regulatorio` no Consultor).  
> Referência: [Knowledge Base](https://zeromathai.com/en/knowledge-base-en/), [Inference Engine](https://zeromathai.com/en/knowledge-base-en/inference-engine/), [Expert Systems](https://zeromathai.com/en/expert-system-en/), [Forward](https://zeromathai.com/en/knowledge-base-en/forward-chaining/) / [Backward Chaining](https://zeromathai.com/en/backward-chaining-en/), [Frames](https://zeromathai.com/en/frames-en/), [Scripts](https://zeromathai.com/en/scripts-en/), [OWA](https://zeromathai.com/en/open-world-assumption-en/) / [CWA](https://zeromathai.com/en/closed-world-assumption-en/).  
> Data: 2026-07-22 · status: análise + **P0 implementado** (`tools/regulatorio_lookup.py`).

## Veredito em uma frase

Hoje o Regulatório tem **base de conhecimento boa + grounding + carimbo**, mas **não tem motor de inferência separado** — o LLM recupera trechos e “raciocina” na prosa. O ganho real é o mesmo padrão do Responsável Técnico: **fatos fechados viram FunctionTool determinística; o LLM só narra e cita**.

---

## 1. O que a Zero Math descreve (mapa útil)

| Conceito | Papel | Tradução prática GymSite |
|---|---|---|
| **Knowledge Base** | “O que se sabe” (fatos + regras) | Docs Vertex `gymsite-regulatorio-docs` + (futuro) tabelas versionadas |
| **Inference Engine** | “Como concluir” a partir da KB | Hoje: implícito no Gemini. Ideal: tools Python com regras explícitas |
| **Working Memory** | Fatos da situação atual | Contexto da conversa (`cidade`/`UF`, tipo PJ) — ainda frouxo no Regulatório |
| **Forward chaining** | Fatos → dispara regras → novos fatos | Checklist: “UF=CE e sem RT” → itens faltantes |
| **Backward chaining** | Meta → condições necessárias | “Posso abrir?” → prova cada pré-requisito |
| **Frames** | Slots/atributos de uma situação | Frame `AberturaAcademia`: uf, município, tem_rt, cref_cref… |
| **Scripts** | Sequência típica de eventos | Roteiro: Junta → CNPJ → alvarás → CREF+RT → operar |
| **OWA** | Ausente na KB = **desconhecido** | Já é a postura correta p/ municipal |
| **CWA** | Ausente na KB = **falso** | Só em tabelas fechadas (mapa UF→CREF) |
| **Explanation facility** | Por que concluiu (regras disparadas) | Parcial: carimbo `valor · base · fonte · janela` |

Separação KB ↔ engine é o ponto central da KB Zero Math: **atualizar conhecimento sem reescrever o raciocínio**.

---

## 2. O que já existe no Regulatório

### 2.1 Arquitetura atual (híbrido LLM + RAG)

```
Pergunta do visitante
    → Root roteia para Regulatorio
    → LLM (temp 0.2) decide chamar consultar_base_regulatoria
    → Vertex AI Search (gymsite-regulatorio-app / regulatorio-docs)
    → LLM narra + emite JSON citacoes
    → carimbo.py valida fonte legal (rejeita Vertex/slug .txt)
```

Código de referência:

- Agente ADK: `agents_site/agent.py` (`regulatorio`)
- Tool: `agents_site/tools.py` → `consultar_base_regulatoria`
- Persona espelho: `services/consultor/consultor_engine.py` (`_PERSONA_REGULATORIO`)
- Spec: `docs/agente/agentes_site/02_regulatorio.md`
- Curadoria RAG: `agents_site/specs/SPEC_RAG_AGENTES_SITE.md`
- Fontes versionadas: `docs/agente/agentes_site/rag/regulatorio_*.txt`, `mapa_uf_cref_registro.txt`

### 2.2 Já alinhado com Zero Math / expert system

| Peça Zero Math | Estado no Regulatório |
|---|---|
| Knowledge Base dedicada | ✅ Store próprio (não mistura com mercado) |
| Grounding obrigatório | ✅ “SEMPRE chame a tool antes de afirmar” |
| OWA em lacuna | ✅ “base não trouxe → oriente CREF/prefeitura; não invente” |
| Explanation / auditabilidade | ✅ Carimbo legal + filtro de fonte proibida |
| Manutenção / consistência | ✅ Processo de purga+ingest (ex.: matou `regulatorio_valores_crefs`) |
| Escopo fechado (narrow expert) | ✅ Só CREF/Lei/licenças; redireciona o resto |
| Modelo factual | ✅ Flash + temperatura 0.2 |

### 2.3 O que *parece* regra, mas ainda é prosa

Os `.txt` já carregam lógica de especialista (ex.: “nunca mande registrar num CREF que ainda não opera”; transição CREF23–27 até 02/01/2027). Isso **não é motor de inferência**: depende do ranking do retrieval + do LLM aplicar a frase. O caso Paraíba / CREF10 mostrou que retrieval + curadoria resolvem muito — mas a regra ainda não é executável.

### 2.4 Benchmark interno: Responsável Técnico

O Técnico já separa KB e engine melhor:

| Camada | Técnico | Regulatório |
|---|---|---|
| KB qualitativa | catálogo Vertex | docs CONFEF/Lei Vertex |
| Engine determinística | `dimensionar_cardio_por_pico`, `dimensionar_musculacao`, `calcular_equipamentos_por_area` | ❌ nenhuma |
| Working memory / slots | “pergunte só o que muda a resposta” (pico, m²) | quase só “se não tiver município, não cite exigência municipal” |

**Conclusão:** o padrão GymSite certo já existe no time — o Regulatório ainda não o adotou.

---

## 3. O que pode (e vale) implementar — priorizado

### P0 — Tabelas fechadas como FunctionTools (CWA local) ✅ FEITO

**Implementado:** `tools/regulatorio_lookup.py` + seeds em `tools/regulatorio_seeds/`;
wrappers em `agents_site/tools.py`; wire ADK (`agents_site/agent.py`) + Consultor
(`consultor_engine.py`). Testes: `tests/agents_site/test_regulatorio_lookup_p0.py`.

Tools:

1. `resolver_cref_por_uf(uf, data_ref?)`  
   - Retorna: `cref_registro`, `cref_futuro?`, `em_transicao`, `vigencia_futuro`, carimbo.  
   - Fonte: seed de `mapa_uf_cref_registro.txt` (Res. CONFEF 623–627/2026).

2. `consultar_anuidade_pj_cref(cref_ou_uf, exercicio?)`  
   - Valor-base nacional + variações regionais **só quando curadas**; senão `status=consultar_regional`.  
   - Fonte: seed de `regulatorio_anuidades_processo_2026.txt` / Res. CONFEF 596/2025.

Efeito prático: pergunta “qual CREF da Paraíba?” deixa de depender de chunk lucky — a tool devolve o fato; o LLM só explica.

### P1 — Script + checklist (backward chaining leve)

Meta típica do usuário: *“O que eu preciso pra abrir?”* / *“Posso ser dono sem ser EF?”*.

Tool candidata:

`checklist_abertura_academia(uf, municipio=None, tem_profissional_ef=None, …)`

Retorno estruturado (working memory + conclusão parcial):

```text
meta: apto_a_operar
passos (script):
  1. constituição PJ / Junta
  2. CNPJ ativo
  3. alvará local + sanitária + bombeiros   [OWA se município ausente]
  4. RT (Lei 9.696 / Res. CONFEF 134)      [slot tem_profissional_ef]
  5. registro PJ no CREF da UF             [chama resolver_cref_por_uf]
status por passo: satisfeito | faltando | desconhecido
proximo_dado_util: "informe a cidade" | "tem RT indicado?"
```

Isso é **backward chaining pragmático**: parte da meta “abrir legalmente”, decompõe em subgoals, marca o que a KB/tabela sabe e o que fica unknown (OWA).

Não precisa de Prolog: um checklist ordenado + regras IF–THEN em Python cobre 80% das perguntas de abertura.

### P2 — Frame de conversa (slots)

Formalizar working memory do Regulatório (espelhar disciplina do Técnico):

| Slot | Quando pedir | O que libera |
|---|---|---|
| `uf` | CREF / anuidade regional | lookup determinístico |
| `municipio` | alvará / AVCB / sanitária | citação municipal com carimbo |
| `tem_rt` / sócio é EF? | “posso ser só investidor?” | regra RT vs. propriedade |
| `exercicio` | anuidade | janela do carimbo |

Regra de ouro (já no Técnico): **perguntar só o slot que muda a estrutura da resposta**.

### P3 — Explanation facility além do carimbo

Quando houver tools de regra, devolver `regras_aplicadas: ["UF_EM_TRANSICAO", "RT_OBRIGATORIO"]` no JSON da tool. A UI/carimbo já explica *fonte*; a lista de regras explica *por quê* — ponto forte clássico dos expert systems (Zero Math).

### P4 — Consistência da KB (knowledge engineering)

Já feito na mão (purga de doc obsoleto). Automatizável depois:

- seed estruturado vs. trechos RAG: teste N≥3 de recuperação por UF;
- lint: proibir dois valores de anuidade sem `janela` diferente;
- gate de ingest: doc novo não entra se contradizer tabela seed sem `supersedes`.

Isso ataca o aviso Zero Math: à medida que a KB cresce, **conflito e ambiguidade** viram o custo principal — não o LLM.

---

## 4. O que não faz sentido (agora)

| Ideia Zero Math | Por que não encaixa no Regulatório GymSite |
|---|---|
| **Prolog / FOL completo / unificação clássica** | Domínio estreito (checklist + lookups). Custo de manutenção >> ganho; time já padronizou FunctionTools. |
| **Ontologia OWL / reasoner pesado** | Municipal é incompleto por natureza; ontologia nacional falsa dá sensação de cobertura. |
| **Closed World Assumption global** | Tratar “não está no RAG” como “não é exigido” inventaria ausência de alvará/AVCB. **OWA permanece default** fora das tabelas fechadas. |
| **Commonsense reasoning livre** | Em compliance, “senso comum” = alucinação de exigência. Preferir abstenção. |
| **Fuzzy rules para obrigação legal** | Exigência legal é crisp (obrigatório / não / desconhecido). Fuzzy só faria sentido em *score de risco* futuro — não no chat de “preciso ou não”. |
| **Forward chaining exaustivo a cada turno** | Zero Math alerta: gera conclusões irrelevantes. No chat, preferir **goal-driven** (backward / checklist da pergunta). |
| **BDI / Memory Networks / MemNet** | Camada errada: orquestração de agente e memória neural não resolvem CREF/anuidade. |
| **Substituir RAG por só regras** | Prosa legal (interpretação Lei 9.696, ressalvas, “não substitui consulta”) continua melhor em documento curado + LLM narrador. Híbrido vence. |
| **Misturar zoneamento LUOS do relatório (A6) no chat Regulatório sem contrato** | Zoneamento é viabilidade de **ponto** (pipeline). Chat Regulatório = abertura/CREF. Cruzar sem tool dedicada e carimbo municipal vira ruído. |

---

## 5. Desenho-alvo (híbrido alinhado à Zero Math)

```
                    ┌─────────────────────────────┐
  Working Memory    │ uf, município, slots RT…    │
  (conversa)        └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  Tabelas CWA              Script/checklist            RAG OWA
  resolver_cref_*          checklist_abertura_*        consultar_base_regulatoria
  anuidade_pj_*            (regras IF–THEN Python)     (prosa Lei/Res./licenças)
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   ▼
                         Inference “engine”
                    (FunctionTools + ordem fixa)
                                   │
                                   ▼
                         LLM narrador + carimbo
                    (explica; não inventa número/norma)
```

Espelha a separação clássica: **KB atualizável** (docs + seeds) / **engine estável** (tools) / **UI** (chat + carimbos).

---

## 6. Critérios de sucesso (quando for implementar)

1. Pergunta “CREF da UF X” → tool determinística chamada; resposta correta **sem** depender do top-4 do Vertex.
2. “Anuidade PJ 2026” → valor só se a tool/tabela tiver carimbo; senão abstenção explícita.
3. “O que preciso pra abrir em {cidade}?” → checklist com passos `desconhecido` onde municipal faltar — **nunca** “não precisa de alvará”.
4. Trajetória ADK: 5 perguntas de `02_regulatorio.md` passam com tool certa + citação válida em `carimbo.py`.
5. Teste primeiro vermelho (AssertionError), depois verde — padrão do repo.

---

## 7. Ordem sugerida de entrega (sem estimativa de calendário)

1. Seed JSON do mapa UF→CREF + tool `resolver_cref_por_uf` + testes das 27 UFs (+ casos transição).  
2. Seed anuidade-base + tool `consultar_anuidade_pj_*` + teste Res. 596/2025.  
3. Instrução do agente: para CREF/anuidade **obrigar** essas tools (RAG só para prosa/contexto).  
4. `checklist_abertura_academia` + disciplina de slots.  
5. Só então expandir RAG municipal (exemplos SP/Fortaleza/…) — sem CWA.

---

## 8. Próximos agentes (fora deste doc, mesma lente)

| Agente | Já tem “engine”? | Primeiro passo análogo |
|---|---|---|
| Responsável Técnico | ✅ sim (dimensionamento) | Manter; frames de mix já parcialmente no prompt |
| Arquiteto / Engenheiro | parcial (`calcular_sanitarios_*`) | Mais lookups NBR fechados; OWA no COE municipal |
| Mercado | tools de dado ao vivo | Não virar expert system legal; saturação já é determinística |

Regulatório é o **melhor primeiro alvo**: domínio normativo estável, tabelas fechadas óbvias, dor histórica de retrieval, e ainda zero FunctionTool além do RAG.
