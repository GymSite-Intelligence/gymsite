import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Combobox, type ComboboxOption } from '@/components/ui/combobox'
import { SelectGrouped } from '@/components/ui/select-grouped'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useMunicipioAutocomplete, type MunicipioIBGE } from '@/hooks/useMunicipioAutocomplete'
import { useBairrosDoMunicipio } from '@/hooks/useBairrosDoMunicipio'
import { useBairroQuery } from '@/hooks/useBairroQuery'
import { usePublicoFaixas, faixasParaRange } from '@/hooks/usePublicoFaixas'
import { useDebounce } from '@/hooks/useDebounce'
import { UFS_BRASIL, type UF } from '@/data/ufs-brasil'
import {
  TAMANHOS_POR_MODELO,
  getTamanhoAncora,
  type ModeloNegocio,
  type TamanhoCodigo,
} from '@/data/tamanhos-por-modelo'
import { cn } from '@/lib/utils'
import { EXPLORAR_CHROME } from './explorar-chrome'
import type { TipoNegocioExplorar } from './explorarIso'

const schema = z
  .object({
    uf: z.string().length(2),
    municipio: z.string().min(2),
    bairro: z.string().min(2),
    areaMin: z.number().int().min(200).max(5000),
    areaMax: z.number().int().min(200).max(5000),
    publicoAlvo: z.string().regex(/^\d{1,3}(-\d{1,3}|\+)$/),
    publicoFaixas: z.array(z.string()).min(1),
    generoAlvo: z.enum([
      'misto',
      'predominantemente_feminino',
      'predominantemente_masculino',
      'exclusivamente_feminino',
      'exclusivamente_masculino',
    ]),
    tipoNegocio: z.enum([
      'academia',
      'crossfit_box',
      'studio_pilates',
      'studio_funcional',
      'outro',
    ]),
    tamanho: z.enum(['pp', 'p', 'm', 'g', 'gg']),
  })
  .refine((d) => d.areaMax >= d.areaMin, { path: ['areaMax'] })

export type ExplorarBriefing = z.infer<typeof schema>

const UFS_POR_REGIAO = UFS_BRASIL.reduce<Record<UF['regiao'], UF[]>>((acc, uf) => {
  if (!acc[uf.regiao]) acc[uf.regiao] = []
  acc[uf.regiao].push(uf)
  return acc
}, {} as Record<UF['regiao'], UF[]>)

