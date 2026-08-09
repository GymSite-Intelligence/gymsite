/**
 * Extração e normalização de localização BR a partir de texto livre.
 *
 * O backend (`api.getgymsite.com.br`) resolve bairro/cidade/UF; o frontend
 * envia um hint estruturado + formas com/sem acento para o parser tolerar
 * entradas como "Parangaba" vs "Parangabá".
 */

export interface LocalizacaoExtraida {
  bairro?: string;
  cidade?: string;
  uf?: string;
  /** Forma original capturada (pode ter acento). */
  bruto: string;
}

export type ConversarLocHint = {
  bairro?: string;
  cidade?: string;
  uf?: string;
};

const UFS = new Set([
  "AC",
  "AL",
  "AP",
  "AM",
  "BA",
  "CE",
  "DF",
  "ES",
  "GO",
  "MA",
  "MT",
  "MS",
  "MG",
  "PA",
  "PB",
  "PR",
  "PE",
  "PI",
  "RJ",
  "RN",
  "RS",
  "RO",
  "RR",
  "SC",
  "SP",
  "SE",
  "TO",
]);

/** Remove diacríticos: "Parangabá" → "Parangaba", "São" → "Sao". */
export function foldAcentos(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "");
}

/** Comparação case/accent-insensitive. */
export function samePlace(a: string, b: string): boolean {
  return foldAcentos(a).trim().toLowerCase() === foldAcentos(b).trim().toLowerCase();
}

