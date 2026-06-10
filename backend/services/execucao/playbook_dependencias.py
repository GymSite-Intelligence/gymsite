"""
Playbook Dependências — Modelo de dependências entre tarefas de abertura.

Define quais tarefas precisam de outras para começar, quais podem rodar
em paralelo, e quais devem terminar juntas.

As dependências são universais (aplicam-se a todos os tipos de negócio)
com exceções documentadas.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DependenciaTemplate:
    """Define uma dependência entre duas tarefas no template."""
    tarefa_origem_titulo: str       # tarefa que deve acontecer PRIMEIRO
    tarefa_destino_titulo: str      # tarefa que depende da origem
    tipo: str = "TERMINA_PARA_COMECAR"  # TERMINA_PARA_COMECAR | COMECA_JUNTO | TERMINA_JUNTO
    justificativa: str = ""         # por que existe esta dependência


# =============================================================================
# DEPENDÊNCIAS UNIVERSAIS (aplicam-se a todos os tipos de negócio)
# =============================================================================

DEPENDENCIAS_UNIVERSAIS: list[DependenciaTemplate] = [
    # IMOBILIARIO → LEGAL
    DependenciaTemplate(
        tarefa_origem_titulo="Buscar e avaliar pontos comerciais",
        tarefa_destino_titulo="Negociar e assinar contrato de locação",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Só se negocia contrato depois de encontrar o ponto",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Negociar e assinar contrato de locação",
        tarefa_destino_titulo="Abrir CNPJ e constituir empresa",
        tipo="COMECA_JUNTO",
        justificativa="CNPJ pode ser aberto em paralelo à negociação, mas é mais seguro ter endereço definido",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Negociar e assinar contrato de locação",
        tarefa_destino_titulo="Obter Alvará de Funcionamento",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Alvará exige endereço comercial definido",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Negociar e assinar contrato de locação",
        tarefa_destino_titulo="Obter Auto de Vistoria do Corpo de Bombeiros (AVCB/CLCB)",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="AVCB é vinculado ao imóvel",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Negociar e assinar contrato de locação",
        tarefa_destino_titulo="Contratar arquiteto e aprovar projeto",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Projeto arquitetônico precisa do imóvel real",
    ),

    # LEGAL → OBRAS
    DependenciaTemplate(
        tarefa_origem_titulo="Obter Alvará de Funcionamento",
        tarefa_destino_titulo="Executar obra civil",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Obra só pode começar com alvará",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Obter Auto de Vistoria do Corpo de Bombeiros (AVCB/CLCB)",
        tarefa_destino_titulo="Executar obra civil",
        tipo="COMECA_JUNTO",
        justificativa="AVCB pode ser solicitado em paralelo à obra, mas deve estar pronto antes da abertura",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar arquiteto e aprovar projeto",
        tarefa_destino_titulo="Executar obra civil",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Obra segue projeto aprovado",
    ),

    # OBRAS → EQUIPAMENTOS / TECNOLOGIA
    DependenciaTemplate(
        tarefa_origem_titulo="Executar obra civil",
        tarefa_destino_titulo="Instalar pisos e acabamentos",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Piso é a última etapa da obra",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Executar obra civil",
        tarefa_destino_titulo="Definir layout de equipamentos",
        tipo="COMECA_JUNTO",
        justificativa="Layout pode ser refinado durante a obra, mas equipamentos só chegam depois",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Instalar pisos e acabamentos",
        tarefa_destino_titulo="Comprar aparelhos de musculação",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Equipamentos chegam após obra pronta (ou quase)",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Instalar pisos e acabamentos",
        tarefa_destino_titulo="Instalar sistema de acesso (catracas/biometria)",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Catraca precisa de piso e estrutura pronta",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Instalar pisos e acabamentos",
        tarefa_destino_titulo="Instalar CFTV e sistema de som",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="CFTV e som são instalados após acabamento",
    ),

    # EQUIPAMENTOS → TECNOLOGIA
    DependenciaTemplate(
        tarefa_origem_titulo="Comprar aparelhos de musculação",
        tarefa_destino_titulo="Testar todos os equipamentos",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Só testa depois de receber",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar software de gestão de academia",
        tarefa_destino_titulo="Instalar sistema de acesso (catracas/biometria)",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Catraca integra com software de gestão",
    ),

    # RH
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar gerente geral da unidade",
        tarefa_destino_titulo="Contratar instrutores de musculação",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Gerente participa da seleção de equipe",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar instrutores de musculação",
        tarefa_destino_titulo="Cadastrar instrutores no CREF",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Só cadastra quem foi contratado",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar instrutores de musculação",
        tarefa_destino_titulo="Treinar equipe",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Só treina quem está contratado",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Contratar professores de aulas coletivas",
        tarefa_destino_titulo="Treinar equipe",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Treinamento inclui toda a equipe",
    ),

    # MARKETING
    DependenciaTemplate(
        tarefa_origem_titulo="Definir nome e identidade visual",
        tarefa_destino_titulo="Criar site e redes sociais",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Site precisa de nome e marca definidos",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Criar site e redes sociais",
        tarefa_destino_titulo="Lançar campanha de pré-venda",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Pré-venda precisa de canal de captura",
    ),

    # FINANCEIRO
    DependenciaTemplate(
        tarefa_origem_titulo="Abrir CNPJ e constituir empresa",
        tarefa_destino_titulo="Abrir conta bancária PJ",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Conta PJ precisa de CNPJ",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Abrir conta bancária PJ",
        tarefa_destino_titulo="Negociar financiamento ou linha de crédito",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Banco exige conta PJ para liberar crédito",
    ),

    # OPERACIONAL → INAUGURAÇÃO
    DependenciaTemplate(
        tarefa_origem_titulo="Testar todos os equipamentos",
        tarefa_destino_titulo="Realizar evento de inauguração",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Não inaugura com equipamento quebrado",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Treinar equipe",
        tarefa_destino_titulo="Realizar evento de inauguração",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Equipe precisa estar pronta para receber visitantes",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Lançar campanha de pré-venda",
        tarefa_destino_titulo="Realizar evento de inauguração",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Evento converte leads da pré-venda",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Realizar evento de inauguração",
        tarefa_destino_titulo="Inaugurar unidade",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Inauguração oficial ocorre após evento",
    ),
    DependenciaTemplate(
        tarefa_origem_titulo="Realizar limpeza final e organização",
        tarefa_destino_titulo="Inaugurar unidade",
        tipo="TERMINA_PARA_COMECAR",
        justificativa="Unidade deve estar limpa para abrir",
    ),
]


# =============================================================================
# DEPENDÊNCIAS ESPECÍFICAS POR TIPO DE NEGÓCIO
# =============================================================================

DEPENDENCIAS_ESPECIFICAS: dict[str, list[DependenciaTemplate]] = {
    "crossfit_box": [
        DependenciaTemplate(
            tarefa_origem_titulo="Instalar rigs, ropes e equipamentos de CrossFit",
            tarefa_destino_titulo="Testar todos os equipamentos",
            tipo="TERMINA_PARA_COMECAR",
            justificativa="Testar rigs e barbells",
        ),
    ],
    "studio_pilates": [
        DependenciaTemplate(
            tarefa_origem_titulo="Comprar equipamentos de Pilates (Reformer, Cadillac, Chair)",
            tarefa_destino_titulo="Testar todos os equipamentos",
            tipo="TERMINA_PARA_COMECAR",
            justificativa="Testar reformers e cadillacs",
        ),
    ],
    "studio_funcional": [
        DependenciaTemplate(
            tarefa_origem_titulo="Comprar equipamentos funcionais (TRX, kettlebells, ropes)",
            tarefa_destino_titulo="Testar todos os equipamentos",
            tipo="TERMINA_PARA_COMECAR",
            justificativa="Testar TRX e kettlebells",
        ),
    ],
}


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def get_dependencias_por_tipo(tipo_negocio: str) -> list[DependenciaTemplate]:
    """Retorna todas as dependências (universais + específicas) para o tipo de negócio."""
    especificas = DEPENDENCIAS_ESPECIFICAS.get(tipo_negocio, [])
    return DEPENDENCIAS_UNIVERSAIS + especificas


def validar_dependencias_circulares(
    dependencias: list[DependenciaTemplate]
) -> list[str]:
    """Detecta ciclos no grafo de dependências. Retorna lista de erros."""
    grafo: dict[str, list[str]] = {}
    for dep in dependencias:
        grafo.setdefault(dep.tarefa_origem_titulo, []).append(dep.tarefa_destino_titulo)

    visitado: set[str] = set()
    pilha: set[str] = set()
    ciclos: list[str] = []

    def dfs(node: str, caminho: list[str]):
        if node in pilha:
            ciclo = " → ".join(caminho[caminho.index(node):] + [node])
            ciclos.append(f"Ciclo detectado: {ciclo}")
            return
        if node in visitado:
            return
        visitado.add(node)
        pilha.add(node)
        caminho.append(node)
        for vizinho in grafo.get(node, []):
            dfs(vizinho, caminho)
        caminho.pop()
        pilha.remove(node)

    for node in grafo:
        if node not in visitado:
            dfs(node, [])

    return ciclos


def ordenar_tarefas_por_dependencias(
    titulos_tarefas: list[str],
    dependencias: list[DependenciaTemplate]
) -> list[str]:
    """
    Ordenação topológica simples. Retorna lista de títulos na ordem de execução.
    Se houver ciclo, levanta exceção.
    """
    erros = validar_dependencias_circulares(dependencias)
    if erros:
        raise ValueError(f"Dependências circulares encontradas: {erros}")

    grafo: dict[str, set[str]] = {t: set() for t in titulos_tarefas}
    for dep in dependencias:
        if dep.tarefa_destino_titulo in grafo:
            grafo[dep.tarefa_destino_titulo].add(dep.tarefa_origem_titulo)

    ordenado: list[str] = []
    while grafo:
        # Encontra nós sem dependências pendentes
        sem_deps = [t for t, deps in grafo.items() if not deps]
        if not sem_deps:
            raise ValueError("Ciclo detectado (dependências restantes: " + str(grafo) + ")")
        for t in sem_deps:
            ordenado.append(t)
            del grafo[t]
            for deps in grafo.values():
                deps.discard(t)

    return ordenado


def tarefas_bloqueadas_por(
    tarefa_titulo: str,
    dependencias: list[DependenciaTemplate]
) -> list[str]:
    """Retorna quais tarefas estão BLOQUEADAS porque dependem de `tarefa_titulo`."""
    return [
        dep.tarefa_destino_titulo
        for dep in dependencias
        if dep.tarefa_origem_titulo == tarefa_titulo
        and dep.tipo == "TERMINA_PARA_COMECAR"
    ]


def tarefas_que_bloqueiam(
    tarefa_titulo: str,
    dependencias: list[DependenciaTemplate]
) -> list[str]:
    """Retorna quais tarefas ainda não concluídas BLOQUEIAM `tarefa_titulo`."""
    return [
        dep.tarefa_origem_titulo
        for dep in dependencias
        if dep.tarefa_destino_titulo == tarefa_titulo
        and dep.tipo == "TERMINA_PARA_COMECAR"
    ]
