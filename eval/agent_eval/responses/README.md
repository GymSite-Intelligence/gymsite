# responses/

Respostas do agente coladas do Preview (Agent Studio), 1 arquivo por caso:

    eval/agent_eval/responses/<case_id>.txt

O nome do arquivo deve bater com o case_id em cases/<case_id>.json.
O runner em modo --transcript le estes arquivos e aplica os asserts.

Fluxo:
1. Abra o Preview do agente e clique "Nova sessao" (isola o contexto).
2. Envie a user_message do caso (campo "user_message" do JSON).
3. Cole a resposta completa do agente em responses/<case_id>.txt
4. Rode: python eval/agent_eval/run_agent_eval.py --transcript

Caso falte um arquivo de resposta, o caso e marcado como SKIP (transcript vazio).
Nao versionar respostas que contenham dados sensiveis reais; use saidas de teste.
