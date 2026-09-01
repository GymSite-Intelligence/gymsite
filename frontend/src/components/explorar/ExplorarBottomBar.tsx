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
        'pointer-events-auto flex flex-col gap-2 rounded-xl border p-2 shadow-lg md:flex-row md:items-center md:gap-2 md:p-2.5',
      )}
    >
      <div className="flex min-w-0 items-stretch gap-1.5">
        <SelectGrouped
          value={tipoNegocio}
          onChange={(v) => onTipo(v as TipoNegocioExplorar)}
          options={EXPLORAR_TIPOS.map((t) => ({ value: t.id, label: t.label }))}
          contentClassName={cn(chrome, 'border shadow-lg')}
          className="explorar-ctrl min-h-11 w-auto min-w-0 flex-1 justify-between px-2.5 md:h-10 md:min-h-0 md:w-40 md:flex-none md:px-3"
          ariaLabel="Tipo de negócio"
        />
        <div className="flex min-w-0 flex-2 items-stretch gap-1">
          {LENTES.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onLente(item.id)}
              className={cn(
                'explorar-ctrl min-h-11 min-w-0 flex-1 justify-center px-1.5 text-xs md:h-10 md:min-h-0 md:flex-none md:px-3 md:text-sm',
                lente === item.id && 'explorar-ctrl-on',
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex min-w-0 items-stretch gap-1.5">
        <button
          type="button"
          onClick={onControles}
          className={cn(
            'explorar-ctrl min-h-11 flex-1 justify-center px-2 md:h-10 md:min-h-0 md:flex-none md:px-3',
            controlesOpen && 'explorar-ctrl-on',
          )}
        >
          Controles
        </button>
        <button
          type="button"
          onClick={onDados}
          className={cn(
            'explorar-ctrl min-h-11 flex-1 justify-center px-2 md:h-10 md:min-h-0 md:flex-none md:px-3',
            dadosOpen && 'explorar-ctrl-on',
          )}
        >
          <span className="md:hidden">{dadosOk ? 'Dados ✓' : 'Dados'}</span>
          <span className="hidden md:inline">{dadosOk ? 'Dados do projeto ✓' : 'Dados do projeto'}</span>
        </button>
        <button
          type="button"
          disabled={!canAnalyze || loading}
          onClick={onAnalisar}
          className="explorar-cta min-h-11 flex-[1.4] md:ml-auto md:h-10 md:min-h-0 md:flex-none"
        >
          {loading ? 'Analisando…' : 'Analisar'}
        </button>
      </div>
    </div>
  )
}
