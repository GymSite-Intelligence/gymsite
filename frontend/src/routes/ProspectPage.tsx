/**
 * ProspectPage (/prospect) — hub consolidado dos entrantes CNPJ captados em TODOS
 * os relatórios da org (fonte de leads do V1). Seleção em massa → envia pra
 * oportunidades_prospeccao (reusa o bridge por-relatório). Daí o /prospeccao
 * qualifica e dispara o Navi.
 */
import { useState, useMemo } from 'react'
import { toast } from 'sonner'
import { Send, Search, Sparkles, Phone, Radar } from 'lucide-react'
import {
  useEntrantesCaptados,
  useEnviarEntrantesProspeccao,
  useEnriquecerEntrante,
  useBuscarEntrantes,
  useCaptarEntrantes,
  type EntranteCaptado,
} from '@/hooks/useProspeccao'
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
  return (s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('pt-BR')
}

export function ProspectPage() {
  const { data: agregado, isLoading } = useEntrantesCaptados()
  const enviar = useEnviarEntrantesProspeccao()
  const enriquecer = useEnriquecerEntrante()
  const buscarEntrantes = useBuscarEntrantes()
  const captar = useCaptarEntrantes()

  // ── Busca DIRETA por município (independente do pipeline) ──
  const [ufBusca, setUfBusca] = useState<UF | null>(null)
  const [munQuery, setMunQuery] = useState('')
  const [munSel, setMunSel] = useState<MunicipioIBGE | null>(null)
  const [diasBusca, setDiasBusca] = useState('90')
  // resultadoBusca !== null → modo BUSCA (mostra o resultado ao vivo, envia via captar).
  const [resultadoBusca, setResultadoBusca] = useState<{
    entrantes: EntranteCaptado[]; cidade: string; uf: string
  } | null>(null)

  const debMun = useDebounce(munQuery, 200)
  const { sugestoes: munsSugeridos, isLoading: loadingMun, total: totalMun } =
    useMunicipioAutocomplete(debMun, ufBusca?.sigla ?? '')

  const modoBusca = resultadoBusca !== null
  // Fonte da tabela: resultado da busca (modo busca) OU o agregado dos relatórios.
  const data = modoBusca
    ? { entrantes: resultadoBusca!.entrantes, total: resultadoBusca!.entrantes.length, relatorios: 0 }
    : agregado

  async function rodarBusca() {
    const cidade = munSel?.nome ?? ''
    const uf = ufBusca?.sigla ?? ''
    if (!cidade || !uf) return
    try {
      const r = await buscarEntrantes.mutateAsync({ cidade, uf, dias: Number(diasBusca) || 90 })
      setResultadoBusca({ entrantes: r.entrantes ?? [], cidade: r.cidade || cidade, uf: r.uf || uf })
      setSelecionados(new Set())
      // Reseta os filtros estruturados — senão um fMunicipio/fSegmento velho
      // esconde o resultado da nova busca.
      setFMunicipio(''); setFCnae(''); setFSegmento(''); setBusca('')
      toast.success(`${r.total ?? 0} entrante(s) encontrado(s) em ${r.cidade || cidade}`)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  function limparBusca() {
    setResultadoBusca(null)
    setSelecionados(new Set())
  }

  const [busca, setBusca] = useState('')
  const [soNovos, setSoNovos] = useState(true)
  const [fMunicipio, setFMunicipio] = useState('')
  const [fCnae, setFCnae] = useState('')
  const [fSegmento, setFSegmento] = useState('')
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [enviando, setEnviando] = useState(false)
  const [enriquecendo, setEnriquecendo] = useState(false)

  // Valores distintos p/ os dropdowns (a partir do conjunto completo captado).
  const opcoes = useMemo(() => {
    const mun = new Set<string>()
    const cnae = new Set<string>()
    const seg = new Set<string>()
    for (const e of data?.entrantes ?? []) {
      if (e.cidade) mun.add(e.cidade)
      if (e.cnae) cnae.add(e.cnae)
      if (e.segmento_operacao) seg.add(e.segmento_operacao)
    }
    const ord = (s: Set<string>) => [...s].sort((a, b) => a.localeCompare(b, 'pt-BR'))
    return { municipios: ord(mun), cnaes: ord(cnae), segmentos: ord(seg) }
  }, [data])

  const lista = useMemo(() => {
    let out: EntranteCaptado[] = data?.entrantes ?? []
    if (soNovos) out = out.filter((e) => !e.ja_em_prospeccao)
    if (fMunicipio) out = out.filter((e) => e.cidade === fMunicipio)
    if (fCnae) out = out.filter((e) => e.cnae === fCnae)
    if (fSegmento) out = out.filter((e) => e.segmento_operacao === fSegmento)
    const q = _norm(busca)
    if (q) {
      out = out.filter(
        (e) =>
          _norm(e.nome).includes(q) ||
          e.cnpj.includes(q.replace(/\D/g, '')) ||
          _norm(e.bairro).includes(q) ||
          _norm(e.socio_nome).includes(q),
      )
    }
    return out
  }, [data, busca, soNovos, fMunicipio, fCnae, fSegmento])

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
    const cnpjsSel = [...selecionados]
    if (!cnpjsSel.length) return
    setEnviando(true)

    // Modo BUSCA: persiste direto via captar-entrantes (enriquece no servidor).
    if (modoBusca && resultadoBusca) {
      try {
        const r = await captar.mutateAsync({
          cidade: resultadoBusca.cidade, uf: resultadoBusca.uf, cnpjs: cnpjsSel,
        })
        toast.success(`${r.total_enviados} enviado(s) para prospecção`)
        setResultadoBusca((prev) => prev && {
          ...prev,
          entrantes: prev.entrantes.map((e) =>
            cnpjsSel.includes(e.cnpj) ? { ...e, ja_em_prospeccao: true } : e),
        })
      } catch (e) {
        toast.error((e as Error).message)
      }
      setEnviando(false)
      setSelecionados(new Set())
      return
    }

    // Modo AGREGADO: bridge por relatório de origem.
    const escolhidos = (agregado?.entrantes ?? []).filter((e) => selecionados.has(e.cnpj))
    const porRelatorio = new Map<string, string[]>()
    for (const e of escolhidos) {
      if (!e.relatorio_id) continue
      const arr = porRelatorio.get(e.relatorio_id) ?? []
      arr.push(e.cnpj)
      porRelatorio.set(e.relatorio_id, arr)
    }
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
    // Só no modo agregado (por-relatório). No modo busca o captar já enriquece.
    const escolhidos = (agregado?.entrantes ?? []).filter(
      (e) => selecionados.has(e.cnpj) && e.relatorio_id,
    )
    if (!escolhidos.length) return
    setEnriquecendo(true)
    let ok = 0
    let falhas = 0
    for (const e of escolhidos) {
      try {
        await enriquecer.mutateAsync({ relatorioId: e.relatorio_id!, cnpj: e.cnpj })
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
          Busque novos entrantes CNPJ fitness por município (90 dias, direto do RFB) ou
          use os já captados nos relatórios. Selecione → envie pra Prospecção → Navi.
        </p>
      </header>

      {/* Busca DIRETA por município (independente do pipeline) */}
      <div className="rounded-lg border bg-card/40 p-4 space-y-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider font-mono font-medium text-muted-foreground">
          <Radar size={14} /> Buscar novos entrantes por município
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Estado (UF)</label>
            <SelectGrouped
              value={ufBusca?.sigla}
              onChange={(v) => {
                setUfBusca(UFS_BRASIL.find((u) => u.sigla === v) ?? null)
                setMunSel(null); setMunQuery('')
              }}
              placeholder="— UF —"
              groups={(['Sudeste', 'Sul', 'Nordeste', 'Centro-Oeste', 'Norte'] as const).map((regiao) => ({
                label: regiao,
                options: (UFS_POR_REGIAO[regiao] ?? []).map((u) => ({ value: u.sigla, label: `${u.sigla} — ${u.nome}` })),
              }))}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              Município{ufBusca ? ` · ${totalMun} em ${ufBusca.sigla}` : ''}
            </label>
            <Combobox<MunicipioIBGE>
              inputValue={munQuery}
              onInputChange={(v) => { setMunQuery(v); if (munSel && v !== munSel.nome) setMunSel(null) }}
              options={munsSugeridos.map((m) => ({ label: m.nome, description: m.uf_nome || m.uf, value: String(m.id), payload: m }))}
              onSelect={(opt: ComboboxOption<MunicipioIBGE>) => { if (opt.payload) { setMunSel(opt.payload); setMunQuery(opt.payload.nome) } }}
              isLoading={loadingMun}
              placeholder={ufBusca ? 'Digite o município…' : 'Selecione a UF primeiro'}
              disabled={!ufBusca}
              minChars={0}
              emptyMessage={<span>Nenhum município em {ufBusca?.sigla} contém "{munQuery}"</span>}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Janela (dias)</label>
            <Input value={diasBusca} onChange={(e) => setDiasBusca(e.target.value)} className="w-20" type="number" min={7} max={365} />
          </div>
          <Button onClick={rodarBusca} disabled={!munSel || !ufBusca || buscarEntrantes.isPending} size="sm">
            <Radar size={14} className="mr-1.5" />
            {buscarEntrantes.isPending ? 'Buscando…' : 'Buscar entrantes'}
          </Button>
          {modoBusca && (
            <Button variant="ghost" size="sm" onClick={limparBusca}>Ver captados</Button>
          )}
        </div>
        {modoBusca && (
          <p className="text-xs text-muted-foreground">
            Mostrando <strong>{resultadoBusca!.entrantes.length}</strong> entrante(s) ao vivo de{' '}
            <strong>{resultadoBusca!.cidade}/{resultadoBusca!.uf}</strong> (RFB, últimos {diasBusca}d).
            Selecionar + Enviar persiste em prospecção (enriquece no envio).
          </p>
        )}
      </div>

      {/* Resumo (só no modo captados) */}
      {!modoBusca && data && (
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

      {/* Filtros — Município/Segmento/CNAE só no modo CAPTADOS (no modo busca o
          município já vem da pesquisa; evita o "segundo Município" confuso). */}
      <div className="flex flex-wrap items-end gap-3">
        {!modoBusca && (
          <>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Município</label>
              <Select value={fMunicipio} onValueChange={setFMunicipio}>
                <SelectTrigger className="w-48"><SelectValue placeholder="Todos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  {opcoes.municipios.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Segmento</label>
              <Select value={fSegmento} onValueChange={setFSegmento}>
                <SelectTrigger className="w-48"><SelectValue placeholder="Todos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  {opcoes.segmentos.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">CNAE</label>
              <Select value={fCnae} onValueChange={setFCnae}>
                <SelectTrigger className="w-40"><SelectValue placeholder="Todos" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  {opcoes.cnaes.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </>
        )}
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Busca</label>
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Nome, CNPJ, bairro ou sócio"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-8 w-64"
            />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground pb-2">
          <Checkbox checked={soNovos} onCheckedChange={(v) => setSoNovos(!!v)} />
          Ocultar já enviados
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
            {!modoBusca && (
              <Button variant="outline" size="sm" onClick={enriquecerSelecionados} disabled={enviando || enriquecendo}>
                <Sparkles size={14} className="mr-1.5" />
                {enriquecendo ? 'Enriquecendo…' : `Enriquecer ${selecionados.size}`}
              </Button>
            )}
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
              <th className="text-left px-3 py-2 font-medium">CNAE</th>
              <th className="text-left px-3 py-2 font-medium">Sócio Adm.</th>
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
                  {Array.from({ length: 10 }).map((__, j) => (
                    <td key={j} className="px-3 py-2"><Skeleton className="h-4 w-20" /></td>
                  ))}
                </tr>
              ))}
            {!isLoading && lista.length === 0 && (
              <tr>
                <td colSpan={10} className="px-3 py-8 text-center text-muted-foreground">
                  {modoBusca
                    ? `Nenhum entrante fitness (90d) em ${resultadoBusca!.cidade}/${resultadoBusca!.uf}. Tente outro município ou aumente a janela.`
                    : (data?.total ?? 0) === 0
                      ? 'Nenhum entrante captado ainda — busque por município acima ou gere relatórios.'
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
                <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{e.cnae || '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">{e.socio_nome || '—'}</td>
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
