# Spec self-review (canônico)

> Adotada 2026-08-06. **Toda** design spec criada ou materialmente revisada termina com self-review **antes** de pedir aprovação humana e **antes** de `writing-plans`.

## Onde

- `docs/superpowers/specs/*-design.md` (padrão superpowers / brainstorming)
- Specs longas em `agents/specs/SPEC_*.md` quando forem design de feature (não só contrato de agente)

## Gate

Não considerar a spec “pronta” sem:

1. Rodar o checklist abaixo
2. Corrigir achados **inline** na própria spec
3. Acrescentar seção final `## Self-review` (data + resultado: ok / o que foi corrigido)

Sem `## Self-review` → spec incompleta.

## Checklist (obrigatório)

1. **Placeholder:** TBD, TODO, “depois a gente vê”, seção vazia, requisito vago → fechar ou cortar do escopo.
2. **Consistência:** decisões vs waves vs aceite vs “fora” — sem contradição.
3. **Escopo:** cabe em um plano (ou waves explícitas)? Se for plataforma multi-subsistema → decompor specs.
4. **Ambiguidade:** requisito com 2 leituras → escolher uma e escrever.
5. **Aceite testável:** cada wave tem critério que dá pra falhar/passar.
6. **Fora explícito:** o que *não* entra (evita creep na implementação).

## Relação com skills

| Momento | Skill / passo |
|---|---|
| Criar design | `brainstorming` → grava spec → **este self-review** |
| Plano | `writing-plans` (cobertura spec→task) — **depois** do self-review |
| Código | review vs plano — não substitui self-review da spec |

Não existe skill separada “analisa specs”: o self-review **é** o passo canônico, registrado no arquivo.

## Depois da implementação visual

Mudança PDF/UI → [preview-aprovacao.md](preview-aprovacao.md) (artefato em `docs/superpowers/previews/` antes do ok humano).
