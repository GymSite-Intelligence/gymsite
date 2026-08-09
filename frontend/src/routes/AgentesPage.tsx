import { degustacaoHref } from "@/lib/degustacaoUrls";
import { DEGUSTACAO_COPY } from "@/lib/degustacaoCopy";
import "./agentes.scoped.css";

// Mini-página dos 5 especialistas. Cada card abre `/degustacao?agente=<id>`;
// `?agente=` pré-seleciona o card na UI (ADR-003); a API usa sempre o roteador.

type Card = { id: string; nome: string; esp: string; ex: string; ac: string; img: string };

// id = id do rail/backend. "Mercado" manda `degustacao` (roteador decide) — decisão de produto.
const AGENTES: Card[] = [
  {
    id: "degustacao",
    nome: "Mercado",
    esp: "Concorrência, demografia e saturação do bairro",
    ex: "quantas academias tem no Cocó, Fortaleza, CE?",
    ac: "var(--c-mercado)",
    img: "/agentes/mercado.png",
  },
  {
    id: "responsavel_tecnico",
    nome: "Técnico",
    esp: "Equipamentos: mix, specs e fornecedores",
    ex: "que mix pra 300 m² de musculação?",
    ac: "var(--c-tecnico)",
    img: "/agentes/tecnico.png",
  },
  {
    id: "regulatorio",
    nome: "Regulatório",
    esp: "CREF, registro, licença e Lei 9.696",
    ex: "preciso de registro no CREF?",
    ac: "var(--c-regulatorio)",
    img: "/agentes/regulatorio.png",
  },
  {
    id: "arquiteto",
    nome: "Arquiteto",
    esp: "Projeto do espaço, zonas e acessibilidade",
    ex: "quantos banheiros pra 200 alunos?",
    ac: "var(--c-arquiteto)",
    img: "/agentes/arquiteto.png",
  },
  {
    id: "engenheiro_obra",
    nome: "Engenheiro",
    esp: "Obra, estrutura, instalações e licenças",
    ex: "a laje aguenta peso livre?",
    ac: "var(--c-engenheiro)",
    img: "/agentes/engenheiro.png",
  },
];

const abrirChat = (id: string) => degustacaoHref({ agente: id });

export function AgentesPage() {
  return (
    <div className="gs-ag">
      <div className="wrap">
        <header>
          <a className="brand" href="/">
            <img src="/gymsite-logo-white.png" alt="GymSite Intelligence" />
          </a>
          <nav className="nav">
            <a href="/#fontes">Fontes</a>
            <a href="/#metodo">Método</a>
            <a href="/explorar">Explorar</a>
            <a href="/blog">Blog</a>
            <a href="/#lgpd">LGPD</a>
          </nav>
        </header>

        <section className="hero">
          <div className="eyebrow">Degustação · 5 especialistas</div>
          <h1>
            Escolha o especialista.
            <br />
            Faça sua pergunta.
          </h1>
          <p className="lede">
            Cinco agentes, cada um com sua especialidade. Pergunte direto pra quem entende do
            assunto — <b>concorrência, equipamentos, obra, projeto ou regulatório</b> — e receba uma
            amostra da inteligência que alimenta o relatório completo.
          </p>
          <div className="tagchips">
            {DEGUSTACAO_COPY.badgesAtritoZero.map((b) => (
              <span key={b}>
                {b.includes("fonte carimbada") ? (
                  <>
                    dados com <b>fonte carimbada</b>
                  </>
                ) : (
                  b
                )}
              </span>
            ))}
          </div>
        </section>

        <section className="grid">
          {AGENTES.map((a) => (
            <a
              key={a.id}
              className="agent"
              style={{ ["--ac" as string]: a.ac }}
              href={abrirChat(a.id)}
            >
              <div className="halo" style={{ ["--ac" as string]: a.ac }}>
                <img src={a.img} alt={a.nome} loading="lazy" />
              </div>
              <div className="nome">{a.nome}</div>
              <div className="esp">{a.esp}</div>
              <div className="ex">{a.ex}</div>
              <div className="card-cta">Perguntar →</div>
            </a>
          ))}
        </section>

        <div className="roda">
          <span className="ico">🔄</span>
          <div>
            <h3>Cada pergunta afina o especialista</h3>
            <p>
              As dúvidas mais frequentes viram treino dos próprios agentes — a{" "}
              <b>roda de aprendizado</b>. Perguntas são anonimizadas antes de qualquer uso (LGPD);
              nada que te identifique entra no treino.
            </p>
          </div>
        </div>

        <section className="how">
          <div>
            <div className="n">01</div>
            <h3>Pergunte ao especialista</h3>
            <p>
              Escolha o agente pela especialidade e mande sua dúvida real sobre abrir ou operar a
              academia.
            </p>
          </div>
          <div>
            <div className="n">02</div>
            <h3>Veja quem responde</h3>
            <p>
              Cada resposta traz o crachá de quem falou. Se a dúvida for de outra área, o
              especialista certo assume — a passagem de bastão.
            </p>
          </div>
          <div>
            <div className="n">03</div>
            <h3>Peça a análise completa</h3>
            <p>
              Gostou da amostra? O relatório de viabilidade da sua região cruza +27 fontes públicas
              oficiais.
            </p>
          </div>
        </section>

        <div className="foot">
          GymSite Intelligence · degustação dos agentes consultores · dados de bases públicas
          oficiais
        </div>
      </div>
    </div>
  );
}
