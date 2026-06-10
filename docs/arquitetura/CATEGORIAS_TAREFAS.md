# Categorias de Tarefa — Validação e Definição

> Mapeamento do processo real de abertura de unidades fitness e agrupamento nas categorias do sistema.

---

## 1. Processo Real de Abertura (Desk Research + Domínio)

Mapeamos o processo típico de abertura de 3 tipos de negócio no Brasil. O objetivo é garantir que **nenhuma etapa real fique sem categoria**.

### 1.1. Academia Tradicional (800-1500m²)

**Fase 1 — Estruturação Legal e Imobiliária**
- Abertura de CNPJ (MEI não serve — precisa de Ltda)
- Contrato social com sócios
- Busca e negociação de ponto comercial
- Assinatura de contrato de locação ou compra
- Registro em cartório de imóveis (se compra)
- Consulta viabilidade na prefeitura (zoneamento)

**Fase 2 — Licenciamentos e Regularizações**
- Alvará de funcionamento na prefeitura
- Auto de Vistoria do Corpo de Bombeiros (AVCB/CLCB)
- Licença da Vigilância Sanitária
- Cadastro ambiental (se aplicável)
- Cadastro na ANVISA (se oferecer suplementos ou serviços de estética)
- Registro no CREF (Conselho Regional de Educação Física) para instrutores

**Fase 3 — Projeto e Obras**
- Contratação de arquiteto/engenheiro
- Projeto arquitetônico aprovado
- Projeto elétrico e hidráulico
- Projeto de combate a incêndio
- Obra civil (demolição, alvenaria, acabamento)
- Instalação elétrica e hidráulica
- Piso (vinílico, borracha, etc.)
- Pintura e acabamento
- Vestiários e banheiros

**Fase 4 — Equipamentos e Tecnologia**
- Definição de layout de equipamentos
- Cotação e compra de aparelhos de musculação
- Cotação e compra de cardio (esteiras, bikes, elípticos)
- Cotação e compra de acessórios (halteres, kettlebells, colchonetes)
- Sistema de som e TVs
- Sistema de acesso (catracas, biometria)
- Software de gestão de academia
- Sistema de CFTV

**Fase 5 — Recursos Humanos**
- Definição do organograma
- Contratação de gerente geral
- Contratação de instrutores de musculação
- Contratação de professores de aulas coletivas
- Contratação de recepcionistas
- Contratação de equipe de limpeza
- Treinamento de equipe (protocolos, atendimento, vendas)

**Fase 6 — Marketing e Pré-Lançamento**
- Definição de nome e identidade visual
- Registro de marca no INPI
- Criação de site e redes sociais
- Campanha de pré-lançamento (captação de leads)
- Definição de planos e preços
- Parcerias com empresas locais (corporate)
- Evento de inauguração

**Fase 7 — Financeiro e Administrativo**
- Abertura de conta bancária PJ
- Contratação de contador
- Definição de sistema de gestão financeira
- Negociação de financiamento/linha de crédito
- Contratação de seguros (RC profissional, patrimonial)
- Fluxo de caixa inicial (3-6 meses de reserva)

**Fase 8 — Operações e Abertura**
- Teste de equipamentos
- Treinamento de emergência
- Limpeza final
- Estoque de suplementos/produtos (se houver)
- Uniformes
- Inauguração

### 1.2. Crossfit Box (200-400m²)

Diferenças em relação à academia tradicional:
- **Equipamentos:** Rings, ropes, wall balls, plyo boxes, barbells, bumper plates (não precisa de máquinas de musculação)
- **RH:** Coaches com certificação CrossFit Level 1 (ou similar)
- **Legal:** Mesmas licenças, mas área menor pode simplificar bombeiros
- **Marketing:** Comunidade é mais forte — precisa de estratégia de engajamento desde o início
- **Obra:** Piso de borracha específico, rigs de parede/teto, espaço para correr

### 1.3. Studio de Pilates (80-200m²)

Diferenças:
- **Equipamentos:** Reformers, Cadillacs, Chairs, Barrels (equipamentos de pilates — custo alto por m²)
- **RH:** Fisioterapeutas ou educadores físicos com formação em pilates
- **Legal:** Pode precisar de registro no CREF + associação profissional
- **Obra:** Piso de madeira ou vinílico específico, espelhos, iluminação suave
- **Marketing:** Foco em nicho feminário/ premium, convênios com fisioterapia/ortopedia

### 1.4. Studio Funcional (150-300m²)

Diferenças:
- **Equipamentos:** TRX, kettlebells, medicine balls, battle ropes, sandbags (funcional puro)
- **RH:** Instrutores com certificação em treinamento funcional
- **Obra:** Piso de borracha ou EVA, espaço aberto, poucas divisórias
- **Marketing:** Foco em emagrecimento, condicionamento, comunidade

---

## 2. Agrupamento nas Categorias do Sistema

### Categorias Definidas

