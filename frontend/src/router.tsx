/**
 * router.tsx — TanStack Router code-based.
 *
 * Por que code-based (não file-based):
 * - File-based exige o plugin Vite `@tanstack/router-plugin` + arquivo gerado
 *   `routeTree.gen.ts` que precisa rebuild ao adicionar rota.
 *
 * Auth: o root component decide se renderiza AppShell+RequireAuth ou só
 * `<Outlet />` (rotas públicas: /login, /auth/callback, /privacidade).
 * Mantém os paths das rotas autenticadas como `/relatorios`, `/mapa`, etc.
 * — sem afetar `useSearch({ from: ... })` nas páginas.
 */
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
  useRouterState,
} from '@tanstack/react-router'
import { AuthenticatedSidebarLayout } from '@/components/layout/AuthenticatedSidebarLayout'
import { RequireAuth } from '@/components/layout/RequireAuth'
import { RelatoriosListPage } from '@/routes/RelatoriosListPage'
import { RelatorioViewerPage } from '@/routes/RelatorioViewerPage'
import { NovoRelatorioPage } from '@/routes/NovoRelatorioPage'
import { RelatorioAguardandoPage } from '@/routes/RelatorioAguardandoPage'
import { ComparadorPage } from '@/routes/ComparadorPage'
import { MapaRelatoriosPage } from '@/routes/MapaRelatoriosPage'
import { CustosPage } from '@/routes/CustosPage'
import { PerfilPage } from '@/routes/PerfilPage'
import { LoginPage } from '@/routes/LoginPage'
import { AuthCallbackPage } from '@/routes/AuthCallbackPage'
import { PrivacidadePage } from '@/routes/PrivacidadePage'
import { DashboardPage } from '@/routes/DashboardPage'
import { MarketAtlasPage } from '@/routes/MarketAtlasPage'
import { PdfSmokePage } from '@/routes/PdfSmokePage'
import { ProspeccaoPage } from '@/routes/ProspeccaoPage'
import { LeadAccessPage } from '@/routes/LeadAccessPage'
import { AssistentePage } from '@/routes/AssistentePage'
import AdminParceirosPage from '@/routes/AdminParceirosPage'
import { ProjetoExecucaoPage } from '@/routes/ProjetoExecucaoPage'
import { PlanosListPage } from '@/routes/PlanosListPage'
import type { Veredito } from '@/types/domain'

// Rotas que NÃO exigem auth (útil para smoke pages e fluxos de acesso externo).
const PUBLIC_PATHS = new Set(['/login', '/auth/callback', '/privacidade', '/pdf-smoke', '/acesso'])

function RootLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  if (PUBLIC_PATHS.has(pathname)) {
    return <Outlet />
  }
  return (
    <RequireAuth>
      <AuthenticatedSidebarLayout />
    </RequireAuth>
  )
}

const rootRoute = createRootRoute({
  component: RootLayout,
})

// ── Rotas públicas ─────────────────────────────────────────────────────────
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
})

const authCallbackRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/auth/callback',
  component: AuthCallbackPage,
})

const privacidadeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/privacidade',
  component: PrivacidadePage,
})

const leadAccessRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/acesso',
  validateSearch: (search: Record<string, unknown>): { code?: string } => ({
    code: typeof search.code === 'string' ? search.code : undefined,
  }),
  component: LeadAccessPage,
})

// ── Rotas autenticadas ─────────────────────────────────────────────────────
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: () => {
    throw redirect({ to: '/dashboard', replace: true })
  },
})

interface RelatoriosSearch {
  cidade?: string
  veredito?: Veredito
  since?: string
}

const relatoriosListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/relatorios',
  validateSearch: (search: Record<string, unknown>): RelatoriosSearch => {
    return {
      cidade: typeof search.cidade === 'string' ? search.cidade : undefined,
      veredito:
        typeof search.veredito === 'string'
          ? (search.veredito as Veredito)
          : undefined,
      since: typeof search.since === 'string' ? search.since : undefined,
    }
  },
  component: RelatoriosListPage,
})

