import { useEffect } from "react";
import { SiteNavBrand, SitePublicMenu, LANDING_NAV } from "@/components/site/SiteNavBrand";
import "./gymsite-landing.scoped.css";

export function LandingPage() {
  // count-up animation on scroll
  useEffect(() => {
    const root = document.getElementById("counters");
    if (!root) return;
    const animate = (el: HTMLElement) => {
      const target = +(el.dataset.target || "0");
      const dur = 1400, t0 = performance.now();
      const tick = (now: number) => {
        const p = Math.min((now - t0) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased).toLocaleString("pt-BR");
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.querySelectorAll<HTMLElement>(".num").forEach(animate);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.4 });
    io.observe(root);
    return () => io.disconnect();
  }, []);

  return (
    <div className="gs-d">
      <nav>
        <div className="wrap nav-in">
          <a href="/" className="logo" aria-label="GymSite Intelligence"><SiteNavBrand /></a>
          <SitePublicMenu links={LANDING_NAV} />
        </div>
      </nav>

      <header className="hero">
        <div className="wrap hero-grid">
          <div>
            <span className="eyebrow">Inteligência de mercado · setor fitness</span>
            <h1>Onde abrir a próxima academia? <span className="hl">Os dados já sabem.</span></h1>
            <p className="lede">A GymSite cruza dezenas de bases públicas oficiais com modelagem proprietária para mapear saturação, demanda reprimida e potencial de faturamento — região por região, antes de você assinar o contrato.</p>
            <div className="hero-cta">
              <a href="/degustacao" className="btn btn-primary">Falar com um especialista</a>
              <a href="#metodo" className="btn btn-ghost">Como funciona</a>
            </div>
            <div className="micro">▸ <b>+2.400 regiões</b> já mapeadas · <b>+30 indicadores</b> por região</div>
          </div>

          <div className="map">
            <div className="map-frame banner">
              <img className="map-bg" src="/gymsite-dashboard.jpg" alt="Dashboard GymSite Intelligence — heatmap de saturação, radar de viabilidade e janela de oportunidade por região" />
            </div>
            <div className="banner-cap">
              <span className="live"><span className="pulse"></span> Amostra ao vivo</span>
              <span>Heatmap de saturação · radar de viabilidade · janela de oportunidade</span>
            </div>
          </div>
        </div>
      </header>

      <div className="counters" id="counters">
        <div className="wrap">
          <div className="cnt"><div className="n"><span className="u">+</span><span className="num" data-target="2400">0</span></div><div className="l">regiões mapeadas</div></div>
          <div className="cnt"><div className="n"><span className="u">+</span><span className="num" data-target="30">0</span></div><div className="l">indicadores / região</div></div>
          <div className="cnt"><div className="n"><span className="u">+</span><span className="num" data-target="27">0</span></div><div className="l">fontes cruzadas</div></div>
          <div className="cnt"><div className="n"><span className="num" data-target="87">0</span><span className="u">%</span></div><div className="l">acerto de viabilidade*</div></div>
        </div>
      </div>

      <section className="s" id="fontes">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">O que cruzamos</span>
            <h2>Dezenas de variáveis. <span className="hl">Um único score de viabilidade.</span></h2>
            <p className="sec-sub">Cada região é avaliada combinando bases oficiais, dados geolocalizados e modelagem proprietária — não um palpite de visita de campo.</p>
          </div>
          <div className="src">
            <div className="it"><div className="h"><span className="d"></span>Demanda reprimida</div><p>população fitness potencial vs. oferta atual de academias</p></div>
            <div className="it"><div className="h"><span className="d"></span>Concorrência</div><p>academias no raio, ticket estimado, perfil e densidade</p></div>
            <div className="it"><div className="h"><span className="d"></span>Renda & consumo</div><p>renda média, classe social, gasto estimado com saúde</p></div>
            <div className="it"><div className="h"><span className="d"></span>Censo & demografia</div><p>faixas etárias, domicílios, densidade populacional</p></div>
            <div className="it"><div className="h"><span className="d"></span>Fluxo de pessoas</div><p>movimentação, vias, polos geradores de tráfego</p></div>
            <div className="it"><div className="h"><span className="d"></span>Entorno comercial</div><p>nível de aquecimento, subcentros, âncoras próximas</p></div>
            <div className="it"><div className="h"><span className="d"></span>Imóveis & locação</div><p>oferta, valores e disponibilidade de pontos comerciais</p></div>
            <div className="it x"><span className="tag">Exclusivo</span><div className="h"><span className="d"></span>Modelo GymSite</div><p>scoring proprietário de viabilidade por modelo de operação</p></div>
          </div>
        </div>
      </section>

      <section className="s" id="beneficios">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Benefícios</span>
            <h2>Decisão de expansão sem achismo</h2>
          </div>
          <div className="cards3">
            <div className="card">
              <div className="ic">◎</div>
              <h3>Encontrar oportunidades</h3>
              <p>Identificamos microrregiões com demanda reprimida e perfil socioeconômico compatível com o seu modelo de operação.</p>
              <div className="chip"><span>low-cost</span><span>premium</span><span>boutique</span><span>crossfit</span></div>
            </div>
            <div className="card">
              <div className="ic">◓</div>
              <h3>Entender a concorrência</h3>
              <p>Mapeamos todas as academias num raio definido, com estimativa de ticket, perfil de clientes e janelas de vulnerabilidade competitiva.</p>
              <div className="chip"><span>raio configurável</span><span>ticket est.</span><span>vulnerabilidade</span></div>
            </div>
            <div className="card">
              <div className="ic">▲</div>
              <h3>Expandir com segurança</h3>
              <p>Cada nova unidade passa por scoring preditivo de viabilidade. Você reduz o risco e ataca os pontos certos, na ordem certa.</p>
              <div className="chip"><span>scoring</span><span>ranking de pontos</span><span>risco ↓</span></div>
            </div>
          </div>
        </div>
      </section>

      <section className="s" id="metodo">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Humano × Inteligência</span>
            <h2>O custo invisível da decisão por intuição</h2>
            <p className="sec-sub">A mesma decisão, com e sem dados. A diferença aparece no tempo, na profundidade e no acerto.</p>
          </div>
          <div className="cmp">
            <div className="cmp-col bad">
              <div className="cmp-h">⌧ DECISÃO TRADICIONAL</div>
              <div className="cmp-row"><span className="k">Tempo até decisão</span><span className="v">45 a 90 dias</span></div>
              <div className="cmp-row"><span className="k">Bases consultadas</span><span className="v">2 a 3</span></div>
              <div className="cmp-row"><span className="k">Acerto de viabilidade</span><span className="v">~ 41%</span></div>
              <div className="cmp-row"><span className="k">Custo do erro de ponto</span><span className="v">Alto</span></div>
            </div>
            <div className="cmp-col good">
              <div className="cmp-h">▸ COM GYMSITE INTELLIGENCE</div>
              <div className="cmp-row"><span className="k">Tempo até decisão</span><span className="v">48 horas</span></div>
              <div className="cmp-row"><span className="k">Bases consultadas</span><span className="v">+27 fontes</span></div>
              <div className="cmp-row"><span className="k">Acerto de viabilidade</span><span className="v">~ 87%</span></div>
              <div className="cmp-row"><span className="k">Custo do erro evitado</span><span className="v">Reduzido</span></div>
            </div>
          </div>
          <p className="cmp-note">* Números ilustrativos com base em estudos internos e amostra de clientes. Resultados variam por região, modelo e maturidade da operação.</p>
        </div>
      </section>

      <section className="s">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Como funciona</span>
            <h2>Do diagnóstico ao ponto certo, em 3 passos</h2>
          </div>
          <div className="steps">
            <div className="step">
              <div className="no">01</div>
              <h3>Diagnóstico no chat</h3>
              <p>Você responde algumas perguntas sobre o seu modelo e a região de interesse. Sem cadastro longo, sem compromisso.</p>
            </div>
            <div className="step">
              <div className="no">02</div>
              <h3>Análise preliminar</h3>
              <p>Cruzamos as bases e devolvemos um retrato da região: saturação, demanda reprimida e score de viabilidade.</p>
            </div>
            <div className="step">
              <div className="no">03</div>
              <h3>Plano de expansão</h3>
              <p>Recebe o ranking de pontos e a janela ideal. Condições e próximos passos são apresentados depois do teste.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="s" id="clientes">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Quem já usa</span>
            <h2>Operadores que pararam de chutar</h2>
          </div>
          <div className="quotes">
            <div className="q">
              <div className="mark">"</div>
              <p>Saiba onde existe demanda reprimida antes de assinar o contrato de aluguel — e evite abrir no lugar errado.</p>
              <div className="who"><div className="nm">Diretor de expansão</div><div className="rl">Operador parceiro · em validação</div></div>
            </div>
            <div className="q">
              <div className="mark">"</div>
              <p>Descubra se o seu modelo de academia tem aderência no bairro antes de investir, com scoring de viabilidade por região.</p>
              <div className="who"><div className="nm">Sócia-proprietária</div><div className="rl">Operador parceiro · em validação</div></div>
            </div>
            <div className="q">
              <div className="mark">"</div>
              <p>Pare de decidir por feeling: cada nova unidade passa por um score de viabilidade preditivo antes da expansão.</p>
              <div className="who"><div className="nm">CEO de rede</div><div className="rl">Operador parceiro · em validação</div></div>
            </div>
          </div>
          <div className="bases" style={{ marginTop: "34px" }}>
            <div className="lab">CRUZAMOS +27 FONTES PÚBLICAS OFICIAIS, ENTRE ELAS</div>
            <div className="row">
              <span>IBGE</span><span>RAIS / CAGED</span><span>Receita Federal</span><span>DataSUS</span><span>Censo Demográfico</span><span>Mapas de mobilidade</span><span>Bases imobiliárias</span>
            </div>
          </div>
        </div>
      </section>

      <section className="s" id="lgpd">
        <div className="wrap">
          <div className="lgpd">
            <div>
              <div className="seal">LGPD<br />OK</div>
              <span className="eyebrow">Selo de conformidade</span>
              <h2>100% aderente à LGPD</h2>
              <p>Trabalhamos exclusivamente com bases públicas oficiais e modelagem proprietária, além de dados fornecidos com consentimento explícito. Nenhum dado sensível, nenhuma coleta sem opt-in. Você pode solicitar exclusão a qualquer momento.</p>
            </div>
            <div className="lgpd-list">
              <div className="it"><span className="ck">✓</span> Bases auditáveis</div>
              <div className="it"><span className="ck">✓</span> Consentimento explícito</div>
              <div className="it"><span className="ck">✓</span> Direito de revogação a qualquer momento</div>
            </div>
          </div>
        </div>
      </section>

      <section className="s" id="cta">
        <div className="wrap">
          <div className="cta">
            <span className="eyebrow" style={{ justifyContent: "center" }}>Diagnóstico gratuito</span>
            <h2>Comece pelo diagnóstico gratuito</h2>
            <p>Você responde a algumas perguntas no chat e recebe uma análise preliminar da sua região. Condições e próximos passos são apresentados depois do teste, sem compromisso.</p>
            <div className="hero-cta">
              <a href="#metodo" className="btn btn-ghost">Rever metodologia</a>
            </div>
          </div>
        </div>
      </section>

      <footer>
        <div className="wrap">
          <div className="foot">
            <div>
              <img className="foot-logo" src="/gymsite-logo-white.png" alt="GymSite Intelligence" />
              <p>Inteligência de mercado e prospecção preditiva para o setor fitness no Brasil.</p>
              <div className="foot-social">
                <a href="https://www.instagram.com/gymsiteintelligence/" target="_blank" rel="noopener noreferrer" aria-label="Instagram · GymSite Intelligence">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <rect x="2.5" y="2.5" width="19" height="19" rx="5.5" stroke="currentColor" strokeWidth="1.7" />
                    <circle cx="12" cy="12" r="4.2" stroke="currentColor" strokeWidth="1.7" />
                    <circle cx="17.4" cy="6.6" r="1.2" fill="currentColor" />
                  </svg>
                </a>
                <a href="https://www.facebook.com/profile.php?id=61591552805353" target="_blank" rel="noopener noreferrer" aria-label="Facebook · GymSite Intelligence">
                  <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path d="M14 8.5V6.9c0-.8.2-1.2 1.3-1.2H16.7V2.9C16.4 2.85 15.4 2.8 14.3 2.8c-2.4 0-4 1.45-4 4.1v1.6H7.7v3h2.6V21h3.7v-6.5h2.5l.4-3H14z" />
                  </svg>
                </a>
              </div>
            </div>
            <div>
              <h4>Plataforma</h4>
              <a href="#fontes">Fontes de dados</a>
              <a href="#beneficios">Benefícios</a>
              <a href="#metodo">Metodologia</a>
              <a href="/blog">Blog</a>
            </div>
            <div>
              <h4>Empresa</h4>
              <a href="#lgpd">LGPD</a>
              <a href="/privacidade">Política de privacidade</a>
              <a href="#">Contato</a>
            </div>
          </div>
          <div className="foot-bottom">
            <span>© 2026 GymSite Intelligence · Todos os direitos reservados</span>
            <span>Feito no Brasil · Conforme a LGPD</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
