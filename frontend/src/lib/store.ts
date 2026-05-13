/**
 * lib/store.ts — Zustand store global. Estado verdadeiramente global apenas:
 * - activeOrgId: org selecionada no topbar (multi-tenant)
 * - session: dados do Supabase Auth quando autenticado
 *
 * Server state (relatórios, candidatos, etc) NÃO vive aqui — usar TanStack Query.
 */
import { create } from 'zustand'

interface AppState {
  activeOrgId: string
  setActiveOrgId: (id: string) => void
  session: { userId: string; email: string } | null
  setSession: (s: AppState['session']) => void
}

// UUID da org Vectra (default no seed.sql). Quando o usuário trocar
// de org pelo OrgSelector, esse valor muda e dispara refetch dos queries.
const DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000001'

export const useAppStore = create<AppState>((set) => ({
  activeOrgId: DEFAULT_ORG_ID,
  setActiveOrgId: (id) => set({ activeOrgId: id }),
  session: null,
  setSession: (s) => set({ session: s }),
}))
