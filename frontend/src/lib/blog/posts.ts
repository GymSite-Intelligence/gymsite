import { renderMarkdown } from "./markdown";
import {
  enhanceArticleHtml,
  extractAgeBands,
  ageBandsTitle,
  extractChurnPill,
  extractKpis,
  extractRankPill,
  extractToc,
  injectHeadingIds,
  prepareBodyMarkdown,
  type AgeBand,
  type BlogKpi,
  type TocItem,
} from "./enrich";

import mdBh from "../../../content/blog/2026-Q1-belo-horizonte-mg-crescimento.md?raw";
import mdBs from "../../../content/blog/2026-Q1-brasilia-df-mortalidade.md?raw";
import mdFt from "../../../content/blog/2026-Q1-fortaleza-ce-mortalidade.md?raw";
import mdRj from "../../../content/blog/2026-Q1-rio-de-janeiro-rj-crescimento.md?raw";
import mdSp from "../../../content/blog/2026-Q1-sao-paulo-sp-ambos.md?raw";

export type BlogAngle = "mortalidade" | "crescimento" | "ambos";

export type BlogPostMeta = {
  slug: string;
  title: string;
  excerpt: string;
  quarter: string;
  cityLabel: string;
  uf: string;
  angle: BlogAngle;
  angleLabel: string;
  pills: string[];
  kpis: BlogKpi[];
};

export type BlogPost = BlogPostMeta & {
  bodyMarkdown: string;
  bodyHtml: string;
  ageBands: AgeBand[];
  ageBandsTitle: string;
  toc: TocItem[];
  sourceSeal: string;
};

const ANGLE_LABEL: Record<BlogAngle, string> = {
  mortalidade: "Mortalidade",
  crescimento: "Crescimento",
  ambos: "Crescimento & mortalidade",
};

type RawEntry = { file: string; md: string };

const RAW: RawEntry[] = [
  { file: "2026-Q1-belo-horizonte-mg-crescimento.md", md: mdBh },
  { file: "2026-Q1-brasilia-df-mortalidade.md", md: mdBs },
  { file: "2026-Q1-fortaleza-ce-mortalidade.md", md: mdFt },
  { file: "2026-Q1-rio-de-janeiro-rj-crescimento.md", md: mdRj },
  { file: "2026-Q1-sao-paulo-sp-ambos.md", md: mdSp },
];

function titleCaseCity(slugPart: string): string {
  return slugPart
    .split("-")
    .map((w) =>
      w.length <= 2 ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1),
    )
    .join(" ");
}

function parseFilename(file: string): {
  slug: string;
  quarter: string;
  citySlug: string;
  uf: string;
  angle: BlogAngle;
} | null {
  const base = file.replace(/\.md$/i, "");
  const m = base.match(
    /^(20\d{2}-Q[1-4])-(.+)-([a-z]{2})-(mortalidade|crescimento|ambos)$/i,
  );
  if (!m) return null;
  const [, quarter, citySlug, uf, angleRaw] = m;
  return {
    slug: base.toLowerCase(),
    quarter,
    citySlug,
    uf: uf.toUpperCase(),
    angle: angleRaw.toLowerCase() as BlogAngle,
  };
}

