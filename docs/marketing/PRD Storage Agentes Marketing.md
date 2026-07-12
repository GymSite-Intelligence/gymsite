# **Especificação de Requisitos de Produto (PRD) para a Infraestrutura de Armazenamento Semântico e Multiagentes de Marketing**

## **Arquitetura de Referência da Plataforma e Integração Conversacional**

A evolução dos sistemas de inteligência artificial generativa exige a transição de abordagens puramente determinísticas para sistemas probabilísticos complexos, onde a precisão das respostas é diretamente proporcional à qualidade, estrutura e governança dos dados de suporte1. A criação de um armazenamento de dados unificado (Data Store) para marketing funciona como a memória semântica de longo prazo para agentes autônomos, viabilizando a Geração Recuperada por Pesquisa (RAG)3. Diferente de bancos de dados relacionais que realizam correspondências exatas de palavras-chave, esta arquitetura utiliza representações vetoriais de alta dimensão para associar conceitos correlacionados de forma contextual4.  
No ecossistema do Agent Studio, a solução baseia-se em um padrão de design de sistemas multiagentes estruturado a partir do Agent Development Kit (ADK)6. O fluxo de interação inicia-se no Agente Raiz (Root Agent), que opera como um controlador central responsável pela triagem das mensagens do usuário, classificação de intenções e delegação de tarefas por meio de instruções estruturadas em formato XML7. Quando uma tarefa é classificada, o Agente Raiz transfere a sessão de forma dinâmica para um dos subagentes especialistas: o Especialista em SEO ou o Especialista em Marketing Meta (Instagram e Facebook)7. Ambos os especialistas utilizam as ferramentas de recuperação (Tools) para interagir diretamente com a Data Store de Marketing, garantindo que qualquer conteúdo gerado permaneça ancorado nos manuais e históricos reais da marca7.  
O mecanismo de busca semântica calcula a distância matemática entre o vetor da consulta do usuário (![][image1]) e os vetores dos fragmentos de texto armazenados (![][image2])4. Para este sistema, a similaridade é determinada por meio do cálculo da similaridade de cosseno, descrita pela fórmula:  
![][image3]  
Este cálculo matemático assegura que variações linguísticas ou sinônimos aplicados pelo usuário sejam mapeados para os conceitos idênticos contidos na base de conhecimento corporativa3.

## **Estrutura Taxonômica da Data Store e Gestão de Ativos**

Para maximizar a eficiência dos algoritmos de busca semântica e evitar a contaminação de contextos entre as frentes de marketing, a Data Store deve ser organizada em uma taxonomia lógica de diretórios10. Essa segregação impede que métricas de campanhas interfiram na redação criativa de novas peças de conteúdo10. O processamento de dados aceita tanto formatos textuais estruturados e não estruturados quanto referências externas e imagens, respeitando os limites operacionais nativos do Agent Studio2.  
Os links de posts públicos fornecidos pelo usuário são processados como ativos dinâmicos de leitura2. O sistema limita a ingestão a até 10 URLs por agente e 25 por conta corporativa, capturando apenas o conteúdo em formato de texto estático e ignorando elementos dinâmicos, scripts de execução ou mídias integradas sob proteção de autenticação2.  
A tabela a seguir estabelece as especificações de cada diretório, formatos de arquivos e a associação sugerida de leitura para os agentes especialistas:

| Diretório Pai | Subdiretório e Ativos | Formatos Suportados | Descrição Técnica do Conteúdo | Agente de Destino |
| :---- | :---- | :---- | :---- | :---- |
| 📁 Branding | /identidade • Guia de estilo • Tom de voz | PDF, DOCX \[cite: 2\] | Manual contendo missão corporativa, diretrizes de tom de voz, paleta de cores hexadecimais e hashtags oficiais da marca10. | Especialista Meta10 Especialista SEO14 |
|  | /assets • Logos • Slogans | PNG, JPG, TXT \[cite: 2\] | Logotipos em alta resolução e slogans institucionais mapeados textualmente10. | Especialista Meta10 |
| 📁 Posts & Conteúdo | /instagram • Copies históricos • Roteiros de Reels | PDF, DOCX, TXT \[cite: 2\] | Histórico de publicações orgânicas de alto engajamento e estruturas textuais de roteiros de vídeo10. | Especialista Meta10 |
|  | /facebook • Variações de anúncios • Textos de apoio | PDF, DOCX, TXT \[cite: 2\] | Exemplos de textos publicitários aplicados em campanhas corporativas10. | Especialista Meta10 |
|  | /referencias • Links de posts públicos | URLs (Texto estático)2 | Endereços de páginas públicas de referência para inspiração e alinhamento de concorrência2. | Especialista Meta10 |
| 📁 Campanhas | /historico • Planilhas de anúncios • Métricas de conversão | CSV, XLSX \[cite: 2\] | Consolidação histórica de desempenho de mídia paga, incluindo métricas de CTR, CPC e conversões por criativo10. | Especialista Meta10 |
|  | /calendario • Cronograma editorial • Datas sazonais | CSV, PDF \[cite: 2\] | Calendário de publicação contendo datas sazonais críticas, cronograma de postagens e eventos de mercado10. | Especialista Meta10 Especialista SEO16 |
| 📁 Pesquisa de Mercado | /personas • Perfis de clientes • Preferências | PDF, DOCX \[cite: 2\] | Relatórios consolidados sobre perfis de público-alvo, faixas demográficas e dores de consumo10. | Especialista Meta10 Especialista SEO17 |
|  | /competidores • Benchmarks • Tendências de busca | PDF, TXT, URLs \[cite: 2\] | Estudos de mercado sobre o posicionamento de competidores diretos e mapeamento de comportamento de pesquisa10. | Especialista SEO14 |

