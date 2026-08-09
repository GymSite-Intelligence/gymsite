/**
 * AbsorcaoMargemFrescaCard — leitura executiva: aluno novo vs disputa com o parque.
 * Vernáculo (leitura-executiva-pdf); IDs técnicos ficam no JSON.
 */
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AbsorcaoMargemFrescaJSON } from '@/hooks/useRelatorioDetail'

const NOME_FAIXA: Record<string, string> = {
  '15-24': 'Jovem',
  '25-39': 'Core',
  '40-59': 'Maduro',
  '60+': 'Silver',
}

const ROTULO_UI: Record<
  string,
  { label: string; variant: 'success' | 'warning' | 'destructive' | 'secondary' }
> = {
  fresco: { label: 'Aluno novo disponível', variant: 'success' },
  misto: { label: 'Crescimento misto', variant: 'warning' },
  roubo: { label: 'Disputa com o parque', variant: 'destructive' },
}

function _int(n: number | undefined | null): string {
  if (n == null || Number.isNaN(Number(n))) return '—'
  return Math.round(Number(n)).toLocaleString('pt-BR')
}

function faixasHumanas(faixas: string[] | undefined): string {
  if (!faixas?.length) return ''
  return faixas.map((f) => `${f} · ${NOME_FAIXA[f] ?? f}`).join('; ')
}

function carimboText(raw: unknown): string {
  if (raw == null) return ''
  if (typeof raw === 'string') return raw
  if (typeof raw === 'object') {
    const o = raw as { valor?: unknown; base?: string; fonte?: string; janela?: string }
    const parts = [o.valor, o.base, o.fonte, o.janela].filter((x) => x != null && x !== '')
    return parts.map(String).join(' · ')
  }
  return String(raw)
}

function conclusaoTexto(rotulo: string): string {
  if (rotulo === 'fresco') {
    return (
      'Ainda há espaço para matricular alunos que hoje não estão no parque de academias do bairro. ' +
      'O potencial do público escolhido cobre a capacidade da sua unidade sem depender só de tirar aluno do concorrente.'
    )
  }
  if (rotulo === 'misto') {
    return (
      'Parte do crescimento pode vir de alunos novos; outra parte exige disputar quem já treina no bairro. ' +
      "Planeje aquisição mista (lançamento + migração) e não conte só com 'mercado virgem'."
    )
  }
  if (rotulo === 'roubo') {
    return (
      'No público escolhido, a oferta instalada já supera o potencial estimado de alunos. ' +
      'Crescer nesta unidade significa, na prática, atrair quem hoje treina em outra academia do bairro — ' +
      'custo de aquisição mais alto e guerra de proposta de valor.'
    )
  }
  return 'Cruzar potencial do público-alvo com a capacidade já instalada antes de decidir o modelo.'
}

function notaVoronoi(smoke: AbsorcaoMargemFrescaJSON['voronoi_smoke']): string | null {
  if (!smoke || smoke.status !== 'ok') return null
  const pv = smoke.pool_voronoi
  const d = smoke.delta_pct
  if (pv == null || d == null || Number.isNaN(Number(d))) return null
  const dF = Number(d)
  const pct = `${Math.round(Math.abs(dF) * 100)}%`
  const sentido = dF < 0 ? 'menor' : 'maior'
  const como =
    smoke.metodo_pool === 'piramide_celula'
      ? 'recontando a faixa etária só nessa área'
      : 'proporcional à população nessa área'
  const onde =
    smoke.pin_fonte === 'centroide_bairro'
      ? 'se a unidade ficasse no centro do bairro'
      : 'na área de influência entre academias'
  return (
    `Se usássemos ${onde} (Voronoi clássico), ${como}, o potencial no público escolhido seria cerca de ` +
    `${_int(pv)} alunos (${pct} ${sentido} que o bairro inteiro). ` +
    `O veredito fresco/roubo desta versão usa o bairro. ` +
    `Medição interna — não muda a decisão nesta versão.`
  )
}

function voronoiNumero(smoke: AbsorcaoMargemFrescaJSON['voronoi_smoke']): string | undefined {
  if (!smoke || smoke.status !== 'ok') return undefined
  const pv = smoke.pool_voronoi
  const d = smoke.delta_pct
  if (pv == null || d == null || Number.isNaN(Number(d))) return undefined
  const dF = Number(d)
  const sentido = dF < 0 ? 'menor' : 'maior'
  return `${_int(pv)} alunos · ${Math.round(Math.abs(dF) * 100)}% ${sentido} vs bairro`
}

