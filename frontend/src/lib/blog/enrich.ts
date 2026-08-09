/** Extrai KPIs, faixas de vida, TOC e limpa MD pra layout dossier. */

export type BlogKpiTone = "neutral" | "positive" | "alert" | "warn";

export type BlogKpi = {
  key: string;
  label: string;
  value: string;
  tone: BlogKpiTone;
};

export type AgeBand = {
  label: string;
  pct: number;
  tone: "alert" | "warn" | "neutral" | "positive";
};

export type TocItem = {
  id: string;
  label: string;
};

function decodeEntities(s: string): string {
  return s
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"');
}

function stripMd(s: string): string {
  return decodeEntities(s)
    .replace(/\*\*/g, "")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\\_/g, "_")
    .trim();
}

function slugify(label: string): string {
  return label
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
}

/** Parse GFM tables → rows of cells. */
export function parseMdTables(md: string): string[][][] {
  const lines = md.split(/\r?\n/);
  const tables: string[][][] = [];
  let i = 0;
  while (i < lines.length) {
    if (!/^\|/.test(lines[i] ?? "")) {
      i += 1;
      continue;
    }
    const block: string[] = [];
    while (i < lines.length && /^\|/.test(lines[i] ?? "")) {
      block.push(lines[i]!);
      i += 1;
    }
    if (block.length < 2) continue;
    const rows: string[][] = [];
    for (const row of block) {
      if (/^\|\s*:?-{3,}/.test(row)) continue;
      const cells = row
        .replace(/^\|/, "")
        .replace(/\|$/, "")
        .split("|")
        .map((c) => stripMd(c));
      if (cells.length) rows.push(cells);
    }
    if (rows.length >= 2) tables.push(rows);
  }
  return tables;
}

function pickCell(rows: string[][], pred: (ind: string) => boolean): string | null {
  for (const row of rows.slice(1)) {
    const ind = row[0] ?? "";
    if (pred(ind.toLowerCase())) return row[1] ?? null;
  }
  return null;
}

function firstNumberish(raw: string): string | null {
  const m = raw.match(/[+\-]?\d[\d.,]*%?/);
  return m ? m[0] : null;
}

function formatDensityDisplay(raw: string): string {
  if (raw.includes("→")) {
    const right = raw.split("→").pop()?.trim() ?? raw;
    const num = right.match(/[\d.]+/)?.[0];
    return num ?? right;
  }
  return firstNumberish(raw) ?? raw;
}

function parseComboParts(combo: string): {
  aberturas?: string;
  baixas?: string;
  saldo?: string;
} {
  const parts = combo.split("/").map((p) => stripMd(p.trim()));
  if (parts.length < 3) return { saldo: firstNumberish(combo) ?? combo };
  return {
    aberturas: firstNumberish(parts[0] ?? "") ?? parts[0],
    baixas: firstNumberish(parts[1] ?? "") ?? parts[1],
    saldo: firstNumberish(parts[2] ?? "") ?? parts[2],
  };
}

export type KpiAngle = "mortalidade" | "crescimento" | "ambos" | undefined;

