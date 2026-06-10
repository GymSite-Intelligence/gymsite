# Benchmark de Frete — Dados ANTT 2024

## Metadados

| Campo | Valor |
|-------|-------|
| **Data de criação** | 2026-06-05 |
| **Fonte de tarifas** | ANTT — RNDC (Registro Nacional de Transportadores de Cargas) |
| **URL de referência** | https://antt.gov.br/transporte-de-cargas/rndc/tabela-de-fretes |
| **Tipo de carga** | carga_geral (equipamentos fitness) |
| **Script de execução** | `tools/frete_benchmark.py` |
| **Workflow CI** | `.github/workflows/benchmark-frete.yml` |

## Tarifas ANTT 2024 (R$/km)

| Tipo de Carga | Tarifa (R$/km) | Descrição |
|---------------|----------------|-----------|
| `carga_geral` | 0.85 | Equipamentos fitness (barras, anilhas, máquinas) |
| `fracionado` | 1.20 | Kits menores (< 500kg) |
| `lotacao` | 0.65 | Grandes volumes (> 2 toneladas) |
| `expresso` | 1.50 | Transporte urgente (24-48h) |

## Fornecedores Monitorados

| Chave | Nome | Localização | Coordenadas |
|-------|------|-------------|-------------|
| `movement` | Movement Fitness | Cotia / SP | -23.6037, -46.9189 |
| `athletic` | Athletic Brasil | Caxias do Sul / RS | -29.1689, -51.1796 |
| `life_fitness` | Life Fitness | Pinhais / PR | -25.4477, -49.1903 |
| `rhs` | RHS Equipamentos | Rio Claro / SP | -22.4108, -47.5611 |
| `eleiko` | Eleiko (importação) | Santos / SP | -23.9608, -46.3331 |
| `default` | São Paulo (genérico) | São Paulo / SP | -23.5505, -46.6333 |

## Destinos de Benchmark

| Chave | Cidade | Coordenadas |
|-------|--------|-------------|
| `fortaleza_ce` | Fortaleza / CE | -3.7172, -38.5433 |
| `recife_pe` | Recife / PE | -8.0476, -34.8770 |
| `salvador_ba` | Salvador / BA | -12.9714, -38.5124 |
| `brasilia_df` | Brasília / DF | -15.7942, -47.8822 |
| `belém_pa` | Belém / PA | -1.4558, -48.5044 |
| `manaus_am` | Manaus / AM | -3.1190, -60.0217 |
| `porto_alegre_rs` | Porto Alegre / RS | -30.0346, -51.2177 |
| `curitiba_pr` | Curitiba / PR | -25.4284, -49.2733 |
| `niteroi_rj` | Niterói / RJ | -22.8834, -43.1034 |
| `goiania_go` | Goiânia / GO | -16.6864, -49.2643 |

## Resultados (Atualizar a cada execução)

> **Nota:** Os resultados abaixo são exemplos. Execute `python tools/frete_benchmark.py` para gerar dados reais.

### Top 5 Rotas Mais Baratas (carga_geral)

| Posição | Rota | Distância (km) | Custo (R$) | Custo/Aluno (R$) |
|---------|------|----------------|------------|------------------|
| 1 | Movement → Niterói | ~450 | R$ 382,50 | R$ 7,65 |
| 2 | RHS → Brasília | ~850 | R$ 722,50 | R$ 14,45 |
| 3 | Movement → Goiânia | ~900 | R$ 765,00 | R$ 15,30 |
| 4 | Eleiko → Curitiba | ~400 | R$ 340,00 | R$ 6,80 |
| 5 | Life Fitness → Curitiba | ~80 | R$ 68,00 | R$ 1,36 |

### Top 5 Rotas Mais Caras (carga_geral)

| Posição | Rota | Distância (km) | Custo (R$) | Custo/Aluno (R$) |
|---------|------|----------------|------------|------------------|
| 1 | Movement → Manaus | ~3.800 | R$ 3.230,00 | R$ 64,60 |
| 2 | Athletic → Belém | ~3.200 | R$ 2.720,00 | R$ 54,40 |
| 3 | Eleiko → Fortaleza | ~2.800 | R$ 2.380,00 | R$ 47,60 |
| 4 | Movement → Belém | ~2.600 | R$ 2.210,00 | R$ 44,20 |
| 5 | RHS → Salvador | ~1.800 | R$ 1.530,00 | R$ 30,60 |

## Como Executar

### Manual

```bash
# Executar benchmark completo
python tools/frete_benchmark.py

# Executar com fornecedores específicos
python tools/frete_benchmark.py --fornecedores movement rhs eleiko

# Executar com destinos específicos
python tools/frete_benchmark.py --destinos fortaleza_ce recife_pe salvador_ba

# Executar com tipo de carga diferente
python tools/frete_benchmark.py --tipo-carga fracionado

# Salvar em caminho customizado
python tools/frete_benchmark.py --output data/frete_benchmark_custom.json
```

### Via GitHub Actions

O workflow `.github/workflows/benchmark-frete.yml` executa automaticamente às **06:00 UTC (03:00 BRT)** todos os dias.

Para executar manualmente:
1. Acesse **Actions** → **Benchmark Diário de Frete ANTT**
2. Clique em **Run workflow**
3. (Opcional) Configure fornecedores, destinos ou tipo de carga
4. Clique em **Run workflow**

### Ajuste Automático de Escopo

O workflow ajusta automaticamente o número de destinos baseado na taxa de falhas do benchmark anterior:
- **Taxa de falha ≤ 30%**: Executa todos os destinos
- **Taxa de falha > 30%**: Reduz para destinos principais (Fortaleza, Recife, Salvador, Brasília, Curitiba)

## Cache de Distâncias

As distâncias são cacheadas em `tools/cache/distance_matrix/*.json` para reduzir chamadas à API do Google.

- **Custo da API**: $5/1000 elements (Google Maps Platform)
- **Taxa de hit do cache**: ~80-90% após 50 cidades cobertas
- **Validade do cache**: Infinita (distâncias rodoviárias não mudam em horizonte de anos)

## Notas

- Tarifas ANTT são valores médios de mercado — custos reais podem variar ±15%
- Para fretes com pedágios, adicionar ~R$ 0.15/km ao custo estimado
- Regiões Norte/Nordeste podem ter sobretaxa de 20-40% pela logística reversa limitada
