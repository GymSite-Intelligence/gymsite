# Vídeo 05 — Ajustando modelos Gemma para visão computacional

> Canal: Google Cloud Tech (Google I/O) · ~12:10
> Tema: fine-tuning de modelos Gemma personalizados para visão computacional de alta velocidade (edge/Nvidia Jetson; caso de uso: processamento de imagem em tempo real).
> Feature GymSite: extração de anexos (fotos do ponto, plantas, PDFs) — hoje a UI aceita mas o backend ignora (ADR-005). Para o GymSite, usar Gemini Vision tende a ser suficiente; Gemma fine-tuned fica como opção avançada se houver volume/custo recorrente.

## Conceito aplicado
Processar imagens enviadas no chat para extrair características do imóvel (área aproximada, layout, fachada) e alimentar a análise de viabilidade.

## Testes de validação

### T05.1 — Anexo de imagem é processado
- Dado que o usuário envia foto do ponto comercial
- Então o backend extrai descrição estruturada (não ignora o arquivo).

### T05.2 — Extração de planta/área
- Dado uma planta ou PDF com metragem
- Então o sistema sugere preenchimento de area_m2 a partir da imagem (com revisão do usuário).

### T05.3 — Tipo de arquivo não suportado
- Dado um anexo inválido (ex.: arquivo corrompido)
- Então mensagem clara de erro em linguagem de domínio, sem termos proibidos.

### T05.4 — Privacidade do anexo
- Então anexos não são cacheados em chave compartilhada nem expostos a outros usuários.

### T05.5 — Fallback sem visão
- Dado que o serviço de visão falha
- Então o fluxo continua pedindo os dados por texto, sem bloquear a análise.