/** Hero KPIs. Mortalidade prioriza baixas/churn/mediana vida; crescimento prioriza saldo/densidade. */
export function extractKpis(md: string, angle?: KpiAngle): BlogKpi[] {
  const tables = parseMdTables(md);
  const destaques =
    tables.find((t) =>
      (t[0]?.[0] ?? "").toLowerCase().includes("indicador"),
    ) ?? tables[0];
  if (!destaques) return [];

  const kpis: BlogKpi[] = [];
  const mortAngle = angle === "mortalidade";

  const parque = pickCell(
    destaques,
    (i) => i.includes("parque ativo") || i === "parque ativo",
  );
  if (parque) {
    kpis.push({
      key: "parque",
      label: "Parque ativo",
      value: firstNumberish(parque) ?? stripMd(parque),
      tone: "neutral",
    });
  }

  const combo = pickCell(
    destaques,
    (i) => i.includes("aberturas") && (i.includes("saldo") || i.includes("baixas")),
  );
  const comboParts = combo ? parseComboParts(combo) : null;

  if (mortAngle && comboParts?.baixas) {
    kpis.push({
      key: "baixas",
      label: "Baixas no trimestre",
      value: comboParts.baixas,
      tone: "alert",
    });
  } else {
    const saldoCell = pickCell(destaques, (i) => i.includes("saldo") && !i.includes("aberturas"));
    const saldoRaw = saldoCell ?? comboParts?.saldo;
    if (saldoRaw) {
      const v = firstNumberish(saldoRaw) ?? stripMd(saldoRaw);
      const neg = v.trim().startsWith("-");
      kpis.push({
        key: "saldo",
        label: "Saldo líquido",
        value: v.startsWith("+") || v.startsWith("-") ? v : `+${v}`,
        tone: neg ? "alert" : "positive",
      });
    }
  }

  const churn = pickCell(destaques, (i) => i.includes("churn"));
  if (churn && (mortAngle || kpis.length < 4)) {
    const v = firstNumberish(churn) ?? stripMd(churn);
    kpis.push({
      key: "churn",
      label: "Churn trimestral",
      value: v.includes("%") ? v : `${v}%`,
      tone: "warn",
    });
  }

  const mediana = pickCell(
    destaques,
    (i) => i.includes("mediana de vida") || i.includes("mediana vida"),
  );
  if (mediana && mortAngle) {
    const v = firstNumberish(mediana) ?? stripMd(mediana);
    kpis.push({
      key: "mediana_vida",
      label: "Mediana de vida",
      value: /ano/i.test(v) ? v : `${v} anos`,
      tone: "warn",
    });
  }

  if (!mortAngle || kpis.length < 4) {
    const mort = pickCell(
      destaques,
      (i) =>
        i.includes("mortalidade") ||
        (i.includes("< 1") && i.includes("ano")) ||
        (i.includes("1 ano") && i.includes("mortalidade")),
    );
    if (mort && !kpis.some((k) => k.key === "mortalidade")) {
      const v = firstNumberish(mort) ?? stripMd(mort);
      const n = parseFloat(v.replace("%", "").replace(",", "."));
      kpis.push({
        key: "mortalidade",
        label: "Mortalidade < 1 ano",
        value: v.includes("%") ? v : `${v}%`,
        tone: !Number.isNaN(n) && n >= 30 ? "alert" : n >= 15 ? "warn" : "neutral",
      });
    }
  }

  if (!mortAngle || kpis.length < 4) {
    const dens = pickCell(destaques, (i) => i.includes("densidade"));
    if (dens && !kpis.some((k) => k.key === "densidade")) {
      kpis.push({
        key: "densidade",
        label: "Habitantes / academia",
        value: formatDensityDisplay(dens),
        tone: "neutral",
      });
    }
  }

  return kpis.slice(0, 4);
}

/** Extraí churn pra pill do hero. */
export function extractChurnPill(md: string): string | null {
  const tables = parseMdTables(md);
  const destaques =
    tables.find((t) =>
      (t[0]?.[0] ?? "").toLowerCase().includes("indicador"),
    ) ?? tables[0];
  if (!destaques) return null;
  const churn = pickCell(destaques, (i) => i.includes("churn"));
  if (!churn) return null;
  const v = firstNumberish(churn);
  return v ? `CHURN ${v.includes("%") ? v : `${v}%`}` : null;
}

function bandToneInfant(label: string): AgeBand["tone"] {
  const l = label.toLowerCase();
  if (l.includes("< 1") || l.includes("&lt; 1") || l.startsWith("<")) return "alert";
  if (l.includes("1–3") || l.includes("1-3")) return "warn";
  if (l.includes("3–5") || l.includes("3-5")) return "neutral";
  return "positive";
}

/** Saída madura (DF): &lt;1ano verde; ≥5 anos alerta. */
function bandToneMaturity(label: string): AgeBand["tone"] {
  const l = label.toLowerCase();
  if (l.includes("< 1") || l.includes("&lt; 1") || l.startsWith("<")) return "positive";
  if (l.includes("1–3") || l.includes("1-3")) return "warn";
  if (l.includes("3–5") || l.includes("3-5")) return "warn";
  return "alert";
}

