import { Car, PersonStanding, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { explorarChrome, useExplorarSite } from './explorar-chrome'
import type { Camada, MapStyle, ModoDesloc } from './explorarIso'

export function ExplorarControles({
  mapStyle,
  camada,
  modo,
  nMaps,
  onStyle,
  onCamada,
  onModo,
  onClose,
}: {
  mapStyle: MapStyle
  camada: Camada
  modo: ModoDesloc
  nMaps: number
  onStyle: (s: MapStyle) => void
  onCamada: (c: Camada) => void
  onModo: (m: ModoDesloc) => void
  onClose: () => void
}) {
  const chrome = explorarChrome(useExplorarSite())
  return (
    <aside className={cn(chrome, 'pointer-events-auto w-73 rounded-xl border p-3.5 shadow-lg')}>
      <div className="mb-3.5 flex items-center justify-between">
        <h2 className="text-xs font-semibold text-foreground">Controles</h2>
        <button
          type="button"
          aria-label="Fechar controles"
          onClick={onClose}
          className="rounded-md p-1 text-muted-foreground hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <X className="size-4" />
        </button>
      </div>

      <p className="mb-2 text-[10px] font-medium tracking-[0.5px] text-muted-foreground">
        ESTILO DO MAPA
      </p>
      <div className="mb-4 grid grid-cols-3 overflow-hidden rounded-lg border border-border">
        {(
          [
            ['claro', 'Claro'],
            ['escuro', 'Escuro'],
            ['satelite', 'Satélite'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => onStyle(id)}
            className={cn(
              'border-r border-border px-1 py-1.75 text-xs font-normal last:border-r-0',
              mapStyle === id
                ? 'bg-primary text-primary-foreground'
                : 'bg-secondary text-foreground hover:bg-muted',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <p className="mb-2 text-[10px] font-medium tracking-[0.5px] text-muted-foreground">
        CAMADAS
      </p>
      <CamadaRow
        label="Mapa de calor"
        selected={camada === 'calor'}
        onClick={() => onCamada(camada === 'calor' ? 'off' : 'calor')}
      />
      <CamadaRow
        label="Área de influência"
        selected={camada === 'influencia'}
        onClick={() => onCamada(camada === 'influencia' ? 'off' : 'influencia')}
      />
      {camada === 'influencia' && (
        <div className="mb-2.5 ml-6 mt-1 grid grid-cols-2 gap-2">
          <button
            type="button"
            title="A pé"
            aria-label="A pé"
            onClick={() => onModo('pe')}
            className={cn(
              'flex items-center justify-center rounded-lg border px-3 py-3',
              modo === 'pe'
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-secondary text-foreground hover:bg-muted',
            )}
          >
            <PersonStanding className="size-5" />
          </button>
          <button
            type="button"
            title="Carro"
            aria-label="Carro"
            onClick={() => onModo('carro')}
            className={cn(
              'flex items-center justify-center rounded-lg border px-3 py-3',
              modo === 'carro'
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-secondary text-foreground hover:bg-muted',
            )}
          >
            <Car className="size-5" />
          </button>
        </div>
      )}

      <div className="mt-3 border-t border-border pt-3">
        <p className="mb-2 text-[10px] font-medium tracking-[0.5px] text-muted-foreground">
          LEGENDA
        </p>
        <div className="flex items-center gap-2.5 text-xs font-normal text-foreground">
          <i className="inline-block size-2.5 rounded-full bg-destructive" />
          Google Maps ({nMaps})
        </div>
      </div>
    </aside>
  )
}

function CamadaRow({
  label,
  selected,
  onClick,
}: {
  label: string
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        'mb-1 flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left text-xs font-normal',
        selected ? 'bg-primary/15 text-foreground' : 'text-foreground hover:bg-secondary',
      )}
    >
      <span
        className={cn(
          'size-4 shrink-0 rounded-full border-2',
          selected ? 'border-primary bg-primary ring-2 ring-card ring-inset' : 'border-border',
        )}
      />
      {label}
    </button>
  )
}
