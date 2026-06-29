/**
 * ProspeccaoPage — CRM de oportunidades CNPJ × CNO (v2, independente do relatório).
 *
 * Fluxo:
 *  1. Localização em cascata Estado → Município → Bairro (mesmos componentes do
 *     formulário de relatório). UF + Município alimentam o motor (municipal);
 *     Bairro estreita a lista exibida.
 *  2. "Executar prospecção" roda o motor (CNPJ-only quando não há CNO) e popula
 *     a tabela de CNPJs.
 *  3. Checkbox por linha + seleção em massa → "Qualificar + Enviar ao Navi"
 *     (status=qualificado + webhook pro destino interno Navi/Claw).
 */
import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import {
  Play,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Download,
  Send,
} from 'lucide-react'
import {
  useOportunidades,
  useExecutarProspeccao,
  usePatchStatusOportunidade,
  useReenviarWebhook,
} from '@/hooks/useProspeccao'
import { StatusBadge } from '@/components/prospeccao/StatusBadge'
import { PrioridadeBadge } from '@/components/prospeccao/PrioridadeBadge'
import { OportunidadeDrawer } from '@/components/prospeccao/OportunidadeDrawer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SelectGrouped } from '@/components/ui/select-grouped'
import { Combobox, type ComboboxOption } from '@/components/ui/combobox'
import { UFS_BRASIL, type UF } from '@/data/ufs-brasil'
import {
  useMunicipioAutocomplete,
  type MunicipioIBGE,
} from '@/hooks/useMunicipioAutocomplete'
import { useBairrosDoMunicipio } from '@/hooks/useBairrosDoMunicipio'
import { useBairroQuery } from '@/hooks/useBairroQuery'
import { useDebounce } from '@/hooks/useDebounce'

const UFS_POR_REGIAO = UFS_BRASIL.reduce<Record<UF['regiao'], UF[]>>(
  (acc, uf) => {
    if (!acc[uf.regiao]) acc[uf.regiao] = []
    acc[uf.regiao].push(uf)
    return acc
  },
  {} as Record<UF['regiao'], UF[]>,
)

