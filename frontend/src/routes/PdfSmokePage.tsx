/**
 * PdfSmokePage — página simples para validar layout de impressão/PDF.
 *
 * Objetivo: permitir testar o fluxo "Baixar PDF" sem depender do backend
 * gerar PDF server-side. Usa print do browser (Salvar como PDF).
 */
import { useEffect } from 'react'
import { Link, useSearch } from '@tanstack/react-router'
import { ArrowLeft, Printer } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

export function PdfSmokePage() {
  const search = useSearch({ from: '/pdf-smoke' }) as { print?: string }

  useEffect(() => {
    if (search?.print !== '1') return
    const t = window.setTimeout(() => window.print(), 350)
    return () => window.clearTimeout(t)
  }, [search?.print])

  return (
    <div className="space-y-6">
      {/* Toolbar (não aparece no print) */}
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/relatorios">
            <ArrowLeft size={14} /> Voltar
          </Link>
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() => window.print()}
          >
            <Printer size={14} /> Imprimir / Salvar PDF
          </Button>
        </div>
      </div>

      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">
          GymSite Intelligence — Smoke PDF
        </h1>
        <p className="text-sm text-muted-foreground">
          Use para validar quebra de linha, margens, tipografia e tabelas.
        </p>
        <Separator />
      </header>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Resumo executivo
        </h2>
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm leading-relaxed">
            Bairro com alta densidade de academias no raio (Aggregate), porém com
            oportunidade clara em climatização e limpeza. Recomendação: avançar
            com diligência no candidato #1 e posicionamento mid-premium.
          </p>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Scores regionais
        </h2>
        <div className="overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr className="text-left">
                <th className="px-3 py-2">Dimensão</th>
                <th className="px-3 py-2 w-[120px]">Score</th>
                <th className="px-3 py-2">Classificação</th>
              </tr>
            </thead>
            <tbody className="[&>tr:not(:last-child)]:border-b">
              <tr>
                <td className="px-3 py-2">Demográfico</td>
                <td className="px-3 py-2 font-mono tabular-nums">7.4</td>
                <td className="px-3 py-2">Bom</td>
              </tr>
              <tr>
                <td className="px-3 py-2">Competitivo</td>
                <td className="px-3 py-2 font-mono tabular-nums">2.1</td>
                <td className="px-3 py-2">SATURADO</td>
              </tr>
              <tr>
                <td className="px-3 py-2">Viabilidade financeira</td>
                <td className="px-3 py-2 font-mono tabular-nums">6.3</td>
                <td className="px-3 py-2">MEDIO</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground font-mono">
          Academias no raio 3km (Aggregate): 253 | amostra analisada (reviews): 10
          (Nearby retornou: 20, limitado por maxResultCount)
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Top 3 candidatos
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {[
            { n: 1, nome: 'Galpão Av. Principal', score: 7.9 },
            { n: 2, nome: 'Loja esquina fluxo', score: 7.4 },
            { n: 3, nome: 'Prédio comercial', score: 6.8 },
          ].map((c) => (
            <div key={c.n} className="rounded-lg border bg-card p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs text-muted-foreground">#{c.n}</div>
                  <div className="font-semibold truncate">{c.nome}</div>
                </div>
                <div className="font-mono font-semibold tabular-nums">
                  {c.score.toFixed(1)}
                </div>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Endereço: Av. Exemplo, 123 — Bairro Exemplo
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Força uma margem melhor no PDF */}
      <style>{`
        @media print {
          @page { margin: 14mm; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        }
      `}</style>
    </div>
  )
}

