import { describe, expect, test } from "bun:test";
import {
  ageBandsTitle,
  enhanceArticleHtml,
  extractAgeBands,
  extractChurnPill,
  extractKpis,
  extractRankPill,
  extractToc,
  prepareBodyMarkdown,
} from "./enrich";

const BH = `# Raio-X BH

Belo Horizonte ficou na **2ª posição** do ranking.

## Destaques do trimestre

| Indicador | Valor (Q1 2026) |
| --- | --- |
| Parque ativo mapeado | 596 |
| Saldo líquido | **+51** (~**+8,6%**) |
| Densidade hab./academia (início → fim)* | **4.433 → 4.053** |
| Mortalidade &lt; 1 ano (entre baixados) | **40%** |

---

## 2. Vale da morte

| Faixa de vida | Qtd | % |
| --- | --- | --- |
| &lt; 1 ano | 4 | 40% |
| 1–3 anos | 2 | 20% |
| ≥ 5 anos | 3 | 30% |

\`\`\`
[< 1 Ano]    ████ 40%
\`\`\`

## Checklist

1. Foo
`;

const BSB = `# Brasília

rank 2 mortalidade

## Destaques

| Indicador | Valor (Q1 2026) |
| --- | --- |
| Parque ativo | 636 |
| Aberturas / Baixas / Saldo | 31 / 17 / **+14** |
| Taxa de churn | **2,67%** |
| Mediana de vida (baixados) | **5,14 anos** |
| Mortalidade &lt; 1 ano | **5,88%** |

## Vida dos baixados

| Faixa | Qtd | % |
| --- | --- | --- |
| &lt; 1 ano | 1 | 5,88% |
| ≥ 5 anos | 9 | 52,94% |

> **Ressalva metodológica:** não confundir mediana municipal com ticket no Lago Sul.
`;

describe("blog enrich", () => {
  test("extractKpis from destaques table", () => {
    const kpis = extractKpis(BH);
    expect(kpis.map((k) => k.key)).toEqual([
      "parque",
      "saldo",
      "mortalidade",
      "densidade",
    ]);
    expect(kpis.find((k) => k.key === "saldo")?.tone).toBe("positive");
    expect(kpis.find((k) => k.key === "mortalidade")?.tone).toBe("alert");
    expect(kpis.find((k) => k.key === "densidade")?.value).toContain("4.053");
  });

  test("mortalidade KPIs prefer baixas + churn + mediana", () => {
    const kpis = extractKpis(BSB, "mortalidade");
    expect(kpis.map((k) => k.key)).toEqual([
      "parque",
      "baixas",
      "churn",
      "mediana_vida",
    ]);
    expect(kpis.find((k) => k.key === "baixas")?.value).toBe("17");
    expect(kpis.find((k) => k.key === "churn")?.tone).toBe("warn");
    expect(extractChurnPill(BSB)).toContain("CHURN");
  });

  test("extractAgeBands + rank + toc", () => {
    const bhBands = extractAgeBands(BH);
    expect(bhBands.length).toBeGreaterThanOrEqual(3);
    expect(bhBands.find((b) => b.label.includes("1 ano"))?.tone).toBe("alert");
    expect(extractRankPill(BH, "Crescimento")).toContain("RANK 2");
    const toc = extractToc(BH);
    expect(toc.some((t) => /vale/i.test(t.label))).toBe(true);
    expect(toc.some((t) => /destaques/i.test(t.label))).toBe(false);
  });

  test("maturity-exit age tones invert for DF story", () => {
    const bands = extractAgeBands(BSB);
    expect(bands.find((b) => b.label.includes("5 anos"))?.tone).toBe("alert");
    expect(bands.find((b) => b.label.includes("1 ano"))?.tone).toBe("positive");
    expect(ageBandsTitle(bands)).toMatch(/saída madura|estabelecidos/i);
  });

  test("caveat blockquote becomes data-caveat", () => {
    const html = enhanceArticleHtml(
      "<blockquote><p><strong>Ressalva metodológica:</strong> não confundir.</p></blockquote>",
    );
    expect(html).toContain('class="data-caveat"');
    expect(html).toContain("badge-warning");
  });

  test("prepareBody strips destaques and marks age bars", () => {
    const out = prepareBodyMarkdown(BH.replace(/^#.*\n\n/, ""));
    expect(out).not.toMatch(/Parque ativo mapeado/);
    expect(out).toContain("<!--AGE_BANDS-->");
    expect(out).not.toContain("█");
  });
});