| Categoria | Código | Etapas Reais Incluídas | Tipos de Negócio |
|-----------|--------|------------------------|------------------|
| **IMOBILIÁRIO** | `IMOB` | Busca de ponto, negociação, contrato de locação/compra, registro em cartório, consulta de zoneamento | Todos |
| **LEGAL** | `LEGA` | CNPJ, contrato social, alvará, bombeiros, vigilância sanitária, ANVISA, CREF, registro de marca INPI | Todos |
| **OBRAS** | `OBRA` | Projeto arquitetônico, elétrico, hidráulico, combate a incêndio, obra civil, instalações, piso, pintura, acabamento | Todos |
| **EQUIPAMENTOS** | `EQUI` | Definição de layout, cotação e compra de aparelhos, cardio, acessórios, som, TVs, catracas, CFTV | Todos |
| **TECNOLOGIA** | `TECN` | Software de gestão, sistema de acesso, CFTV, site, app, automação | Todos |
| **RECURSOS HUMANOS** | `RH` | Organograma, contratação, treinamento, certificações, uniformes | Todos |
| **MARKETING** | `MARK` | Naming, identidade visual, redes sociais, pré-lançamento, planos e preços, parcerias, evento de inauguração | Todos |
| **FINANCEIRO** | `FIN` | Conta bancária PJ, contador, gestão financeira, financiamento, seguros, fluxo de caixa, reserva | Todos |
| **OPERACIONAL** | `OPER` | Estoque, suplementos, limpeza, testes, treinamento de emergência, abertura oficial | Todos |

### Validação: Todas as Etapas Cobertas?

| Etapa Real | Categoria | ✅/❌ |
|-----------|-----------|-------|
| Abertura de CNPJ | LEGAL | ✅ |
| Contrato social | LEGAL | ✅ |
| Busca/negociação de ponto | IMOBILIÁRIO | ✅ |
| Contrato de locação | IMOBILIÁRIO | ✅ |
| Alvará de funcionamento | LEGAL | ✅ |
| Corpo de Bombeiros | LEGAL | ✅ |
| Vigilância Sanitária | LEGAL | ✅ |
| ANVISA | LEGAL | ✅ |
| CREF | LEGAL + RH | ✅ (dual) |
| Projeto arquitetônico | OBRAS | ✅ |
| Projeto elétrico/hidráulico | OBRAS | ✅ |
| Obra civil | OBRAS | ✅ |
| Piso/acabamento | OBRAS | ✅ |
| Compra de aparelhos musculação | EQUIPAMENTOS | ✅ |
| Compra de cardio | EQUIPAMENTOS | ✅ |
| Sistema de som/TVs | EQUIPAMENTOS + TECNOLOGIA | ✅ |
| Software de gestão | TECNOLOGIA | ✅ |
| Catracas/biometria | TECNOLOGIA + EQUIPAMENTOS | ✅ |
| Contratação de gerente | RH | ✅ |
| Contratação de instrutores | RH | ✅ |
| Treinamento de equipe | RH + OPERACIONAL | ✅ |
| Naming/ID visual | MARKETING | ✅ |
| Redes sociais | MARKETING + TECNOLOGIA | ✅ |
| Pré-lançamento | MARKETING | ✅ |
| Conta bancária PJ | FINANCEIRO | ✅ |
| Contador | FINANCEIRO | ✅ |
| Financiamento | FINANCEIRO | ✅ |
| Seguros | FINANCEIRO | ✅ |
| Estoque/suplementos | OPERACIONAL | ✅ |
| Testes de equipamentos | OPERACIONAL + EQUIPAMENTOS | ✅ |
| Inauguração | MARKETING + OPERACIONAL | ✅ |

**Resultado:** ✅ 100% das etapas reais estão cobertas pelas 9 categorias.

---

## 3. Categorias por Tipo de Negócio (Peso)

Nem todas as categorias têm o mesmo peso em cada tipo de negócio. Isso influencia o template:

| Categoria | Academia | Crossfit | Pilates | Funcional |
|-----------|:--------:|:--------:|:-------:|:---------:|
| IMOBILIÁRIO | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| LEGAL | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| OBRAS | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| EQUIPAMENTOS | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| TECNOLOGIA | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| RH | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| MARKETING | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| FINANCEIRO | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| OPERACIONAL | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

**Observações:**
- **Pilates:** EQUIPAMENTOS tem peso máximo (Reformers/Cadillacs são caríssimos e definem o negócio).
- **Crossfit:** MARKETING tem peso maior (comunidade é tudo no box).
- **Academia:** FINANCEIRO tem peso maior (CAPEX mais alto, payback mais longo).

---

## 4. Decisões

| Código | Decisão |
|--------|---------|
| **CAT-001** | Manter 9 categorias. Cobrem 100% das etapas reais. |
| **CAT-002** | TECNOLOGIA separado de EQUIPAMENTOS. Software é CAPEX diferente de aparelho físico. |
| **CAT-003** | Tarefas de CREF ficam em LEGAL (documento) + RH (contratação de profissional habilitado). |
| **CAT-004** | Inauguração é MARKETING (evento) + OPERACIONAL (abertura oficial). Gerar 2 tarefas ou 1 tarefa com checklist duplo? Decisão: 1 tarefa em MARKETING com checklist operacional. |
| **CAT-005** | Ordem padrão das categorias no playbook: IMOB → LEGAL → OBRAS → EQUIP → TECN → RH → MARK → FIN → OPER. Reflete a cronologia real de abertura. |

---

## 5. Checklist

- [x] Mapear etapas reais de abertura (academia, box, pilates, funcional)
- [x] Agrupar etapas nas 9 categorias propostas
- [x] Validar que 100% das etapas estão cobertas
- [x] Definir peso de cada categoria por tipo de negócio
- [x] Documentar decisões (CAT-001 a CAT-005)
