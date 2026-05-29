/**
 * Botões Run now por canal de dados (formulário novo relatório).
 */
import { useCallback, useState } from 'react'
import { Loader2, Play, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  runCanalProbe,
  type CanalId,
  type CanalProbeResult,
} from '@/lib/canais-api'

type CanalDef = {
  id: CanalId
  label: string
  hint: string
}

const CANAIS: CanalDef[] = [
  {
    id: 'kimi',
    label: 'Kimi Research',
    hint: 'Briefing A0 via OpenClaw (5 pesquisas)',
  },
  {
    id: 'places',
    label: 'Google Places',
    hint: 'Geocode + academias no raio',
  },
  {
    id: 'osm',
    label: 'OSM / Overpass',
    hint: 'Competição via mapa aberto',
  },
  {
    id: 'cnpj',
    label: 'CNPJ RFB',
    hint: 'Parque fitness no bairro',
  },
]

export interface CanalRunPanelProps {
  cidade: string
  bairro: string
  uf?: string
  tipoNegocio?: string
  publicoAlvo?: string
  disabled?: boolean
}

export function CanalRunPanel({
  cidade,
  bairro,
  uf,
  tipoNegocio = 'academia',
  publicoAlvo = 'premium',
  disabled = false,
}: CanalRunPanelProps) {
  const [loading, setLoading] = useState<CanalId | null>(null)
  const [results, setResults] = useState<Partial<Record<CanalId, CanalProbeResult>>>({})

  const run = useCallback(
    async (canal: CanalId) => {
      setLoading(canal)
      try {
        const out = await runCanalProbe(canal, {
          cidade,
          bairro,
          uf,
          tipo_negocio: tipoNegocio,
          publico_alvo: publicoAlvo,
        })
        setResults((prev) => ({ ...prev, [canal]: out }))
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        setResults((prev) => ({
          ...prev,
          [canal]: { canal, ok: false, erro: msg },
        }))
      } finally {
        setLoading(null)
      }
    },
    [cidade, bairro, uf, tipoNegocio, publicoAlvo],
  )

  const podeRodar = !disabled && cidade.length >= 2 && bairro.length >= 2

  return (
    <section className="rounded-lg border border-dashed border-border bg-muted/20 p-4 space-y-3">
      <div>
        <h2 className="text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
          Testar canais (Run now)
        </h2>
        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
          Dispara só um canal antes do pipeline completo. Útil para validar Maps,
          OSM, CNPJ ou pré-aquecer o briefing Kimi no cache do A0.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {CANAIS.map((c) => {
          const res = results[c.id]
          const isLoading = loading === c.id
          return (
            <Button
              key={c.id}
              type="button"
              variant="outline"
              size="sm"
              disabled={!podeRodar || loading !== null}
              className="gap-1.5 h-8 text-xs"
              title={c.hint}
              onClick={() => void run(c.id)}
            >
              {isLoading ? (
                <Loader2 size={12} className="animate-spin" />
              ) : res?.ok ? (
                <CheckCircle2 size={12} className="text-veredito-aprovado" />
              ) : res && !res.ok ? (
                <XCircle size={12} className="text-veredito-reprovado" />
              ) : (
                <Play size={12} />
              )}
              {c.label}
            </Button>
          )
        })}
      </div>

      {Object.entries(results).map(([id, res]) => {
        if (!res) return null
        return (
          <CanalResultCard key={id} canalId={id as CanalId} result={res} />
        )
      })}
    </section>
  )
}

function CanalResultCard({
  canalId,
  result,
}: {
  canalId: CanalId
  result: CanalProbeResult
}) {
  const titulo = CANAIS.find((c) => c.id === canalId)?.label ?? canalId

  return (
    <div
      className={cn(
        'rounded-md border p-3 text-xs space-y-1.5',
        result.ok
          ? 'border-veredito-aprovado/30 bg-veredito-aprovado/5'
          : 'border-status-critical/30 bg-status-critical/5',
      )}
    >
      <p className="font-medium text-foreground">
        {titulo}{' '}
        <span className="text-muted-foreground font-normal">
          — {result.ok ? 'OK' : 'falhou'}
        </span>
      </p>
      {result.erro && (
        <p className="text-muted-foreground font-mono break-all">{result.erro}</p>
      )}
      {typeof result.total === 'number' && (
        <p className="text-muted-foreground">
          {result.total} registro(s)
          {result.fonte_busca_competidores
            ? ` · fonte ${result.fonte_busca_competidores}`
            : ''}
          {result.tier ? ` · tier ${result.tier}` : ''}
        </p>
      )}
      {canalId === 'kimi' && result.preview_markdown && (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[10px] text-muted-foreground bg-background/60 p-2 rounded border border-border">
          {result.preview_markdown}
        </pre>
      )}
      {canalId !== 'kimi' && Array.isArray(result.amostra) && result.amostra.length > 0 && (
        <ul className="list-disc pl-4 text-muted-foreground space-y-0.5">
          {(
            result.amostra as {
              nome?: string
              nome_exibicao?: string
              razao_social?: string
              bairro?: string
              nome_fantasia_inferido_de?: string
            }[]
          )
            .slice(0, 5)
            .map((item, i) => {
              const label =
                item.nome_exibicao?.trim() ||
                item.nome?.trim() ||
                item.razao_social?.trim() ||
                '—'
              const bairro = item.bairro?.trim()
              return (
                <li key={i}>
                  {label}
                  {item.nome_fantasia_inferido_de === 'razao_social' && (
                    <span className="text-muted-foreground"> (razão social)</span>
                  )}
                  {bairro ? (
                    <span className="text-muted-foreground"> · {bairro}</span>
                  ) : null}
                </li>
              )
            })}
        </ul>
      )}
    </div>
  )
}