## **Protocolos de Processamento de Dados e Estratégias de Chunking**

A divisão de documentos extensos em fragmentos menores (chunking) é uma etapa de pré-processamento que determina a relevância das informações injetadas no contexto do modelo de linguagem8. A estratégia de fragmentação deve ser ajustada ao tipo de dado para garantir que o significado semântico original seja preservado20.

### **Documentos Textuais (PDF e DOCX)**

Para relatórios, guias de identidade e manuais, utiliza-se o fatiamento hierárquico por meio do algoritmo de divisão recursiva por caracteres (Recursive Character Text Splitter)22. Esse método prioriza a integridade estrutural, evitando a separação de frases e mantendo parágrafos completos unidos20.

* **Tamanho do Fragmento (Chunk Size):** Definido em 512 tokens para capturar ideias isoladas de forma concisa22.  
* **Sobreposição de Fragmentos (Chunk Overlap):** Fixado em 10% do tamanho total (aproximadamente 51 tokens), garantindo que as fronteiras conceituais entre fragmentos sequenciais mantenham uma transição contextual suave20.

A estimativa volumétrica de fragmentos gerados a partir de um documento é regida pela relação matemática:  
![][image4]  
Onde ![][image5] é a extensão do texto em tokens, ![][image6] é a capacidade de cada fragmento e ![][image7] é a área de sobreposição compartilhada entre os fragmentos adjacentes19.

### **Dados Tabulares (CSV e Excel)**

A aplicação de divisores baseados em número de caracteres em planilhas estruturadas quebra a associação bidimensional das células, tornando o dado incompreensível para o modelo de linguagem21. A estratégia para arquivos estruturados exige a transformação de cada linha da planilha em um objeto JSON completo21. O processo de ingestão extrai os cabeçalhos das colunas e os repete como chaves em todos os registros individuais de linhas, de modo que cada fragmento contenha tanto o valor do dado quanto a sua definição semântica21.

### **Elementos Visuais (Imagens de Campanhas)**

Para habilitar o entendimento de tendências visuais e referências estéticas, o pipeline de imagens deve adotar abordagens focadas em reconhecimento e estruturação25. Cada arquivo de imagem (PNG ou JPG) é submetido a um modelo de linguagem visual (VLM) que atua na extração de texto em layout (OCR) e na geração de resumos detalhados que descrevem a paleta de cores, a disposição espacial dos elementos e o estilo visual25.  
As diretrizes técnicas para garantir um alto índice de sucesso no processamento óptico incluem:

* **Fidelidade de Contraste:** O texto contido na imagem deve apresentar uma relação de contraste mínima de 7:1 em relação ao fundo para evitar que a tokenização sofra com distorções de ruído cromático26.  
* **Tipografia Sans-Serif:** Prioriza-se o uso de fontes geométricas limpas, como Inter ou Roboto, eliminando-se variações em itálico ou textos rotacionados que reduzem a precisão dos sistemas de leitura visual26.  
* **Separação Espacial (Whitespace):** Uso de margens amplas para delimitar os blocos informacionais e evitar falsas associações espaciais por proximidade26.

## **Modelo de Dados e Esquema de Metadados de Marketing**

O uso combinado de termos semânticos e filtros de metadados (filtragem híbrida) otimiza os tempos de resposta e restringe o espaço de busca vetorial, assegurando que o agente recupere somente as informações de marketing que atendam às especificações de governança3.

JSON  
{  
  "$schema": "https://json-schema.org/draft/2020-12/schema",  
  "title": "MarketingStorageMetadataSchema",  
  "type": "object",  
  "required": \[  
    "id",  
    "filename",  
    "content\_type",  
    "department\_owner",  
    "access\_level",  
    "freshness\_timestamp"  
  \],  
  "properties": {  
    "id": {  
      "type": "string",  
      "format": "uuid",  
      "description": "Identificador único global do fragmento de dados indexado."  
    },  
    "filename": {  
      "type": "string",  
      "description": "Nome do arquivo original carregado no repositório de nuvem."  
    },  
    "content\_type": {  
      "type": "string",  
      "enum": \[  
        "branding\_guide",  
        "editorial\_calendar",  
        "target\_persona",  
        "successful\_post\_copy",  
        "ad\_metric\_sheet",  
        "visual\_template"  
      \],  
      "description": "Classificação do tipo de ativo de marketing para filtros direcionados."  
    },  
    "department\_owner": {  
      "type": "string",  
      "enum": \[  
        "seo\_team",  
        "social\_media\_team",  
        "brand\_identity\_team"  
      \],  
      "description": "Identifica a área proprietária do documento para controle de acesso."  
    },  
    "access\_level": {  
      "type": "string",  
      "enum": \[  
        "public",  
        "internal\_marketing",  
        "restricted\_financial"  
      \],  
      "description": "Regras de permissão de visualização aplicadas ao fragmento."  
    },  
    "freshness\_timestamp": {  
      "type": "string",  
      "format": "date-time",  
      "description": "Data e hora de ingestão ou última resincronização do arquivo."  
    },  
    "topic\_tags": {  
      "type": "array",  
      "items": {  
        "type": "string"  
      },  
      "description": "Palavras-chave temáticas para otimização de busca conceitual."  
    }  
  }  
}