function titleCaseBr(s: string): string {
  return s
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => {
      const lower = w.toLowerCase();
      if (["de", "da", "do", "das", "dos", "e"].includes(lower)) return lower;
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

function limparToken(s: string): string {
  return s
    .replace(/^[\s,.;:/\-–—?]+|[\s,.;:/\-–—?]+$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function parseUf(token?: string): string | undefined {
  if (!token) return undefined;
  const u = foldAcentos(token).trim().toUpperCase();
  return UFS.has(u) ? u : undefined;
}

/** Separa UF final ("Fortaleza CE" | "Fortaleza - CE" | "Fortaleza/CE"). */
function peelUf(text: string): { rest: string; uf?: string } {
  const t = limparToken(text);
  const m = t.match(/^(.*?)(?:\s+|[\s]*[,/\-–—]\s*)([A-Za-z]{2})$/i);
  if (!m) return { rest: t };
  const uf = parseUf(m[2]);
  if (!uf) return { rest: t };
  return { rest: limparToken(m[1]), uf };
}

function looksLikePlaceName(s: string): boolean {
  const words = s.trim().split(/\s+/);
  if (words.length === 0 || words.length > 4) return false;
  if (/quantas|academia|academias|abrir|quero|preciso|analise|análise/i.test(s)) return false;
  return /^[\p{L}'’.\\-]+(?:\s+[\p{L}'’.\\-]+)*$/u.test(s.trim());
}

/**
 * Extrai bairro/cidade/UF de frases comuns da degustação:
 * - "bairro Parangaba em Fortaleza CE"
 * - "Parangabá, Fortaleza - CE"
 * - "Parangaba Fortaleza CE"
 * - "no Cocó, Fortaleza?"
 */
export function extractLocalizacao(texto: string): LocalizacaoExtraida | null {
  const raw = texto.trim();
  if (!raw) return null;

  // 1) "bairro X em/de/na Cidade [UF]"
  const mBairroEm = raw.match(/\bbairro\s+(.+?)\s+(?:em|de|da|do|na|no)\s+(.+?)(?=[?!.]*$)/i);
  if (mBairroEm) {
    const bairro = titleCaseBr(limparToken(mBairroEm[1]));
    const { rest: cidadeRaw, uf } = peelUf(mBairroEm[2]);
    const cidade = titleCaseBr(cidadeRaw);
    if (looksLikePlaceName(bairro) && looksLikePlaceName(cidade)) {
      return { bairro, cidade, uf, bruto: mBairroEm[0] };
    }
  }

  // 2) "em/no/na Bairro, Cidade [UF]"
  const mEm = raw.match(/\b(?:em|no|na)\s+([^,?!.]+?)\s*,\s*([^?!.]+)/i);
  if (mEm) {
    const bairro = titleCaseBr(limparToken(mEm[1]));
    const { rest: cidadeRaw, uf } = peelUf(mEm[2]);
    const cidade = titleCaseBr(cidadeRaw);
    if (looksLikePlaceName(bairro) && looksLikePlaceName(cidade)) {
      return { bairro, cidade, uf, bruto: mEm[0] };
    }
  }

  // 3) Confirmação curta / "Cidade - UF"
  const compact = limparToken(raw.replace(/[?!.]+$/g, ""));
  if (compact.split(/\s+/).length <= 8) {
    // "Cidade - UF" / "Cidade/UF" (sem bairro) — antes do split por espaço
    // pra não tratar "-" como "cidade".
    const mCidadeUf = compact.match(/^(.+?)\s*[,/\-–—]\s*([A-Za-z]{2})$/i);
    if (mCidadeUf) {
      const uf = parseUf(mCidadeUf[2]);
      const cidade = titleCaseBr(limparToken(mCidadeUf[1]));
      // Se o lado esquerdo tem vírgola, é "Bairro, Cidade - UF" (tratado abaixo).
      if (uf && looksLikePlaceName(cidade) && !cidade.includes(",")) {
        return { cidade, uf, bruto: mCidadeUf[0] };
      }
    }

    // "Bairro, Cidade - UF" ou "Bairro, Cidade, UF"
    const mComma = compact.match(/^([^,]+),\s*([^,]+?)(?:\s*[,/\-–—]\s*|\s+)([A-Za-z]{2})$/i);
    if (mComma) {
      const uf = parseUf(mComma[3]);
      const bairro = titleCaseBr(limparToken(mComma[1]));
      const cidade = titleCaseBr(limparToken(mComma[2]));
      if (uf && looksLikePlaceName(bairro) && looksLikePlaceName(cidade)) {
        return { bairro, cidade, uf, bruto: compact };
      }
    }

    // "Bairro Cidade UF" (últimas 2 tokens: cidade + UF, resto = bairro)
    const parts = compact.split(/\s+/).filter((p) => !/^[,/\-–—]+$/.test(p));
    if (parts.length >= 3) {
      const uf = parseUf(parts[parts.length - 1]);
      if (uf) {
        const cidade = titleCaseBr(parts[parts.length - 2]);
        const bairro = titleCaseBr(parts.slice(0, -2).join(" "));
        if (looksLikePlaceName(bairro) && looksLikePlaceName(cidade)) {
          return { bairro, cidade, uf, bruto: compact };
        }
      }
    }
  }

  return null;
}

/** Bloco anexado à mensagem da API (não aparece na bolha do usuário). */
export function formatLocalizacaoHint(loc: LocalizacaoExtraida): string {
  const parts: string[] = [];
  if (loc.bairro) {
    parts.push(`bairro=${loc.bairro}`);
    const ascii = foldAcentos(loc.bairro);
    if (ascii !== loc.bairro) parts.push(`bairro_ascii=${ascii}`);
  }
  if (loc.cidade) {
    parts.push(`cidade=${loc.cidade}`);
    const ascii = foldAcentos(loc.cidade);
    if (ascii !== loc.cidade) parts.push(`cidade_ascii=${ascii}`);
  }
  if (loc.uf) parts.push(`uf=${loc.uf}`);
  return `[contexto_localizacao: ${parts.join("; ")}]`;
}

/** Mensagem enviada à API = texto do usuário + hint estruturado (se houver). */
export function enrichMensagemComLocalizacao(texto: string): {
  mensagem: string;
  localizacao?: ConversarLocHint;
} {
  const loc = extractLocalizacao(texto);
  if (!loc) return { mensagem: texto };
  const localizacao: ConversarLocHint = {
    bairro: loc.bairro,
    cidade: loc.cidade,
    uf: loc.uf,
  };
  if (/\[contexto_localizacao:/i.test(texto)) {
    return { mensagem: texto, localizacao };
  }
  return {
    mensagem: `${texto.trim()}\n\n${formatLocalizacaoHint(loc)}`,
    localizacao,
  };
}
