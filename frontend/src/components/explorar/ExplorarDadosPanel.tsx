import { usePublicoFaixas, faixasParaRange } from '@/hooks/usePublicoFaixas'
import { SelectGrouped } from '@/components/ui/select-grouped'
import { Input } from '@/components/ui/input'
import {
  TAMANHOS_POR_MODELO,
  type TamanhoCodigo,
} from '@/data/tamanhos-por-modelo'
import { cn } from '@/lib/utils'
import type { ExplorarBriefing } from './ExplorarBriefingDialog'
import { explorarChrome, useExplorarSite } from './explorar-chrome'
import type { TipoNegocioExplorar } from './explorarIso'


const GENERO: { value: ExplorarBriefing['generoAlvo']; label: string }[] = [
  { value: 'misto', label: 'Misto' },
  { value: 'predominantemente_feminino', label: 'Pred. feminino' },
  { value: 'predominantemente_masculino', label: 'Pred. masculino' },
  { value: 'exclusivamente_feminino', label: 'Só feminino' },
  { value: 'exclusivamente_masculino', label: 'Só masculino' },
]

export function ExplorarDadosPanel({
  lugar,
  tipoNegocio,
  tamanho,
  areaMin,
  areaMax,
  publicoFaixas,
  generoAlvo,
  onTamanho,
  onArea,
  onPublicoFaixas,
  onGenero,
  onClose,
}: {
  lugar: { bairro?: string; cidade?: string; uf?: string }
  tipoNegocio: TipoNegocioExplorar
  tamanho: TamanhoCodigo
  areaMin: number
  areaMax: number
  publicoFaixas: string[]
  generoAlvo: ExplorarBriefing['generoAlvo']
  onTamanho: (cod: TamanhoCodigo, min: number, max: number) => void
  onArea: (min: number, max: number) => void
  onPublicoFaixas: (faixas: string[], publicoAlvo: string) => void
  onGenero: (g: ExplorarBriefing['generoAlvo']) => void
  onClose: () => void
}) {
  const chrome = explorarChrome(useExplorarSite())
  const { data: faixasCat = [] } = usePublicoFaixas()
  const faixasTam = TAMANHOS_POR_MODELO[tipoNegocio] ?? []
  const endereco = [lugar.bairro, lugar.cidade, lugar.uf].filter(Boolean).join(', ')

  function toggleFaixa(faixa: string) {
    const next = publicoFaixas.includes(faixa)
      ? publicoFaixas.filter((f) => f !== faixa)
      : [...publicoFaixas, faixa]
    if (!next.length) return
    const range = faixasParaRange(next, faixasCat)
    onPublicoFaixas(next, range || next[0])
  }

  return (
    <div className={cn(chrome, 'pointer-events-auto rounded-xl border p-3 shadow-lg')}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="explorar-label">Dados do projeto</p>
          <p className="truncate text-sm font-semibold text-foreground">
            {endereco || 'Busque o endereço em cima — UF, município e bairro entram sozinhos.'}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 text-xs font-semibold text-muted-foreground hover:text-foreground"
        >
          Fechar
        </button>
      </div>

      <div className="mb-2">
        <p className="explorar-label">Tamanho</p>
        <div className="grid grid-cols-5 gap-1.5">
          {faixasTam.map((f) => (
            <button
              key={f.codigo}
              type="button"
              onClick={() => onTamanho(f.codigo, f.min, f.max)}
              className={cn(
                'explorar-ctrl h-auto min-h-10 flex-col items-start py-1.5',
                tamanho === f.codigo && 'explorar-ctrl-on',
              )}
            >
              <span>{f.label}</span>
              <span className="mt-0.5 text-[10px] font-medium opacity-70">
                {f.min}–{f.max} m²
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-2 grid grid-cols-2 gap-2">
        <Input
          type="number"
          min={200}
          max={5000}
          step={50}
          value={areaMin}
          onChange={(e) => onArea(Number(e.target.value) || areaMin, areaMax)}
          aria-label="Área mínima"
          className="explorar-ctrl w-full"
        />
        <Input
          type="number"
          min={200}
          max={5000}
          step={50}
          value={areaMax}
          onChange={(e) => onArea(areaMin, Number(e.target.value) || areaMax)}
          aria-label="Área máxima"
          className="explorar-ctrl w-full"
        />
      </div>

      <div className="mb-2">
        <p className="explorar-label">Público</p>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
          {faixasCat.map((f) => {
            const on = publicoFaixas.includes(f.faixa)
            return (
              <button
                key={f.faixa}
                type="button"
                onClick={() => toggleFaixa(f.faixa)}
                className={cn(
                  'explorar-ctrl h-auto min-h-10 flex-col items-start py-1.5',
                  on && 'explorar-ctrl-on',
                )}
              >
                <span>{f.nome}</span>
                <span className="mt-0.5 font-mono text-[10px] font-medium opacity-70">
                  {f.faixa}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      <div>
        <p className="explorar-label">Gênero</p>
        <SelectGrouped
          value={generoAlvo}
          onChange={(v) => onGenero(v as ExplorarBriefing['generoAlvo'])}
          options={GENERO}
          contentClassName={cn(chrome, 'border shadow-lg')}
          className="explorar-ctrl w-full justify-between"
        />
      </div>
    </div>
  )
}
