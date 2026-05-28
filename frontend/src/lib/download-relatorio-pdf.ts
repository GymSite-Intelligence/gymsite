/**
 * Baixa PDF server-side (GET /api/relatorios/{id}/pdf).
 */
import { API_BASE, supabase } from '@/lib/supabase'

export type PdfLayout = 'classic' | 'executive' | 'data_room'

export async function downloadRelatorioPdf(
  relatorioId: string,
  layout: PdfLayout = 'classic',
): Promise<void> {
  const { data: sessionData } = await supabase.auth.getSession()
  const token = sessionData.session?.access_token
  const headers: HeadersInit = {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const url = `${API_BASE}/api/relatorios/${encodeURIComponent(relatorioId)}/pdf?layout=${layout}`
  const res = await fetch(url, { headers })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Falha ao gerar PDF (${res.status})`)
  }

  const blob = await res.blob()
  const dispo = res.headers.get('Content-Disposition') ?? ''
  const match = /filename="?([^";]+)"?/i.exec(dispo)
  const filename = match?.[1] ?? `gymsite-relatorio-${relatorioId.slice(0, 8)}.pdf`

  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(objectUrl)
}