function extractTitle(md: string): string {
  const line = md.split(/\r?\n/).find((l) => /^#\s+/.test(l));
  return line ? line.replace(/^#\s+/, "").trim() : "Sem título";
}

function extractExcerpt(md: string): string {
  const lines = md.split(/\r?\n/);
  let pastMeta = false;
  const buf: string[] = [];
  for (const line of lines) {
    if (/^---\s*$/.test(line)) {
      pastMeta = true;
      continue;
    }
    if (!pastMeta) continue;
    if (/^#/.test(line)) break;
    if (/^\|/.test(line)) break;
    const t = line.trim();
    if (!t) {
      if (buf.length) break;
      continue;
    }
    if (/^Por\s+\*\*|^\*\*Ficha/.test(t)) continue;
    buf.push(t.replace(/\*\*/g, "").replace(/`[^`]+`/g, "").replace(/&lt;/g, "<"));
    if (buf.join(" ").length > 160) break;
  }
  const text = buf.join(" ").replace(/\s+/g, " ").trim();
  if (text.length <= 180) return text;
  return `${text.slice(0, 177).trim()}…`;
}

function stripLeadingH1(md: string): string {
  return md.replace(/^#\s+[^\n]+\n+/, "");
}

function stripByline(md: string): string {
  return md
    .replace(/^Por\s+\*\*[^\n]+\n+/m, "")
    .replace(/^\*\*Ficha:\*\*[^\n]+\n+/m, "")
    .replace(/^---\s*\n+/m, "");
}

function buildPills(
  quarter: string,
  angleLabel: string,
  md: string,
): string[] {
  const q = quarter.replace("-", " ");
  const pills = [q, "CNAE 9313-1/00"];
  const rank = extractRankPill(md, angleLabel);
  if (rank) pills.push(rank);
  else pills.push(angleLabel.toUpperCase());
  const churn = extractChurnPill(md);
  if (churn) pills.push(churn);
  return pills;
}

function sourceSealFor(uf: string, md: string): string {
  if (uf === "DF" || /PDAD/i.test(md)) {
    return "Receita Federal · PDAD Ampliada 2024 (IPEDF CODEPLAN) · PIB IBGE";
  }
  return "Dados verificados via Receita Federal & IBGE Censo 2022";
}

function buildPosts(): BlogPost[] {
  const posts: BlogPost[] = [];
  for (const { file, md } of RAW) {
    const parsed = parseFilename(file);
    if (!parsed) continue;
    const title = extractTitle(md);
    const angleLabel = ANGLE_LABEL[parsed.angle];
    const rawBody = stripByline(stripLeadingH1(md));
    const kpis = extractKpis(md, parsed.angle);
    const ageBands = extractAgeBands(md);
    const toc = extractToc(rawBody);
    const prepared = prepareBodyMarkdown(rawBody);
    const bodyHtml = injectHeadingIds(
      enhanceArticleHtml(renderMarkdown(prepared)),
      toc,
    );

    posts.push({
      slug: parsed.slug,
      title,
      excerpt: extractExcerpt(md),
      quarter: parsed.quarter,
      cityLabel: titleCaseCity(parsed.citySlug),
      uf: parsed.uf,
      angle: parsed.angle,
      angleLabel,
      pills: buildPills(parsed.quarter, angleLabel, md),
      kpis,
      bodyMarkdown: prepared,
      bodyHtml,
      ageBands,
      ageBandsTitle: ageBandsTitle(ageBands),
      toc,
      sourceSeal: sourceSealFor(parsed.uf, md),
    });
  }
  return posts.sort((a, b) => {
    const q = b.quarter.localeCompare(a.quarter);
    if (q !== 0) return q;
    return a.cityLabel.localeCompare(b.cityLabel, "pt-BR");
  });
}

const POSTS = buildPosts();

export function listBlogPosts(): BlogPostMeta[] {
  return POSTS.map(
    ({
      bodyHtml: _h,
      bodyMarkdown: _m,
      ageBands: _a,
      ageBandsTitle: _at,
      toc: _t,
      sourceSeal: _s,
      ...meta
    }) => meta,
  );
}

export function getBlogPost(slug: string): BlogPost | undefined {
  return POSTS.find((p) => p.slug === slug.toLowerCase());
}

export function getAllBlogSlugs(): string[] {
  return POSTS.map((p) => p.slug);
}

export function getRelatedPosts(slug: string, limit = 3): BlogPostMeta[] {
  const current = getBlogPost(slug);
  if (!current) return listBlogPosts().slice(0, limit);
  return listBlogPosts()
    .filter((p) => p.slug !== slug && p.quarter === current.quarter)
    .slice(0, limit);
}