function _norm(s: string | null | undefined): string {
  return (s ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

export function ProspeccaoPage() {
  // ── Localização em cascata (igual ao formulário de relatório) ──
  const [ufSelecionada, setUfSelecionada] = useState<UF | null>(null)
  const [municipioQuery, setMunicipioQuery] = useState('')
  const [municipioSelecionado, setMunicipioSelecionado] =
    useState<MunicipioIBGE | null>(null)
  const [bairroQuery, setBairroQuery] = useState('')

  const debouncedMunicipio = useDebounce(municipioQuery, 200)
  const {
    sugestoes: municipiosSugeridos,
    isLoading: loadingMun,
    total: totalMun,
  } = useMunicipioAutocomplete(debouncedMunicipio, ufSelecionada?.sigla ?? '')

  const { data: bairrosDoMunicipio = [], isFetching: loadingBai } =
    useBairrosDoMunicipio(
      municipioSelecionado?.nome ?? '',
      municipioSelecionado?.uf ?? '',
    )
  const debouncedBairro = useDebounce(bairroQuery, 300)
  const { data: bairrosLive = [] } = useBairroQuery({
    input: debouncedBairro,
    municipio: municipioSelecionado?.nome ?? '',
    uf: municipioSelecionado?.uf ?? '',
  })

  const bairrosSugeridos = useMemo(() => {
    const q = _norm(bairroQuery)
    const filtrados = q
      ? bairrosDoMunicipio.filter((b) => _norm(b.bairro).includes(q))
      : bairrosDoMunicipio
    const visto = new Set<string>()
    const out: typeof bairrosDoMunicipio = []
    for (const b of [...bairrosLive, ...filtrados]) {
      const key = b.placeId || b.textoCompleto || b.bairro
      if (!visto.has(key)) {
        visto.add(key)
        out.push(b)
      }
    }
    return out
  }, [bairrosDoMunicipio, bairrosLive, bairroQuery])

  const cidade = municipioSelecionado?.nome ?? ''
  const uf = ufSelecionada?.sigla ?? ''

  // ── Filtros de listagem ──
  const [status, setStatus] = useState('')
  const [prioridade, setPrioridade] = useState('')
  const [scoreMin, setScoreMin] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 20
  const [sortKey, setSortKey] = useState<'score_match' | 'created_at' | 'prioridade' | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  // ── Seleção em massa + drawer ──
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [enviando, setEnviando] = useState(false)
  const [drawerId, setDrawerId] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const { data, isLoading } = useOportunidades({
    cidade: cidade || undefined,
    uf: uf || undefined,
    status: status || undefined,
    prioridade: prioridade || undefined,
    score_min: scoreMin ? Number(scoreMin) : undefined,
    limit: pageSize,
    offset: page * pageSize,
  })

  const executar = useExecutarProspeccao()
  const patchStatus = usePatchStatusOportunidade()
  const reenviarWebhook = useReenviarWebhook()

  // Bairro estreita a lista exibida (motor é municipal). Lê do endereco_cnpj jsonb.
  const filtradoPorBairro = useMemo(() => {
    if (!data) return data
    const alvo = _norm(bairroQuery)
    if (!alvo) return data
    return data.filter((o) => {
      const end = (o as { endereco_cnpj?: { bairro?: string } }).endereco_cnpj
      return _norm(end?.bairro).includes(alvo)
    })
  }, [data, bairroQuery])

  const sortedData = useMemo(() => {
    if (!filtradoPorBairro || !sortKey) return filtradoPorBairro
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtradoPorBairro].sort((a, b) => {
      if (sortKey === 'score_match') {
        return ((a.score_match ?? 0) - (b.score_match ?? 0)) * dir
      }
      if (sortKey === 'created_at') {
        return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir
      }
      if (sortKey === 'prioridade') {
        const ordem = { critica: 4, alta: 3, media: 2, baixa: 1 }
        return ((ordem[a.prioridade] ?? 0) - (ordem[b.prioridade] ?? 0)) * dir
      }
      return 0
    })
  }, [filtradoPorBairro, sortKey, sortDir])

  function toggleSort(key: 'score_match' | 'created_at' | 'prioridade') {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('pt-BR')
  }

  function scoreColor(score: number | null) {
    if (score == null) return 'text-muted-foreground'
    if (score >= 0.7) return 'text-green-600'
    if (score >= 0.4) return 'text-amber-600'
    return 'text-red-600'
  }

  // ── Cascata: handlers de reset ──
  function selecionarUf(sigla: string) {
    setUfSelecionada(UFS_BRASIL.find((u) => u.sigla === sigla) ?? null)
    setMunicipioSelecionado(null)
    setMunicipioQuery('')
    setBairroQuery('')
    setPage(0)
  }

  function selecionarMunicipio(opt: ComboboxOption<MunicipioIBGE>) {
    if (!opt.payload) return
    setMunicipioSelecionado(opt.payload)
    setMunicipioQuery(opt.payload.nome)
    setBairroQuery('')
    setPage(0)
  }

  const municipioOptions: ComboboxOption<MunicipioIBGE>[] =
    municipiosSugeridos.map((m) => ({
      label: m.nome,
      description: m.uf_nome || m.uf,
      value: String(m.id),
      payload: m,
    }))

  const bairroOptions: ComboboxOption[] = bairrosSugeridos.map((b) => ({
    label: b.bairro,
    description: b.contexto,
    value: b.placeId || b.textoCompleto,
  }))

  // ── Seleção em massa ──
  const idsVisiveis = useMemo(() => (sortedData ?? []).map((o) => o.id), [sortedData])
  const todosSelecionados =
    idsVisiveis.length > 0 && idsVisiveis.every((id) => selecionados.has(id))

  function toggleSelecionado(id: string) {
    setSelecionados((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleTodos() {
    setSelecionados((prev) => {
      if (idsVisiveis.every((id) => prev.has(id))) {
        const next = new Set(prev)
        idsVisiveis.forEach((id) => next.delete(id))
        return next
      }
      return new Set([...prev, ...idsVisiveis])
    })
  }

  async function qualificarEEnviar() {
    const ids = [...selecionados]
    if (!ids.length) return
    setEnviando(true)
    let ok = 0
    let falhas = 0
    for (const id of ids) {
      try {
        await patchStatus.mutateAsync({ id, status: 'qualificado' })
        await reenviarWebhook.mutateAsync(id)
        ok++
      } catch {
        falhas++
      }
    }
    setEnviando(false)
    setSelecionados(new Set())
    if (ok) toast.success(`${ok} oportunidade(s) qualificada(s) e enviada(s) ao Navi`)
    if (falhas) toast.error(`${falhas} falha(s) no envio ao Navi`)
  }

  function abrirDrawer(id: string) {
    setDrawerId(id)
    setDrawerOpen(true)
  }

  const podeExecutar = !!cidade && !!uf

  return (
    <div className="container max-w-6xl py-8 space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Prospecção CNPJ × CNO</h1>
        <p className="text-sm text-muted-foreground">
          Selecione o estado, município e bairro, execute a prospecção e envie os CNPJs
          qualificados ao Navi.
        </p>
      </header>

      {/* Resumo estatístico */}
      {data && data.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {[
            { label: 'Total', value: data.length, className: 'bg-slate-50' },
            { label: 'Novo', value: data.filter((o) => o.status === 'novo').length, className: 'bg-blue-50 text-blue-700' },
            { label: 'Qualificado', value: data.filter((o) => o.status === 'qualificado').length, className: 'bg-indigo-50 text-indigo-700' },
            { label: 'Webhook', value: data.filter((o) => o.status === 'webhook_enviado').length, className: 'bg-teal-50 text-teal-700' },
            { label: 'Engajado', value: data.filter((o) => o.status === 'engajado').length, className: 'bg-amber-50 text-amber-700' },
            { label: 'Fechado', value: data.filter((o) => o.status === 'fechado').length, className: 'bg-green-50 text-green-700' },
          ].map((card) => (
            <div key={card.label} className={`rounded-md border px-3 py-2 ${card.className}`}>
              <p className="text-xs text-muted-foreground">{card.label}</p>
              <p className="text-lg font-semibold">{card.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Localização em cascata (Estado → Município → Bairro) */}
      <div className="rounded-lg border bg-card/40 p-4 space-y-3">
        <h2 className="text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
          Localização alvo
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {/* 1. Estado */}
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Estado (UF)</label>
            <SelectGrouped
              value={ufSelecionada?.sigla}
              onChange={(v) => selecionarUf(v)}
              placeholder="— Selecione um estado —"
              groups={(
                ['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'] as const
              ).map((regiao) => ({
                label: regiao,
                options: (UFS_POR_REGIAO[regiao] ?? []).map((u) => ({
                  value: u.sigla,
                  label: `${u.sigla} — ${u.nome}`,
                })),
              }))}
            />
          </div>

          {/* 2. Município */}
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              Município{ufSelecionada ? ` · ${totalMun} em ${ufSelecionada.sigla}` : ''}
            </label>
            <Combobox<MunicipioIBGE>
              inputValue={municipioQuery}
              onInputChange={(v) => {
                setMunicipioQuery(v)
                if (municipioSelecionado && v !== municipioSelecionado.nome) {
                  setMunicipioSelecionado(null)
                  setBairroQuery('')
                }
              }}
              options={municipioOptions}
              onSelect={selecionarMunicipio}
              isLoading={loadingMun}
              placeholder={ufSelecionada ? 'Digite o município…' : 'Selecione o estado primeiro'}
              disabled={!ufSelecionada}
              minChars={0}
              emptyMessage={<span>Nenhum município em {ufSelecionada?.sigla} contém "{municipioQuery}"</span>}
            />
          </div>

          {/* 3. Bairro (estreita a lista) */}
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Bairro (opcional · filtra a lista)</label>
            <Combobox
              inputValue={bairroQuery}
              onInputChange={(v) => { setBairroQuery(v); setPage(0) }}
              options={bairroOptions}
              onSelect={(opt) => { setBairroQuery(opt.label); setPage(0) }}
              isLoading={loadingBai}
              placeholder={municipioSelecionado ? 'Ex: Aldeota, Meireles' : 'Selecione o município primeiro'}
              disabled={!municipioSelecionado}
              minChars={0}
              emptyMessage={<span>Sem bairros para "{bairroQuery}"</span>}
            />
          </div>
        </div>
      </div>

      {/* Filtros de status + Ações */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Status</label>
            <Select value={status} onValueChange={(v) => { setStatus(v); setPage(0) }}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos</SelectItem>
                <SelectItem value="novo">Novo</SelectItem>
                <SelectItem value="qualificado">Qualificado</SelectItem>
                <SelectItem value="webhook_enviado">Webhook Enviado</SelectItem>
                <SelectItem value="engajado">Engajado</SelectItem>
                <SelectItem value="fechado">Fechado</SelectItem>
                <SelectItem value="descartado">Descartado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Prioridade</label>
            <Select value={prioridade} onValueChange={(v) => { setPrioridade(v); setPage(0) }}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Todas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todas</SelectItem>
                <SelectItem value="baixa">Baixa</SelectItem>
                <SelectItem value="media">Média</SelectItem>
                <SelectItem value="alta">Alta</SelectItem>
                <SelectItem value="critica">Crítica</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Score mín</label>
            <Input
              placeholder="0.5"
              value={scoreMin}
              onChange={(e) => { setScoreMin(e.target.value); setPage(0) }}
              className="w-24"
              type="number"
              min={0}
              max={1}
              step={0.1}
            />
          </div>
        </div>

        <div className="flex items-end gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!sortedData || sortedData.length === 0}
            onClick={() => {
              const headers = ['CNPJ','Razao Social','Nome Fantasia','Cidade','UF','Score','Status','Prioridade','Obra','Area m2','Entrada']
              const rows = sortedData!.map((o) => [
                o.cnpj, o.razao_social || '', o.nome_fantasia || '', o.cidade, o.uf,
                o.score_match != null ? String(o.score_match) : '', o.status, o.prioridade,
                o.nome_obra || '', o.area_total_m2 != null ? String(o.area_total_m2) : '', formatDate(o.created_at),
              ])
              const csv = [headers, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
              const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `prospeccao_${new Date().toISOString().slice(0,10)}.csv`
              a.click()
              URL.revokeObjectURL(url)
              toast.success('CSV exportado!')
            }}
          >
            <Download size={14} className="mr-1.5" />
            Exportar
          </Button>
          <Button
            onClick={() => executar.mutate({ cidade, uf })}
            disabled={executar.isPending || !podeExecutar}
            size="sm"
            title={podeExecutar ? undefined : 'Selecione estado e município'}
          >
            <Play size={14} className="mr-1.5" />
            {executar.isPending ? 'Executando…' : 'Executar prospecção'}
          </Button>
        </div>
      </div>

      {/* Barra de ação em massa */}
      {selecionados.size > 0 && (
        <div className="flex items-center justify-between rounded-md border border-primary/40 bg-primary/5 px-4 py-2">
          <span className="text-sm font-medium">{selecionados.size} selecionado(s)</span>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelecionados(new Set())} disabled={enviando}>
              Limpar
            </Button>
            <Button size="sm" onClick={qualificarEEnviar} disabled={enviando}>
              <Send size={14} className="mr-1.5" />
              {enviando ? 'Enviando…' : `Qualificar + Enviar ao Navi (${selecionados.size})`}
            </Button>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-3 py-2 w-10">
                <Checkbox
                  checked={todosSelecionados}
                  onCheckedChange={toggleTodos}
                  aria-label="Selecionar todos"
                  disabled={idsVisiveis.length === 0}
                />
              </th>
              <th className="text-left px-3 py-2 font-medium">Empresa / Obra</th>
              <th className="text-left px-3 py-2 font-medium">Cidade</th>
              <th
                className="text-left px-3 py-2 font-medium cursor-pointer select-none hover:bg-muted/80"
                onClick={() => toggleSort('score_match')}
              >
                <span className="inline-flex items-center gap-1">
                  Score
                  {sortKey === 'score_match' ? (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} className="text-muted-foreground" />}
                </span>
              </th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
              <th
                className="text-left px-3 py-2 font-medium cursor-pointer select-none hover:bg-muted/80"
                onClick={() => toggleSort('prioridade')}
              >
                <span className="inline-flex items-center gap-1">
                  Prioridade
                  {sortKey === 'prioridade' ? (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} className="text-muted-foreground" />}
                </span>
              </th>
              <th
                className="text-left px-3 py-2 font-medium cursor-pointer select-none hover:bg-muted/80"
                onClick={() => toggleSort('created_at')}
              >
                <span className="inline-flex items-center gap-1">
                  Entrada
                  {sortKey === 'created_at' ? (sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />) : <ArrowUpDown size={12} className="text-muted-foreground" />}
                </span>
              </th>
              <th className="text-left px-3 py-2 font-medium">Navi</th>
              <th className="text-left px-3 py-2 font-medium w-20">Ações</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b">
                  <td className="px-3 py-2"><Skeleton className="h-4 w-4" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-12" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-14" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-10" /></td>
                  <td className="px-3 py-2"><Skeleton className="h-4 w-16" /></td>
                </tr>
              ))
            )}
            {sortedData && sortedData.length === 0 && (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-muted-foreground">
                  {podeExecutar
                    ? 'Nenhuma oportunidade. Clique em "Executar prospecção".'
                    : 'Selecione estado e município para começar.'}
                </td>
              </tr>
            )}
            {sortedData?.map((opp) => (
              <tr key={opp.id} className="border-b hover:bg-muted/40">
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selecionados.has(opp.id)}
                    onCheckedChange={() => toggleSelecionado(opp.id)}
                    aria-label={`Selecionar ${opp.cnpj}`}
                  />
                </td>
                <td className="px-3 py-2 cursor-pointer" onClick={() => abrirDrawer(opp.id)}>
                  <div className="font-medium">{opp.nome_fantasia || opp.razao_social || opp.cnpj}</div>
                  {opp.nome_obra && (<div className="text-xs text-muted-foreground">{opp.nome_obra}</div>)}
                </td>
                <td className="px-3 py-2">{opp.cidade}</td>
                <td className={`px-3 py-2 font-medium ${scoreColor(opp.score_match)}`}>
                  {opp.score_match != null ? opp.score_match.toFixed(2) : '—'}
                </td>
                <td className="px-3 py-2"><StatusBadge status={opp.status} /></td>
                <td className="px-3 py-2"><PrioridadeBadge prioridade={opp.prioridade} /></td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(opp.created_at)}</td>
                <td className="px-3 py-2">
                  {opp.webhook_enviado_at ? (
                    <span className="text-green-600 text-xs">OK</span>
                  ) : (
                    <span className="text-amber-600 text-xs">Pendente</span>
                  )}
                </td>
                <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                  <Select
                    value={opp.status}
                    onValueChange={(novo) => {
                      patchStatus.mutate(
                        { id: opp.id, status: novo },
                        { onSuccess: () => toast.success('Status atualizado') },
                      )
                    }}
                  >
                    <SelectTrigger className="h-7 text-xs w-full">
                      <SelectValue placeholder="…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="novo">Novo</SelectItem>
                      <SelectItem value="qualificado">Qualificado</SelectItem>
                      <SelectItem value="webhook_enviado">Webhook</SelectItem>
                      <SelectItem value="engajado">Engajado</SelectItem>
                      <SelectItem value="fechado">Fechado</SelectItem>
                      <SelectItem value="descartado">Descartado</SelectItem>
                    </SelectContent>
                  </Select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Página {page + 1} • {sortedData?.length ?? 0} resultados
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
            Anterior
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={!data || data.length < pageSize}>
            Próxima
          </Button>
        </div>
      </div>

      <OportunidadeDrawer id={drawerId} open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </div>
  )
}
