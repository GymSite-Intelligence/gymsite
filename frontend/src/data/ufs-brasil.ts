/**
 * UFs do Brasil — dataset estático (27 itens, IDs IBGE oficiais).
 *
 * Não vale a pena fetch da API — dados não mudam em horizonte de décadas.
 * Ordenado por nome pra dropdown imediato.
 */
export interface UF {
  id: number
  sigla: string
  nome: string
  regiao: 'Norte' | 'Nordeste' | 'Centro-Oeste' | 'Sudeste' | 'Sul'
}

export const UFS_BRASIL: UF[] = [
  { id: 12, sigla: 'AC', nome: 'Acre', regiao: 'Norte' },
  { id: 27, sigla: 'AL', nome: 'Alagoas', regiao: 'Nordeste' },
  { id: 16, sigla: 'AP', nome: 'Amapá', regiao: 'Norte' },
  { id: 13, sigla: 'AM', nome: 'Amazonas', regiao: 'Norte' },
  { id: 29, sigla: 'BA', nome: 'Bahia', regiao: 'Nordeste' },
  { id: 23, sigla: 'CE', nome: 'Ceará', regiao: 'Nordeste' },
  { id: 53, sigla: 'DF', nome: 'Distrito Federal', regiao: 'Centro-Oeste' },
  { id: 32, sigla: 'ES', nome: 'Espírito Santo', regiao: 'Sudeste' },
  { id: 52, sigla: 'GO', nome: 'Goiás', regiao: 'Centro-Oeste' },
  { id: 21, sigla: 'MA', nome: 'Maranhão', regiao: 'Nordeste' },
  { id: 51, sigla: 'MT', nome: 'Mato Grosso', regiao: 'Centro-Oeste' },
  { id: 50, sigla: 'MS', nome: 'Mato Grosso do Sul', regiao: 'Centro-Oeste' },
  { id: 31, sigla: 'MG', nome: 'Minas Gerais', regiao: 'Sudeste' },
  { id: 15, sigla: 'PA', nome: 'Pará', regiao: 'Norte' },
  { id: 25, sigla: 'PB', nome: 'Paraíba', regiao: 'Nordeste' },
  { id: 41, sigla: 'PR', nome: 'Paraná', regiao: 'Sul' },
  { id: 26, sigla: 'PE', nome: 'Pernambuco', regiao: 'Nordeste' },
  { id: 22, sigla: 'PI', nome: 'Piauí', regiao: 'Nordeste' },
  { id: 33, sigla: 'RJ', nome: 'Rio de Janeiro', regiao: 'Sudeste' },
  { id: 24, sigla: 'RN', nome: 'Rio Grande do Norte', regiao: 'Nordeste' },
  { id: 43, sigla: 'RS', nome: 'Rio Grande do Sul', regiao: 'Sul' },
  { id: 11, sigla: 'RO', nome: 'Rondônia', regiao: 'Norte' },
  { id: 14, sigla: 'RR', nome: 'Roraima', regiao: 'Norte' },
  { id: 42, sigla: 'SC', nome: 'Santa Catarina', regiao: 'Sul' },
  { id: 35, sigla: 'SP', nome: 'São Paulo', regiao: 'Sudeste' },
  { id: 28, sigla: 'SE', nome: 'Sergipe', regiao: 'Nordeste' },
  { id: 17, sigla: 'TO', nome: 'Tocantins', regiao: 'Norte' },
]

function foldUfToken(s: string): string {
  return s
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toUpperCase()
}

const SKIP_LUGAR = new Set(
  [
    'BRASIL',
    'BRAZIL',
    'NORTE',
    'NORDESTE',
    'SUL',
    'SUDESTE',
    'CENTRO-OESTE',
    'CENTRO OESTE',
    'REGIAO NORTE',
    'REGIAO NORDESTE',
    'REGIAO SUL',
    'REGIAO SUDESTE',
    'REGIAO CENTRO-OESTE',
    'REGIAO CENTRO OESTE',
    ...UFS_BRASIL.map((u) => foldUfToken(u.nome)),
    ...UFS_BRASIL.map((u) => u.sigla),
  ],
)

function isUfPart(part: string): boolean {
  const folded = foldUfToken(part).replace(/\s+/g, ' ').trim()
  if (!folded) return true
  if (SKIP_LUGAR.has(folded)) return true
  if (folded.length === 2 && UFS_BRASIL.some((u) => u.sigla === folded)) return true
  return false
}

function stripTrailingUf(part: string): string {
  const bits = part.trim().split(/\s+/)
  if (bits.length < 2) return part.trim()
  const last = bits[bits.length - 1] ?? ''
  if (last.length === 2 && /^[A-Za-z]{2}$/.test(last) && isUfPart(last)) {
    return bits.slice(0, -1).join(' ')
  }
  return part.trim()
}

/** Sigla a partir do texto (nome do estado ou MG/CE/…). Nomes longos primeiro. */
export function ufFromText(s: string): string | undefined {
  const folded = foldUfToken(s)
  if (!folded.trim()) return undefined
  const byNome = [...UFS_BRASIL].sort((a, b) => b.nome.length - a.nome.length)
  for (const uf of byNome) {
    const nome = foldUfToken(uf.nome)
    if (new RegExp(`\\b${nome}\\b`).test(folded)) return uf.sigla
  }
  for (const uf of UFS_BRASIL) {
    const re = new RegExp(`(^|[^A-Z0-9])${uf.sigla}([^A-Z0-9]|$)`)
    if (re.test(folded)) return uf.sigla
  }
  return undefined
}

export function parseLugarExplorar(q: string): {
  bairro?: string
  cidade?: string
  uf?: string
} {
  const parts = (q || '')
    .replace(/\s+-\s+/g, ',')
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean)
  const uf = ufFromText(q)
  const bairro = parts[0] ? stripTrailingUf(parts[0]) : ''
  let cidade = ''
  for (const raw of parts.slice(1)) {
    const part = stripTrailingUf(raw)
    if (!part || isUfPart(part)) continue
    cidade = part
    break
  }
  return {
    bairro: bairro.length >= 2 ? bairro : undefined,
    cidade: cidade.length >= 2 ? cidade : undefined,
    uf,
  }
}
