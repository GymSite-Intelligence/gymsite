import { useQuery } from '@tanstack/react-query'
import { useRouterState } from '@tanstack/react-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, FileText, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function LeadAccessPage() {
  const search = useRouterState({ select: (s) => s.location.search }) as {
    code?: string
    id?: string
  }
  const accessCode = search.code?.trim()
  // id ≠ code: link canônico /acesso?id={relatorio_id}&code={access_code}
  // Legacy: só ?code= → id=code (stub GYM-22 onde eram iguais)
  const relatorioId = (search.id?.trim() || accessCode)?.trim()

  const { data: relatorio, isLoading, error } = useQuery({
    queryKey: ['lead_access', relatorioId, accessCode],
    queryFn: async () => {
      if (!relatorioId || !accessCode) throw new Error('Parâmetros ausentes')
      const res = await fetch(
        `${API_BASE}/api/relatorios/${encodeURIComponent(relatorioId)}?access_code=${encodeURIComponent(accessCode)}`,
      )
      if (!res.ok) {
        throw new Error('Acesso negado ou relatório não encontrado')
      }
      return res.json()
    },
    enabled: !!relatorioId && !!accessCode,
    retry: false,
  })

  if (!accessCode || !relatorioId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-slate-600">
              Link incompleto. Use o link completo do e-mail (id + code).
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <p className="text-slate-500 animate-pulse">Carregando relatório...</p>
      </div>
    )
  }

  if (error || !relatorio) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <Card className="w-full max-w-md border-red-200">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-lg font-bold text-slate-800 mb-2">Acesso Indisponível</h2>
            <p className="text-sm text-slate-600">
              O código informado não é válido, não foi encontrado ou ocorreu um erro.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { header, output_consolidado } = relatorio
  const ex = output_consolidado?.executive_summary || {}

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 mb-4">
            <FileText className="w-8 h-8 text-blue-600" />
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">
            Análise de Viabilidade
          </h1>
          <p className="text-slate-500 text-lg">
            {header?.cidade}/{header?.uf} — {header?.bairro}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-500 uppercase tracking-wide">Veredito</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-800 capitalize">
                {ex.veredito || 'Não avaliado'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-500 uppercase tracking-wide">Nota Geral</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-800">
                {ex.nota_geral ? `${ex.nota_geral}/10` : '-'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-500 uppercase tracking-wide">Risco</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-800 capitalize">
                {ex.nivel_risco || '-'}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-6">
            <h3 className="font-semibold text-blue-900 mb-2">Oportunidade Principal</h3>
            <p className="text-blue-800 text-sm leading-relaxed">
              {ex.oportunidade_principal || 'Análise de oportunidade não disponível no sumário.'}
            </p>
          </CardContent>
        </Card>

        <div className="mt-12 bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-600"></div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Acesse o Relatório Completo</h2>
          <p className="text-slate-600 mb-8 max-w-2xl mx-auto">
            Este é apenas um resumo executivo da região. Para liberar o PDF completo contendo o mapeamento exato dos concorrentes, análise demográfica detalhada e simulação financeira (Capex, Opex, Break-even), agende uma apresentação com nosso time.
          </p>
          <a
            href="https://vectracargo.com.br/contato"
            target="_blank"
            rel="noreferrer"
          >
            <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 rounded-xl text-lg font-semibold shadow-lg shadow-blue-200 transition-all hover:scale-105">
              Agendar Apresentação
            </Button>
          </a>
          <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-500">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            <span>Consultoria sem compromisso</span>
          </div>
        </div>
      </div>
    </div>
  )
}
