/**
 * useBairroQuery — top-up por TERMO digitado contra o cache de bairros (Places→DB).
 *
 * A lista pré-carregada (useBairrosDoMunicipio) vem da varredura por prefixo de 1
 * letra, que pega só o top-5 do Places por letra — então bairros fora desse top-5
 * (ex.: "Cocó" atrás de Centro/Cidade dos Funcionários em Fortaleza) não entram.
 * Este hook busca o termo digitado em GET /api/municipios/bairros?...&q=<termo>:
 * o backend consulta o Places, PERSISTE o achado no cache e devolve. Ou seja,
 * resgata o bairro faltante E auto-cura o cache (próxima vez vem na lista completa).
 */
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/supabase'
import type { BairroSugestao } from '@/hooks/useBairrosDoMunicipio'

async function fetchQuery(
  municipio: string,
  uf: string,
  q: string,
): Promise<BairroSugestao[]> {
  const base = API_BASE.replace(/\/$/, '')
  const url = `${base}/api/municipios/bairros?municipio=${encodeURIComponent(
    municipio,
  )}&uf=${encodeURIComponent(uf)}&q=${encodeURIComponent(q)}`
  const res = await fetch(url)
  if (!res.ok) return []
  const data = (await res.json()) as { bairros?: BairroSugestao[] }
  return data.bairros || []
}

export function useBairroQuery({
  input,
  municipio,
  uf,
}: {
  input: string
  municipio: string
  uf: string
}) {
  // Só dispara com 3+ chars (evita queimar Places em 1-2 letras já cobertas pelo sweep).
  const enabled = input.trim().length >= 3 && municipio.length >= 2
  return useQuery({
    queryKey: [
      'bairro-query',
      municipio.toLowerCase(),
      uf.toLowerCase(),
      input.toLowerCase().trim(),
    ],
    queryFn: () => fetchQuery(municipio, uf, input.trim()),
    enabled,
    staleTime: 60 * 60 * 1000, // 1h — termo já cacheado no backend
    retry: 1,
    meta: { silent: true },
  })
}
