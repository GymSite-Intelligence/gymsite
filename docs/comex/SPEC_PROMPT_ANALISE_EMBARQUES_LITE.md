# Prompt / wizard adaptado — Análise de Embarques Lite (Vectra)

Espelho do agente Logcomex (`POST /v1/agent-api-execute/{agent_id}/{prompt_id}`),
reescrito para o que **conseguimos entregar** com Comex Stat + RFB (L2), sem fingir BL.

## O que o endpoint Logcomex é

| Peça | Leitura |
|---|---|
| URL | `https://api.logcomex.ai/v1/agent-api-execute/{agent_id}/{prompt_id}` |
| IDs no link | `0413538f-…` = **agent_id**, `646894b6-…` = **prompt_id** |
| Auth | API key obrigatória (`401 Missing or invalid API key` sem header) |
| Poll | `GET /agent-api-execute/{request_id}` (async) |
| Wizard `{:wizard}` | Form DSL → preenche o input schema → agente consulta **base BL/embarquies** deles |

O **output schema** que você colou espelha o **input** (eco dos filtros). O resultado de negócio (tabela TEU/importador) vem **depois**, no dataset da execução — não está nesse schema.

## Matriz: campo Logcomex → nosso stack

| Campo | Logcomex (BL) | Vectra Lite | Ação |
|---|---|---|---|
| `centro_da_analise=Empresa` | consignatário/shipper nominal | L2 RFB candidatos + score | **manter** (com carimbo “candidato”) |
| `centro_da_analise=Rota` | porto origem→destino | Stat: país origem + URF destino | **manter** (porto CN fraco) |
| `centro_da_analise=HS Code` | HS/NCM | Stat NCM/SH4 | **manter** (default nosso) |
| `centro_da_analise=Player logístico` | armador/agente | **sem fonte** | **remover** no lite |
| `tipo=Evolução TEUS` | série BL | Stat kg→TEU estimado | **manter** |
| `tipo=Principais Rotas` | rotas BL | Stat país×URF | **manter** |
| `tipo=Empresas para prospecção` | ranking importadores | L2 recall/candidatos | **manter** (core) |
| `tipo=Análise dos meus clientes` | CRM+BL | fora do escopo v0 | **adiar** |
| `tipo=Identificar players logísticos` | armador/agente | **sem fonte** | **remover** |
| `tipo_embarque` Direto/House/Master | BL | **sem fonte** | **remover** |
| `pais_dados` | multi-país | só Brasil (Stat) | fixar **Brasil** |
| Coluna Shipper/Exportador | sim | não | omitir ou `null` |
| Coluna Player/Armador/Agente | sim | não | omitir |
| Coluna Consignatário | sim | candidato RFB | com `nivel=candidato` |
| Coluna TEUs | BL | kg Stat / 26500 | `teus_estimados` + método |
| Coluna Porto embarque | Ningbo… | só país (Stat) | `pais_origem` |

---

## Wizard adaptado (prompt UX)

```text
{:wizard}

{Filtros:section|Recorte da análise Company Intel Lite}

Centro da análise: {centro_da_analise:Empresa, Rota, HS Code:radio|Centro, defaultValue:HS Code}*.

{empresa:text?if=centro_da_analise=Empresa|Importador (candidato)|Razão social — busca RFB + score; NÃO prova DI}
{rota:text?if=centro_da_analise=Rota|Rota|País de origem e porto/URF de destino (ex: China > Navegantes)}
{hs_code:text?if=centro_da_analise="HS Code"|HS/NCM|Ex: 9506 ou 95069100}*.

Tipo: {tipo_de_analise:Evolução de volume (TEUs estimados),Principais rotas (país×URF),Empresas para prospecção (candidatos RFB):radio|Tipo, defaultValue:Empresas para prospecção}*.

País dos dados: Brasil (fixo — Comex Stat MDIC).
Fluxo: {fluxo:Importação Marítima:radio|Fluxo, defaultValue:Importação Marítima}*.

{Recorte temporal:section|Janela}
{recorte:Relativo, Datas:radio|Recorte, defaultValue:Relativo}* —
{janela:Ultimos 3 meses, Ultimos 6 meses, Ultimos 12 meses, Ultimos 24 meses:radio?if=recorte=Relativo|Janela, defaultValue:Ultimos 3 meses}*
{mes_ano_inicio:monthyear?if=recorte=Datas|Início}
{mes_ano_fim:monthyear?if=recorte=Datas|Fim}*.

{Análise:section|Saída}
{mais_informacoes:textarea|Contexto|Ex: foco SC / academias / NCM 9506}
JSON para API? {api:Sim, Não:radio|API JSON, defaultValue:Sim}*.

Colunas: {colunas:Ano e mês,Importador candidato,CNPJ,Cidade sede,UF,HS/NCM,País origem,URF/porto destino,TEUs estimados,Score candidato,Fonte/carimbo:multiselect|Colunas|selectAll}*.
```

---

