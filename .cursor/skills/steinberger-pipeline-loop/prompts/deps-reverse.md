# /goal — Pipeline deps reverse (contrato → consumidor → entradas)

Faça o mapa em `tools/pipeline_deps.py` cumprir o contrato de
`tests/test_pipeline_deps.py`, e mantenha
`.superpowers/sdd/pipeline-deps-reverse.md` alinhado.

## CONDIÇÃO DE PARADA (VERIFIER GATE)

```powershell
C:\Users\marce\gymsite_intelligence\.venv\Scripts\python.exe -m pytest tests/test_pipeline_deps.py -q --tb=short -x
```

O ciclo só encerra quando **todos** os testes passarem com exit code 0.

## O QUE ESTE LOOP ANALISA (de trás pra frente)

Ordem: **A9 → A6 → A4 → A3b → A3a → A2 → A1 → A0**

Para cada agente, responder e travar no mapa:

1. **Contrato** — quais chaves de state escreve?
2. **Consumidores** — quem lê essas chaves (agente ou persistência/PDF)?
3. **Entradas** — de quais chaves depende, e quem as produz?

## REGRAS INEGOCIÁVEIS

1. PROIBIDO alterar `tests/test_pipeline_deps.py` para passar.
2. Fonte única do grafo = `tools/pipeline_deps.py`.
3. Toda `reads` tem produtor conhecido (agente ou `entrypoint`).
4. Toda `writes` tem consumidor OU está em `TERMINAL_WRITES`.
5. Uma chave = um dono (sem double-write).
6. O `.py` do agente deve mencionar as chaves declaradas.
7. Se o wiring real mudou no agente, atualize o mapa — não o teste.
8. Se o mapa estiver certo e o agente divergiu, corrija o agente.
9. Atualize `PIPELINE_AGENTES.md` §4 quando o mapa mudar.
10. Uma mudança pontual por iteração.

## CICLO POR AGENTE (reverso)

1. [OBSERVAR] Abrir cartão do agente em `pipeline-deps-reverse.md`.
2. [CHECAR] Código do agente confirma writes/reads do mapa?
3. [AGIR] Ajustar mapa OU agente (não o gate).
4. [VERIFICAR] Rodar o pytest do gate.
5. [AVANÇAR] Próximo agente na ordem reversa só com gate verde.
