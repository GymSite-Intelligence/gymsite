# PRD — O assistente que vai atrás da regra da sua cidade

## Em uma frase

Fazer o especialista de Arquitetura, quando não tiver a regra da cidade do usuário, **ir buscar essa regra na fonte oficial na hora** — e responder só com o que encontrou, em vez de dar um palpite genérico.

## A história que deu origem a isto

Um visitante perguntou ao nosso assistente de Arquitetura: *"quantos banheiros para 200 alunos?"*. O assistente respondeu um número redondo — 10 bacias, metade para cada gênero — como se fosse a regra. Quando o visitante disse *"minha cidade é João Pessoa, confere lá"*, o assistente foi honesto e admitiu: *"não tenho o Código de Obras de João Pessoa"*.

Só que o número que ele tinha dado antes **estava errado para João Pessoa**. A lei de lá não é meio a meio: exige mais banheiros femininos que masculinos, obriga chuveiros e bebedouros que o assistente nem mencionou. Ou seja: ele deu um número com cara de verdade oficial, e a verdade oficial era outra.

## O que já arrumamos

O assistente **parou de dar palpite com cara de lei**. Agora, quando faz uma conta genérica, ele avisa claramente: *"isto é uma estimativa de planejamento, o número que vale é o do Código de Obras da sua cidade — confirme lá"*. Isso impede o erro de apresentar chute como regra oficial.

Mas isso resolve metade. Ele avisa que não sabe — **mas continua sem saber**. O dono de academia fica sabendo que precisa checar, e tem que ir atrás sozinho.

## O que falta — esta camada

Não dá para guardar de antemão a regra de todas as 5.570 cidades do Brasil dentro do assistente. É informação demais, muda o tempo todo, e cada prefeitura publica do seu jeito. Guardar tudo é impossível.

A solução é outra: **ensinar o assistente a procurar na hora, na fonte certa**. Quando ele não tiver a regra da cidade do usuário, em vez de parar em *"não sei"*, ele vai até os sites oficiais daquela prefeitura, encontra o texto da lei, lê, e responde com base no que achou — dizendo de onde tirou.

## Objetivo

Que o dono de academia receba a **regra real da cidade dele** — com a fonte declarada — sempre que ela existir e estiver publicada, sem precisar sair da conversa para pesquisar por conta própria.

## Como fica para quem usa

**Hoje:**
> — Quantos banheiros para 200 alunos em João Pessoa?
> — Uma estimativa é 10 banheiros, mas o número oficial depende do Código de Obras de João Pessoa. Confirme na prefeitura.

**Com esta camada:**
> — Quantos banheiros para 200 alunos em João Pessoa?
> — Consultei o Código de Obras de João Pessoa. Para 200 alunos, a exigência de lá é [números reais da lei], com estas particularidades [...]. Fonte: Lei Municipal de João Pessoa, artigo tal. Vale confirmar com um arquiteto local antes do projeto.

A diferença: sai do "vira-te" e entra o "achei para você, e aqui está de onde tirei".

## A regra de ouro (não negociável)

O assistente **só pode dizer o que encontrou e conferiu na fonte oficial**. Se procurar e não achar o texto da lei daquela cidade, ele volta ao honesto *"não localizei a regra publicada de [cidade]; confirme na prefeitura ou com um arquiteto local"* — **nunca** completa o buraco com conhecimento genérico nem inventa número. É a mesma regra que já vale hoje: fonte real ou "não sei", sem meio-termo.

E todo número sai com **carimbo** — a regra da casa que vale para tudo que o usuário vê. O carimbo tem quatro partes:

- **Valor:** o número em si (ex.: 7 bacias femininas).
- **Base:** em cima de quê foi calculado (ex.: para 200 alunos, metade de cada gênero).
- **Fonte:** de onde veio (ex.: Código de Obras de João Pessoa, artigo tal).
- **Janela:** de quando é a informação (ex.: lei de 1971, conferida em 2026).

Exemplo de carimbo completo: *"7 bacias femininas · para 100 alunas · Código de Obras de João Pessoa, art. X · lei de 1971"*. Número sem carimbo não sai.

> **Vale para todos os especialistas, não só o Arquiteto.** Qualquer assistente que cite uma lei, código ou norma da sua área — o Regulatório (CREF, licenças), o Engenheiro (normas de obra), etc. — usa o mesmo carimbo. É regra da casa para todos, não uma exceção desta feature.

## O que entra nesta etapa

- O assistente de Arquitetura ganha a capacidade de **procurar a regra da cidade em fontes oficiais** (sites de prefeitura e câmara) quando não a tem guardada.
- Ele passa a **preferir a regra oficial da cidade** sobre a estimativa genérica, sempre que conseguir encontrá-la.
- Cada regra encontrada e conferida pode ser **guardada** para as próximas pessoas — a base vai ficando mais completa com o uso, começando pelas cidades mais perguntadas.

## O que fica de fora (por enquanto)

- Cobrir as 5.570 cidades de uma vez — a base cresce por demanda, cidade por cidade, conforme as perguntas aparecem.
- Substituir o arquiteto: a resposta é um ponto de partida forte e com fonte, não a aprovação do projeto na prefeitura.
- Os outros especialistas (Mercado, Regulatório etc.) — esta camada começa pelo Arquiteto, que foi onde o problema apareceu.

## Cuidados e riscos

- **Site oficial errado ou desatualizado:** o assistente só busca em fontes oficiais (domínios de governo), nunca em blog ou fórum, para não trazer informação de procedência duvidosa.
- **Lei mal interpretada:** por isso toda resposta manda confirmar com um profissional local antes do projeto — a ferramenta orienta, não assina o projeto.
- **Cidade sem lei publicada na internet:** nesses casos ele é honesto e diz que não localizou, em vez de forçar uma resposta.
- **Custo e velocidade:** procurar ao vivo é mais lento e mais caro que responder do que já se sabe — então ele só faz isso quando realmente não tem a regra guardada.

## Como vamos saber que funcionou

- Perguntas sobre regra de uma cidade específica passam a receber **o número real com fonte**, em vez de "confirme na prefeitura".
- O caso que originou tudo — João Pessoa, banheiros para 200 alunos — passa a ser respondido com a regra real da cidade, com a fonte citada.
- A base de cidades cobertas **cresce** a cada semana, puxada pelas cidades mais perguntadas.
- Nenhuma resposta apresenta número sem o **carimbo completo** (valor · base · fonte · janela).
