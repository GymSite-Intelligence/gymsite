/**
 * Exporta totais dos 20 kits (TS) pra JSON consumível pelo backend Python.
 *
 * Como rodar:
 *   node scripts/exportar-kits-totais.mjs > ../tools/kits_totais.json
 *
 * O backend (tools/kits_equipamentos.py) lê esse JSON e usa pra cascata
 * financeira no A4. Frontend continua sendo source-of-truth pros detalhes UI.
 *
 * Roda diretamente sem tsc — usa @ts-blank-space ou parsing manual via regex.
 * Como nossos kits são objects com forma estável, vamos com regex direto.
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const KITS_DIR = join(__dirname, '../src/data/kits')

/**
 * Parse muito simples — extrai `preco_un: NUMERO` e `qtd: NUMERO` de cada item
 * via regex sobre o source TS. Não roda o TS, só lê o texto.
 */
function parseKit(source, exportName) {
  // Acha o bloco do export. Usa `\\b` pós-nome pra evitar match parcial
  // (ex: ACADEMIA_P casando com ACADEMIA_PP). E `:` força ser declaração.
  const regex = new RegExp(
    `export const ${exportName}\\b[^=]*=\\s*\\{([\\s\\S]*?)\\n\\}`,
    'm',
  )
  const match = source.match(regex)
  if (!match) {
    throw new Error(`Kit ${exportName} não encontrado no arquivo`)
  }
  const block = match[1]

  // Extrai desconto_volume_pct: [min, max]
  const descMatch = block.match(
    /desconto_volume_pct:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]/,
  )
  const descMin = descMatch ? parseFloat(descMatch[1]) : 0.15
  const descMax = descMatch ? parseFloat(descMatch[2]) : 0.35

  // Soma preco_un × qtd dos itens. Regex captura pares (qtd, preco_un).
  const itensRegex = /qtd:\s*(\d+)[^}]*preco_un:\s*(\d+)/g
  let total = 0
  let count = 0
  let m
  while ((m = itensRegex.exec(block)) !== null) {
    total += parseInt(m[1], 10) * parseInt(m[2], 10)
    count++
  }

  return {
    bruto: total,
    estimado_min: Math.round(total * (1 - descMax)),
    estimado_max: Math.round(total * (1 - descMin)),
    mediana_real: Math.round((total * (1 - descMax) + total * (1 - descMin)) / 2),
    itens_count: count,
    desconto_min: descMin,
    desconto_max: descMax,
  }
}

const arquivos = readdirSync(KITS_DIR).filter((f) => f.endsWith('.ts') && f !== 'types.ts' && f !== 'index.ts')

const KIT_EXPORTS = [
  // modelo, tamanho, arquivo, export-name
  ['academia', 'pp', 'academia.ts', 'ACADEMIA_PP'],
  ['academia', 'p', 'academia.ts', 'ACADEMIA_P'],
  ['academia', 'm', 'academia.ts', 'ACADEMIA_M'],
  ['academia', 'g', 'academia.ts', 'ACADEMIA_G'],
  ['academia', 'gg', 'academia.ts', 'ACADEMIA_GG'],
  ['crossfit_box', 'pp', 'crossfit-box.ts', 'CROSSFIT_PP'],
  ['crossfit_box', 'p', 'crossfit-box.ts', 'CROSSFIT_P'],
  ['crossfit_box', 'm', 'crossfit-box.ts', 'CROSSFIT_M'],
  ['crossfit_box', 'g', 'crossfit-box.ts', 'CROSSFIT_G'],
  ['crossfit_box', 'gg', 'crossfit-box.ts', 'CROSSFIT_GG'],
  ['studio_pilates', 'pp', 'studio-pilates.ts', 'PILATES_PP'],
  ['studio_pilates', 'p', 'studio-pilates.ts', 'PILATES_P'],
  ['studio_pilates', 'm', 'studio-pilates.ts', 'PILATES_M'],
  ['studio_pilates', 'g', 'studio-pilates.ts', 'PILATES_G'],
  ['studio_pilates', 'gg', 'studio-pilates.ts', 'PILATES_GG'],
  ['studio_funcional', 'pp', 'studio-funcional.ts', 'FUNCIONAL_PP'],
  ['studio_funcional', 'p', 'studio-funcional.ts', 'FUNCIONAL_P'],
  ['studio_funcional', 'm', 'studio-funcional.ts', 'FUNCIONAL_M'],
  ['studio_funcional', 'g', 'studio-funcional.ts', 'FUNCIONAL_G'],
  ['studio_funcional', 'gg', 'studio-funcional.ts', 'FUNCIONAL_GG'],
]

const result = {}
const cacheArquivos = new Map()

for (const [modelo, tamanho, arquivo, exportName] of KIT_EXPORTS) {
  if (!cacheArquivos.has(arquivo)) {
    cacheArquivos.set(arquivo, readFileSync(join(KITS_DIR, arquivo), 'utf-8'))
  }
  const source = cacheArquivos.get(arquivo)
  const kit = parseKit(source, exportName)
  if (!result[modelo]) result[modelo] = {}
  result[modelo][tamanho] = kit
}

console.log(JSON.stringify(result, null, 2))
console.error(`\n✓ Exportados ${KIT_EXPORTS.length} kits`)
