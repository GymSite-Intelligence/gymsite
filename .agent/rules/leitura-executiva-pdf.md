# Leitura executiva no PDF (canônico)

> Adotada 2026-08-07. Todo bloco numérico do relatório que o **cliente** lê precisa de **leitura em português de negócio**, no padrão do estudo (Potencial · Modelo · …): prosa + carimbo. Tabela sozinha com jargão interno = entrega inválida.

## Gate

Seção nova ou alterada em `pdf/html_builder.py` **não passa** preview se:

1. Rótulos usam jargão de engenharia (`pool`, `form × pen.`, `matr/m²`, `proxy`, `fallback`, IDs de param) **sem** tradução ao lado  
2. Coluna de valor **não diz a unidade** (ex.: “alunos estimados”, “R$/mês”, “academias”)  
3. Falta **bloco de leitura** por tópico (o que o número significa + o que fazer)  
4. Faixas etárias / mix / bases aparecem só como código (`15-24`) sem nome humano (Jovem · Core · Maduro · Silver)

## Formato obrigatório por seção analítica

| Camada | O quê |
|---|---|
| **Título** | Nome de negócio (“Quem ainda pode matricular”, não “Pool primário”) |
| **Número** | Valor + **unidade explícita** |
| **Leitura** | 2–5 frases: o que é · o que NÃO é · implicação pra decisão |
| **Carimbo** | valor · base · fonte · janela (pode ficar em nota menor) |

Ordem típica Absorção / saturação:

1. Capacidade da **sua** unidade  
2. Capacidade das academias **já no bairro**  
3. Alunos potenciais no **público do formulário** (faixas nomeadas)  
4. Alunos potenciais nas **outras idades** (faixas nomeadas — informam modelo)  
5. **Conclusão** (há aluno novo / misto / só tirando do parque)

## Proibido no texto ao cliente

`pool`, `pen.`, `interesse×`, `matr_m2`, `area_proxy`, `gate_espacial`, `fallback_pop_total`, `rotulo`, `fresco|misto|roubo` como ID cru.

IDs internos ficam no state/JSON; PDF só vernáculo.

## Relação

| Regra | Papel |
|---|---|
| `preview-aprovacao.md` | Gerar `gerar_html` + **abrir** browser |
| **este arquivo** | Copy / estrutura da leitura que o cliente entende |
| carimbo P-000 / CLAUDE | Número sem base rotulada = doença |

## Checklist do agente

1. Tabela (se houver): labels humanos + coluna “Alunos (estimativa)” ou unidade clara  
2. Blocos de leitura por tópico (não uma linha “Leitura” genérica no rodapé da tabela)  
3. Faixas etárias detalhadas com nome  
4. Preview `gerar_html` + abrir browser  
5. Teste HTML asserta frases humanas, não só chaves técnicas
