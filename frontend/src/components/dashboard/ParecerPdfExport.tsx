/**
 * ParecerPdfExport — gera PDF ou abre impressão do parecer executivo.
 *
 * Funcionalidades:
 * - PDF via html2pdf.js com numeração de páginas
 * - Impressão via popup dedicado
 * - QR code com link para o comparador online
 * - Selo de confidencialidade
 * - Modo resumido (1 página) vs completo
 * - Layout institucional com cores da marca
 */
import { useRef, useState, useEffect } from 'react'
import { useSearch } from '@tanstack/react-router'
import { FileDown, Printer, Building2, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { CenarioJSON } from '@/hooks/useRelatorioDetail'

interface ParecerPdfExportProps {
  bairroA: string
  bairroB: string
  cidadeA: string
  cidadeB: string
  cenarioA?: CenarioJSON
  cenarioB?: CenarioJSON
  aluguelA?: number | null
  aluguelB?: number | null
  vereditoA: string
  vereditoB: string
  scoreA: number | null
  scoreB: number | null
}

const MARCA = 'GymSite Intelligence'
const COR_TEAL = '#0f766e'
const COR_TEXTO = '#111827'
const COR_MUTED = '#4b5563'
const COR_BORDA = '#d1d5db'
const COR_CONFIDENCIAL = '#dc2626'

export function ParecerPdfExport(props: ParecerPdfExportProps) {
  const [gerandoPdf, setGerandoPdf] = useState(false)
  const [modo, setModo] = useState<'resumido' | 'completo'>('completo')
  const [qrDataUrl, setQrDataUrl] = useState<string>('')
  const containerRef = useRef<HTMLDivElement>(null)
  const search = useSearch({ strict: false }) as { a?: string; b?: string }

  const comparadorUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/comparar?a=${search.a ?? ''}&b=${search.b ?? ''}`
    : ''

  useEffect(() => {
    if (!comparadorUrl) return
    let cancelled = false
    import('qrcode').then((QR) => {
      QR.toDataURL(comparadorUrl, { width: 120, margin: 1, color: { dark: COR_TEAL, light: '#ffffff' } })
        .then((url: string) => { if (!cancelled) setQrDataUrl(url) })
        .catch(() => {})
    })
    return () => { cancelled = true }
  }, [comparadorUrl])

  async function handleExportPdf() {
    if (!props.cenarioA || !props.cenarioB) return
    setGerandoPdf(true)
    try {
      const mod = await import('html2pdf.js')
      const html2pdf = (mod as any).default ?? mod
      if (typeof html2pdf !== 'function') {
        throw new Error('html2pdf.js não carregou corretamente.')
      }

      requestAnimationFrame(() => {
        try {
          const element = containerRef.current
          if (!element) { setGerandoPdf(false); return }

          const opt = {
            margin: [16, 12, 18, 12],
            filename: `parecer-viabilidade-${props.bairroA}-vs-${props.bairroB}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
          } as any

          const worker = html2pdf().set(opt).from(element)
          worker.toPdf().get('pdf').then((pdf: any) => {
            const totalPages = pdf.internal.getNumberOfPages()
            for (let i = 1; i <= totalPages; i++) {
              pdf.setPage(i)
              pdf.setFontSize(8)
              pdf.setTextColor(150, 150, 150)
              pdf.text(
                `${MARCA} · Página ${i} de ${totalPages}`,
                pdf.internal.pageSize.getWidth() / 2,
                pdf.internal.pageSize.getHeight() - 6,
                { align: 'center' }
              )
            }
          }).catch(() => {
            // ignora erro na numeração de páginas para não travar o download
          })
          worker.save().catch(() => {}).finally(() => setGerandoPdf(false))
        } catch (innerErr) {
          console.error('Erro ao gerar PDF:', innerErr)
          setGerandoPdf(false)
        }
      })
    } catch (err) {
      console.error('Falha ao carregar html2pdf.js:', err)
      setGerandoPdf(false)
    }
  }

  function handlePrint() {
    if (!props.cenarioA || !props.cenarioB) return
    const html = renderPrintHtml(props, modo, qrDataUrl)
    const popup = window.open('', '_blank', 'width=950,height=750,scrollbars=yes')
    if (!popup) { alert('Permita popups para imprimir o parecer.'); return }
    popup.document.write(html)
    popup.document.close()
    setTimeout(() => { popup.focus(); popup.print() }, 500)
  }

  return (
    <>
      <div className="flex items-center gap-2 flex-wrap">
        <ToggleGroup
          type="single"
          value={modo}
          onValueChange={(v) => v && setModo(v as 'resumido' | 'completo')}
          variant="outline"
          size="sm"
        >
          <ToggleGroupItem value="completo" className="text-xs h-8 px-2.5">
            <Eye size={12} className="mr-1" /> Completo
          </ToggleGroupItem>
          <ToggleGroupItem value="resumido" className="text-xs h-8 px-2.5">
            <EyeOff size={12} className="mr-1" /> Resumido
          </ToggleGroupItem>
        </ToggleGroup>

        <Button
          variant="outline"
          size="sm"
          onClick={handleExportPdf}
          disabled={gerandoPdf || !props.cenarioA || !props.cenarioB}
          className="h-8"
        >
          <FileDown size={14} className="mr-1.5" />
          {gerandoPdf ? 'Gerando…' : 'PDF'}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrint}
          disabled={!props.cenarioA || !props.cenarioB}
          className="h-8"
        >
          <Printer size={14} className="mr-1.5" />
          Imprimir
        </Button>
      </div>

      {/* Container invisível para html2pdf capturar */}
      <div
        ref={containerRef}
        style={{
          position: 'fixed',
          left: '-99999px',
          top: 0,
          width: '210mm',
          background: '#fff',
          color: COR_TEXTO,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          fontSize: '11px',
          lineHeight: 1.5,
        }}
      >
        <PdfLayout {...props} modo={modo} qrDataUrl={qrDataUrl} />
      </div>
    </>
  )
}