// Search params do /relatorios/new — usados pra pré-preencher o form quando
// o user clica "Tentar de novo" num relatório falho. Tudo opcional: o caller
// passa só o que sabe, o resto fica nos defaults.
interface NovoRelatorioSearch {
  cidade?: string
  uf?: string
  bairro?: string
  area_m2_min?: number
  area_m2_max?: number
  tamanho_preset?: string
  publico_alvo?: string
  genero_alvo?: string
  tipo_negocio?: string
  estacionamento_obrigatorio?: boolean
  /** Quando veio do "Editar" da listagem. */
  edit_relatorio_id?: string
}
const novoRelatorioRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/relatorios/new',
  validateSearch: (search: Record<string, unknown>): NovoRelatorioSearch => {
    const estacionamentoObrigatorioRaw = search.estacionamento_obrigatorio
    return {
      cidade: typeof search.cidade === 'string' ? search.cidade : undefined,
      uf: typeof search.uf === 'string' ? search.uf : undefined,
      bairro: typeof search.bairro === 'string' ? search.bairro : undefined,
      area_m2_min:
        typeof search.area_m2_min === 'number'
          ? search.area_m2_min
          : typeof search.area_m2_min === 'string'
            ? Number(search.area_m2_min) || undefined
            : undefined,
      area_m2_max:
        typeof search.area_m2_max === 'number'
          ? search.area_m2_max
          : typeof search.area_m2_max === 'string'
            ? Number(search.area_m2_max) || undefined
            : undefined,
      tamanho_preset:
        typeof search.tamanho_preset === 'string'
          ? search.tamanho_preset
          : undefined,
      publico_alvo:
        typeof search.publico_alvo === 'string' ? search.publico_alvo : undefined,
      genero_alvo:
        typeof search.genero_alvo === 'string' ? search.genero_alvo : undefined,
      tipo_negocio:
        typeof search.tipo_negocio === 'string' ? search.tipo_negocio : undefined,
      estacionamento_obrigatorio:
        typeof estacionamentoObrigatorioRaw === 'boolean'
          ? estacionamentoObrigatorioRaw
          : typeof estacionamentoObrigatorioRaw === 'string'
            ? estacionamentoObrigatorioRaw === 'true'
            : undefined,
      edit_relatorio_id:
        typeof search.edit_relatorio_id === 'string'
          ? search.edit_relatorio_id
          : undefined,
    }
  },
  component: NovoRelatorioPage,
})

const relatorioDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/relatorios/$relatorioId',
  validateSearch: (search: Record<string, unknown>): { print?: string } => ({
    print: typeof search.print === 'string' ? search.print : undefined,
  }),
  component: RelatorioViewerPage,
})

const relatorioAguardandoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/relatorios/$relatorioId/aguardando',
  component: RelatorioAguardandoPage,
})

interface ComparadorSearch {
  a?: string
  b?: string
}
const comparadorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/comparar',
  validateSearch: (search: Record<string, unknown>): ComparadorSearch => ({
    a: typeof search.a === 'string' ? search.a : undefined,
    b: typeof search.b === 'string' ? search.b : undefined,
  }),
  component: ComparadorPage,
})

interface MapaSearch {
  cidade?: string
  veredito?: Veredito
}
const mapaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/mapa',
  validateSearch: (search: Record<string, unknown>): MapaSearch => ({
    cidade: typeof search.cidade === 'string' ? search.cidade : undefined,
    veredito:
      typeof search.veredito === 'string'
        ? (search.veredito as Veredito)
        : undefined,
  }),
  component: MapaRelatoriosPage,
})

// "/custos" — dashboard admin de consumo Gemini por relatório.
// Gate de role aplicado dentro do componente (useMembership).
const custosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/custos',
  component: CustosPage,
})

interface ProspeccaoSearch {
  cidade?: string
  status?: string
  prioridade?: string
}
const prospeccaoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/prospeccao',
  validateSearch: (search: Record<string, unknown>): ProspeccaoSearch => ({
    cidade: typeof search.cidade === 'string' ? search.cidade : undefined,
    status: typeof search.status === 'string' ? search.status : undefined,
    prioridade: typeof search.prioridade === 'string' ? search.prioridade : undefined,
  }),
  component: ProspeccaoPage,
})

// "/perfil" — edição de nome + foto do user logado.
const perfilRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/perfil',
  component: PerfilPage,
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: DashboardPage,
})

const marketAtlasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/market-atlas',
  component: MarketAtlasPage,
})

const pdfSmokeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pdf-smoke',
  validateSearch: (search: Record<string, unknown>): { print?: string } => ({
    print: typeof search.print === 'string' ? search.print : undefined,
  }),
  component: PdfSmokePage,
})

const assistenteRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/assistente',
  component: AssistentePage,
})

const adminParceirosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/admin/parceiros',
  component: AdminParceirosPage,
})

const planosListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/execucao',
  component: PlanosListPage,
})

const execucaoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/execucao/$playbookId',
  component: ProjetoExecucaoPage,
  validateSearch: (
    s: Record<string, unknown>,
  ): { categoria?: string; etapa?: string; view?: string; situacao?: string } => ({
    categoria: typeof s.categoria === 'string' ? s.categoria : undefined,
    etapa: typeof s.etapa === 'string' ? s.etapa : undefined,
    view: typeof s.view === 'string' ? s.view : undefined,
    situacao: typeof s.situacao === 'string' ? s.situacao : undefined,
  }),
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  authCallbackRoute,
  privacidadeRoute,
  indexRoute,
  relatoriosListRoute,
  novoRelatorioRoute,
  relatorioAguardandoRoute,
  relatorioDetailRoute,
  comparadorRoute,
  mapaRoute,
  prospeccaoRoute,
  custosRoute,
  perfilRoute,
  dashboardRoute,
  marketAtlasRoute,
  pdfSmokeRoute,
  leadAccessRoute,
  assistenteRoute,
  adminParceirosRoute,
  planosListRoute,
  execucaoRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
