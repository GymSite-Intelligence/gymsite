# A9 — Especificação Visual dos Selos de Confiança (PDF)

> Desenho exato dos *badges* de confiança usados no relatório PDF do A9. Define geometria, cores, tipografia, espaçamento e variantes. Complementa `docs/A9_DATA_CONFIDENCE.md` (conceito) e `docs/A9_REPORT_DESIGN.md` (paleta/layout). Unidades em pontos PDF (pt), onde 1 pt = 1/72 pol.

## 1. Anatomia do selo

```
  +-------------------------------------+
  | [•]  TEXTO DO SELO                  |
  +-------------------------------------+
   ^   ^                              ^
   |   |                              +-- padding direito 8pt
   |   +-- gap ícone→texto 5pt
   +-- ponto/ícone 6pt diâmetro
```

Componentes: container (pill arredondada), marcador (ponto circular ou ícone), rótulo de texto.

## 2. Geometria (dimensões fixas)

| Propriedade | Valor |
|---|---|
| Altura do container | 16 pt |
| Padding horizontal | 8 pt (esq. e dir.) |
| Padding vertical | 3 pt |
| Raio de canto (border-radius) | 8 pt (pill — metade da altura) |
| Diâmetro do ponto marcador | 6 pt |
| Gap ícone → texto | 5 pt |
| Espessura da borda | 0.75 pt |
| Largura | automática (hug do conteúdo); mín. 54 pt |

## 3. Variantes (3 níveis de confiança)

Cada variante define cor da borda+ícone+texto (foreground) e cor de fundo (background, versão clara da mesma matiz).

### 3.1 Alta confiança — "DADO MEDIDO"
| Token | HEX |
|---|---|
| Foreground (texto, ícone, borda) | `#0D9488` (TEAL) |
| Background | `#CCFBF1` (TEAL_LIGHT) |
| Ícone | círculo preenchido |
| Rótulo | DADO MEDIDO |

### 3.2 Confiança média — "ESTIMATIVA"
| Token | HEX |
|---|---|
| Foreground | `#E8751A` (ORANGE) |
| Background | `#FDEBD8` (orange 10% — derivado) |
| Ícone | círculo com contorno (metade preenchido) |
| Rótulo | ESTIMATIVA |

### 3.3 Baixa confiança — "PROJEÇÃO"
| Token | HEX |
|---|---|
| Foreground | `#64748B` (SLATE) |
| Background | `#F1F5F9` (CARD_BG) |
| Ícone | círculo vazado (apenas contorno, tracejado) |
| Rótulo | PROJEÇÃO |

## 4. Tipografia do rótulo

| Propriedade | Valor |
|---|---|
| Família | Helvetica-Bold (consistente com theme.py) |
| Tamanho | 6.5 pt |
| Caixa | MAIÚSCULAS |
| Tracking (letter-spacing) | +0.4 pt |
| Cor | = foreground da variante |
| Alinhamento vertical | centralizado no container |

## 5. Posicionamento no relatório

- **Inline ao lado da métrica:** alinhado à direita do número, baseline compartilhada, margem-esquerda 6 pt.
- **Em tabelas:** coluna própria "Confiança", selo centralizado na célula.
- **Em cards de KPI:** canto superior direito do card, margem 8 pt das bordas.
- Nunca dois selos na mesma linha de métrica; se houver dúvida, usar o de menor confiança.

## 6. Legenda (rodapé / glossário)

Bloco fixo no rodapé da primeira página de dados, em uma linha horizontal:

```
[• TEAL] Dado medido    [◑ ORANGE] Estimativa calculada    [○ SLATE] Projeção modelada
```

Tipografia da legenda: Helvetica 6.5 pt, cor TEXT `#1E293B`; ícones nas cores das variantes.

## 7. Acessibilidade / impressão P&B

- Diferenciar também pela **forma do ícone** (preenchido / meio / vazado), não só pela cor, garantindo leitura em impressão monocromática.
- Contraste mínimo texto/fundo >= 4.5:1 (todas as combinações acima atendem).

## 8. Regras de uso

1. Todo número derivado de modelagem DEVE exibir selo; dados medidos diretos também.
2. O selo reflete o **menor** nível de confiança entre as entradas que geraram a métrica.
3. Não usar selo em texto narrativo/interpretação (ver opção 9 de `A9_DATA_CONFIDENCE.md`).
4. Cores e formas são fixas; não criar variantes ad-hoc.

---

*Especificação de design — implementável em `pdf/theme.py` (tokens) e `pdf/builder.py` (render dos selos). Nenhuma fonte real é citada.*