export function ExplorarBriefingDialog({
  open,
  onOpenChange,
  onConfirm,
  confirmLabel = 'Analisar no mapa',
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (data: ExplorarBriefing) => void | Promise<void>
  confirmLabel?: string
}) {
  const [ufSel, setUfSel] = useState<UF | null>(null)
  const [munQuery, setMunQuery] = useState('')
  const [munSel, setMunSel] = useState<MunicipioIBGE | null>(null)
  const [baiQuery, setBaiQuery] = useState('')
  const debMun = useDebounce(munQuery, 200)
  const debBai = useDebounce(baiQuery, 300)
  const { sugestoes: munSug, isLoading: loadMun, total: totalMun } = useMunicipioAutocomplete(
    debMun,
    ufSel?.sigla ?? '',
  )
  const { data: bairrosMun = [], isFetching: loadBai } = useBairrosDoMunicipio(
    munSel?.nome ?? '',
    munSel?.uf ?? '',
  )
  const { data: bairrosLive = [] } = useBairroQuery({
    input: debBai,
    municipio: munSel?.nome ?? '',
    uf: munSel?.uf ?? '',
  })
  const { data: faixasCat = [] } = usePublicoFaixas()
  const { register, handleSubmit, setValue, watch, formState } = useForm<ExplorarBriefing>({
    resolver: zodResolver(schema),
    defaultValues: {
      uf: '',
      municipio: '',
      bairro: '',
      areaMin: 800,
      areaMax: 1500,
      publicoAlvo: '25-39',
      publicoFaixas: ['25-39'],
      generoAlvo: 'misto',
      tipoNegocio: 'academia',
      tamanho: 'm',
    },
  })
  const tipo = watch('tipoNegocio') as ModeloNegocio
  const faixasSel = watch('publicoFaixas')
  const tamanho = watch('tamanho')
  const faixasTam = TAMANHOS_POR_MODELO[tipo] ?? []

  useEffect(() => {
    const range = faixasParaRange(faixasSel || [], faixasCat)
    if (range) setValue('publicoAlvo', range, { shouldValidate: true })
  }, [faixasSel, faixasCat, setValue])

  const bairroOpts = useMemo(() => {
    const n = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
    const q = n(baiQuery)
    const filtrados = q ? bairrosMun.filter((b) => n(b.bairro).includes(q)) : bairrosMun
    const visto = new Set<string>()
    const out: typeof bairrosMun = []
    for (const b of [...bairrosLive, ...filtrados]) {
      const key = b.placeId || b.textoCompleto || b.bairro
      if (!visto.has(key)) {
        visto.add(key)
        out.push(b)
      }
    }
    return out.map((b) => ({
      label: b.bairro,
      description: b.contexto,
      value: b.placeId || b.textoCompleto,
    }))
  }, [bairrosMun, bairrosLive, baiQuery])

  function selUf(sigla: string) {
    const uf = UFS_BRASIL.find((u) => u.sigla === sigla) ?? null
    setUfSel(uf)
    setValue('uf', uf?.sigla ?? '', { shouldValidate: !!uf })
    setMunSel(null)
    setMunQuery('')
    setValue('municipio', '')
    setBaiQuery('')
    setValue('bairro', '')
  }

  function selTipo(t: ModeloNegocio) {
    setValue('tipoNegocio', t, { shouldDirty: true })
    const ancora = getTamanhoAncora(t)
    setValue('tamanho', ancora.codigo)
    setValue('areaMin', ancora.min)
    setValue('areaMax', ancora.max)
  }

  function selTam(cod: TamanhoCodigo) {
    setValue('tamanho', cod, { shouldDirty: true })
    const f = faixasTam.find((x) => x.codigo === cod)
    if (f) {
      setValue('areaMin', f.min)
      setValue('areaMax', f.max)
    }
  }

  function toggleFaixa(faixa: string) {
    const atuais = faixasSel || []
    const next = atuais.includes(faixa) ? atuais.filter((f) => f !== faixa) : [...atuais, faixa]
    if (!next.length) return
    setValue('publicoFaixas', next, { shouldDirty: true, shouldValidate: true })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          EXPLORAR_CHROME,
          'max-h-[88vh] max-w-xl overflow-y-auto border-border bg-card text-foreground',
        )}
      >
        <DialogHeader>
          <DialogTitle>Novo relatório</DialogTitle>
          <DialogDescription>
            Mesmos dados do relatório completo. Sem isso a análise no mapa não inventa público nem área.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={handleSubmit(async (data) => {
            await onConfirm(data)
          })}
        >
          <SelectGrouped
            value={ufSel?.sigla}
            onChange={selUf}
            placeholder="Estado"
            groups={(['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'] as const).map((r) => ({
              label: r,
              options: (UFS_POR_REGIAO[r] ?? []).map((u) => ({
                value: u.sigla,
                label: `${u.sigla} — ${u.nome}`,
              })),
            }))}
          />
          <Combobox<MunicipioIBGE>
            inputValue={munQuery}
            onInputChange={(v) => {
              setMunQuery(v)
              if (munSel && v !== munSel.nome) {
                setMunSel(null)
                setValue('municipio', '')
                setBaiQuery('')
                setValue('bairro', '')
              }
            }}
            options={munSug.map((m) => ({
              label: m.nome,
              description: m.uf_nome || m.uf,
              value: String(m.id),
              payload: m,
            }))}
            onSelect={(opt) => {
              if (!opt.payload) return
              setMunSel(opt.payload)
              setMunQuery(opt.payload.nome)
              setValue('municipio', opt.payload.nome, { shouldValidate: true })
              setBaiQuery('')
              setValue('bairro', '')
            }}
            isLoading={loadMun}
            placeholder={ufSel ? `${totalMun} municípios · digite` : 'Aguardando estado'}
            disabled={!ufSel}
            minChars={0}
          />
          <Combobox
            inputValue={baiQuery}
            onInputChange={(v) => {
              setBaiQuery(v)
              if (!v) setValue('bairro', '')
            }}
            options={bairroOpts}
            onSelect={(opt: ComboboxOption) => {
              setBaiQuery(opt.label)
              setValue('bairro', opt.label, { shouldValidate: true })
            }}
            isLoading={loadBai}
            placeholder={munSel ? 'Bairro' : 'Aguardando município'}
            disabled={!munSel}
            minChars={0}
          />
          <SelectGrouped
            value={tipo}
            onChange={(v) => selTipo(v as ModeloNegocio)}
            options={[
              { value: 'academia', label: 'Academia tradicional' },
              { value: 'crossfit_box', label: 'CrossFit / Box' },
              { value: 'studio_pilates', label: 'Estúdio Pilates' },
              { value: 'studio_funcional', label: 'Studio Funcional' },
              { value: 'outro', label: 'Outro' },
            ]}
          />
          <div className="grid grid-cols-5 gap-1.5">
            {faixasTam.map((f) => (
              <button
                key={f.codigo}
                type="button"
                onClick={() => selTam(f.codigo)}
                className={cn(
                  'rounded-md border px-1.5 py-1.5 text-left text-[11px]',
                  tamanho === f.codigo ? 'border-primary bg-primary/10' : 'border-border',
                )}
              >
                <span className="font-semibold">{f.label}</span>
                <span className="mt-0.5 block text-[10px] text-muted-foreground">
                  {f.min}–{f.max} m²
                </span>
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input type="number" min={200} max={5000} step={50} {...register('areaMin', { valueAsNumber: true })} />
            <Input type="number" min={200} max={5000} step={50} {...register('areaMax', { valueAsNumber: true })} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            {faixasCat.map((f) => {
              const on = (faixasSel || []).includes(f.faixa)
              return (
                <button
                  key={f.faixa}
                  type="button"
                  onClick={() => toggleFaixa(f.faixa)}
                  className={cn(
                    'rounded-md border px-2 py-2 text-left text-xs',
                    on ? 'border-primary bg-primary/10' : 'border-border',
                  )}
                >
                  <span className="font-semibold">{f.nome}</span>
                  <span className="mt-0.5 block font-mono text-[10px] text-muted-foreground">
                    {f.faixa}
                  </span>
                </button>
              )
            })}
          </div>
          <SelectGrouped
            value={watch('generoAlvo')}
            onChange={(v) => setValue('generoAlvo', v as ExplorarBriefing['generoAlvo'], { shouldDirty: true })}
            options={[
              { value: 'misto', label: 'Misto' },
              { value: 'predominantemente_feminino', label: 'Predominantemente feminino' },
              { value: 'predominantemente_masculino', label: 'Predominantemente masculino' },
              { value: 'exclusivamente_feminino', label: 'Exclusivamente feminino' },
              { value: 'exclusivamente_masculino', label: 'Exclusivamente masculino' },
            ]}
          />
          <DialogFooter>
            <Button
              type="submit"
              disabled={formState.isSubmitting || !watch('bairro') || !watch('municipio')}
            >
              {confirmLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function briefingAreaM2(b: ExplorarBriefing): number {
  return Math.round((Number(b.areaMin) + Number(b.areaMax)) / 2)
}

export function idadesDoBriefing(publicoAlvo: string): {
  idade_min?: number
  idade_max?: number
} {
  const range = publicoAlvo.match(/^(\d+)\s*-\s*(\d+)$/)
  if (range) return { idade_min: Number(range[1]), idade_max: Number(range[2]) }
  const aberto = publicoAlvo.match(/^(\d+)\s*\+$/)
  if (aberto) return { idade_min: Number(aberto[1]), idade_max: 120 }
  return {}
}

export function isExplorarTipo(t: string): t is TipoNegocioExplorar {
  return t === 'academia' || t === 'studio_funcional' || t === 'crossfit_box' || t === 'studio_pilates'
}