function Bloco({
  titulo,
  numero,
  texto,
  carimbo,
  compact = false,
  className,
}: {
  titulo: string
  numero?: string
  texto: string
  carimbo?: string
  compact?: boolean
  className?: string
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card',
        compact ? 'min-w-62 max-w-70 shrink-0 snap-start p-3' : 'p-4',
        className,
      )}
    >
      <h4 className={cn('font-semibold text-foreground', compact ? 'text-[11px]' : 'text-sm')}>
        {titulo}
      </h4>
      {numero && (
        <p className={cn('font-semibold text-primary', compact ? 'mt-1 text-base' : 'mt-1 text-lg')}>
          {numero}
        </p>
      )}
      <p
        className={cn(
          'text-muted-foreground',
          compact ? 'mt-1.5 line-clamp-4 text-[11px] leading-snug' : 'mt-2 text-sm leading-relaxed',
        )}
      >
        {texto}
      </p>
      {carimbo ? (
        <p className="mt-2 text-[11px] font-mono text-muted-foreground/80">{carimbo}</p>
      ) : null}
    </div>
  )
}

export function AbsorcaoMargemFrescaCard({
  block,
  className,
  layout = 'stack',
}: {
  block: AbsorcaoMargemFrescaJSON
  className?: string
  layout?: 'stack' | 'row' | 'sidebar'
}) {
  if (!block?.rotulo) return null

  const rotulo = String(block.rotulo)
  const ui = ROTULO_UI[rotulo] ?? { label: rotulo, variant: 'secondary' as const }
  const car = block.carimbos ?? {}
  const poolP = block.pool_primario ?? block.pool_demografico
  const faixasP = faixasHumanas(block.faixas_primario)
  const faixasS = faixasHumanas(block.faixas_secundario)
  const margem = block.margem_fresca
  const notaV = notaVoronoi(block.voronoi_smoke)
  const row = layout === 'row'
  const sidebar = layout === 'sidebar'
  const tiles = (
    <>
      <Bloco
        compact={row}
        titulo="1. Capacidade da sua unidade"
        numero={`${_int(block.teto_unidade)} alunos`}
        texto={
          'Quantas matrículas esta academia comporta no cenário realista ' +
          '(área do imóvel × densidade típica do modelo). ' +
          'Não é a população do bairro — é o teto operacional da unidade.'
        }
        carimbo={carimboText(car.teto_unidade)}
      />
      <Bloco
        compact={row}
        titulo="2. Capacidade das academias já no bairro"
        numero={`${_int(block.capacidade_parque_estimada)} alunos`}
        texto={
          'Estimativa de quantos alunos o conjunto de academias mapeadas no polígono já comporta, ' +
          'somando cada uma por porte típico da rede. Proxy de oferta instalada — não é contagem real de matrículas.'
        }
        carimbo={carimboText(car.capacidade_parque_estimada)}
      />
      <Bloco
        compact={row}
        titulo="3. Potencial no público escolhido"
        numero={`${_int(poolP)} alunos`}
        texto={
          (faixasP
            ? `Alunos potenciais nas idades ${faixasP}. `
            : 'Alunos potenciais na faixa etária desta análise. ') +
            'Parte dos habitantes tem interesse em fitness; dessa parcela, só uma fração vira aluno de academia. ' +
            `Os ${_int(block.estoque_primario)} habitantes na faixa não são todos alunos — o número acima já aplica esse filtro.`
        }
        carimbo={carimboText(car.pool_demografico)}
      />
      <Bloco
        compact={row}
        titulo="4. Potencial nas outras idades (informa o modelo)"
        numero={`${_int(block.pool_secundario)} alunos`}
        texto={
            'Alunos potenciais fora do público escolhido' +
            (faixasS ? ` (${faixasS})` : '') +
            '. Não decidem sozinhos se há aluno novo ou disputa com o parque, ' +
          'mas mostram se vale um braço de oferta para outra faixa. ' +
          `Habitantes nessas faixas: ${_int(block.estoque_secundario)}.`
        }
      />
      <Bloco
        compact={row}
        className={row ? undefined : 'sm:col-span-2'}
        titulo="5. Conclusão — aluno novo ou disputa com o parque?"
        numero={
          margem != null
            ? `${margem >= 0 ? 'Folga' : 'Déficit'} ${_int(Math.abs(margem))} alunos`
            : undefined
        }
        texto={conclusaoTexto(rotulo)}
        carimbo={carimboText(car.margem_fresca)}
      />
      {notaV && (
        <Bloco
          compact={row}
          className={row ? undefined : 'sm:col-span-2'}
          titulo="6. Leitura espacial (experimental) — área de influência"
          numero={voronoiNumero(block.voronoi_smoke)}
          texto={notaV}
        />
      )}
    </>
  )

  if (row) return tiles
  if (sidebar) {
    return <div className={cn('grid grid-cols-1 gap-3', className)}>{tiles}</div>
  }

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={ui.variant}>{ui.label}</Badge>
        {block.base_espacial === 'poligono_ibge' && (
          <span className="text-[11px] text-muted-foreground">Base: polígono do bairro (IBGE)</span>
        )}
        {block.base_espacial === 'raio_fallback' && (
          <span className="text-[11px] text-muted-foreground">Base: raio ao redor do ponto</span>
        )}
      </div>
      <div className="grid gap-3 sm:grid-cols-2">{tiles}</div>
    </div>
  )
}
