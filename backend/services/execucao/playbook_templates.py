"""
Playbook Templates — Tarefas base por tipo de negócio.

Cada template é uma lista de TarefaTemplate que serve como ponto de partida
para o playbook_generator.py. O LLM personaliza títulos, descrições, prazos
e custos com base no relatório de viabilidade.

Regra: template é fallback. Se o LLM falhar, o playbook ainda é gerado com
estas tarefas base.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TarefaTemplate:
    """Estrutura de uma tarefa base no template."""
    titulo: str
    categoria: str  # IMOBILIARIO, LEGAL, OBRAS, EQUIPAMENTOS, TECNOLOGIA, RH, MARKETING, FINANCEIRO, OPERACIONAL
    descricao: str
    ordem: int
    custo_planejado_default: int  # em centavos (R$)
    dias_duracao_default: int     # dias estimados para conclusão
    prioridade: str = "MEDIA"     # BAIXA, MEDIA, ALTA, CRITICA
    responsavel_sugestao: str = "Empreendedor"  # quem normalmente faz
    checklist: tuple[str, ...] = ()


# =============================================================================
# TEMPLATE: ACADEMIA TRADICIONAL
# =============================================================================

TEMPLATE_ACADEMIA_TRADICIONAL: list[TarefaTemplate] = [
    # IMOBILIARIO
    TarefaTemplate(
        titulo="Buscar e avaliar pontos comerciais",
        categoria="IMOBILIARIO",
        descricao="Visitar no mínimo 3 imóveis comerciais no bairro escolhido. Avaliar: visibilidade, acesso, estacionamento, vizinhança, metragem e valor do aluguel.",
        ordem=10,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor / Corretor",
        checklist=("Listar 5 imóveis potenciais", "Visitar 3 opções", "Verificar zoneamento na prefeitura", "Tirar fotos e medidas"),
    ),
    TarefaTemplate(
        titulo="Negociar e assinar contrato de locação",
        categoria="IMOBILIARIO",
        descricao="Negociar valor, prazo de carência, obras permitidas, multa rescisória e condições de entrega. Assinar contrato com aval de advogado.",
        ordem=20,
        custo_planejado_default=0,
        dias_duracao_default=7,
        prioridade="CRITICA",
        responsavel_sugestao="Empreendedor / Advogado",
        checklist=("Revisar contrato com advogado", "Negociar carência de aluguel", "Verificar fiador/seguro-fiança", "Registrar contrato se exigido"),
    ),

    # LEGAL
    TarefaTemplate(
        titulo="Abrir CNPJ e constituir empresa",
        categoria="LEGAL",
        descricao="Constituir sociedade limitada (Ltda) ou escolher outro regime. Definir sócios, cotas e contrato social.",
        ordem=30,
        custo_planejado_default=150000,  # R$ 1.500
        dias_duracao_default=10,
        prioridade="CRITICA",
        responsavel_sugestao="Contador / Empreendedor",
        checklist=("Definir regime tributário", "Redigir contrato social", "Registrar na Junta Comercial", "Obter CNPJ ativo"),
    ),
    TarefaTemplate(
        titulo="Obter Alvará de Funcionamento",
        categoria="LEGAL",
        descricao="Solicitar alvará na prefeitura do município. Pode exigir projeto aprovado e vistoria prévia.",
        ordem=40,
        custo_planejado_default=80000,  # R$ 800
        dias_duracao_default=21,
        prioridade="CRITICA",
        responsavel_sugestao="Empreendedor / Despachante",
        checklist=("Verificar documentação exigida", "Pagar taxas", "Agendar vistoria se necessário", "Retirar alvará"),
    ),
    TarefaTemplate(
        titulo="Obter Auto de Vistoria do Corpo de Bombeiros (AVCB/CLCB)",
        categoria="LEGAL",
        descricao="Contratar profissional habilitado para projeto de prevenção contra incêndio. Submeter à CBMMG/CBMPB/etc. Agendar vistoria.",
        ordem=50,
        custo_planejado_default=350000,  # R$ 3.500
        dias_duracao_default=30,
        prioridade="CRITICA",
        responsavel_sugestao="Empreendedor / Engenheiro",
        checklist=("Contratar engenheiro/arquiteto habilitado", "Elaborar projeto do PCI", "Submeter ao Corpo de Bombeiros", "Realizar vistoria", "Obter AVCB/CLCB"),
    ),
    TarefaTemplate(
        titulo="Regularizar na Vigilância Sanitária",
        categoria="LEGAL",
        descricao="Solicitar licença sanitária. Pode exigir projeto de instalações, comprovação de limpeza e condições higiênico-sanitárias.",
        ordem=60,
        custo_planejado_default=50000,  # R$ 500
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor",
        checklist=("Verificar exigências municipais", "Preparar documentação", "Agendar inspeção", "Obter licença"),
    ),
    TarefaTemplate(
        titulo="Cadastrar instrutores no CREF",
        categoria="LEGAL",
        descricao="Garantir que todos os instrutores tenham registro ativo no Conselho Regional de Educação Física.",
        ordem=70,
        custo_planejado_default=40000,  # R$ 400 (R$ 100 por instrutor, 4 instrutores)
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="RH / Empreendedor",
        checklist=("Confirmar registro de cada instrutor", "Verificar validade", "Solicitar regularização se necessário"),
    ),

    # OBRAS
    TarefaTemplate(
        titulo="Contratar arquiteto e aprovar projeto",
        categoria="OBRAS",
        descricao="Desenvolver projeto arquitetônico, elétrico, hidráulico e de prevenção contra incêndio. Aprovar na prefeitura.",
        ordem=80,
        custo_planejado_default=250000,  # R$ 2.500
        dias_duracao_default=21,
        prioridade="CRITICA",
        responsavel_sugestao="Empreendedor / Arquiteto",
        checklist=("Contratar arquiteto/engenheiro", "Aprovar layout", "Elaborar projeto executivo", "Submeter à prefeitura", "Obter aprovação"),
    ),
    TarefaTemplate(
        titulo="Executar obra civil",
        categoria="OBRAS",
        descricao="Demolição (se necessário), alvenaria, divisórias, instalações elétricas e hidráulicas, pintura e acabamento.",
        ordem=90,
        custo_planejado_default=28000000,  # R$ 280.000
        dias_duracao_default=60,
        prioridade="CRITICA",
        responsavel_sugestao="Construtora / Empreendedor",
        checklist=("Contratar construtora/mao de obra", "Acompanhar cronograma semanal", "Fazer vistorias de qualidade", "Validar conforme projeto aprovado"),
    ),
    TarefaTemplate(
        titulo="Instalar pisos e acabamentos",
        categoria="OBRAS",
        descricao="Piso vinílico/borracha/EPVC nas áreas de treino, cerâmica nos banheiros/vestiários, pintura final.",
        ordem=100,
        custo_planejado_default=8000000,  # R$ 80.000
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Construtora / Empreendedor",
        checklist=("Definir tipo de piso por área", "Contratar instalador especializado", "Verificar nivelamento", "Inspeção final"),
    ),

    # EQUIPAMENTOS
    TarefaTemplate(
        titulo="Definir layout de equipamentos",
        categoria="EQUIPAMENTOS",
        descricao="Distribuir aparelhos de musculação, cardio e acessórios no piso. Considerar: circulação, segurança, ventilação e capacidade.",
        ordem=110,
        custo_planejado_default=0,
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Arquiteto / Empreendedor",
        checklist=("Levantamento de medidas do imóvel", "Posicionar cada equipamento", "Validar distâncias de segurança", "Aprovar layout final"),
    ),
    TarefaTemplate(
        titulo="Comprar aparelhos de musculação",
        categoria="EQUIPAMENTOS",
        descricao="Cotar e comprar estações de musculação, bancos, racks, cabos e aparelhos específicos. Negociar prazo de entrega e instalação.",
        ordem=120,
        custo_planejado_default=28000000,  # R$ 280.000
        dias_duracao_default=21,
        prioridade="CRITICA",
        responsavel_sugestao="Empreendedor",
        checklist=("Cotar 3 fornecedores", "Definir kit por área", "Negociar pagamento", "Acompanhar entrega", "Verificar integridade"),
    ),
    TarefaTemplate(
        titulo="Comprar equipamentos de cardio",
        categoria="EQUIPAMENTOS",
        descricao="Esteiras, bicicletas ergométricas, elípticos, remos. Considerar modelo comercial (uso contínuo).",
        ordem=130,
        custo_planejado_default=12000000,  # R$ 120.000
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor",
        checklist=("Definir quantidade por tipo", "Cotar marcas (Life Fitness, Technogym, etc.)", "Negociar garantia estendida", "Agendar entrega"),
    ),
    TarefaTemplate(
        titulo="Comprar acessórios e halteres",
        categoria="EQUIPAMENTOS",
        descricao="Halteres, kettlebells, colchonetes, elásticos, medicine balls, step, etc.",
        ordem=140,
        custo_planejado_default=5000000,  # R$ 50.000
        dias_duracao_default=7,
        prioridade="MEDIA",
        responsavel_sugestao="Empreendedor",
        checklist=("Montar lista completa", "Cotar fornecedores", "Verificar qualidade", "Receber e conferir"),
    ),

    # TECNOLOGIA
    TarefaTemplate(
        titulo="Contratar software de gestão de academia",
        categoria="TECNOLOGIA",
        descricao="Sistema de check-in, matrículas, financeiro, relatórios e app do aluno. Exemplos: W12, GymPass (parceria), WodGuru.",
        ordem=150,
        custo_planejado_default=150000,  # R$ 1.500 (setup)
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor",
        checklist=("Comparar 3 sistemas", "Verificar integração com catraca", "Negociar mensalidade", "Configurar cadastro"),
    ),
    TarefaTemplate(
        titulo="Instalar sistema de acesso (catracas/biometria)",
        categoria="TECNOLOGIA",
        descricao="Catracas com leitor de QR Code, pulseira ou biometria. Integrar com software de gestão.",
        ordem=160,
        custo_planejado_default=2000000,  # R$ 20.000
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Técnico / Empreendedor",
        checklist=("Definir tipo de acesso", "Comprar equipamentos", "Contratar instalador", "Integrar com software", "Testar"),
    ),
    TarefaTemplate(
        titulo="Instalar CFTV e sistema de som",
        categoria="TECNOLOGIA",
        descricao="Câmeras de segurança em todas as áreas comuns. Sistema de som ambiente e TVs para aulas coletivas.",
        ordem=170,
        custo_planejado_default=1500000,  # R$ 15.000
        dias_duracao_default=5,
        prioridade="MEDIA",
        responsavel_sugestao="Técnico / Empreendedor",
        checklist=("Definir pontos de câmera", "Comprar equipamentos", "Instalar e configurar", "Testar gravação"),
    ),

    # RH
    TarefaTemplate(
        titulo="Contratar gerente geral da unidade",
        categoria="RH",
        descricao="Profissional com experiência em gestão de academias. Responsável por operação, vendas e equipe.",
        ordem=180,
        custo_planejado_default=0,
        dias_duracao_default=21,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor",
        checklist=("Definir perfil e remuneração", "Publicar vaga", "Entrevistar", "Contratar", "Integrar ao projeto"),
    ),
    TarefaTemplate(
        titulo="Contratar instrutores de musculação",
        categoria="RH",
        descricao="Equipe de instrutores com CREF ativo. Quantidade conforme porte da academia (1 a cada 300m² aprox.).",
        ordem=190,
        custo_planejado_default=0,
        dias_duracao_default=21,
        prioridade="ALTA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Definir número de instrutores", "Publicar vagas", "Entrevistar e testar", "Verificar CREF", "Contratar"),
    ),
    TarefaTemplate(
        titulo="Contratar professores de aulas coletivas",
        categoria="RH",
        descricao="Instrutores de Zumba, Spinning, Body Pump, etc. Pode ser regime PJ por aula ministrada.",
        ordem=200,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="MEDIA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Definir grade de aulas", "Contratar professores", "Validar certificações", "Agendar ensaios"),
    ),
    TarefaTemplate(
        titulo="Treinar equipe",
        categoria="RH",
        descricao="Treinamento de: atendimento ao cliente, vendas, segurança, uso de equipamentos, protocolos de emergência.",
        ordem=210,
        custo_planejado_default=500000,  # R$ 5.000
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Preparar conteúdo de treinamento", "Agendar dias de treino", "Aplicar prova prática", "Certificar participação"),
    ),

    # MARKETING
    TarefaTemplate(
        titulo="Definir nome e identidade visual",
        categoria="MARKETING",
        descricao="Naming, logotipo, paleta de cores, tipografia. Registrar marca no INPI se for marca própria.",
        ordem=220,
        custo_planejado_default=1000000,  # R$ 10.000
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor / Agência",
        checklist=("Brainstorm de nomes", "Verificar disponibilidade", "Contratar designer", "Aprovar identidade", "Registrar INPI (opcional)"),
    ),
    TarefaTemplate(
        titulo="Criar site e redes sociais",
        categoria="MARKETING",
        descricao="Site institucional com página de captura. Perfis no Instagram, Facebook, TikTok e Google Meu Negócio.",
        ordem=230,
        custo_planejado_default=300000,  # R$ 3.000
        dias_duracao_default=14,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor / Agência",
        checklist=("Registrar domínio", "Contratar desenvolvedor/plataforma", "Criar perfis", "Publicar conteúdo inicial"),
    ),
    TarefaTemplate(
        titulo="Lançar campanha de pré-venda",
        categoria="MARKETING",
        descricao="Captar leads interessados antes da inauguração. Oferecer preço early-bird ou isenção de matrícula.",
        ordem=240,
        custo_planejado_default=500000,  # R$ 5.000
        dias_duracao_default=30,
        prioridade="ALTA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Definir oferta de pré-lançamento", "Criar landing page", "Rodar anúncios", "Captar leads", "Acompanhar conversão"),
    ),
    TarefaTemplate(
        titulo="Realizar evento de inauguração",
        categoria="MARKETING",
        descricao="Evento para convidados, leads da pré-venda, parceiros e imprensa local. Incluir aulas experimentais e brindes.",
        ordem=250,
        custo_planejado_default=300000,  # R$ 3.000
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Definir data e horário", "Montar lista de convidados", "Preparar estrutura", "Contratar catering/sonorização", "Executar evento"),
    ),

    # FINANCEIRO
    TarefaTemplate(
        titulo="Abrir conta bancária PJ",
        categoria="FINANCEIRO",
        descricao="Conta corrente em nome da empresa. Comparar taxas de diferentes bancos.",
        ordem=260,
        custo_planejado_default=0,
        dias_duracao_default=5,
        prioridade="ALTA",
        responsavel_sugestao="Contador / Empreendedor",
        checklist=("Escolher banco", "Reunir documentação", "Abrir conta", "Solicitar cartão PJ"),
    ),
    TarefaTemplate(
        titulo="Contratar contador",
        categoria="FINANCEIRO",
        descricao="Profissional ou escritório para folha, impostos, obrigações acessórias e consultoria fiscal.",
        ordem=270,
        custo_planejado_default=50000,  # R$ 500 (mensalidade proporcional)
        dias_duracao_default=7,
        prioridade="ALTA",
        responsavel_sugestao="Empreendedor",
        checklist=("Cotar 3 contadores", "Verificar especialidade em academias", "Negociar mensalidade", "Assinar contrato"),
    ),
    TarefaTemplate(
        titulo="Negociar financiamento ou linha de crédito",
        categoria="FINANCEIRO",
        descricao="Se necessário, estruturar capital de giro ou financiamento de equipamentos. Comparar taxas de juros e prazos.",
        ordem=280,
        custo_planejado_default=0,
        dias_duracao_default=30,
        prioridade="MEDIA",
        responsavel_sugestao="Empreendedor",
        checklist=("Calcular necessidade de capital", "Cotar bancos e fintechs", "Preparar documentação", "Assinar contrato"),
    ),
    TarefaTemplate(
        titulo="Contratar seguros",
        categoria="FINANCEIRO",
        descricao="Seguro patrimonial (imóvel + equipamentos), RC Profissional e seguro de vida para sócios (se exigido por financiador).",
        ordem=290,
        custo_planejado_default=300000,  # R$ 3.000
        dias_duracao_default=7,
        prioridade="MEDIA",
        responsavel_sugestao="Empreendedor",
        checklist=("Cotar seguro patrimonial", "Cotar RC profissional", "Comparar coberturas", "Contratar"),
    ),

    # OPERACIONAL
    TarefaTemplate(
        titulo="Testar todos os equipamentos",
        categoria="OPERACIONAL",
        descricao="Ligar e testar cada aparelho. Verificar: funcionamento, segurança, ajustes, ruídos. Registrar defeitos.",
        ordem=300,
        custo_planejado_default=0,
        dias_duracao_default=3,
        prioridade="ALTA",
        responsavel_sugestao="Gerente / Técnico",
        checklist=("Testar musculação", "Testar cardio", "Testar acessórios", "Registrar defeitos", "Solicitar assistência se necessário"),
    ),
    TarefaTemplate(
        titulo="Realizar limpeza final e organização",
        categoria="OPERACIONAL",
        descricao="Limpeza profissional pós-obra. Organização de vestiários, recepção, estoque de produtos.",
        ordem=310,
        custo_planejado_default=200000,  # R$ 2.000
        dias_duracao_default=2,
        prioridade="MEDIA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Contratar limpeza profissional", "Organizar recepção", "Arrumar vestiários", "Checar suprimentos"),
    ),
    TarefaTemplate(
        titulo="Inaugurar unidade",
        categoria="OPERACIONAL",
        descricao="Abertura oficial ao público. Equipe completa, sistemas funcionando, estoque de produtos, materiais de vendas prontos.",
        ordem=320,
        custo_planejado_default=0,
        dias_duracao_default=1,
        prioridade="CRITICA",
        responsavel_sugestao="Gerente / Empreendedor",
        checklist=("Confirmar equipe escalada", "Testar sistemas", "Abrir caixa", "Iniciar atendimento"),
    ),
]


# =============================================================================
# TEMPLATE: CROSSFIT BOX
# =============================================================================

TEMPLATE_CROSSFIT_BOX: list[TarefaTemplate] = [
    # Adaptações em relação à academia tradicional
    TarefaTemplate(
        titulo="Buscar e avaliar ponto para box",
        categoria="IMOBILIARIO",
        descricao="Ponto com piso industrial, pé-direito alto (mínimo 4m), espaço para rigs e ropes. Preferência por galpão ou térreo.",
        ordem=10,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Verificar pé-direito", "Testar pisada do piso", "Avaliar acesso para equipamentos pesados", "Checar vizinhança para ruído"),
    ),
    TarefaTemplate(
        titulo="Assinar contrato de locação",
        categoria="IMOBILIARIO",
        descricao="Igual academia, mas atenção a: permissão para fixar rigs na parede/teto e tolerância a ruído.",
        ordem=20,
        custo_planejado_default=0,
        dias_duracao_default=7,
        prioridade="CRITICA",
        checklist=("Cláusula de fixação de equipamentos", "Autorização para ruído", "Carência para obras"),
    ),
    # LEGAL: similar, omitido para brevidade no template — generator completa
    TarefaTemplate(
        titulo="Instalar rigs, ropes e equipamentos de CrossFit",
        categoria="EQUIPAMENTOS",
        descricao="Rigs de parede ou free-standing, ropes, wall balls, plyo boxes, barbells, bumper plates, kettlebells.",
        ordem=120,
        custo_planejado_default=8000000,  # R$ 80.000
        dias_duracao_default=14,
        prioridade="CRITICA",
        checklist=("Definir configuração do rig", "Fixar na estrutura", "Comprar barbells e plates", "Comprar acessórios"),
    ),
    TarefaTemplate(
        titulo="Contratar coaches certificados",
        categoria="RH",
        descricao="Coaches com certificação CrossFit Level 1 (ou equivalente: OPEX, SEALFIT, etc.).",
        ordem=180,
        custo_planejado_default=0,
        dias_duracao_default=21,
        prioridade="ALTA",
        checklist=("Verificar certificações", "Avaliar experiência", "Contratar", "Treinar cultura do box"),
    ),
    TarefaTemplate(
        titulo="Construir comunidade antes da inauguração",
        categoria="MARKETING",
        descricao="CrossFit vende comunidade. Criar grupo WhatsApp, eventos ao ar livre, aulas experimentais em parque.",
        ordem=220,
        custo_planejado_default=100000,  # R$ 1.000
        dias_duracao_default=30,
        prioridade="ALTA",
        checklist=("Criar grupo de leads", "Organizar WODs experimentais", "Postar conteúdo diário", "Captar founders"),
    ),
]

# Nota: template de box é mais enxuto porque o generator do LLM expandirá
# com base no template de academia + instruções de adaptação.


# =============================================================================
# TEMPLATE: STUDIO DE PILATES
# =============================================================================

TEMPLATE_STUDIO_PILATES: list[TarefaTemplate] = [
    TarefaTemplate(
        titulo="Buscar ponto com ambiente apropriado para pilates",
        categoria="IMOBILIARIO",
        descricao="Preferência por andar térreo ou 1º andar com elevador. Ambiente silencioso, bem iluminado, possibilidade de climatização.",
        ordem=10,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Verificar isolamento acústico", "Testar iluminação natural", "Confirmar climatização"),
    ),
    TarefaTemplate(
        titulo="Comprar equipamentos de Pilates (Reformer, Cadillac, Chair)",
        categoria="EQUIPAMENTOS",
        descricao="Equipamentos de madeira ou alumínio. Marcas: Metalife, Physio Pilates, Balanced Body. Custo alto por unidade.",
        ordem=120,
        custo_planejado_default=12000000,  # R$ 120.000 (4 reformers + 1 cadillac + 2 chairs + barrels)
        dias_duracao_default=21,
        prioridade="CRITICA",
        checklist=("Definir quantidade por equipamento", "Cotar marcas nacionais e importadas", "Negociar prazo", "Verificar garantia"),
    ),
    TarefaTemplate(
        titulo="Contratar fisioterapeuta ou educador físico formado em Pilates",
        categoria="RH",
        descricao="Profissional com formação em método Pilates (Classical ou Contemporâneo). Pode exigir registro no CREF e associação profissional.",
        ordem=180,
        custo_planejado_default=0,
        dias_duracao_default=21,
        prioridade="ALTA",
        checklist=("Verificar formação em Pilates", "Confirmar CREF", "Avaliar experiência clínica", "Contratar"),
    ),
    TarefaTemplate(
        titulo="Criar parcerias com fisioterapia e ortopedia",
        categoria="MARKETING",
        descricao="Indicação cruzada com clínicas de fisioterapia, ortopedistas e reumatologistas da região.",
        ordem=220,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Mapear clínicas próximas", "Agendar visitas", "Propor parceria", "Criar material de indicação"),
    ),
]


# =============================================================================
# TEMPLATE: STUDIO FUNCIONAL
# =============================================================================

TEMPLATE_STUDIO_FUNCIONAL: list[TarefaTemplate] = [
    TarefaTemplate(
        titulo="Buscar ponto com espaço aberto e poucas colunas",
        categoria="IMOBILIARIO",
        descricao="Espaço tipo salão com poucas divisórias. Pé-direito mínimo 3m. Piso plano e resistente.",
        ordem=10,
        custo_planejado_default=0,
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Medir espaço livre", "Verificar colunas estruturais", "Confirmar capacidade do piso"),
    ),
    TarefaTemplate(
        titulo="Comprar equipamentos funcionais (TRX, kettlebells, ropes)",
        categoria="EQUIPAMENTOS",
        descricao="Equipamentos versáteis e portáteis. Menor investimento inicial que musculação tradicional.",
        ordem=120,
        custo_planejado_default=4000000,  # R$ 40.000
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Definir kit base", "Cotar fornecedores", "Verificar durabilidade", "Receber e organizar"),
    ),
    TarefaTemplate(
        titulo="Contratar instrutores de treinamento funcional",
        categoria="RH",
        descricao="Instrutores com certificação em treinamento funcional, HIIT ou similar.",
        ordem=180,
        custo_planejado_default=0,
        dias_duracao_default=21,
        prioridade="ALTA",
        checklist=("Verificar certificações", "Avaliar capacidade de montar aulas", "Contratar"),
    ),
    TarefaTemplate(
        titulo="Criar desafios e programas de emagrecimento",
        categoria="MARKETING",
        descricao="Programas de 8-12 semanas com acompanhamento. Desafios em grupo para engajamento.",
        ordem=220,
        custo_planejado_default=50000,  # R$ 500
        dias_duracao_default=14,
        prioridade="ALTA",
        checklist=("Definir programas", "Criar material", "Lançar campanha", "Captar primeiros alunos"),
    ),
]


# =============================================================================
# REGISTRY
# =============================================================================

TEMPLATE_REGISTRY: dict[str, list[TarefaTemplate]] = {
    "academia": TEMPLATE_ACADEMIA_TRADICIONAL,
    "crossfit_box": TEMPLATE_CROSSFIT_BOX,
    "studio_pilates": TEMPLATE_STUDIO_PILATES,
    "studio_funcional": TEMPLATE_STUDIO_FUNCIONAL,
}


def get_template_por_tipo_negocio(tipo: str) -> list[TarefaTemplate]:
    """Retorna o template base para o tipo de negócio. Fallback para academia."""
    return TEMPLATE_REGISTRY.get(tipo, TEMPLATE_ACADEMIA_TRADICIONAL)


def listar_tarefas_por_categoria(
    template: list[TarefaTemplate],
    categoria: str
) -> list[TarefaTemplate]:
    """Filtra tarefas do template por categoria."""
    return [t for t in template if t.categoria == categoria]


def calcular_custo_planejado_total(template: list[TarefaTemplate]) -> int:
    """Soma dos custos planejados default do template (em centavos)."""
    return sum(t.custo_planejado_default for t in template)


def calcular_duracao_total_dias(template: list[TarefaTemplate]) -> int:
    """Soma da duração default (caminho crítico simplificado)."""
    # Na prática, dependências definem o caminho crítico.
    # Aqui retornamos a soma simples como estimativa inicial.
    return sum(t.dias_duracao_default for t in template)
