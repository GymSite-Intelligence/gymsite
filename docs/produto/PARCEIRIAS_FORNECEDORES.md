# Parcerias com Fornecedores — Marketplace B2B no Playbook

> Como integrar fornecedores de insumos, equipamentos e serviços ao playbook de abertura, criando valor para o empreendedor e receita para a plataforma.

---

## 1. Conceito

O playbook de abertura não é apenas uma lista de tarefas — é um **guia de compras inteligente**. Em cada etapa do processo, o empreendedor precisa adquirir produtos ou contratar serviços. Parcerias estratégicas permitem:

1. **Recomendar fornecedores confiáveis** (curadoria da plataforma)
2. **Oferecer descontos exclusivos** (poder de negociação da base de usuários)
3. **Simplificar a jornada** (menor fricção na decisão de compra)
4. **Gerar receita** (comissão, afiliado, lead generation, sponsored placement)

---

## 2. Exemplo Prático: Unicold (Climatização)

### Contexto
Tarefa no playbook: **"Instalar sistema de climatização"** (categoria: OBRAS ou EQUIPAMENTOS)

### Sem parceria
Empreendedor precisa:
1. Pesquisar empresas de ar condicionado no Google
2. Cotar 3 fornecedores
3. Avaliar qualidade sem referência
4. Negociar preço sozinho

