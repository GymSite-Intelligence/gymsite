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
      'O potencial do público do formulário cobre a capacidade da sua unidade sem depender só de tirar aluno do concorrente.'
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
      'No público do formulário, a oferta instalada já supera o potencial estimado de alunos. ' +
      'Crescer nesta unidade significa, na prática, atrair quem hoje treina em outra academia do bairro — ' +
      'custo de aquisição mais alto e guerra de proposta de valor.'
    )
  }
  return 'Cruzar potencial do público-alvo com a capacidade já instalada antes de decidir o modelo.'
}

function Bloco({
  titulo,
  numero,
  texto,
  carimbo,
}: {
  titulo: string
  numero?: string
  texto: string
  carimbo?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h4 className="text-sm font-semibold text-foreground">{titulo}</h4>
      {numero && <p className="mt-1 text-lg font-semibold text-primary">{numero}</p>}
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{texto}</p>
      {carimbo ? (
        <p className="mt-2 text-[11px] font-mono text-muted-foreground/80">{carimbo}</p>
      ) : null}
    </div>
  )
}

export function AbsorcaoMargemFrescaCard({
  block,
  className,
}: {
  block: AbsorcaoMargemFrescaJSON
  className?: string
}) {
  if (!block?.rotulo) return null

  const rotulo = String(block.rotulo)
  const ui = ROTULO_UI[rotulo] ?? { label: rotulo, variant: 'secondary' as const }
  const car = block.carimbos ?? {}
  const poolP = block.pool_primario ?? block.pool_demografico
  const faixasP = faixasHumanas(block.faixas_primario)
  const faixasS = faixasHumanas(block.faixas_secundario)
  const margem = block.margem_fresca

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

      <div className="grid gap-3 sm:grid-cols-2">
        <Bloco
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
          titulo="2. Capacidade das academias já no bairro"
          numero={`${_int(block.capacidade_parque_estimada)} alunos`}
          texto={
            'Estimativa de quantos alunos o conjunto de academias mapeadas no polígono já comporta, ' +
            'somando cada uma por porte típico da rede. Proxy de oferta instalada — não é contagem real de matrículas.'
          }
          carimbo={carimboText(car.capacidade_parque_estimada)}
        />
        <Bloco
          titulo="3. Potencial no público do formulário"
          numero={`${_int(poolP)} alunos`}
          texto={
            'Alunos potenciais entre as idades que você escolheu no formulário' +
            (faixasP ? ` (${faixasP})` : '') +
            '. Parte dos habitantes tem interesse em fitness; dessa parcela, só uma fração vira aluno de academia. ' +
            `Os ${_int(block.estoque_primario)} habitantes na faixa não são todos alunos — o número acima já aplica esse filtro.`
          }
          carimbo={carimboText(car.pool_demografico)}
        />
        <Bloco
          titulo="4. Potencial nas outras idades (informa o modelo)"
          numero={`${_int(block.pool_secundario)} alunos`}
          texto={
            'Alunos potenciais fora do gancho do formulário' +
            (faixasS ? ` (${faixasS})` : ' (ex. Jovem · Silver)') +
            '. Não decidem sozinhos se há aluno novo ou disputa com o parque, ' +
            'mas mostram se vale um braço de oferta para outra faixa. ' +
            `Habitantes nessas faixas: ${_int(block.estoque_secundario)}.`
          }
        />
      </div>

      <Bloco
        titulo="5. Conclusão — aluno novo ou disputa com o parque?"
        numero={
          margem != null
            ? `${margem >= 0 ? 'Folga' : 'Déficit'} ${_int(Math.abs(margem))} alunos`
            : undefined
        }
        texto={conclusaoTexto(rotulo)}
        carimbo={carimboText(car.margem_fresca)}
      />
    </div>
  )
}