// ── Layout compartilhado ──

function PdfLayout({
  bairroA, bairroB, cidadeA, cidadeB, cenarioA, cenarioB,
  aluguelA, aluguelB, vereditoA, vereditoB, scoreA, scoreB,
  modo, qrDataUrl,
}: ParecerPdfExportProps & { modo: 'resumido' | 'completo'; qrDataUrl: string }) {
  if (!cenarioA || !cenarioB) return null

  const hoje = new Date().toLocaleDateString('pt-BR')
  const isResumido = modo === 'resumido'

  const lucroA = cenarioA.lucro_mensal_estimado
  const lucroB = cenarioB.lucro_mensal_estimado
  const payA = cenarioA.payback_meses
  const payB = cenarioB.payback_meses
  const tirA = cenarioA.tir_anual_pct
  const tirB = cenarioB.tir_anual_pct
  const vplA = cenarioA.vpl_5_anos
  const vplB = cenarioB.vpl_5_anos
  const margemA = cenarioA.margem_percentual
  const margemB = cenarioB.margem_percentual
  const receitaA = cenarioA.receita_mensal
  const receitaB = cenarioB.receita_mensal
  const ticketA = cenarioA.ticket_medio
  const ticketB = cenarioB.ticket_medio
  const matrA = cenarioA.matriculas?.realista?.valor ?? cenarioA.alunos_projetados ?? 0
  const matrB = cenarioB.matriculas?.realista?.valor ?? cenarioB.alunos_projetados ?? 0
  const capexA = cenarioA.investimento_total ?? cenarioA.capex_total ?? cenarioA.capex_estimado ?? 0
  const capexB = cenarioB.investimento_total ?? cenarioB.capex_total ?? cenarioB.capex_estimado ?? 0
  const custoFixoA = aluguelA ?? cenarioA.custos_detalhados?.aluguel ?? cenarioA.custos_fixos_total ?? 0
  const custoFixoB = aluguelB ?? cenarioB.custos_detalhados?.aluguel ?? cenarioB.custos_fixos_total ?? 0

  const mesmosModelos = cenarioA.modelo === cenarioB.modelo
  let ptsA = 0, ptsB = 0
  if (lucroA != null && lucroB != null) { if (lucroA > lucroB) ptsA += 3; else if (lucroB > lucroA) ptsB += 3 }
  if (payA != null && payB != null) { if (payA < payB) ptsA += 2; else if (payB < payA) ptsB += 2 }
  if (margemA != null && margemB != null) { if (margemA > margemB) ptsA += 1; else if (margemB > margemA) ptsB += 1 }
  if (tirA != null && tirB != null) { if (tirA > tirB) ptsA += 1.5; else if (tirB > tirA) ptsB += 1.5 }
  const rec = ptsB > ptsA * 1.2 ? 'B' : ptsA > ptsB * 1.2 ? 'A' : 'empate'

  const thHead: React.CSSProperties = { padding: '7px 10px', textAlign: 'left', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.04em', border: `1px solid ${COR_BORDA}`, background: COR_TEAL, color: '#fff', fontWeight: 600 }
  const thHeadRight: React.CSSProperties = { ...thHead, textAlign: 'right' }
  const tdBase: React.CSSProperties = { padding: '6px 10px', border: `1px solid #e5e7eb`, fontSize: '10px' }

  return (
    <div style={{ padding: '22px' }}>
      {/* Cabeçalho institucional */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: `2px solid ${COR_TEAL}`, paddingBottom: '14px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: COR_TEAL, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Building2 size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '17px', fontWeight: 800, margin: 0, color: COR_TEAL, letterSpacing: '-0.02em' }}>{MARCA}</h1>
            <p style={{ fontSize: '9px', color: COR_MUTED, margin: 0, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Parecer Executivo de Viabilidade</p>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          {/* Selo de confidencialidade */}
          <div style={{
            display: 'inline-block',
            padding: '3px 10px',
            borderRadius: '4px',
            border: `1.5px solid ${COR_CONFIDENCIAL}`,
            color: COR_CONFIDENCIAL,
            fontSize: '9px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            marginBottom: '6px',
          }}>
            Confidencial
          </div>
          <p style={{ fontSize: '10px', color: COR_MUTED, margin: 0 }}>Emitido em</p>
          <p style={{ fontSize: '12px', fontWeight: 700, color: COR_TEXTO, margin: '2px 0 0' }}>{hoje}</p>
        </div>
      </div>

      {/* Subtítulo */}
      <p style={{ fontSize: '11px', color: COR_MUTED, margin: '0 0 16px' }}>
        Análise comparativa entre <strong>{bairroA}</strong> ({cidadeA}) e <strong>{bairroB}</strong> ({cidadeB}) · baseada em dados de mercado e benchmark do setor.
      </p>

      {/* Identificação */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '16px' }}>
        <thead><tr>
          <th style={thHead}>Critério</th>
          <th style={thHead}>Opção A — {bairroA}</th>
          <th style={thHead}>Opção B — {bairroB}</th>
        </tr></thead>
        <tbody>
          <tr><td style={tdBase}>Veredito</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{vereditoA}</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{vereditoB}</td></tr>
          <tr><td style={tdBase}>Score Top 1</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{scoreA?.toFixed(1) ?? '—'}</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{scoreB?.toFixed(1) ?? '—'}</td></tr>
          <tr><td style={tdBase}>Modelo recomendado</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{cenarioA.modelo ?? '—'}</td><td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{cenarioB.modelo ?? '—'}</td></tr>
        </tbody>
      </table>

      {/* Recomendação */}
      <div style={{
        padding: '12px 14px', borderRadius: '6px', marginBottom: '16px', border: '1px solid',
        background: rec === 'empate' ? '#eff6ff' : '#ecfdf5',
        borderColor: rec === 'empate' ? '#3b82f6' : '#10b981',
      }}>
        <p style={{ margin: 0, fontSize: '12px', fontWeight: 700, color: COR_TEXTO }}>
          {rec === 'B' ? `Recomendamos ${bairroB}` : rec === 'A' ? `Recomendamos ${bairroA}` : 'Decisão equilibrada — fatores qualitativos devem desempatar'}
        </p>
        <p style={{ margin: '4px 0 0', fontSize: '10px', color: COR_MUTED, lineHeight: 1.5 }}>
          {rec === 'empate'
            ? 'As métricas financeiras apresentam convergência. A decisão final deve considerar visibilidade do ponto, concorrência local e projeção de crescimento do bairro.'
            : mesmosModelos
              ? `Ambos operam no modelo ${cenarioA.modelo}. A vantagem de ${rec === 'B' ? bairroB : bairroA} está na relação custo/benefício e retorno do capital investido.`
              : `Modelos distintos (${cenarioA.modelo} vs ${cenarioB.modelo}). Recomendamos priorizar payback e TIR como métricas normalizadas de comparação.`}
        </p>
      </div>

      {/* Métricas financeiras */}
      <h2 style={{ fontSize: '12px', fontWeight: 700, margin: '0 0 8px', color: COR_TEAL, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Métricas financeiras comparativas
      </h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: isResumido ? '12px' : '18px' }}>
        <thead><tr>
          <th style={thHead}>Indicador</th>
          <th style={thHeadRight}>Opção A</th>
          <th style={thHeadRight}>Opção B</th>
          <th style={thHeadRight}>Diferença</th>
        </tr></thead>
        <tbody>
          <PdfRow label="Receita mensal" a={receitaA} b={receitaB} fmt="brl" />
          <PdfRow label="Ticket médio" a={ticketA} b={ticketB} fmt="brl" />
          {!isResumido && <PdfRow label="Matrículas projetadas" a={matrA} b={matrB} fmt="int" />}
          {!isResumido && <PdfRow label="Custos fixos mensais" a={custoFixoA} b={custoFixoB} fmt="brl" invert />}
          <PdfRow label="Lucro mensal estimado" a={lucroA} b={lucroB} fmt="brl" />
          <PdfRow label="Margem líquida" a={margemA} b={margemB} fmt="pct" />
          {!isResumido && <PdfRow label="Investimento total" a={capexA} b={capexB} fmt="brl" invert />}
          <PdfRow label="Payback" a={payA} b={payB} fmt="meses" invert />
          {!isResumido && <PdfRow label="TIR anual" a={tirA} b={tirB} fmt="pct" />}
          {!isResumido && <PdfRow label="VPL 5 anos" a={vplA} b={vplB} fmt="brl" />}
        </tbody>
      </table>

      {/* Drivers (só no completo) */}
      {!isResumido && (
        <>
          <h2 style={{ fontSize: '12px', fontWeight: 700, margin: '0 0 8px', color: COR_TEAL, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Drivers de diferença e base de análise
          </h2>
          <div style={{ marginBottom: '18px' }}>
            <DriverBlock label="Receita mensal projetada" a={fmt(receitaA, 'brl')} b={fmt(receitaB, 'brl')} meta="Ticket médio estimado × matrículas projetadas, calibrado com benchmark de ocupação do setor fitness para o perfil demográfico do bairro." />
            <DriverBlock label="Ticket médio" a={fmt(ticketA, 'brl')} b={fmt(ticketB, 'brl')} meta="Pesquisa de preços praticados na região, considerando renda média do bairro, posicionamento de mercado e concorrência local." />
            <DriverBlock label="Matrículas projetadas" a={fmt(matrA, 'int')} b={fmt(matrB, 'int')} meta="Projeção de demanda a partir de densidade populacional, renda e comportamento de consumo do público-alvo, validada com benchmark de academias comparáveis." />
            <DriverBlock label="Custos fixos" a={fmt(custoFixoA, 'brl')} b={fmt(custoFixoB, 'brl')} meta="Estimativa a partir de dados de mercado imobiliário local e benchmark de condomínio, IPTU e serviços para o porte da unidade." />
            <DriverBlock label="Lucro mensal" a={fmt(lucroA, 'brl')} b={fmt(lucroB, 'brl')} meta="Receita projetada menos custos totais (fixos + variáveis + marketing) no cenário realista de ocupação." />
            <DriverBlock label="Payback" a={fmt(payA, 'meses')} b={fmt(payB, 'meses')} meta="Tempo estimado para recuperação do capital investido (CAPEX + giro) a partir do fluxo de caixa mensal projetado." />
            <DriverBlock label="TIR anual" a={fmt(tirA, 'pct')} b={fmt(tirB, 'pct')} meta="Taxa interna de retorno do projeto em 5 anos, considerando crescimento conservador de matrículas e inflação de custos." />
            <DriverBlock label="VPL 5 anos" a={fmt(vplA, 'brl')} b={fmt(vplB, 'brl')} meta="Valor presente líquido dos fluxos de caixa futuros, descontado pela taxa mínima de atratividade do setor." />
            <DriverBlock label="Investimento inicial" a={fmt(capexA, 'brl')} b={fmt(capexB, 'brl')} meta="Soma de equipamentos, obra de adaptação, projeto, alvarás, frete e capital de giro — orçamento referenciado em fornecedores do setor." />
          </div>
        </>
      )}

      {/* Resumo executivo de 1 linha no modo resumido */}
      {isResumido && (
        <div style={{ padding: '10px 12px', borderRadius: '6px', background: '#f9fafb', border: `1px solid ${COR_BORDA}`, marginBottom: '16px' }}>
          <p style={{ margin: 0, fontSize: '10px', color: COR_MUTED, lineHeight: 1.5 }}>
            <strong>Versão resumida.</strong> Para acesso à metodologia completa, drivers detalhados e base de análise de cada indicador, consulte a versão completa do parecer ou acesse o comparador online.
          </p>
        </div>
      )}

      {/* QR Code + Assinatura */}
      <div style={{ marginTop: isResumido ? '12px' : '24px', borderTop: `1px solid ${COR_BORDA}`, paddingTop: '18px', display: 'flex', justifyContent: 'space-between', gap: '20px', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Elaborado por</p>
          <div style={{ borderBottom: `1px solid ${COR_TEXTO}`, height: '24px', marginBottom: '4px' }} />
          <p style={{ fontSize: '10px', fontWeight: 600, color: COR_TEXTO, margin: 0 }}>{MARCA}</p>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '2px 0 0' }}>Análise de viabilidade comercial</p>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Aprovação / Assinatura</p>
          <div style={{ borderBottom: `1px solid ${COR_TEXTO}`, height: '24px', marginBottom: '4px' }} />
          <p style={{ fontSize: '10px', fontWeight: 600, color: COR_TEXTO, margin: 0 }}>___________________________</p>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '2px 0 0' }}>Nome e cargo do decisor</p>
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Data</p>
          <div style={{ borderBottom: `1px solid ${COR_TEXTO}`, height: '24px', marginBottom: '4px' }} />
          <p style={{ fontSize: '10px', fontWeight: 600, color: COR_TEXTO, margin: 0 }}>{hoje}</p>
          <p style={{ fontSize: '9px', color: COR_MUTED, margin: '2px 0 0' }}>Data de emissão do parecer</p>
        </div>

        {/* QR Code */}
        {qrDataUrl && (
          <div style={{ textAlign: 'center', minWidth: '100px' }}>
            <img src={qrDataUrl} alt="QR Code" style={{ width: '72px', height: '72px', display: 'block', margin: '0 auto 4px' }} />
            <p style={{ fontSize: '7px', color: COR_MUTED, margin: 0, lineHeight: 1.3 }}>Acesse o comparador<br />online em tempo real</p>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div style={{ borderTop: `1px solid ${COR_BORDA}`, paddingTop: '10px', marginTop: '16px' }}>
        <p style={{ fontSize: '7.5px', color: '#9ca3af', lineHeight: 1.5, margin: 0 }}>
          <strong>Base de análise:</strong> Todos os indicadores financeiros são projetados a partir de dados públicos de demografia, pesquisa de mercado local e benchmark operacional do setor fitness. Os cenários consideram ocupação realista, sazonalidade de matrículas e inflação de custos. Não constituem garantia de performance, mas sim referência para tomada de decisão estratégica. Recomendamos validação presencial do ponto e negociação comercial antes da assinatura do contrato.
        </p>
      </div>
    </div>
  )
}

// ── Helpers ──

function fmt(v: number | null | undefined, type: 'brl' | 'pct' | 'int' | 'meses'): string {
  if (v == null || !Number.isFinite(v)) return '—'
  if (type === 'brl') return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v)
  if (type === 'pct') return `${v.toFixed(1)}%`
  if (type === 'meses') return `${v} meses`
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(v)
}

function PdfRow({ label, a, b, fmt: fmtType, invert }: { label: string; a: number | null | undefined; b: number | null | undefined; fmt: 'brl' | 'pct' | 'int' | 'meses'; invert?: boolean }) {
  const va = fmt(a, fmtType)
  const vb = fmt(b, fmtType)
  let diffStr = '—'
  let color = COR_MUTED
  if (a != null && b != null && Number.isFinite(a) && Number.isFinite(b)) {
    const delta = ((b - a) / Math.abs(a || 1)) * 100
    const isBetter = invert ? delta < 0 : delta > 0
    diffStr = `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%`
    color = isBetter ? '#059669' : delta === 0 ? COR_MUTED : '#dc2626'
  }
  const tdBase: React.CSSProperties = { padding: '6px 10px', border: '1px solid #e5e7eb', fontSize: '10px' }
  return (
    <tr>
      <td style={tdBase}>{label}</td>
      <td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{va}</td>
      <td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace' }}>{vb}</td>
      <td style={{ ...tdBase, textAlign: 'right', fontFamily: 'monospace', color }}>{diffStr}</td>
    </tr>
  )
}

function DriverBlock({ label, a, b, meta }: { label: string; a: string; b: string; meta: string }) {
  return (
    <div style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid #f3f4f6' }}>
      <p style={{ margin: 0, fontSize: '10px', fontWeight: 600, color: COR_TEXTO }}>{label}</p>
      <p style={{ margin: '4px 0 0', fontSize: '10px', color: COR_MUTED }}>A: <strong style={{ color: COR_TEXTO }}>{a}</strong> &nbsp;·&nbsp; B: <strong style={{ color: COR_TEXTO }}>{b}</strong></p>
      <p style={{ margin: '3px 0 0', fontSize: '8px', color: '#9ca3af', fontStyle: 'italic' }}>Base: {meta}</p>
    </div>
  )
}

// ── Renderização para popup de impressão ──

function renderPrintHtml(
  props: ParecerPdfExportProps,
  modo: 'resumido' | 'completo',
  qrDataUrl: string,
): string {
  const hoje = new Date().toLocaleDateString('pt-BR')
  const { bairroA, bairroB, cidadeA, cidadeB, cenarioA, cenarioB, aluguelA, aluguelB, vereditoA, vereditoB, scoreA, scoreB } = props
  if (!cenarioA || !cenarioB) return '<html><body>Dados insuficientes</body></html>'
  const isResumido = modo === 'resumido'

  const f = (v: number | null | undefined, t: 'brl' | 'pct' | 'int' | 'meses') => {
    if (v == null || !Number.isFinite(v)) return '—'
    if (t === 'brl') return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v)
    if (t === 'pct') return `${v.toFixed(1)}%`
    if (t === 'meses') return `${v} meses`
    return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(v)
  }

  const row = (label: string, a: number | null | undefined, b: number | null | undefined, ft: 'brl' | 'pct' | 'int' | 'meses', inv?: boolean) => {
    const va = f(a, ft), vb = f(b, ft)
    let diff = '—', color = '#4b5563'
    if (a != null && b != null && Number.isFinite(a) && Number.isFinite(b)) {
      const d = ((b - a) / Math.abs(a || 1)) * 100
      const better = inv ? d < 0 : d > 0
      diff = `${d > 0 ? '+' : ''}${d.toFixed(1)}%`
      color = better ? '#059669' : d === 0 ? '#4b5563' : '#dc2626'
    }
    return `<tr><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px">${label}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${va}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${vb}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace;color:${color}">${diff}</td></tr>`
  }

  const driverBlock = (label: string, av: string, bv: string, meta: string) =>
    `<div style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #f3f4f6"><p style="margin:0;font-size:10px;font-weight:600;color:#111827">${label}</p><p style="margin:4px 0 0;font-size:10px;color:#4b5563">A: <strong style="color:#111827">${av}</strong> &nbsp;·&nbsp; B: <strong style="color:#111827">${bv}</strong></p><p style="margin:3px 0 0;font-size:8px;color:#9ca3af;font-style:italic">Base: ${meta}</p></div>`

  const lucroA = cenarioA.lucro_mensal_estimado
  const lucroB = cenarioB.lucro_mensal_estimado
  const payA = cenarioA.payback_meses
  const payB = cenarioB.payback_meses
  let ptsA = 0, ptsB = 0
  if (lucroA != null && lucroB != null) { if (lucroA > lucroB) ptsA += 3; else if (lucroB > lucroA) ptsB += 3 }
  if (payA != null && payB != null) { if (payA < payB) ptsA += 2; else if (payB < payA) ptsB += 2 }
  const rec = ptsB > ptsA * 1.2 ? 'B' : ptsA > ptsB * 1.2 ? 'A' : 'empate'
  const mesmosModelos = cenarioA.modelo === cenarioB.modelo

  const recBoxBg = rec === 'empate' ? '#eff6ff' : '#ecfdf5'
  const recBoxBorder = rec === 'empate' ? '#3b82f6' : '#10b981'
  const recTitle = rec === 'B' ? `Recomendamos ${bairroB}` : rec === 'A' ? `Recomendamos ${bairroA}` : 'Decisão equilibrada — fatores qualitativos devem desempatar'
  const recText = rec === 'empate'
    ? 'As métricas financeiras apresentam convergência. A decisão final deve considerar visibilidade do ponto, concorrência local e projeção de crescimento do bairro.'
    : mesmosModelos
      ? `Ambos operam no modelo ${cenarioA.modelo}. A vantagem de ${rec === 'B' ? bairroB : bairroA} está na relação custo/benefício e retorno do capital investido.`
      : `Modelos distintos (${cenarioA.modelo} vs ${cenarioB.modelo}). Recomendamos priorizar payback e TIR como métricas normalizadas de comparação.`

  const receitaA = cenarioA.receita_mensal
  const receitaB = cenarioB.receita_mensal
  const ticketA = cenarioA.ticket_medio
  const ticketB = cenarioB.ticket_medio
  const matrA = cenarioA.matriculas?.realista?.valor ?? cenarioA.alunos_projetados ?? 0
  const matrB = cenarioB.matriculas?.realista?.valor ?? cenarioB.alunos_projetados ?? 0
  const capexA = cenarioA.investimento_total ?? cenarioA.capex_total ?? cenarioA.capex_estimado ?? 0
  const capexB = cenarioB.investimento_total ?? cenarioB.capex_total ?? cenarioB.capex_estimado ?? 0
  const custoFixoA = aluguelA ?? cenarioA.custos_detalhados?.aluguel ?? cenarioA.custos_fixos_total ?? 0
  const custoFixoB = aluguelB ?? cenarioB.custos_detalhados?.aluguel ?? cenarioB.custos_fixos_total ?? 0

  const qrImg = qrDataUrl ? `<img src="${qrDataUrl}" alt="QR" style="width:72px;height:72px;display:block;margin:0 auto 4px" />` : ''

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Parecer de Viabilidade · ${bairroA} vs ${bairroB}</title>
<style>
  @media print {
    body { margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .no-print { display: none !important; }
  }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 11px; line-height: 1.5; color: #111827; background: #fff; margin: 0; padding: 22px; }
  table { width: 100%; border-collapse: collapse; }
  h2 { font-size: 12px; font-weight: 700; margin: 0 0 8px; color: #0f766e; text-transform: uppercase; letter-spacing: 0.04em; }
</style>
</head>
<body>
  <div style="display:flex;align-items:flex-start;justify-content:space-between;border-bottom:2px solid #0f766e;padding-bottom:14px;margin-bottom:16px">
    <div style="display:flex;align-items:center;gap:10px">
      <div style="width:36px;height:36px;border-radius:8px;background:#0f766e;display:flex;align-items:center;justify-content:center">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      </div>
      <div>
        <h1 style="font-size:17px;font-weight:800;margin:0;color:#0f766e;letter-spacing:-0.02em">${MARCA}</h1>
        <p style="font-size:9px;color:#4b5563;margin:0;text-transform:uppercase;letter-spacing:0.08em">Parecer Executivo de Viabilidade</p>
      </div>
    </div>
    <div style="text-align:right">
      <div style="display:inline-block;padding:3px 10px;border-radius:4px;border:1.5px solid #dc2626;color:#dc2626;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">Confidencial</div>
      <p style="font-size:10px;color:#4b5563;margin:0">Emitido em</p>
      <p style="font-size:12px;font-weight:700;color:#111827;margin:2px 0 0">${hoje}</p>
    </div>
  </div>

  <p style="font-size:11px;color:#4b5563;margin:0 0 16px">
    Análise comparativa entre <strong>${bairroA}</strong> (${cidadeA}) e <strong>${bairroB}</strong> (${cidadeB}) · baseada em dados de mercado e benchmark do setor.
  </p>

  <table style="margin-bottom:16px">
    <thead><tr style="background:#0f766e;color:#fff">
      <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Critério</th>
      <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Opção A — ${bairroA}</th>
      <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Opção B — ${bairroB}</th>
    </tr></thead>
    <tbody>
      <tr><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px">Veredito</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${vereditoA}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${vereditoB}</td></tr>
      <tr><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px">Score Top 1</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${scoreA?.toFixed(1) ?? '—'}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${scoreB?.toFixed(1) ?? '—'}</td></tr>
      <tr><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px">Modelo recomendado</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${cenarioA.modelo ?? '—'}</td><td style="padding:6px 10px;border:1px solid #e5e7eb;font-size:10px;text-align:right;font-family:monospace">${cenarioB.modelo ?? '—'}</td></tr>
    </tbody>
  </table>

  <div style="padding:12px 14px;border-radius:6px;margin-bottom:16px;border:1px solid ${recBoxBorder};background:${recBoxBg}">
    <p style="margin:0;font-size:12px;font-weight:700;color:#111827">${recTitle}</p>
    <p style="margin:4px 0 0;font-size:10px;color:#4b5563;line-height:1.5">${recText}</p>
  </div>

  <h2>Métricas financeiras comparativas</h2>
  <table style="margin-bottom:16px">
    <thead><tr style="background:#0f766e;color:#fff">
      <th style="padding:7px 10px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Indicador</th>
      <th style="padding:7px 10px;text-align:right;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Opção A</th>
      <th style="padding:7px 10px;text-align:right;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Opção B</th>
      <th style="padding:7px 10px;text-align:right;font-size:9px;text-transform:uppercase;letter-spacing:0.04em;border:1px solid #d1d5db;font-weight:600">Diferença</th>
    </tr></thead>
    <tbody>
      ${row('Receita mensal', receitaA, receitaB, 'brl')}
      ${row('Ticket médio', ticketA, ticketB, 'brl')}
      ${!isResumido ? row('Matrículas projetadas', matrA, matrB, 'int') : ''}
      ${!isResumido ? row('Custos fixos mensais', custoFixoA, custoFixoB, 'brl', true) : ''}
      ${row('Lucro mensal estimado', lucroA, lucroB, 'brl')}
      ${row('Margem líquida', cenarioA.margem_percentual, cenarioB.margem_percentual, 'pct')}
      ${!isResumido ? row('Investimento total', capexA, capexB, 'brl', true) : ''}
      ${row('Payback', cenarioA.payback_meses, cenarioB.payback_meses, 'meses', true)}
      ${!isResumido ? row('TIR anual', cenarioA.tir_anual_pct, cenarioB.tir_anual_pct, 'pct') : ''}
      ${!isResumido ? row('VPL 5 anos', cenarioA.vpl_5_anos, cenarioB.vpl_5_anos, 'brl') : ''}
    </tbody>
  </table>

  ${isResumido
    ? `<div style="padding:10px 12px;border-radius:6px;background:#f9fafb;border:1px solid #d1d5db;margin-bottom:16px"><p style="margin:0;font-size:10px;color:#4b5563;line-height:1.5"><strong>Versão resumida.</strong> Para acesso à metodologia completa, drivers detalhados e base de análise de cada indicador, consulte a versão completa do parecer ou acesse o comparador online.</p></div>`
    : `<h2>Drivers de diferença e base de análise</h2>
    <div style="margin-bottom:18px">
      ${driverBlock('Receita mensal projetada', f(receitaA,'brl'), f(receitaB,'brl'), 'Ticket médio estimado × matrículas projetadas, calibrado com benchmark de ocupação do setor fitness para o perfil demográfico do bairro.')}
      ${driverBlock('Ticket médio', f(ticketA,'brl'), f(ticketB,'brl'), 'Pesquisa de preços praticados na região, considerando renda média do bairro, posicionamento de mercado e concorrência local.')}
      ${driverBlock('Matrículas projetadas', f(matrA,'int'), f(matrB,'int'), 'Projeção de demanda a partir de densidade populacional, renda e comportamento de consumo do público-alvo, validada com benchmark de academias comparáveis.')}
      ${driverBlock('Custos fixos', f(custoFixoA,'brl'), f(custoFixoB,'brl'), 'Estimativa a partir de dados de mercado imobiliário local e benchmark de condomínio, IPTU e serviços para o porte da unidade.')}
      ${driverBlock('Lucro mensal', f(lucroA,'brl'), f(lucroB,'brl'), 'Receita projetada menos custos totais (fixos + variáveis + marketing) no cenário realista de ocupação.')}
      ${driverBlock('Payback', f(payA,'meses'), f(payB,'meses'), 'Tempo estimado para recuperação do capital investido (CAPEX + giro) a partir do fluxo de caixa mensal projetado.')}
      ${driverBlock('TIR anual', f(cenarioA.tir_anual_pct,'pct'), f(cenarioB.tir_anual_pct,'pct'), 'Taxa interna de retorno do projeto em 5 anos, considerando crescimento conservador de matrículas e inflação de custos.')}
      ${driverBlock('VPL 5 anos', f(cenarioA.vpl_5_anos,'brl'), f(cenarioB.vpl_5_anos,'brl'), 'Valor presente líquido dos fluxos de caixa futuros, descontado pela taxa mínima de atratividade do setor.')}
      ${driverBlock('Investimento inicial', f(capexA,'brl'), f(capexB,'brl'), 'Soma de equipamentos, obra de adaptação, projeto, alvarás, frete e capital de giro — orçamento referenciado em fornecedores do setor.')}
    </div>`}

  <div style="margin-top:${isResumido ? '12px' : '24px'};border-top:1px solid #d1d5db;padding-top:18px;display:flex;justify-content:space-between;gap:20px;align-items:flex-start">
    <div style="flex:1">
      <p style="font-size:9px;color:#4b5563;margin:0 0 6px;text-transform:uppercase;letter-spacing:0.06em">Elaborado por</p>
      <div style="border-bottom:1px solid #111827;height:24px;margin-bottom:4px"></div>
      <p style="font-size:10px;font-weight:600;color:#111827;margin:0">${MARCA}</p>
      <p style="font-size:9px;color:#4b5563;margin:2px 0 0">Análise de viabilidade comercial</p>
    </div>
    <div style="flex:1">
      <p style="font-size:9px;color:#4b5563;margin:0 0 6px;text-transform:uppercase;letter-spacing:0.06em">Aprovação / Assinatura</p>
      <div style="border-bottom:1px solid #111827;height:24px;margin-bottom:4px"></div>
      <p style="font-size:10px;font-weight:600;color:#111827;margin:0">___________________________</p>
      <p style="font-size:9px;color:#4b5563;margin:2px 0 0">Nome e cargo do decisor</p>
    </div>
    <div style="flex:1">
      <p style="font-size:9px;color:#4b5563;margin:0 0 6px;text-transform:uppercase;letter-spacing:0.06em">Data</p>
      <div style="border-bottom:1px solid #111827;height:24px;margin-bottom:4px"></div>
      <p style="font-size:10px;font-weight:600;color:#111827;margin:0">${hoje}</p>
      <p style="font-size:9px;color:#4b5563;margin:2px 0 0">Data de emissão do parecer</p>
    </div>
    <div style="text-align:center;min-width:100px">
      ${qrImg}
      <p style="font-size:7px;color:#4b5563;margin:0;line-height:1.3">Acesse o comparador<br/>online em tempo real</p>
    </div>
  </div>

  <div style="border-top:1px solid #d1d5db;padding-top:10px;margin-top:16px">
    <p style="font-size:7.5px;color:#9ca3af;line-height:1.5;margin:0">
      <strong>Base de análise:</strong> Todos os indicadores financeiros são projetados a partir de dados públicos de demografia, pesquisa de mercado local e benchmark operacional do setor fitness. Os cenários consideram ocupação realista, sazonalidade de matrículas e inflação de custos. Não constituem garantia de performance, mas sim referência para tomada de decisão estratégica. Recomendamos validação presencial do ponto e negociação comercial antes da assinatura do contrato.
    </p>
  </div>

  <div class="no-print" style="position:fixed;bottom:20px;right:20px;display:flex;gap:8px">
    <button onclick="window.print()" style="padding:8px 16px;background:#0f766e;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer;font-family:inherit">🖨️ Imprimir / Salvar como PDF</button>
    <button onclick="window.close()" style="padding:8px 16px;background:#f3f4f6;color:#111827;border:1px solid #d1d5db;border-radius:6px;font-size:12px;cursor:pointer;font-family:inherit">Fechar</button>
  </div>
</body>
</html>`
}