function isMaturityExitStory(bands: AgeBand[]): boolean {
  if (!bands.length) return false;
  const top = bands.reduce((a, b) => (a.pct >= b.pct ? a : b));
  return /≥\s*5|>=\s*5|5\s*\+|5 anos/i.test(top.label);
}

export function extractAgeBands(md: string): AgeBand[] {
  const tables = parseMdTables(md);
  // Preferir tabela "Faixa | Qtd | %" — evitar cluster com coluna "Mediana vida".
  const life =
    tables.find((t) => {
      const h = (t[0] ?? []).map((c) => c.toLowerCase());
      return h.some((c) => c.includes("faixa"));
    }) ??
    tables.find((t) => {
      const h = (t[0] ?? []).join(" ").toLowerCase();
      if (!h.includes("vida")) return false;
      // 2ª/3ª colunas tipicamente Qtd/%
      const sample = t[1] ?? [];
      return sample.some((c) => /%/.test(c));
    });
  let bands: AgeBand[] = [];
  if (life) {
    for (const row of life.slice(1)) {
      const label = decodeEntities(row[0] ?? "");
      const pctRaw = row[2] ?? row[1] ?? "";
      const pct = parseFloat(pctRaw.replace("%", "").replace(",", "."));
      if (!label || Number.isNaN(pct)) continue;
      // Ignora linhas de cluster (bairro), não faixas etárias
      if (!/(ano|anos|<|≥|>=)/i.test(label)) continue;
      bands.push({ label, pct, tone: "neutral" });
    }
  }

  if (!bands.length) {
    const re = /\[([^\]]+)\]\s*█+\s*([\d.,]+)\s*%/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(md))) {
      bands.push({
        label: m[1]!.trim(),
        pct: parseFloat(m[2]!.replace(",", ".")),
        tone: "neutral",
      });
    }
  }

  const maturity = isMaturityExitStory(bands);
  const toneFn = maturity ? bandToneMaturity : bandToneInfant;
  return bands.map((b) => ({ ...b, tone: toneFn(b.label) }));
}

export function ageBandsTitle(bands: AgeBand[]): string {
  if (isMaturityExitStory(bands)) {
    return "Tempo de vida das baixas · saída madura";
  }
  return "Tempo de vida das baixas · mortalidade precoce";
}

export function extractRankPill(md: string, angleLabel: string): string | null {
  const text = stripMd(md.slice(0, 1200));
  const m =
    text.match(/(\d+)[ªº°]\s*posi[cç][aã]o/i) ||
    text.match(/rank\s*(\d+)/i) ||
    text.match(/top\s*(\d+)/i);
  if (m) {
    const n = m[1];
    if (/mortalidade/i.test(angleLabel)) return `RANK ${n} MORTALIDADE`;
    if (/crescimento/i.test(angleLabel)) return `RANK ${n} CRESCIMENTO`;
    return `RANK ${n}`;
  }
  return null;
}