Os campos de metadados que acompanham cada fragmento vetorial e suas respectivas capacidades operacionais de consulta estão descritos na tabela abaixo:

| Identificador do Campo | Tipo de Dado | Descrição de Uso Operacional | Operadores de Filtro Suportados |
| :---- | :---- | :---- | :---- |
| id | string (UUID) | Chave primária de identificação do fragmento na base vetorial31. | Igualdade exata (==)30. |
| filename | string | Registro físico do nome do arquivo armazenado para rastreamento de origem29. | Igualdade e verificação de sufixo30. |
| content\_type | string | Filtro categórico que restringe a busca a tipos específicos de documentos30. | Correspondência de múltiplos valores (MatchAny)31. |
| department\_owner | string | Define a equipe proprietária do documento, evitando sobreposição de escopo10. | Igualdade exata (==)12. |
| access\_level | string | Controla o nível de sigilo das informações de campanhas corporativas12. | Filtro de restrição baseado em privilégios32. |
| freshness\_timestamp | datetime | Data de atualização do documento, formatada de acordo com o padrão ISO 860129. | Operações lógicas de tempo (\>, \<, \>=)29. |
| topic\_tags | array\[string\] | Tags livres associadas ao conteúdo do fragmento para buscas mais abrangentes29. | Pesquisa em array (array\_contains)29. |

## **Configuração de Instruções e Ferramentas dos Agentes Especialistas**

Cada agente especialista possui parâmetros de atuação exclusivos e acessa apenas uma parcela dos dados armazenados na Data Store, o que garante a precisão das respostas com base no foco de cada disciplina de marketing7.

### **Agente Especialista em SEO**

O Agente Especialista em SEO atua de forma analítica no mapeamento de tendências de pesquisa e estruturação técnica34.

* **Diretrizes de Atuação:** Focado na avaliação de arquiteturas de dados de portais, descoberta de palavras-chave, análise estrutural de cabeçalhos (H1 a H6) e identificação exata da intenção de busca (informacional, comercial, transacional)14.  
* **Integração com Ferramentas:** Conectado à ferramenta de leitura da Data Store com permissão exclusiva sobre os diretórios /personas e /competidores10. Utiliza conexões externas via protocolo MCP para resgatar dados reais de desempenho orgânico em plataformas de monitoramento de busca (Ahrefs ou Google Search Console)16.  
* **Otimização Avançada (SEO e GEO):** O agente estrutura suas recomendações para garantir relevância nos resultados orgânicos tradicionais do Google e citações em motores de resposta alimentados por inteligência artificial (GEO/AEO)18. Ele prescreve de forma detalhada o preenchimento de esquemas de dados estruturados (schema.org), otimização de metadados para busca semântica corporativa e criação de arquivos llms.txt destinados a agentes de varredura automatizada18.

### **Agente Especialista em Marketing Meta (Instagram e Facebook)**

O Agente Especialista em Marketing Meta tem caráter criativo e é focado em estratégias de atração de público10.

* **Diretrizes de Atuação:** Atribuições voltadas ao desenvolvimento de roteiros de engajamento, análise de tendências estéticas visuais e otimização de cópias para conversão de campanhas publicitárias de mídia paga (Facebook Ads)10.  
* **Integração com Ferramentas:** Integração com a ferramenta de busca da Data Store de Marketing sob controle direto dos diretórios /identidade, /assets, /instagram, /facebook e /historico10. Consome dados históricos de custos de cliques (CPC) e taxas de conversão (CTR) para embasar a proposta de orçamentos criativos futuros10.

A tabela a seguir apresenta uma comparação estrutural das atribuições de cada agente:

| Atributo de Configuração | Agente Especialista em SEO | Agente Especialista em Marketing Meta |
| :---- | :---- | :---- |
| **Foco de Atuação** | Desempenho em busca orgânica e motores generativos18. | Engajamento social e campanhas de conversão de anúncios10. |
| **Ativos Consumidos na Data Store** | /personas, /competidores, /calendario10. | /identidade, /assets, /instagram, /facebook, /historico10. |
| **Ferramentas Externas de Integração** | APis de crawling e ferramentas de busca (Ahrefs)16. | Ferramentas de análise de eventos e tracking de ads15. |
| **Saídas Técnicas de Produção** | Recomendações de schema.org, auditorias e relatórios GEO18. | Cópias publicitárias, roteiros e recomendações visuais10. |
| **Método de Interação Conversacional** | Relatórios detalhados orientados a dados14. | Cópias persuasivas alinhadas ao tom de voz da marca10. |

## **Mecanismos de Orquestração, Controle de Fluxo e Callbacks**