## Input schema (nosso)

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": [
    "centro_da_analise",
    "tipo_de_analise",
    "pais_dados",
    "fluxo",
    "recorte",
    "api",
    "colunas"
  ],
  "properties": {
    "centro_da_analise": {
      "type": "string",
      "enum": ["Empresa", "Rota", "HS Code"],
      "default": "HS Code"
    },
    "empresa": { "type": ["string", "null"] },
    "rota": { "type": ["string", "null"], "description": "ex: China > Navegantes" },
    "hs_code": { "type": ["string", "null"], "description": "9506 ou 95069100" },
    "tipo_de_analise": {
      "type": "string",
      "enum": [
        "Evolução de volume (TEUs estimados)",
        "Principais rotas (país×URF)",
        "Empresas para prospecção (candidatos RFB)"
      ]
    },
    "pais_dados": { "type": "string", "const": "Brasil" },
    "fluxo": { "type": "string", "const": "Importação Marítima" },
    "recorte": { "type": "string", "enum": ["Relativo", "Datas"] },
    "janela": {
      "type": ["string", "null"],
      "enum": [null, "Ultimos 3 meses", "Ultimos 6 meses", "Ultimos 12 meses", "Ultimos 24 meses"]
    },
    "mes_ano_inicio": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}$" },
    "mes_ano_fim": { "type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}$" },
    "mais_informacoes": { "type": ["string", "null"] },
    "api": { "type": "boolean", "default": true },
    "colunas": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "Ano e mês",
          "Importador candidato",
          "CNPJ",
          "Cidade sede",
          "UF",
          "HS/NCM",
          "País origem",
          "URF/porto destino",
          "TEUs estimados",
          "Score candidato",
          "Fonte/carimbo"
        ]
      }
    },
    "payload_teu_kg": {
      "type": "number",
      "default": 26500,
      "description": "kg por TEU estimado (ISO 40')"
    }
  }
}
```

---

## Output schema (resultado de negócio — o que falta no Logcomex schema)

O schema Logcomex que você colou só devolve filtros. O nosso deve devolver **dados + carimbo**:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["meta", "filtros", "linhas"],
  "properties": {
    "meta": {
      "type": "object",
      "required": ["fonte_mercado", "fonte_nominal", "janela", "aviso"],
      "properties": {
        "fonte_mercado": { "type": "string", "const": "comex_stat_mdic" },
        "fonte_nominal": { "type": "string", "const": "rfb_basedosdados_candidatos" },
        "janela": { "type": "string" },
        "aviso": {
          "type": "string",
          "const": "Nome/CNPJ = candidato por sede+CNAE+score. Não é comprovação de DI/NCM."
        },
        "teus_metodo": { "type": "string" }
      }
    },
    "filtros": { "type": "object" },
    "linhas": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "ano_mes": { "type": "string" },
          "importador_candidato": { "type": ["string", "null"] },
          "cnpj": { "type": ["string", "null"] },
          "cidade_sede": { "type": ["string", "null"] },
          "uf": { "type": ["string", "null"] },
          "hs_ncm": { "type": ["string", "null"] },
          "pais_origem": { "type": ["string", "null"] },
          "urf_porto_destino": { "type": ["string", "null"] },
          "teus_estimados": { "type": ["number", "null"] },
          "score_candidato": { "type": ["number", "null"] },
          "nivel": {
            "type": "string",
            "enum": ["mercado_agregado", "candidato_rfb", "golden_hit"]
          },
          "carimbo": { "type": "string" }
        }
      }
    },
    "resumo": {
      "type": "object",
      "properties": {
        "teus_estimados_total": { "type": "number" },
        "n_linhas": { "type": "integer" },
        "recall_vs_golden": { "type": ["number", "null"] }
      }
    }
  }
}
```

---

## Exemplo de payload (nosso caso 9506)

```json
{
  "centro_da_analise": "HS Code",
  "hs_code": "9506",
  "empresa": null,
  "rota": null,
  "tipo_de_analise": "Empresas para prospecção (candidatos RFB)",
  "pais_dados": "Brasil",
  "fluxo": "Importação Marítima",
  "recorte": "Datas",
  "janela": null,
  "mes_ano_inicio": "2026-07",
  "mes_ano_fim": "2026-07",
  "mais_informacoes": "Foco SC portos Navegantes/Itajaí/Itapoá; gabarito golden 12 importadores",
  "api": true,
  "colunas": [
    "Importador candidato", "CNPJ", "Cidade sede", "UF",
    "HS/NCM", "URF/porto destino", "TEUs estimados", "Score candidato", "Fonte/carimbo"
  ],
  "payload_teu_kg": 26500
}
```

Roteamento interno sugerido:

1. `tipo=Evolução…` → Comex Stat `/general` monthDetail + kg→TEU  
2. `tipo=Principais rotas` → Stat country × URF  
3. `tipo=Empresas…` → L2 `tools/comex_l2_candidatos.py` (+ opcional cruzar TEU Stat da **sede**, não do CNPJ)

---

## Como chamar o Logcomex de verdade (se tiver key)

```http
POST https://api.logcomex.ai/v1/agent-api-execute/0413538f-265f-4a08-8f64-09c24faaf506/646894b6-123a-43b9-8f75-da3a4f777073
Authorization: <API_KEY>
Content-Type: application/json
```

Body = input schema deles (com `tipo_embarque`, `player_logistico`, etc.).  
Sem key não dá para inspecionar o dataset de saída — só o contrato do form.

## Decisão de produto

| Caminho | Quando |
|---|---|
| **Adaptar o prompt (este doc)** | construir nosso agente/API lite |
| **Assinar + chamar Logcomex** | precisar shipper, armador, House/Master, porto CN |
| **Híbrido** | Stat+L2 no dia a dia; Logcomex pontual para validar golden |
