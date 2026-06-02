import { USE_MOCKS } from '@/mocks'

/** Rótulo exibido nos blocos do dashboard (ranking, tabela). */
export function getDashboardDataSourceLabel(): string {
  return USE_MOCKS
    ? 'Fixtures locais · VITE_USE_MOCKS=true'
    : 'v_relatorios_resumo · Supabase'
}

export function isDashboardUsingMocks(): boolean {
  return USE_MOCKS
}
