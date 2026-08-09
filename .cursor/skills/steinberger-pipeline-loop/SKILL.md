---
name: steinberger-pipeline-loop
description: >-
  Loop engineering (Steinberger/OpenClaw) para cumprir contratos unitários
  do pipeline A0–A9. Use quando o usuário pedir /goal no agente, rodar verifier
  pytest por agente, ou avançar a lista A0→A9 com maker/checker.
---

# Steinberger Pipeline Loop — GymSite A0–A9

## Ideia

Não promptar o agente “até ficar bom”. Desenhar **ciclos**:

1. **Tarefa** delimitada (ex.: A0 cumprir contrato)
2. **Verifier** objetivo (`pytest tests/test_aN.py` → exit 0)
3. **Paragem** só com evidência de terminal
4. **Anti-racionalização:** proibido editar o teste para passar

Primitivas (lista Peter Steinberger / loop engineering):

| Primitiva | Aqui |
|-----------|------|
| Automação /goal | prompt em `prompts/aN.md` |
| Verifier gate | `tests/test_aN.py` (benchmark fixo) |
| Skills | este SKILL + domínio gymsite-pipeline |
| Subagentes | maker (edita agent) / checker (só lê pytest) |
| Estado | `.superpowers/sdd/pipeline-loop-progress.md` |

## Processo por agente (N = 0…9)

1. Ler `prompts/a{N}.md` (se existir) — é o `/goal`.
2. **OBSERVAR:** rodar verifier (comando no prompt; venv do projeto).
3. **AGIR:** 1 mudança pontual no arquivo de implementação (nunca no teste).
4. **VERIFICAR:** re-rodar pytest.
5. **DECIDIR:** 100% verde → marcar progresso + próximo agente; senão repetir (máx 5 iterações). Se 5 falhas → STOP e reportar.

### Pytest (Windows / este repo)

```powershell
c:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/test_a0.py -q --tb=short -x
```

Flags obrigatórias no verifier ([docs](https://docs.pytest.org/en/stable/how-to/usage.html)):

| Flag | Por quê |
|------|---------|
| `-q` | menos cabeçalho → menos tokens |
| `--tb=short` | só arquivo/linha/assert |
| `-x` / `--maxfail=1` | uma falha por iteração |
| exit `0` | /goal atingido |
| exit `1` | falha → próxima iteração |
| exit `2`/`4` | comando/ambiente — consertar antes |

Opcional no meio do loop: `-k "nome_do_teste"` p/ focar uma assert.

Nunca `python tests/test_a0.py` com Python global.

### Anti-racionalização (mesa)

- PROIBIDO alterar `tests/test_aN.py` para passar.
- PROIBIDO “skip” o verifier.
- PROIBIDO dizer que passou sem colar saída do pytest.
- Warning terceiro = `pytest.ini` filterwarnings; warning nosso = fix código.

## Ordem da esteira (frente)

```
A0 → A1 → A2 → A3a → A3b → A4 → A6 → A9
(A5/A7/A8 fora do Sequential de viabilidade — prompts opcionais depois)
```

Só avance de N para N+1 quando `tests/test_aN.py` estiver verde e o progresso atualizado.

## Esteira 2 — loop reverso (contrato → consumidor → entradas)

Depois que A0–A9 estão verdes, rodar o loop **de trás pra frente**:

```
A9 → A6 → A4 → A3b → A3a → A2 → A1 → A0 → entrypoint
```

Para cada agente, o mapa responde:

| Pergunta | Campo |
|----------|--------|
| O que produz? | `writes` (contrato) |
| Quem depende disso? | `consumers_of(key)` |
| De que precisa pra rodar? | `reads` + produtor |

| Artefato | Caminho |
|----------|---------|
| Fonte do grafo | `tools/pipeline_deps.py` |
| Gate | `tests/test_pipeline_deps.py` |
| /goal | `prompts/deps-reverse.md` |
| Cartões vivos | `.superpowers/sdd/pipeline-deps-reverse.md` |

```powershell
c:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/test_pipeline_deps.py -q --tb=short -x
```

Invariantes do gate: toda entrada tem produtor; toda escrita tem consumidor (ou é terminal); uma chave = um dono; o `.py` do agente cita as chaves.

## Arquivos

| Gate | Implementação |
|------|----------------|
| `tests/test_a0.py` | `agents/a0_context_builder.py` |
| `tests/test_a1.py` | `agents/a1_geoscout.py` (+ macros se o gate exigir) |
| … | … |
| `tests/test_pipeline_deps.py` | `tools/pipeline_deps.py` (+ agentes se wiring quebrou) |

Gates ainda não criados: criar **teste primeiro** (TDD), depois loop.

## Memória

Atualizar `.superpowers/sdd/pipeline-loop-progress.md`:

```text
A0: complete (pytest 4 passed, YYYY-MM-DD)
A1: pending
deps-reverse: complete|pending
```