### Com parceria Unicold
```
┌─────────────────────────────────────────────────────────────┐
│  🔧 Tarefa: Instalar sistema de climatização                │
│                                                             │
│  Descrição: ...                                             │
│                                                             │
│  💡 SUGESTÃO DE PARCEIRO                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ❄️ Unicold — Parceiro GymSite                       │   │
│  │                                                      │   │
│  │  Equipamentos de climatização para ambientes        │   │
│  │  críticos: academias, data centers, food service.   │   │
│  │                                                      │   │
│  │  ✅ Desconto exclusivo: 12% para projetos GymSite   │   │
│  │  ✅ Instalação inclusa em projetos > R$ 50.000      │   │
│  │  ✅ Garantia estendida: 3 anos                       │   │
│  │                                                      │   │
│  │  [Solicitar orçamento]  [Ver catálogo]               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📋 Checklist                                               │
│  ☐ Definir BTUs necessários por área                        │
│  ☐ Solicitar orçamento Unicold                              │
│  ☐ Comparar com mais 2 fornecedores (opcional)              │
│  ☐ Aprovar e agendar instalação                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Modelo de Parceria

### 3.1. Tipos de Parceria

| Tipo | Descrição | Receita para GymSite | Custo para Fornecedor |
|------|-----------|----------------------|----------------------|
| **Lead Generation** | Fornecedor paga por lead qualificado (empreendedor que solicitou orçamento) | R$ 50-150/lead | Médio |
| **Afiliado/Comissão** | GymSite recebe % do valor fechado | 3-8% do contrato | Alto (só paga se vender) |
| **Sponsored Placement** | Fornecedor paga para aparecer destacado na tarefa | Mensalidade fixa (R$ 500-2.000) | Baixo (previsível) |
| **White-label Integrado** | Produto/serviço do fornecedor embutido no playbook como "padrão recomendado" | Taxa de licenciamento anual | Médio |
| **Conteúdo Patrocinado** | Fornecedor cria guia/template exclusivo para o playbook | Taxa de conteúdo | Baixo |

### 3.2. Recomendação

**Fase 1 (agora):** Lead Generation — mais fácil de vender para fornecedores, risco zero para eles (pagam só pelo contato).

**Fase 2:** Afiliado/Comissão — quando tivermos volume de projetos e rastreamento de conversão.

**Fase 3:** Sponsored Placement + White-label — quando a base for grande o suficiente para justificar mensalidade.

---

## 4. Categorias de Fornecedores Relevantes

| Categoria do Playbook | Tipo de Fornecedor | Exemplos |
|----------------------|-------------------|----------|
| **IMOBILIÁRIO** | Imobiliárias corporativas, corretores especializados | Lofty, Loft |
| **LEGAL** | Escritórios de advocacia, despachantes | LegalStart, Abilio Advocacia |
| **OBRAS** | Construtoras, arquitetos, engenheiros | Construtora local |
| **OBRAS** | **Climatização** | **Unicold**, Carrier, Daikin |
| **EQUIPAMENTOS** | Fabricantes de aparelhos musculação | Wellness, Riguetto, Super Tech |
| **EQUIPAMENTOS** | Fabricantes de cardio | Life Fitness, Technogym, Movement |
| **EQUIPAMENTOS** | Fabricantes de pilates | Metalife, Physio Pilates, Balanced Body |
| **EQUIPAMENTOS** | Pisos e acabamentos | PaviFlex, Rubberflex |
| **TECNOLOGIA** | Software de gestão | W12, WodGuru, Gympass |
| **TECNOLOGIA** | Catracas e controle de acesso | iDAccess, ZK Teco |
| **TECNOLOGIA** | CFTV | Intelbras, Hikvision |
| **RH** | Plataformas de recrutamento | Gupy, LinkedIn Talent |
| **MARKETING** | Agências digitais, designers | Agências locais |
| **FINANCEIRO** | Contabilidade online | Contabilizei, O Contador |
| **FINANCEIRO** | Fintechs de crédito | BizCapital, Magnetis |
| **FINANCEIRO** | Seguradoras | SulAmérica, Porto Seguro |
| **OPERACIONAL** | Suplementos e nutrição | Growth, Max Titanium |
| **OPERACIONAL** | Uniformes e brindes | Camisaria local |

---

## 5. Arquitetura de Integração no Playbook

### 5.1. Nova Tabela: `parceiros`

```sql
CREATE TABLE parceiros (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome TEXT NOT NULL,
    descricao TEXT,
    logo_url TEXT,
    site_url TEXT,
    telefone TEXT,
    email TEXT,

    -- Categorias atendidas
    categorias TEXT[] NOT NULL,  -- ['OBRAS', 'EQUIPAMENTOS']

    -- Tipo de parceria
    tipo_parceria TEXT NOT NULL DEFAULT 'LEAD_GENERATION'
        CHECK (tipo_parceria IN ('LEAD_GENERATION', 'AFILIADO', 'SPONSORED', 'WHITE_LABEL')),

    -- Lead generation
    lead_valor DECIMAL(12,2),     -- quanto paga por lead
    lead_maximo_mes INT,          -- máximo de leads/mês

    -- Afiliado
    comissao_percentual DECIMAL(5,2),  -- ex: 5.00 = 5%

    -- Sponsored
    valor_mensalidade DECIMAL(12,2),

    -- Desconto para usuário
    desconto_oferecido TEXT,      -- ex: "12% para projetos GymSite"
    desconto_codigo TEXT,         -- código de cupom

    -- Status
    status TEXT NOT NULL DEFAULT 'ATIVO'
        CHECK (status IN ('ATIVO', 'PAUSADO', 'CANCELADO')),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.2. Nova Tabela: `parceiro_leads`

```sql
CREATE TABLE parceiro_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parceiro_id UUID NOT NULL REFERENCES parceiros(id),
    projeto_id UUID NOT NULL REFERENCES user_projects(id),
    tarefa_id UUID REFERENCES tarefas(id),

    -- Dados do lead
    solicitante_nome TEXT,
    solicitante_email TEXT,
    solicitante_telefone TEXT,

    -- Status
    status TEXT NOT NULL DEFAULT 'NOVO'
        CHECK (status IN ('NOVO', 'CONTATADO', 'ORCAMENTO_ENVIADO', 'CONVERTIDO', 'DESCARTADO')),

    -- Valor (se afiliado)
    valor_fechado DECIMAL(12,2),
    comissao_gerada DECIMAL(12,2),

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### 5.3. Como aparece no Playbook

Quando o sistema gera uma tarefa, ele verifica se há parceiros para aquela categoria:

```python
# services/execucao/parceiro_service.py

async def buscar_parceiros_para_tarefa(
    categoria: str,
    uf: str | None = None,
    cidade: str | None = None
) -> list[dict]:
    """
    Retorna parceiros ativos para a categoria da tarefa.
    Se UF/cidade informados, prioriza parceiros locais.
    Ordena por: sponsored first, depois rating, depois recência.
    """
    # Query no Supabase
    pass
```

No frontend, o card de parceiro aparece **abaixo da descrição da tarefa**, como uma sugestão opcional — nunca como obrigação.

---

## 6. Fluxo de Lead para o Fornecedor

```
Empreendedor vê tarefa "Instalar climatização"
    │
    ├──► Vê card do Unicold como parceiro recomendado
    │
    ├──► Clica "Solicitar orçamento"
    │
    ├──► Sistema captura: nome, email, telefone, dados do projeto (m², cidade)
    │
    ├──► INSERT em parceiro_leads (status: NOVO)
    │
    ├──► Email automático para Unicold: "Novo lead: Projeto Cabo Branco, 800m²"
    │
    ├──► Email para empreendedor: "Unicold recebeu sua solicitação. Eles entrarão em contato em 24h."
    │
    └──► Dashboard do parceiro (futuro): lista de leads, status, conversão
```

---

## 7. Benefícios para Cada Parte

| Parte | Benefício |
|-------|-----------|
| **Empreendedor** | Fornecedores pré-curados, descontos exclusivos, menos tempo pesquisando |
| **Fornecedor (Unicold)** | Leads qualificados (já estão abrindo academia), dados do projeto (m², local), marca associada à plataforma de confiança |
| **GymSite** | Receita recorrente por lead/comissão, retenção de usuário (playbook mais valioso), diferencial competitivo |

---

## 8. Decisões

| Código | Decisão |
|--------|---------|
| **PAR-001** | Parceiros NUNCA substituem a tarefa — são sugestões opcionais. O empreendedor sempre pode escolher outro fornecedor. |
| **PAR-002** | Transparência total: sempre mostrar que é "Parceiro GymSite" e o tipo de relação (lead gen, afiliado, etc.). |
| **PAR-003** | Qualidade primeiro: parceiros precisam ser aprovados pela plataforma (não é "pague e apareça"). |
| **PAR-004** | Badge de desconto real: parceiro deve oferecer vantagem real vs. preço de mercado. |
| **PAR-005** | Rating de parceiro: empreendedor avalia fornecedor após contratação. Parceiros < 4 estrelas são removidos. |

---

## 9. Checklist de Implementação (Futuro)

- [ ] Criar tabela `parceiros`
- [ ] Criar tabela `parceiro_leads`
- [ ] Endpoint `GET /api/parceiros?categoria=OBRAS`
- [ ] Endpoint `POST /api/parceiros/{id}/solicitar-orcamento`
- [ ] Componente `ParceiroCard.tsx` no frontend
- [ ] Dashboard de leads para parceiros (futuro)
- [ ] Contrato/pagamento de lead (Stripe/Asaas para B2B)
