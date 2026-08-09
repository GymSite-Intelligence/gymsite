import type { AgeBand, BlogKpi, TocItem } from "@/lib/blog/enrich";
import type { BlogPostMeta } from "@/lib/blog/posts";
import { Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";

export function PillRow({ pills }: { pills: string[] }) {
  return (
    <div className="pill-row">
      {pills.map((p) => (
        <span key={p} className="pill">
          {p}
        </span>
      ))}
    </div>
  );
}

export function KpiGrid({ kpis }: { kpis: BlogKpi[] }) {
  if (!kpis.length) return null;
  return (
    <div className="kpi-grid">
      {kpis.map((k) => (
        <div key={k.key} className={`kpi-card tone-${k.tone}`}>
          <div className="kpi-value">{k.value}</div>
          <div className="kpi-label">{k.label}</div>
        </div>
      ))}
    </div>
  );
}

export function SourceSeal({ sources }: { sources?: string }) {
  return (
    <p className="source-seal">
      <span className="seal-ico" aria-hidden="true">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6l7-3z"
            stroke="currentColor"
            strokeWidth="1.6"
          />
          <path
            d="M9 12l2 2 4-4"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {sources ?? "Dados verificados via Receita Federal & IBGE Censo 2022"}
    </p>
  );
}

export function AgeBandBars({
  bands,
  title,
}: {
  bands: AgeBand[];
  title?: string;
}) {
  if (!bands.length) return null;
  return (
    <div className="age-bands">
      <h3 className="age-bands-title">
        {title ?? "Distribuição da vida dos baixados"}
      </h3>
      <ul>
        {bands.map((b) => (
          <li key={b.label}>
            <div className="age-row">
              <span className="age-lab">{b.label}</span>
              <span className="age-pct">{b.pct}%</span>
            </div>
            <div className="age-track">
              <div
                className={`age-fill tone-${b.tone}`}
                style={{ width: `${Math.min(100, b.pct)}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StickyToc({ items }: { items: TocItem[] }) {
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    if (!items.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]?.target?.id) setActive(visible[0].target.id);
      },
      { rootMargin: "-20% 0px -65% 0px", threshold: [0, 1] },
    );
    for (const it of items) {
      const el = document.getElementById(it.id);
      if (el) obs.observe(el);
    }
    return () => obs.disconnect();
  }, [items]);

  if (!items.length) return null;

  return (
    <nav className="toc" aria-label="Nesta análise">
      <p className="toc-label">Nesta análise</p>
      <ol>
        {items.map((it) => (
          <li key={it.id}>
            <a
              href={`#${it.id}`}
              className={active === it.id ? "is-active" : undefined}
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(it.id)?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                });
              }}
            >
              {it.label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function LeadMagnet({
  cityLabel,
  uf,
}: {
  cityLabel: string;
  uf?: string;
}) {
  const isDf = (uf || "").toUpperCase() === "DF";
  return (
    <div className="lead-magnet">
      <div>
        <h3>
          {isDf
            ? "Mapa de renda por Região Administrativa"
            : "Mapa de bairros · relatório PDF"}
        </h3>
        <p>
          {isDf
            ? `Cruze PDAD × densidade × concorrência nas RAs de ${cityLabel} antes de fechar ponto ou ticket.`
            : `Receba o PDF de ${cityLabel} com renda × densidade por bairro — sem compromisso.`}
        </p>
      </div>
      <a className="btn" href="/degustacao">
        {isDf ? "Pedir análise por RA" : "Baixar relatório grátis"}
      </a>
    </div>
  );
}

export function SeriesCompare({
  cityLabel,
  related,
}: {
  cityLabel: string;
  related: BlogPostMeta[];
}) {
  if (!related.length) return null;
  const names = related.map((r) => r.cityLabel).join(" e ");
  return (
    <div className="series-compare">
      <p className="series-lede">
        Compare {cityLabel} com {names} no mesmo trimestre
      </p>
      <div className="series-links">
        {related.map((r) => (
          <Link
            key={r.slug}
            to="/blog/$slug"
            params={{ slug: r.slug }}
            className="series-chip"
          >
            {r.cityLabel}/{r.uf}
            <span>{r.angleLabel}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
