/**
 * ProspeccaoPage — listagem de oportunidades CNPJ × CNO.
 */
import { useState, useMemo } from 'react'
import { useSearch } from '@tanstack/react-router'
import { toast } from 'sonner'
import { Search, Play, ArrowUpDown, ArrowUp, ArrowDown, Settings, Download } from 'lucide-react'
import { useOportunidades, useExecutarProspeccao, usePatchStatusOportunidade } from '@/hooks/useProspeccao'
import { StatusBadge } from '@/components/prospeccao/StatusBadge'
import { PrioridadeBadge } from '@/components/prospeccao/PrioridadeBadge'
import { OportunidadeDrawer } from '@/components/prospeccao/OportunidadeDrawer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface SearchParams {
  cidade?: string
  status?: string
  prioridade?: string
}

export function ProspeccaoPage() {
  const search = useSearch({ strict: false }) as SearchParams
  const [cidade, setCidade] = useState(search.cidade ?? '')
  const [status, setStatus] = useState(search.status ?? '')
  const [prioridade, setPrioridade] = useState(search.prioridade ?? '')
  const [scoreMin, setScoreMin] = useState('')
  const [uf, setUf] = useState('CE')
  const [page, setPage] = useState(0)
  const pageSize = 20
  const [sortKey, setSortKey] = useState<'score_match' | 'created_at' | 'prioridade' | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [showWebhookConfig, setShowWebhookConfig] = useState(false)
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookOrgId, setWebhookOrgId] = useState('')
  const [savingWebhook, setSavingWebhook] = useState(false)
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

  const sortedData = useMemo(() => {
    if (!data || !sortKey) return data
    const dir = sortDir === 'asc' ? 1 : -1
    return [...data].sort((a, b) => {
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
  }, [data, sortKey, sortDir])

  function toggleSort(key: 'score_match' | 'created_at' | 'prioridade') {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  function formatDate(iso: string) {
    const d = new Date(iso)
    return d.toLocaleDateString('pt-BR')
  }

  function scoreColor(score: number | null) {
    if (score == null) return 'text-muted-foreground'
    if (score >= 0.7) return 'text-green-600'
    if (score >= 0.4) return 'text-amber-600'
    return 'text-red-600'
  }

  async function salvarWebhook() {
    if (!webhookUrl || !webhookOrgId) return
    setSavingWebhook(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/prospeccao/webhook/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ org_id: webhookOrgId, webhook_url: webhookUrl }),
      })
      if (!res.ok) throw new Error('Falha ao salvar')
      toast.success('Webhook configurado com sucesso!')
      setShowWebhookConfig(false)
    } catch {
      toast.error('Erro ao configurar webhook. Verifique a URL e o org_id.')
    } finally {
      setSavingWebhook(false)
    }
  }

  function abrirDrawer(id: string) {
    setDrawerId(id)
    setDrawerOpen(true)
  }

  return (
    <div className="container max-w-6xl py-8 space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Prospecção CNPJ × CNO</h1>
        <p className="text-sm text-muted-foreground">
          Oportunidades cruzando entrantes CNPJ fitness com obras em andamento/finalizadas.
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

      {/* Filtros + Ação */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-wrap items-end gap-2">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Cidade</label>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Fortaleza"
                value={cidade}
                onChange={(e) => { setCidade(e.target.value); setPage(0) }}
                className="pl-8 w-48"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">UF</label>
            <Input
              placeholder="CE"
              value={uf}
              onChange={(e) => { setUf(e.target.value.toUpperCase()); setPage(0) }}
              className="w-16 uppercase"
              maxLength={2}
            />
          </div>

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
            onClick={() => setShowWebhookConfig((v) => !v)}
          >
            <Settings size={14} className="mr-1.5" />
            Webhook Claw
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!sortedData || sortedData.length === 0}
            onClick={() => {
              const headers = ['CNPJ','Razao Social','Nome Fantasia','Cidade','UF','Score','Status','Prioridade','Obra','Area m2','Entrada']
              const rows = sortedData!.map((o) => [
                o.cnpj,
                o.razao_social || '',
                o.nome_fantasia || '',
                o.cidade,
                o.uf,
                o.score_match != null ? String(o.score_match) : '',
                o.status,
                o.prioridade,
                o.nome_obra || '',
                o.area_total_m2 != null ? String(o.area_total_m2) : '',
                formatDate(o.created_at),
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
            onClick={() => executar.mutate({ cidade: cidade || 'Fortaleza', uf: uf || 'CE' })}
            disabled={executar.isPending}
            size="sm"
          >
            <Play size={14} className="mr-1.5" />
            {executar.isPending ? 'Executando…' : 'Executar prospecção'}
          </Button>
        </div>
      </div>

      {/* Configuração de webhook */}
      {showWebhookConfig && (
        <div className="rounded-md border p-4 space-y-3 bg-muted/20">
          <p className="text-sm font-medium">Configurar webhook do Claw</p>
          <div className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Org ID</label>
              <Input
                placeholder="UUID da organização"
                value={webhookOrgId}
                onChange={(e) => setWebhookOrgId(e.target.value)}
                className="w-64"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">URL do webhook</label>
              <Input
                placeholder="https://..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                className="w-80"
              />
            </div>
            <Button
              size="sm"
              onClick={salvarWebhook}
              disabled={savingWebhook || !webhookUrl || !webhookOrgId}
            >
              {savingWebhook ? 'Salvando…' : 'Salvar'}
            </Button>
          </div>
        </div>
      )}

      {/* Tabela */}
      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
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
              <th className="text-left px-3 py-2 font-medium">Webhook</th>
              <th className="text-left px-3 py-2 font-medium w-20">Ações</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b">
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
                <td colSpan={8} className="px-3 py-8 text-center text-muted-foreground">
                  Nenhuma oportunidade encontrada.
                </td>
              </tr>
            )}
            {sortedData?.map((opp) => (
              <tr
                key={opp.id}
                className="border-b hover:bg-muted/40 cursor-pointer"
                onClick={() => abrirDrawer(opp.id)}
              >
                <td className="px-3 py-2">
                  <div className="font-medium">{opp.nome_fantasia || opp.razao_social || opp.cnpj}</div>
                  {opp.nome_obra && (
                    <div className="text-xs text-muted-foreground">{opp.nome_obra}</div>
                  )}
                </td>
                <td className="px-3 py-2">{opp.cidade}</td>
                <td className={`px-3 py-2 font-medium ${scoreColor(opp.score_match)}`}>
                  {opp.score_match != null ? opp.score_match.toFixed(2) : '—'}
                </td>
                <td className="px-3 py-2">
                  <StatusBadge status={opp.status} />
                </td>
                <td className="px-3 py-2">
                  <PrioridadeBadge prioridade={opp.prioridade} />
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {formatDate(opp.created_at)}
                </td>
                <td className="px-3 py-2">
                  {opp.webhook_enviado_at ? (
                    <span className="text-green-600 text-xs">OK</span>
                  ) : (
                    <span className="text-amber-600 text-xs">Pendente</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  <Select
                    value={opp.status}
                    onValueChange={(novo) => {
                      patchStatus.mutate(
                        { id: opp.id, status: novo },
                        { onSuccess: () => toast.success(`Status atualizado`) }
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
          Página {page + 1} • {data?.length ?? 0} resultados
        </p>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={!data || data.length < pageSize}
          >
            Próxima
          </Button>
        </div>
      </div>

      <OportunidadeDrawer
        id={drawerId}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
