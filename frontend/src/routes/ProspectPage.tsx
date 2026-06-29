/**
 * ProspectPage (/prospect) — hub consolidado dos entrantes CNPJ captados em TODOS
 * os relatórios da org (fonte de leads do V1). Seleção em massa → envia pra
 * oportunidades_prospeccao (reusa o bridge por-relatório). Daí o /prospeccao
 * qualifica e dispara o Navi.
 */
import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import { Send, Search, Sparkles, Phone } from 'lucide-react'
import {
  useEntrantesCaptados,
  useEnviarEntrantesProspeccao,
  useEnriquecerEntrante,
  type EntranteCaptado,
} from '@/hooks/useProspeccao'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'

function _norm(s: string | null | undefined): string {
  return (s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('pt-BR')
}

export function ProspectPage() {
  const { data, isLoading } = useEntrantesCaptados()
  const enviar = useEnviarEntrantesProspeccao()
  const enriquecer = useEnriquecerEntrante()

  const [busca, setBusca] = useState('')
  const [soNovos, setSoNovos] = useState(true)
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [enviando, setEnviando] = useState(false)
  const [enriquecendo, setEnriquecendo] = useState(false)

  const lista = useMemo(() => {
    let out: EntranteCaptado[] = data?.entrantes ?? []
    if (soNovos) out = out.filter((e) => !e.ja_em_prospeccao)
    const q = _norm(busca)
    if (q) {
      out = out.filter(
        (e) =>
          _norm(e.nome).includes(q) ||
          e.cnpj.includes(q.replace(/\D/g, '')) ||
          _norm(e.bairro).includes(q),
      )
    }
    return out
  }, [data, busca, soNovos])

  const idsVisiveis = useMemo(() => lista.map((e) => e.cnpj), [lista])
  const todos = idsVisiveis.length > 0 && idsVisiveis.every((c) => selecionados.has(c))

  function toggle(cnpj: string) {
    setSelecionados((prev) => {
      const next = new Set(prev)
      if (next.has(cnpj)) next.delete(cnpj)
      else next.add(cnpj)
      return next
    })
  }

  function toggleTodos() {
    setSelecionados((prev) => {
      if (idsVisiveis.every((c) => prev.has(c))) {
        const next = new Set(prev)
        idsVisiveis.forEach((c) => next.delete(c))
        return next
      }
      return new Set([...prev, ...idsVisiveis])
    })
  }

  async function enviarSelecionados() {
    const escolhidos = (data?.entrantes ?? []).filter((e) => selecionados.has(e.cnpj))
    if (!escolhidos.length) return
    // Agrupa por relatório de origem (o bridge é por-relatório).
    const porRelatorio = new Map<string, string[]>()
    for (const e of escolhidos) {
      const arr = porRelatorio.get(e.relatorio_id) ?? []
      arr.push(e.cnpj)
      porRelatorio.set(e.relatorio_id, arr)
    }
    setEnviando(true)
    let ok = 0
    let falhas = 0
    for (const [relatorioId, cnpjs] of porRelatorio) {
      try {
        await enviar.mutateAsync({ relatorioId, cnpjs })
        ok += cnpjs.length
      } catch {
        falhas += cnpjs.length
      }
    }
    setEnviando(false)
    setSelecionados(new Set())
    if (ok) toast.success(`${ok} entrante(s) enviado(s) para prospecção`)
    if (falhas) toast.error(`${falhas} falha(s) no envio`)
  }

  async function enriquecerSelecionados() {
    const escolhidos = (data?.entrantes ?? []).filter((e) => selecionados.has(e.cnpj))
    if (!escolhidos.length) return
    setEnriquecendo(true)
    let ok = 0
    let falhas = 0
    for (const e of escolhidos) {
      try {
        await enriquecer.mutateAsync({ relatorioId: e.relatorio_id, cnpj: e.cnpj })
        ok++
      } catch {
        falhas++
      }
    }
    setEnriquecendo(false)
    if (ok) toast.success(`${ok} entrante(s) enriquecido(s) (ReceitaWS)`)
    if (falhas) toast.error(`${falhas} falha(s) no enriquecimento`)
  }

  return (
    <div className="container max-w-5xl py-8 space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Captação de Leads (Entrantes CNPJ)</h1>
        <p className="text-sm text-muted-foreground">
          Novos CNPJs fitness encontrados em todos os seus relatórios. Selecione e envie
          para a Prospecção — de lá você qualifica e dispara o Navi.
        </p>
      </header>

      {/* Resumo */}
      {data && (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'Captados (únicos)', value: data.total },
            { label: 'Já em prospecção', value: data.entrantes.filter((e) => e.ja_em_prospeccao).length },
            { label: 'Relatórios varridos', value: data.relatorios },
          ].map((c) => (
            <div key={c.label} className="rounded-md border bg-muted/40 px-3 py-2">
              <p className="text-xs text-muted-foreground">{c.label}</p>
              <p className="text-lg font-semibold">{c.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Nome, CNPJ ou bairro"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-8 w-72"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <Checkbox checked={soNovos} onCheckedChange={(v) => setSoNovos(!!v)} />
          Ocultar os que já estão em prospecção
        </label>
      </div>

      {/* Barra de envio */}
      {selecionados.size > 0 && (
        <div className="flex items-center justify-between rounded-md border border-primary/40 bg-primary/5 px-4 py-2">
          <span className="text-sm font-medium">{selecionados.size} selecionado(s)</span>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelecionados(new Set())} disabled={enviando || enriquecendo}>
              Limpar
            </Button>
            <Button variant="outline" size="sm" onClick={enriquecerSelecionados} disabled={enviando || enriquecendo}>
              <Sparkles size={14} className="mr-1.5" />
              {enriquecendo ? 'Enriquecendo…' : `Enriquecer ${selecionados.size}`}
            </Button>
            <Button size="sm" onClick={enviarSelecionados} disabled={enviando || enriquecendo}>
              <Send size={14} className="mr-1.5" />
              {enviando ? 'Enviando…' : `Enviar ${selecionados.size} para Prospecção`}
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
                  checked={todos}
                  onCheckedChange={toggleTodos}
                  aria-label="Selecionar todos"
                  disabled={idsVisiveis.length === 0}
                />
              </th>
              <th className="text-left px-3 py-2 font-medium">Empresa</th>
              <th className="text-left px-3 py-2 font-medium">CNPJ</th>
              <th className="text-left px-3 py-2 font-medium">Segmento</th>
              <th className="text-left px-3 py-2 font-medium">Bairro</th>
              <th className="text-left px-3 py-2 font-medium">Abertura</th>
              <th className="text-left px-3 py-2 font-medium">Contato</th>
              <th className="text-left px-3 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className="border-b">
                  {Array.from({ length: 8 }).map((__, j) => (
                    <td key={j} className="px-3 py-2"><Skeleton className="h-4 w-20" /></td>
                  ))}
                </tr>
              ))}
            {!isLoading && lista.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-muted-foreground">
                  {(data?.total ?? 0) === 0
                    ? 'Nenhum entrante captado ainda — gere relatórios com a seção de Novos Entrantes.'
                    : 'Nada para os filtros atuais.'}
                </td>
              </tr>
            )}
            {lista.map((e) => (
              <tr key={e.cnpj} className="border-b hover:bg-muted/40">
                <td className="px-3 py-2">
                  <Checkbox
                    checked={selecionados.has(e.cnpj)}
                    onCheckedChange={() => toggle(e.cnpj)}
                    aria-label={`Selecionar ${e.nome}`}
                  />
                </td>
                <td className="px-3 py-2 font-medium">{e.nome}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.cnpj}</td>
                <td className="px-3 py-2 text-muted-foreground">{e.segmento_operacao || '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">{e.bairro || '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(e.data_abertura)}</td>
                <td className="px-3 py-2">
                  {e.tem_contato ? (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600">
                      <Phone size={12} /> ok
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">sem tel.</span>
                  )}
                </td>
                <td className="px-3 py-2">
                  {e.ja_em_prospeccao ? (
                    <span className="text-xs text-teal-600">Em prospecção</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Novo</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
