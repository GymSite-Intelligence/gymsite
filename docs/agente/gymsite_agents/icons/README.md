# Ícones dos agentes

**Formato preferido: SVG colado no chat** (eu salvo direto — não preciso de arquivo binário).
Cole o markup `<svg>...</svg>` e eu gravo como `<nome>.svg` aqui. Quando o set estiver
completo, troco o `gymsite-icons.tsx` (sai o robô-placeholder, entra a sua arte) e fio nos
dois configs (`config_handoff.ts` + `config_handoff_site.ts`).

## Pipeline (logado)
| Arquivo | Ícone | Status |
|---|---|---|
| `dados.svg` | robô + gráfico de barras | ✅ recebido |
| `financeiro.svg` | robô + baú de moedas + seta | ✅ recebido |
| `contabilidade.svg` | robô + prancheta + ábaco | ✅ recebido |
| `marketing.svg` | robô + alvo + megafone | ✅ recebido |
| `conhecimento.svg` | robô + livro + engrenagem (RAG) | ✅ recebido |

## Site (degustação)
| Arquivo | Ícone | Status |
|---|---|---|
| `mercado.svg` | robô + mapa de loteamento + pino | ✅ recebido |
| `arquiteto.svg` | robô + prancheta/esquadro/régua | ✅ recebido |
| `engenheiro.svg` | robô + capacete + viga "I" | ✅ recebido |
| `regulatorio.svg` | robô + balança da justiça | ✅ recebido |
| `tecnico.svg` | robô + haltere + prédio | ✅ recebido |

## Marca
- Já no repo: `pdf/assets/logo-gymsite.png` (pin + circuito "GYMSITE INTELLIGENCE"). Não precisa reenviar.

## Formato
- **PNG** transparente quadrado (ideal 256×256) — vira `<img>` no badge.
- ou **SVG** — vira componente (mantém `<IconeX className="h-4 w-4" />`).
- Nomes em minúsculo, sem espaço/acento (kebab), exatamente como a tabela.