export function extractToc(md: string): TocItem[] {
  const items: TocItem[] = [];
  const seen = new Set<string>();
  for (const line of md.split(/\r?\n/)) {
    const m = line.match(/^##\s+(.+)$/);
    if (!m) continue;
    const label = stripMd(m[1]!).replace(/^\d+\.\s*/, "");
    if (/^destaques/i.test(label)) continue; // KPIs no hero
    let id = slugify(label);
    if (!id) continue;
    if (seen.has(id)) id = `${id}-${seen.size}`;
    seen.add(id);
    items.push({ id, label });
  }
  return items;
}

/** Remove tabela Destaques + ASCII bars; marca ponto pra AgeBandBars. */
export function prepareBodyMarkdown(md: string): string {
  let out = md;
  let placed = false;
  out = out.replace(/```[\s\S]*?█[\s\S]*?```/g, () => {
    placed = true;
    return "\n<!--AGE_BANDS-->\n";
  });

  out = out.replace(
    /^##\s+Destaques[^\n]*\n+[\s\S]*?(?=^---\s*$|^##\s+)/m,
    "",
  );

  if (!placed) {
    // Após tabela Faixa/vida (posts sem ASCII)
    out = out.replace(
      /(\|[\s\S]*?(?:Faixa|vida)[\s\S]*?\n(?:\|[^\n]*\n)+)/i,
      (block) => {
        placed = true;
        return `${block}\n<!--AGE_BANDS-->\n`;
      },
    );
  }

  return out.trim();
}

/** Atribui id nos H2 na ordem do TOC (âncoras sticky). */
export function injectHeadingIds(html: string, toc: TocItem[]): string {
  let i = 0;
  return html.replace(/<h2([^>]*)>([\s\S]*?)<\/h2>/gi, (_m, attrs: string, inner: string) => {
    const plain = stripMd(inner.replace(/<[^>]+>/g, ""));
    if (/^destaques/i.test(plain)) return `<h2${attrs}>${inner}</h2>`;
    const id = toc[i]?.id ?? slugify(plain);
    i += 1;
    const cleanAttrs = String(attrs).replace(/\s*id="[^"]*"/i, "");
    return `<h2${cleanAttrs} id="${id}">${inner}</h2>`;
  });
}

/** Pós-processa HTML: callouts, caveat metodológico, badges em células %. */
export function enhanceArticleHtml(html: string): string {
  let out = html;

  // Insight / caveat blockquotes
  out = out.replace(
    /<blockquote>\s*<p>([\s\S]*?)<\/p>\s*<\/blockquote>/gi,
    (_m, inner: string) => {
      const text = inner.replace(/<[^>]+>/g, " ");
      const isCaveat =
        /ressalva|metodol[oó]gic|caveat|aten[cç][aã]o.*dado|n[aã]o confundir/i.test(
          text,
        );
      if (isCaveat) {
        return (
          `<aside class="data-caveat" role="note">` +
          `<div class="caveat-header">` +
          `<span class="badge-warning">Ressalva metodológica</span>` +
          `<h4>Leitura correta dos dados de renda</h4>` +
          `</div>` +
          `<div class="caveat-body">${inner}</div>` +
          `</aside>`
        );
      }
      const isInsight =
        /e daí|gestor|significa|interpreta|hipótese/i.test(text);
      if (!isInsight) {
        return `<blockquote class="bq">${inner}</blockquote>`;
      }
      return `<aside class="insight" role="note"><span class="insight-ico" aria-hidden="true">◆</span><div class="insight-body">${inner}</div></aside>`;
    },
  );

  // Cluster diagnosis badges (última coluna curta com Maturidade/Saída)
  out = out.replace(/<td>([\s\S]*?)<\/td>/gi, (_m, inner: string) => {
    const plain = inner.replace(/<[^>]+>/g, "").trim();
    if (/^maturidade/i.test(plain)) {
      return `<td><span class="badge badge-diag badge-warn">${inner}</span></td>`;
    }
    if (/^sa[ií]da\s+tard/i.test(plain)) {
      return `<td><span class="badge badge-diag badge-alert">${inner}</span></td>`;
    }
    const pct = plain.match(/^([+\-]?\d[\d.,]*\s*%)$/);
    if (pct) {
      const neg = plain.includes("-") && !plain.startsWith("+");
      const high =
        parseFloat(plain.replace("%", "").replace(",", ".").replace("+", "")) >=
        30;
      const cls = neg ? "badge badge-neg" : high ? "badge badge-alert" : "badge badge-pos";
      return `<td><span class="${cls}">${inner}</span></td>`;
    }
    const delta = plain.match(/^([+\-]\d[\d.,]*%?)/);
    if (delta && (plain.startsWith("+") || plain.startsWith("-"))) {
      const cls = plain.startsWith("-") ? "badge badge-neg" : "badge badge-pos";
      return `<td><span class="${cls}">${inner}</span></td>`;
    }
    return `<td>${inner}</td>`;
  });

  return out;
}