O controle da execução das ferramentas pelos agentes e a garantia de que as diretrizes corporativas sejam rigorosamente mantidas dependem do pipeline de callbacks implementado na orquestração conversacional do Agent Studio7. Os callbacks atuam como interceptadores lógicos que tratam as entradas e saídas de dados em cada turno de conversação do sistema7.

                     ┌────────────────────────────────────────┐  
                     │          ENTRADA DO USUÁRIO            │  
                     └───────────────────┬────────────────────┘  
                                         │  
                                         ▼  
                     ┌────────────────────────────────────────┐  
                     │         \`before\_tool\_callback\`         │  
                     │  • Valida sintaxe e chaves de metadados│  
                     └───────────────────┬────────────────────┘  
                                         │  
                                         ▼  
                     ┌────────────────────────────────────────┐  
                     │          EXECUÇÃO DA FERRAMENTA        │  
                     │  • Busca vetorial semântica no índice  │  
                     └───────────────────┬────────────────────┘  
                                         │  
                                         ▼  
                     ┌────────────────────────────────────────┐  
                     │         \`after\_tool\_callback\`          │  
                     │  • Consolida e reordena os fragmentos  │  
                     └───────────────────┬────────────────────┘  
                                         │  
                                         ▼  
                     ┌────────────────────────────────────────┐  
                     │         \`after\_model\_callback\`         │  
                     │  • Filtra tom de voz, marcas e PII     │  
                     └───────────────────┬────────────────────┘  
                                         │  
                                         ▼  
                     ┌────────────────────────────────────────┐  
                     │          RESPOSTA FORMATADA            │  
                     └────────────────────────────────────────┘

A atuação lógica desses pontos de controle compreende as seguintes diretrizes operacionais7:

* **Interceptação de Entrada (before\_tool\_callback):** Disparado imediatamente antes da execução de uma consulta à Data Store7. Sua finalidade é interceptar o termo gerado pelo agente e validar se os filtros aplicados correspondem estritamente aos tipos definidos no esquema de metadados, prevenindo erros de execução ou consultas vazias na base vetorial7.  
* **Tratamento de Contexto (after\_tool\_callback):** Intervém logo após o retorno dos fragmentos recuperados da Data Store7. Este callback reordena os fragmentos de texto e dados para posicionar os manuais de identidade da marca antes de exemplos históricos de cópias, reduzindo o fenômeno de perda de atenção do modelo em contextos longos (Lost in the Middle)7. Ele também atua na decodificação de imagens representadas em Base64 para que o agente visual possa interpretá-las27.  
* **Monitoramento de Resposta (after\_model\_callback):** Ativado assim que o agente especialista produz a resposta textual final, mas antes que ela seja visível ao usuário7. Este script realiza buscas por palavras banidas, valida se o tom de voz seguiu o guia de identidade e limpa quaisquer dados confidenciais (PII) ou credenciais que o modelo possa ter exposto de maneira não intencional durante a geração7.

Recomenda-se projetar as instruções de fluxo de forma que os agentes realizem apenas uma chamada de ferramenta por turno de conversação. Quando for necessária a consolidação de dados de múltiplas ferramentas, o callback de pós-execução (after\_tool\_callback) deve ser usado para encadear as requisições de maneira encapsulada, mantendo o processo invisível para o usuário final.

## **Critérios de Aceitação, Métricas de Qualidade e Protocolo de Homologação**

A natureza probabilística das respostas geradas exige que as validações do sistema sejam realizadas sob cenários de teste controlados com conjuntos de dados padronizados (Golden Datasets)1. Esses conjuntos consistem em um banco de 100 perguntas reais e respostas ideais validadas por analistas de marketing, usado para avaliar desvios de desempenho após atualizações no modelo ou novos carregamentos na Data Store32.  
O comportamento do sistema de armazenamento e recuperação deve ser validado com base na transição estruturada de estados funcionais, conforme detalhado na tabela abaixo40:

| Estado Atual | Gatilho de Entrada | Próximo Estado | Comportamento Esperado do Sistema |
| :---- | :---- | :---- | :---- |
| Idle | Solicitação recebida do usuário40. | Loading | Ativa o indicador visual de processamento e inicia a transformação da consulta em vetor semântico19. |
| Loading | Conclusão da busca com dados retornados40. | Loaded | Consolida os fragmentos semânticos e preenche o contexto para processamento do modelo8. |
| Loading | Retorno de índice sem correspondências40. | Empty | Retorna uma resposta padrão neutra indicando que a informação requisitada não foi localizada na base corporativa10. |
| Loading | Falha de infraestrutura ou timeout (![][image8])40. | Error\_Network | Dispara nova tentativa de conexão automática ou exibe mensagem de falha temporária com opção de reiteração manual39. |
| Loading | Token de acesso expirado ou inválido40. | Error\_Auth | Interrompe o fluxo e solicita nova autenticação de sessão, registrando a ocorrência nos logs de segurança38. |
| Loaded | Resposta formulada com sucesso40. | Success | Disponibiliza o texto processado para o usuário final e arquiva o histórico na memória da sessão de trabalho7. |

As métricas quantitativas de aceitação obrigatórias para homologação do sistema em produção compreendem32:

* **Pontuação de Coerência Textual:** Classificação média igual ou superior a 4/5 em avaliações de clareza realizadas em amostras aleatórias de respostas geradas32.  
* **Índice de Recusa de Solicitações Inválidas:** Taxa igual ou superior a 99% em testes de tentativas de injeção de instruções ou questionamentos sobre tópicos não relacionados ao domínio de marketing da empresa32.  
* **Frequência de Alucinações Factuais:** Taxa menor que 2% de inserções de dados factuais ou estatísticos que não estejam explicitamente documentados em alguma fonte válida da Data Store32.

### **Protocolo de Teste Prático de Validação (Campanha Dia dos Pais)**

Como etapa final de homologação, o analista deve submeter o sistema a um teste de ponta a ponta simulando um fluxo real de trabalho10. Este procedimento visa confirmar que os recursos da Data Store de Marketing estão corretamente vinculados ao agente especialista10.

1. **Upload de Documentos de Homologação:** O operador deve certificar-se de que os seguintes documentos estão ativos no sistema de arquivos10:  
   * No diretório /identidade: Arquivo guia\_marca\_2026.pdf com diretrizes que exigem uma abordagem afetuosa e criativa, uso obrigatório das cores hexadecimais \#FF5733 (Laranja Coral) e \#2C3E50 (Azul Profundo), o slogan oficial *"Conectando Histórias"* e a hashtag principal \#ConexaoPaterna10.  
   * No diretório /instagram: Arquivo modelo\_copys\_aprovados.docx demonstrando a aplicação de chamadas para ação (CTA) convidando o usuário a acessar o link da bio da marca10.  
2. **Injeção do Prompt de Teste:** O operador deve inserir a seguinte instrução no canal de testes do Especialista em Marketing Meta10:*"Crie um post para o Instagram focado em nossa campanha do Dia dos Pais utilizando nossa identidade visual de marca."*  
   \[cite: 10\]  
3. **Gabarito de Avaliação de Sucesso:** A resposta gerada pelo agente deve ser considerada válida apenas se contemplar as exigências especificadas abaixo10:

| Critério de Avaliação | Resultado de Sucesso (Passa) | Causa de Falha do Teste (Reprova) |
| :---- | :---- | :---- |
| **Preservação de Identidade Visual** | O texto gerado pelo agente descreve que as artes visuais de apoio devem ser configuradas usando as cores oficiais \#FF5733 e \#2C3E5010. | Omissão dos valores de cores hexadecimais ou indicação de tonalidades diferentes das contidas no manual10. |
| **Uso de Slogans Institucionais** | Inclusão explícita do slogan oficial *"Conectando Histórias"* no fechamento da cópia gerada10. | Geração de slogans criados de forma espontânea pelo modelo de linguagem ou ausência da marca registrada10. |
| **Aplicação de Hashtags** | O bloco de texto final apresenta a hashtag obrigatória \#ConexaoPaterna10. | Esquecimento de hashtags obrigatórias ou inserção de variações não autorizadas10. |
| **Estruturação de Chamada para Ação** | O post incentiva o leitor a acessar o link disponível na bio da conta10. | Omissão de instruções de direcionamento ao usuário ou inserção de CTAs incorretas10. |
| **Adequação de Tom de Voz** | O tom de escrita reflete empatia, proximidade familiar e afeto de acordo com o guia de estilo10. | Uso de linguagem puramente transacional, fria ou focada apenas em vendas sem apelo emocional10. |

Se a saída produzida pelo agente especialista satisfizer de forma cumulativa todos os requisitos de qualidade propostos, a Data Store de Marketing será considerada homologada e pronta para integração no ambiente produtivo de marketing1.

#### **Referências citadas**

1. How Do You Write a PRD for AI Products? From Deterministic to Probabilistic | Ainna, [https://ainna.ai/resources/faq/ai-prd-guide-faq](https://ainna.ai/resources/faq/ai-prd-guide-faq)  
2. Build and curate knowledge AI Agents in Freshdesk, [https://support.freshdesk.com/support/solutions/articles/50000011712-build-and-curate-knowledge-for-ai-agents](https://support.freshdesk.com/support/solutions/articles/50000011712-build-and-curate-knowledge-for-ai-agents)  
3. Best Vector Databases for AI Agents: 2026 Comparison \- Fastio, [https://fast.io/resources/best-vector-databases-ai-agents/](https://fast.io/resources/best-vector-databases-ai-agents/)  
4. What Is a Vector Database and Why AI Agents Need Them | MindStudio, [https://www.mindstudio.ai/blog/what-is-vector-database](https://www.mindstudio.ai/blog/what-is-vector-database)  
5. Top Vector Databases for AI Agents: A 2026 Developer Guide \- DEV Community, [https://dev.to/pratikpathak/top-vector-databases-for-ai-agents-a-2026-developer-guide-436k](https://dev.to/pratikpathak/top-vector-databases-for-ai-agents-a-2026-developer-guide-436k)  
6. Vertex AI Agent Builder Review 2026: Pricing, Setup, Verdict \- BetterClaw, [https://www.betterclaw.io/blog/google-vertex-ai-agent-builder](https://www.betterclaw.io/blog/google-vertex-ai-agent-builder)  
7. The Complete Guide to CX Agent Studio Architecture — Multi-Agent Design Patterns, Tools, Callbacks & Everything You Need to Know : r/CXAgentStudio \- Reddit, [https://www.reddit.com/r/CXAgentStudio/comments/1rwfwfs/the\_complete\_guide\_to\_cx\_agent\_studio/](https://www.reddit.com/r/CXAgentStudio/comments/1rwfwfs/the_complete_guide_to_cx_agent_studio/)  
8. RAG indexing: Structure and evaluate for grounded LLM answers \- Meilisearch, [https://www.meilisearch.com/blog/rag-indexing](https://www.meilisearch.com/blog/rag-indexing)  
9. Are vector databases really necessary for AI agents? : r/AI\_Agents \- Reddit, [https://www.reddit.com/r/AI\_Agents/comments/1jxq0tv/are\_vector\_databases\_really\_necessary\_for\_ai/](https://www.reddit.com/r/AI_Agents/comments/1jxq0tv/are_vector_databases_really_necessary_for_ai/)  
10. AI Knowledge Base: The Complete Guide for 2026 \- Fin, [https://fin.ai/learn/ai-knowledge-base](https://fin.ai/learn/ai-knowledge-base)  
11. Vector Database Architecture: How to Structure Your Data for Production RAG Systems \- DEV Community, [https://dev.to/fagundesv/vector-database-architecture-how-to-structure-your-data-for-production-rag-systems-2f4a](https://dev.to/fagundesv/vector-database-architecture-how-to-structure-your-data-for-production-rag-systems-2f4a)  
12. How to Build a Production RAG System with Metadata Filtering | Reintech media, [https://reintech.io/blog/build-production-rag-system-metadata-filtering](https://reintech.io/blog/build-production-rag-system-metadata-filtering)  
13. AI Agent Studio \- Automation Anywhere, [https://www.automationanywhere.com/products/ai-agent-studio](https://www.automationanywhere.com/products/ai-agent-studio)  
14. 9 Best AI Agents For SEO, Ranked by Workflow and Output Quality | RankUp, [https://www.rankup.so/academy/best-ai-agents-for-seo](https://www.rankup.so/academy/best-ai-agents-for-seo)  
15. How to Build a Facebook Ads Data Model in BigQuery: Schema & Setup Guide, [https://windsor.ai/how-to-build-a-facebook-ads-data-model-in-bigquery/](https://windsor.ai/how-to-build-a-facebook-ads-data-model-in-bigquery/)  
16. AI Agents for SEO: What They Are, How They Work, and How to Build One \- Ahrefs, [https://ahrefs.com/blog/ai-agents-for-seo/](https://ahrefs.com/blog/ai-agents-for-seo/)  
17. I want to build a multi agent AI workflow that scans all of our sitemaps and gives content strategy recommendations \- n8n Community, [https://community.n8n.io/t/i-want-to-build-a-multi-agent-ai-workflow-that-scans-all-of-our-sitemaps-and-gives-content-strategy-recommendations/294978](https://community.n8n.io/t/i-want-to-build-a-multi-agent-ai-workflow-that-scans-all-of-our-sitemaps-and-gives-content-strategy-recommendations/294978)  
18. AI SEO & GEO Agent: Rank in Search & AI Answers | Karum, [https://www.karum.ai/agents/ai-seo-geo-agent/](https://www.karum.ai/agents/ai-seo-geo-agent/)  
19. The Secret to Efficient RAG: A Step-by-Step Guide to Chunking and Counting Your Vectors, [https://dev.to/aairom/the-secret-to-efficient-rag-a-step-by-step-guide-to-chunking-and-counting-your-vectors-25go](https://dev.to/aairom/the-secret-to-efficient-rag-a-step-by-step-guide-to-chunking-and-counting-your-vectors-25go)  
20. Chunk Twice, Retrieve Once: RAG Chunking Strategies Optimized for Different Content Types | Dell Technologies Info Hub, [https://infohub.delltechnologies.com/p/chunk-twice-retrieve-once-rag-chunking-strategies-optimized-for-different-content-types/](https://infohub.delltechnologies.com/p/chunk-twice-retrieve-once-rag-chunking-strategies-optimized-for-different-content-types/)  
21. Chunking Tabular Data for RAG and Search Systems | by Kunal \- Towards AI, [https://pub.towardsai.net/chunking-tabular-data-rag-and-search-systems-655ab0d6def0](https://pub.towardsai.net/chunking-tabular-data-rag-and-search-systems-655ab0d6def0)  
22. (PDF) Data Chunking Strategies for RAG in 2025 \- ResearchGate, [https://www.researchgate.net/publication/395122327\_Data\_Chunking\_Strategies\_for\_RAG\_in\_2025](https://www.researchgate.net/publication/395122327_Data_Chunking_Strategies_for_RAG_in_2025)  
23. RAG Data Preparation: Parsing, Chunking, Embedding \- Ayhan Sipahi | sph.sh, [https://sph.sh/en/posts/rag-data-preparation/](https://sph.sh/en/posts/rag-data-preparation/)  
24. How to Build an Over-Engineered Retrieval System | Towards Data Science, [https://towardsdatascience.com/how-to-build-an-overengineered-retrieval-system/](https://towardsdatascience.com/how-to-build-an-overengineered-retrieval-system/)  
25. What is Multimodal RAG? \- IBM, [https://www.ibm.com/think/topics/multimodal-rag](https://www.ibm.com/think/topics/multimodal-rag)  
26. Designing for Multimodal RAG: Creating "OCR-Optimized" Visual Assets \- SteakHouse Blog, [https://blog.trysteakhouse.com/blog/designing-for-multimodal-rag-ocr-optimized-visuals](https://blog.trysteakhouse.com/blog/designing-for-multimodal-rag-ocr-optimized-visuals)  
27. Explore the new Multimodal RAG template from LangChain and Redis, [https://redis.io/blog/explore-the-new-multimodal-rag-template-from-langchain-and-redis/](https://redis.io/blog/explore-the-new-multimodal-rag-template-from-langchain-and-redis/)  
28. Graph-based metadata filtering to improve vector search in RAG applications \- Neo4j, [https://neo4j.com/blog/developer/graph-metadata-filtering-vector-search-rag/](https://neo4j.com/blog/developer/graph-metadata-filtering-vector-search-rag/)  
29. Advanced Metadata Filtering with Natural Language Generation — NVIDIA RAG blueprint, [https://docs.nvidia.com/rag/latest/custom-metadata.html](https://docs.nvidia.com/rag/latest/custom-metadata.html)  
30. Understanding Metadata in RAG | Vectorize Docs, [https://docs.vectorize.io/build-deploy/data-pipelines/understanding-metadata/](https://docs.vectorize.io/build-deploy/data-pipelines/understanding-metadata/)  
31. How to Build a Multimodal RAG Pipeline with Metadata Filtering | MindStudio, [https://www.mindstudio.ai/blog/multimodal-rag-pipeline-metadata-filtering](https://www.mindstudio.ai/blog/multimodal-rag-pipeline-metadata-filtering)  
32. Writing PRDs for AI Products: A Practical Guide for Senior Product and Cross-Functional Teams \- Nima Torabi, [https://neemz.medium.com/writing-prds-for-ai-products-a-practical-guide-for-senior-product-and-cross-functional-teams-f8f5040474a5](https://neemz.medium.com/writing-prds-for-ai-products-a-practical-guide-for-senior-product-and-cross-functional-teams-f8f5040474a5)  
33. Enterprise Knowledge Management with RAG for Digital-Native Companies \- Confluent, [https://www.confluent.io/blog/enterprise-knowledge-management-with-rag-for-digital-native-companies/](https://www.confluent.io/blog/enterprise-knowledge-management-with-rag-for-digital-native-companies/)  
34. AI SEO Agents: How Autonomous SEO Is Changing Search | Sprints & Sneakers, [https://www.sprintsandsneakers.com/insights/ai-seo-agents](https://www.sprintsandsneakers.com/insights/ai-seo-agents)  
35. AI Agent Workflows for Modern SEO Teams \- Growth Rocket, [https://www.growth-rocket.com/blog/ai-agent-workflows-for-modern-seo-teams/](https://www.growth-rocket.com/blog/ai-agent-workflows-for-modern-seo-teams/)  
36. AI SEO Mastery: The 2026 Guide to GEO & AI Search Ranking \- Katteb, [https://katteb.com/blog/ai-seo-mastery-the-2026-guide-to-geo-ai-search-ranking/](https://katteb.com/blog/ai-seo-mastery-the-2026-guide-to-geo-ai-search-ranking/)  
37. Performing Advanced Facebook Event Data Analysis with a Vector Database | by MyScale, [https://medium.com/@myscale/performing-advanced-facebook-event-data-analysis-with-a-vector-database-44a653384bc2](https://medium.com/@myscale/performing-advanced-facebook-event-data-analysis-with-a-vector-database-44a653384bc2)  
38. Agents | CX Agent Studio \- Google Cloud Documentation, [https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/agent](https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/agent)  
39. Best practices and patterns | CX Agent Studio | Google Cloud Documentation, [https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/best-practices](https://docs.cloud.google.com/gemini-enterprise-cx/cx-agent-studio/best-practices)  
40. How to Write PRDs for AI Agents (With Examples) | Prodmap Blog, [https://www.prodmap.ai/blog/prds-for-ai-agents/](https://www.prodmap.ai/blog/prds-for-ai-agents/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAbCAYAAACjkdXHAAAA7UlEQVR4Xu2SvQtBURiHXwNRiokUJhOjldFosbLblcgqkzJZDTKYjHab1T9gIGU0WUj8Xue659xzv2TUfeqpc9+Pc+55O0R/TQYOYFJP+BGCQ3iCWS3nSxleDXn9NTG4gEd4hxVr2psGHMM+fMK6Ne1OCq5gDvZINDctFR50YctY84nczJv4UiJx17jx/WkemRUuhOEUVpUYD4oHNldijtTgg8RJumsYlaV2fm5OwCUsaHF+nge4ITkHGx3Y1oMkm/cwreXe75eHsoN5LcfwH21JbMAbmfBULyTvdYZFJT+BNyXP6xmMKDUBAc68ALggNDDdcTA1AAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAA/ElEQVR4Xu2SwQoBURSGj9goWUkpRYryABaUB7BgK09g5RlseAFZKcnCI9hYeQIrslJIJMlGShH/deYy9xozS5v56mum+e/t3HvOELk4kYNr+DB5hlvj/Q6HMCU32NGCF5jRvifhAs5hVMsUAnAMZzCkRi/6xKcq6oGZBNzBHvRomSxwhVk1UikRV6rqASgT96UNfVqm0CSuVIARwxiswz2sQO97tQXyuAfi63QMu8Q9asCgXPwLu37EiSczgWE1UrHrh0BORlzVEqfR5ol7NSJea0kaHuGA1KuIJorKJzglbvIXosKKPr+5GOGG+PcXzxtcwhr08xYXlz/xBB76OKePI6vzAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAaCAYAAAAjZdWPAAAB9klEQVR4Xu2WTShtURiGP4X85q9IDBADMnCTTAwoAwZKpszk5i+JgdyhuqNb/g2IASUTRIpiamZigIluJJnIwMCE/Lxv317tc5bOcc7t0L7abz3tvb9v7b3ftde31toivnx9bzWAW/AawCM4ADkB7TypRfACmuyEV5UFjsAlKAhOeVfl4A6sg3gr51m1i9byiJ3wsqbBE6izE16Vqee/IM/KeVYf1XMiSLCDMVQKWAH3oNrKhZSp5yE7AcWBMVDpXNeIruuRKB302cEQSgNbEoVprs+h6rkULIFk57oftLjpsGJHJ+xgCEVlOtz6zJJYEB0Jlk0veAD7YAoUOe0qwCSYBQOiHawFJ+BC9BnNTttWMA7mQY+4ZReVaTaiEbue80VfdgWKA+LLEvylf4Bdcbf7DjAn+iy2Y3ujVLAnWoYsuxnQ6eQiMt0IbsT913gG1w48N/E1Ce6Mbfq3EzPiS89Aibw3bcQVirlVcfeFiEz/q4zpbJArOh9s0+eiK5IxzU6XiZYCR4FwZGj4S03z4fWgDeyIO1H5s8Wapwljmufdovcci5YexVHiysQ586mmu8AmGASFol9vVHQS/gQbol+Z4vEQDIsukxlgG/wRnYQ8nopO3l+iv8fscBVvjrU4oezNhtc0ZYtxtg9UJkiyYr58+fof9AY6uGEybD0PYAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAaCAYAAADbhS54AAACH0lEQVR4Xu2WTahNURTH/0I9IaREkZuPga+BRCElIROlGCozMTBAydN7LxNlonxFJJ8hGSAhRqIYUJiJ0SsxoyQDrx6/f2sf97zNe7yPewbcf/1q373OPXudtdZee0tN/ScaAythE8yB4Wl+NExN40o1F57CF7gGu+AiPIB5cA9W/3y6Ao2ENvgGe2FUT7NWwGd4pwojZqdOQhdszGyFWuBOwuNKtA2+QysMy2xlXYB9+WSjNAvew1uYltlynVGF9bVfEa0D2fzvNE6R9obLLeEhdKvCSPyNpkAnfIAZma2/WqvYzUMS0cIx43Ff8gZZlk+WtAMu6dc2MyBNgGf6s2MT4SxMyg2N1CFFja3LDUluH+7+RX/z7w1wEI4mfFoch1OKI2t8sh+GDjgGa/xntBzOwVXFO3ttT9PhDTyCyZnNafGLd6r+Akf2MoyFEQqnvYkWw+009jPudz5fvfgrxToL4a4iA8bj+epDNXgCX+E8bIEj8BhWqedXuWX42RfQrnoJLIKbCsdqsEThzHPFcWa5JTkAvhgYj9cnW6/y4jVFmsxM1W8UZXnOX7sZbsBLRe2VHbMc7VuwR1HLSxUN2qdHQ+QIuS34Q8wJhVNlxzxvh+6n37Z5V7uOHSVH3ZoNC9J40LJjvgJth62KzePivwIfFel1dD4pau40vFakzNHeDdcV5eL6LZwctBwNL+AbRpG2/spNeMgcaqqpf0Y/AAfzVrCydViMAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD4AAAAaCAYAAADv/O9kAAAC50lEQVR4Xu2XW6hNURSGf6EIIbmVy8ott5LkxaUOUTyQHF5QHsilUJRcElKeRLlfk0PIrcgt8iCE8iKFwsNRojxKHij8f2Msa+259rE3Wemss//62nPNOdfac8w5xpxjAjXVVBPVkdSROWQYae31HUgfLxdKw8kj8pmcI2vISXKbjCA3yZRfvQugtmQT+UrWk/alzZhIPpF3KNCKy+iD5BupD9pitSPXHZULoWXkB9lAWgVtaTWQjWFlc9Ug8p68Jn2DtlDHUKD43gpb7e1BfTl1hoVFs5eOrLvkOwq0ktWoN3lLPpABQdv/0lDyErYgWphcFBsuVP6dtAGOCytz0hhyGTka3pU8QWXDu5HjpEfYkJNyN1zaCYvxaWGDS8ebsrf0+a7kZinZTY7Csj2d7WvJEa+PyCJ/1q++M5ucIqfJeO9ziJwlW2CT2x1Zw2eRXeQwWQ7bYCPYuxfISnIe9r+97JXK6k9ekXvIviQDN5PVSM73NmQ/WeDP8oYbZLT32YfkrB/rZeX5M2GprwatI1QpcE8yCZYN1sEGPwSlhutuoDRZk6/v74VNpKR3n5HB3raC3MIfeEpEHpIv5ARZCJu9+2QySpMabYIvYIOL1YDkONTpoEnU0TePjIRN1kXYSuvSo0l7DPtGuLpSuTpN0gzYN9Z5XdhPY3tDJvhzVZJxEcytxEAkN7K0RpFGZA3f42UZLMPnklUwo7Vqd5AMOK1w8GGdPEQeJuRd+kZThmufaiTT/fmfSn8iN433BIXDVVj8xpLLySumBnWKZU2EpNCIkB28lK5T+SmSzVeetY3M97ZrpJO3yfXVt1IG+tfS/fwSWQKLaeX46YxO7q1Vl3vG0gTJK3QZWgzbNxTr+s5HcgA2EeIM7Cao/v3IFbIDtrHp97mXZbhcW5OhsTyAhWbuaiqFVdjIvctJu3/Vm09KXZC9FcaeoXEoDMqFZiGlhEo7vvKRFiPFfD3slNB+E3pDTTW1dP0EpvSB0p6E8B0AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE4AAAAWCAYAAABud6qHAAAAnElEQVR4Xu3XMQrCQBRF0W+X3srO2KRL6xpcmaRXLCQrsA1YWAiSheU9kiYiOhMs74ELgemGP5kkAgAA/FcxhUw79VCNWr+t4YeVqtVdtaqcLyNFpW5TfkYmT52n76X2MU4lMmzUOdjARXxpXFSvtvMlfOJpO6lnMG1J/H67qi7G25YN+4JPkkzeMB9DH0cfSx9PJDioY/DXAACQAV7QES6V5HF2AAAAAElFTkSuQmCC>