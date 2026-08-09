import { SelectGrouped } from '@/components/ui/select-grouped'
import { cn } from '@/lib/utils'
import { explorarChrome, useExplorarSite } from './explorar-chrome'
import { EXPLORAR_TIPOS, type Lente, type TipoNegocioExplorar } from './explorarIso'


const LENTES: readonly { id: Lente; label: string }[] = [
  { id: '500m', label: '500 m' },
  { id: '1km', label: '1 km' },
  { id: 'bairro', label: 'Bairro' },
]

export function ExplorarBottomBar({
  tipoNegocio,
  lente,
  canAnalyze,
  loading,
  dadosOpen,
  dadosOk,
  controlesOpen,
  onTipo,
  onLente,
  onControles,
  onDados,
  onAnalisar,
}: {
  tipoNegocio: TipoNegocioExplorar
  lente: Lente
  canAnalyze: boolean
  loading: boolean
  dadosOpen: boolean
  dadosOk: boolean
  controlesOpen: boolean
  onTipo: (t: TipoNegocioExplorar) => void
  onLente: (l: Lente) => void
  onControles: () => void
  onDados: () => void
  onAnalisar: () => void
}) {
  const chrome = explorarChrome(useExplorarSite())
  return (
    <div
      className={cn(
        chrome,
        'pointer-events-auto flex items-center gap-2 rounded-xl border p-2.5 shadow-lg',
      )}
    >
      <SelectGrouped
        value={tipoNegocio}
        onChange={(v) => onTipo(v as TipoNegocioExplorar)}
        options={EXPLORAR_TIPOS.map((t) => ({ value: t.id, label: t.label }))}
        contentClassName={cn(chrome, 'border shadow-lg')}
        className="explorar-ctrl w-40 shrink-0 justify-between px-3"
        ariaLabel="Tipo de negócio"
      />
      <div className="flex items-center gap-1.5">
        {LENTES.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onLente(item.id)}
            className={cn('explorar-ctrl justify-center', lente === item.id && 'explorar-ctrl-on')}
          >
            {item.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        onClick={onControles}
        className={cn('explorar-ctrl justify-center', controlesOpen && 'explorar-ctrl-on')}
      >
        Controles
      </button>
      <button
        type="button"
        onClick={onDados}
        className={cn('explorar-ctrl justify-center', dadosOpen && 'explorar-ctrl-on')}
      >
        {dadosOk ? 'Dados do projeto ✓' : 'Dados do projeto'}
      </button>
      <button
        type="button"
        disabled={!canAnalyze || loading}
        onClick={onAnalisar}
        className="explorar-cta ml-auto"
      >
        {loading ? 'Analisando…' : 'Analisar'}
      </button>
    </div>
  )
}
