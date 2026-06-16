/**
 * NovasUnidadesCard — agregado "Novas unidades (90 dias)" em mini-cards.
 *
 * Substitui a tabela detalhada de entrantes CNPJ no relatório de viabilidade:
 * a LISTA individual (com QSA/contato) é material de PROSPECÇÃO e vive na rota
 * própria. Aqui fica só o panorama: total, por segmento, por bairro, com o bairro
 * pesquisado destacado. Abertura = data_inicio_atividade no CNPJ.
 */
import { Building2, MapPin } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { EntrantesCnpj90dJSON } from '@/hooks/useRelatorioDetail'

const SEGMENTO_LABEL: Record<string, string> = {
  academia: 'Academia tradicional',
  studio_pilates: 'Estúdio Pilates',
  studio_funcional: 'Estúdio Funcional',
  studio_bem_estar: 'Bem-estar',
  personal_studio: 'Personal / coaching',
  crossfit_box: 'CrossFit / Box',
  lutas: 'Lutas / MMA',
  aqua_fitness: 'Aquático',
}

function _normBairro(s: string | null | undefined): string {
  return (s ?? '')
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

function MiniCard({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: string | number
  highlight?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-lg border px-3 py-2',
        highlight
          ? 'border-veredito-aprovado/50 bg-veredito-aprovado/5'
          : 'bg-muted/40',
      )}
    >
      <div className={cn('text-lg font-semibold', highlight && 'text-veredito-aprovado')}>
        {value}
      </div>
      <div className="text-[11px] text-muted-foreground leading-tight">{label}</div>
    </div>
  )
}

export function NovasUnidadesCard({
  block,
  bairroAlvo,
}: {
  block: EntrantesCnpj90dJSON
  bairroAlvo?: string | null
}) {
  if (!block || (block.total ?? 0) === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nenhuma nova unidade fitness (abertura CNPJ) nos últimos 90 dias no município.
      </p>
    )
  }

  const segmentos = Object.entries(block.novas_unidades_90d_por_segmento ?? {})
    .filter(([, n]) => (n ?? 0) > 0)
    .sort((a, b) => b[1] - a[1])

  // Por bairro derivado de entrantes[].bairro.
  const porBairro = new Map<string, number>()
  for (const e of block.entrantes ?? []) {
    const b = e.bairro?.trim()
    if (b) porBairro.set(b, (porBairro.get(b) ?? 0) + 1)
  }
  const bairrosOrdenados = [...porBairro.entries()].sort((a, b) => b[1] - a[1])
  const alvoNorm = _normBairro(bairroAlvo)
  const noBairroAlvo = alvoNorm
    ? [...porBairro.entries()].find(([b]) => _normBairro(b) === alvoNorm)?.[1] ?? 0
    : null

  return (
    <div className="space-y-4">
      {/* Topo: total + janela + bairro alvo */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <MiniCard label="novas unidades (90d)" value={block.total ?? 0} />
        <MiniCard label="abertura desde (cutoff)" value={block.cutoff ?? '—'} />
        {noBairroAlvo != null && (
          <MiniCard
            label={`no bairro pesquisado (${bairroAlvo})`}
            value={noBairroAlvo}
            highlight
          />
        )}
      </div>

      {/* Por segmento */}
      {segmentos.length > 0 && (
        <section className="space-y-1.5">
          <h5 className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            <Building2 size={12} /> Por segmento
          </h5>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {segmentos.map(([seg, n]) => (
              <MiniCard key={seg} label={SEGMENTO_LABEL[seg] ?? seg} value={n} />
            ))}
          </div>
        </section>
      )}

      {/* Por bairro */}
      {bairrosOrdenados.length > 0 && (
        <section className="space-y-1.5">
          <h5 className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-mono text-muted-foreground">
            <MapPin size={12} /> Por bairro
          </h5>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {bairrosOrdenados.slice(0, 8).map(([b, n]) => (
              <MiniCard key={b} label={b} value={n} highlight={_normBairro(b) === alvoNorm} />
            ))}
          </div>
        </section>
      )}

      <p className="text-[11px] text-muted-foreground">
        Abertura = data_início_atividade no CNPJ. Segmento por nome/CNAE. A lista nominal
        de cada entrante (com contato/QSA) é material de prospecção. {block.nota ? '' : ''}
      </p>
    </div>
  )
}
