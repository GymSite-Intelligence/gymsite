# CNO × entrantes CNPJ — integração

**Fonte:** [Cadastro Nacional de Obras (CNO)](https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cno) — Receita Federal.

## O que o CNO traz

| Campo | Uso GymSite |
|-------|-------------|
| Área total (m²) | Porte físico da obra |
| Nome da obra | Match com nome fantasia |
| CEP / logradouro | Cruzamento com CNPJ |
| NI responsável | CNPJ (geralmente **construtora**, raro ser a academia) |

## O que o CNO **não** traz

- Faturamento (não existe — o benchmark A4 usa **matrículas/m²**, não receita CNPJ)
- Garantia de que a obra = unidade que abriu CNPJ no mesmo dia

## Cruzamento (amostragem 50 entrantes — Fortaleza)

Script: `python tools/cno_fitness_tools.py` via `dados_parque_cnpj_para_a0` com `CNO_DATA_DIR`.

| Método | Confiança |
|--------|-----------|
| `cnpj_responsavel` | Alta (raro) |
| `nome_obra_cep8` | Média (ex.: "SMART FIT" no nome da obra) |
| `cep8_multiplas_obras` | Baixa — só faixa min/max m², várias obras no CEP |

**Não usar** match só por prefixo CEP-5 sem filtro de nome — infla área (obras civis grandes na mesma região).

## Capacidade operacional

Quando `area_m2_obra` existe:

```
capacidade ≈ area_m2 × MATRICULADOS_POR_M2[perfil]  # financial_tools.py
```

Mesma lógica do A4 (conservador / realista / agressivo).

## Tempo de obra (início × fim ÷ m²)

O CNO **não** informa previsão de término. Para obras **encerradas** (`situação 15`):

| Campo | Uso |
|-------|-----|
| Data de início | Início da obra |
| Data da situação | **Fim cadastral** (quando passou a encerrada) |

Métrica derivada:

```
dias_por_m2 = (data_fim_cadastral − data_inicio) / area_m2
```

`calcular_benchmark_tempo_obra_cno()` agrega mediana / P25 / P75 por município e por porte (pequena &lt;600 m², média, grande).

Obras **em andamento**: `previsao_encerramento_estimada = inicio + dias_por_m2_mediana × area_m2` (projeção a partir do benchmark local).

Tool: `estimar_previsao_encerramento_obra()`.

## Obras em curso (prospecção)

Situação CNO `01`–`04` → `em_curso` (ativa, execução, paralisada, suspensa).  
`15` → encerrada (referência histórica, não entra na lista de prospecção).

Tool: `listar_obras_fitness_em_curso(cno_dir=...)` — também embutido em `cruzamento_cno.obras_fitness_em_curso`.

## Receita mensal estimada (projeção — não é faturamento CNPJ)

Com área da obra e faixa de ticket (low/mid/premium inferida pelo nome ou manual):

```
matrículas[calibração] = area_m2 × MATRICULADOS_POR_M2[faixa][calibração]
receita_mensal[calibração] = matrículas × ticket_nominal × (1 − inadimplência)
```

Helper: `projecao_demanda_receita_obra()` em `financial_tools.py` — mesma fórmula de `calcular_viabilidade_3_cenarios`.

**Exemplo Selfit ~1.829 m², faixa low (agressivo 3,0 matr/m²):**

| Calibração | Matrículas | Receita/mês est. (ticket R$ 89,90, inad. 6%) |
|------------|------------|-----------------------------------------------|
| Conservador (1,5/m²) | ~2.743 | ~R$ 231k |
| Realista (2,2/m²) | ~4.024 | ~R$ 339k |
| Agressivo (3,0/m²) | ~5.487 | ~R$ 462k |

Rotular sempre como **estimativa / parâmetro de prospecção**.

## Bairro (normalização)

`tools/bairro_normalize.py`:

- `normalizar_bairro()` — chave sem acento/case (`ALDEOTA` = `Aldeota`)
- `bairro_em_alvo()` — match com bairro do relatório (inclui compostos `Cocó / Guararapes`)
- Obras em curso: `listar_obras_fitness_em_curso(..., bairro_filtro=...)` usa o bairro do A0/A6

## Configuração

```env
CNO_DATA_DIR=C:\Users\marce\Downloads\cno_extract
```

Extrair `cno.zip` → pasta com `cno.csv`, `cno_areas.csv`, `cno_cnaes.csv`, `cno_vinculos.csv`.

## Próximos passos (opcional)

1. Indexar só Fortaleza (município 1389) em tabela Supabase `cno_obras_fitness`
2. Match por logradouro normalizado + número
3. Expor `area_m2_obra` na tabela de entrantes do relatório (A6)
