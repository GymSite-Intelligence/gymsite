/**
 * RebuscarCandidatosButton — re-busca cirúrgica de pontos (Motor v2.0).
 *
 * Re-executa SÓ a caça de imóveis para um relatório pronto, com o gate de
 * elegibilidade aplicado (fora da cidade/tipo residencial reprovam; bairro
 * adjacente e preço suspeito viram avisos). Mostra o resultado num dialog:
 * aprovados que entraram no relatório E reprovados com o motivo — o gate
 * trabalhando às claras.
 */
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronDown, RefreshCcw, SearchCheck, ShieldX } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { notify } from '@/lib/notify'
import { API_BASE, supabase } from '@/lib/supabase'

type Reprovado = {
  nome: string
  endereco: string | null
  preco: string | null
  flags: string[]
}

type Resultado = {
  encontrados: number
  aprovados: number
  reprovados: Reprovado[]
  candidatos_novos: { nome: string; endereco: string; motivo: string }[]
}

const FLAG_LABEL: Record<string, string> = {
  fora_do_bairro_alvo: 'fora do bairro alvo',
  fora_da_cidade: 'fora da cidade',
  tipo_incompativel: 'imóvel residencial/terreno',
  preco_suspeito_area_de_terreno: 'preço sugere área de terreno',
}

export function RebuscarCandidatosButton({ relatorioId }: { relatorioId: string }) {
  const qc = useQueryClient()
  const [buscando, setBuscando] = useState(false)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [mostrarBarrados, setMostrarBarrados] = useState(false)

  async function rebuscar() {
    setBuscando(true)
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      const res = await fetch(`${API_BASE}/api/relatorios/${relatorioId}/rebuscar-candidatos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: JSON.stringify({ max_candidatos: 5 }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(body?.detail || `Erro ${res.status}`)
      setMostrarBarrados(false)
      setResultado(body as Resultado)
      qc.invalidateQueries({ queryKey: ['relatorio', relatorioId] })
    } catch (e) {
      notify.error(e instanceof Error ? e.message : 'Não foi possível re-buscar pontos.')
    } finally {
      setBuscando(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={rebuscar} disabled={buscando}>
        <RefreshCcw className={`mr-1.5 h-3.5 w-3.5 ${buscando ? 'animate-spin' : ''}`} />
        {buscando ? 'Caçando pontos…' : 'Re-buscar pontos'}
      </Button>

      <Dialog open={Boolean(resultado)} onOpenChange={(v) => !v && setResultado(null)}>
        <DialogContent className="max-h-[85vh] gap-0 overflow-y-auto p-0 sm:max-w-lg">
          <DialogHeader className="px-6 pt-6 text-center sm:text-center">
            <DialogTitle className="text-lg">Re-busca de pontos</DialogTitle>
          </DialogHeader>

          {resultado && (
            <div className="space-y-4 px-6 py-5">
              <p className="text-sm text-muted-foreground">
                {resultado.encontrados} anúncio(s) encontrados na cidade ·{' '}
                <span className="font-medium text-foreground">
                  {resultado.aprovados} aprovado(s) no filtro
                </span>{' '}
                · {resultado.reprovados.length} barrado(s)
              </p>

              {resultado.candidatos_novos.length > 0 && (
                <div>
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-emerald-700">
                    <SearchCheck className="h-3.5 w-3.5" /> Entraram no relatório
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {resultado.candidatos_novos.map((c, i) => (
                      <div key={i} className="rounded-md border border-emerald-200 bg-emerald-50/50 px-3 py-2">
                        <p className="text-sm font-medium">{c.nome}</p>
                        <p className="text-xs text-muted-foreground">{c.endereco}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {resultado.reprovados.length > 0 && (
                <div>
                  <button
                    type="button"
                    onClick={() => setMostrarBarrados((v) => !v)}
                    className="flex w-full items-center gap-1.5 text-xs font-medium text-red-700"
                  >
                    <ShieldX className="h-3.5 w-3.5" />
                    {resultado.reprovados.length} barrado(s) pelo filtro de qualidade
                    <ChevronDown
                      className={`ml-auto h-3.5 w-3.5 transition-transform ${
                        mostrarBarrados ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                  {mostrarBarrados && (
                    <div className="mt-2 flex flex-col gap-1.5">
                      {resultado.reprovados.map((r, i) => (
                        <div key={i} className="rounded-md border px-3 py-2 opacity-75">
                          <p className="text-sm">{r.nome}</p>
                          <p className="text-xs text-muted-foreground">{r.endereco}</p>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {r.flags.map((f) => (
                              <Badge
                                key={f}
                                variant="secondary"
                                className="rounded-full bg-red-50 px-2 text-[10px] font-normal text-red-700"
                              >
                                {FLAG_LABEL[f] ?? f}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {resultado.aprovados === 0 && resultado.reprovados.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Nenhum anúncio novo na faixa de área agora. O estoque do mercado está
                  seco — considere a prospecção de imóveis não anunciados.
                </p>
              )}
            </div>
          )}

          <DialogFooter className="border-t px-6 py-4 sm:justify-end">
            <Button variant="outline" className="h-10" onClick={() => setResultado(null)}>
              Fechar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
