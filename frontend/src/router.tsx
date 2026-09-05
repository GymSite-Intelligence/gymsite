/**
 * router.tsx — TanStack Router code-based.
 *
 * Auth: APP_PATHS → RequireAuth + sidebar. Resto (landing, blog, degustação,
 * explorar anônimo) → `<Outlet />` sem login. `/explorar` logado usa sidebar.
 */
import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
  useRouterState,
} from '@tanstack/react-router'
import { Loader2 } from 'lucide-react'
import { AuthenticatedSidebarLayout } from '@/components/layout/AuthenticatedSidebarLayout'
import { RequireAuth } from '@/components/layout/RequireAuth'
import { useAuth } from '@/lib/auth'
import { RelatoriosListPage } from '@/routes/RelatoriosListPage'
import { RelatorioViewerPage } from '@/routes/RelatorioViewerPage'
import { NovoRelatorioPage } from '@/routes/NovoRelatorioPage'
import { RelatorioAguardandoPage } from '@/routes/RelatorioAguardandoPage'
import { ComparadorPage } from '@/routes/ComparadorPage'
import { MapaRelatoriosPage } from '@/routes/MapaRelatoriosPage'
import { CustosPage } from '@/routes/CustosPage'
import { CnoObrasPage } from '@/routes/CnoObrasPage'
import { PerfilPage } from '@/routes/PerfilPage'
import { LoginPage } from '@/routes/LoginPage'
import { AuthCallbackPage } from '@/routes/AuthCallbackPage'
import { PrivacidadePage } from '@/routes/PrivacidadePage'
import { DashboardPage } from '@/routes/DashboardPage'
import { MarketAtlasPage } from '@/routes/MarketAtlasPage'
import { PdfSmokePage } from '@/routes/PdfSmokePage'
import { ProspeccaoPage } from '@/routes/ProspeccaoPage'
import { ProspectPage } from '@/routes/ProspectPage'
import { LeadAccessPage } from '@/routes/LeadAccessPage'
import { ConsultorPage } from '@/routes/ConsultorPage'
import { ExplorarPage } from '@/routes/ExplorarPage'
import AdminParceirosPage from '@/routes/AdminParceirosPage'
import AdminLlmPage from '@/routes/AdminLlmPage'
import { ProjetoExecucaoPage } from '@/routes/ProjetoExecucaoPage'
import { PlanosListPage } from '@/routes/PlanosListPage'
import { LandingPage } from '@/routes/LandingPage'
import { DegustacaoPage } from '@/routes/DegustacaoPage'
import { TestePage } from '@/routes/TestePage'
import { AgentesPage } from '@/routes/AgentesPage'
import { BlogIndexPage } from '@/routes/BlogIndexPage'
import { BlogSlugPage } from '@/routes/BlogSlugPage'
import type { Veredito } from '@/types/domain'
import {
  legacyAbrirToDegustacaoSearchFromRecord,
  parseDegustacaoSearch,
} from '@/lib/degustacaoUrls'

/** Produto logado — sidebar + RequireAuth. Prefixo casa com subrotas. */
const APP_PREFIXES = [
  '/dashboard',
  '/relatorios',
  '/comparar',
  '/mapa',
  '/custos',
  '/cno-obras',
  '/prospeccao',
  '/prospect',
  '/perfil',
  '/market-atlas',
  '/consultor',
  '/admin',
  '/crm',
  '/execucao',
  '/assistente',
] as const

function isAppPath(pathname: string): boolean {
  return APP_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

function AuthSpinner() {
  return (
    <div className="flex min-h-dvh items-center justify-center gap-2 text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      Carregando…
    </div>
  )
}

function RootLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const { session, loading } = useAuth()

  if (isAppPath(pathname)) {
    return (
      <RequireAuth>
        <AuthenticatedSidebarLayout />
      </RequireAuth>
    )
  }

  if (pathname === '/explorar' || pathname.startsWith('/explorar/')) {
    if (loading) return <AuthSpinner />
    if (session) {
      return (
        <RequireAuth>
          <AuthenticatedSidebarLayout />
        </RequireAuth>
      )
    }
    return <Outlet />
  }

  return <Outlet />
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
  validateSearch: (search: Record<string, unknown>): { code?: string; id?: string } => ({
    code: typeof search.code === 'string' ? search.code : undefined,
    id: typeof search.id === 'string' ? search.id : undefined,
  }),
  component: LeadAccessPage,
})

// ── `/` landing (sempre pública) ───────────────────────────────────────────
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  validateSearch: (search: Record<string, unknown>) => ({
    abrir: typeof search.abrir === 'string' ? search.abrir : undefined,
    agente: typeof search.agente === 'string' ? search.agente : undefined,
    dev_token: typeof search.dev_token === 'string' ? search.dev_token : undefined,
  }),
  beforeLoad: ({ search }) => {
    const next = legacyAbrirToDegustacaoSearchFromRecord(search)
    if (next) {
      throw redirect({
        to: '/degustacao',
        search: {
          agente: next.agente,
          abrir: next.abrir,
          dev_token: next.dev_token,
          pid: next.pid,
        },
      })
    }
  },
  component: LandingPage,
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

const cnoObrasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/cno-obras',
  component: CnoObrasPage,
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

// "/prospect" — hub consolidado de entrantes captados (fonte de leads V1).
const prospectRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/prospect',
  component: ProspectPage,
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
  beforeLoad: () => {
    throw redirect({ to: '/consultor', replace: true })
  },
})

const consultorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/consultor',
  validateSearch: (search: Record<string, unknown>): { projeto_id?: string } => ({
    projeto_id: typeof search.projeto_id === 'string' ? search.projeto_id : undefined,
  }),
  component: ConsultorPage,
})

interface ExplorarSearch {
  novo?: boolean
}

const explorarRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/explorar',
  validateSearch: (search: Record<string, unknown>): ExplorarSearch => ({
    novo:
      search.novo === true || search.novo === '1' || search.novo === 'true'
        ? true
        : undefined,
  }),
  component: ExplorarPage,
})

const degustacaoExplorarRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/degustacao/explorar',
  beforeLoad: () => {
    throw redirect({ to: '/explorar', replace: true })
  },
  component: () => null,
})

const degustacaoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/degustacao',
  validateSearch: parseDegustacaoSearch,
  component: DegustacaoPage,
})

const testeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/teste',
  validateSearch: parseDegustacaoSearch,
  component: TestePage,
})

const agentesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/agentes',
  component: AgentesPage,
})

const blogIndexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/blog',
  component: BlogIndexPage,
})

const blogSlugRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/blog/$slug',
  component: BlogSlugPage,
})

const adminParceirosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/admin/parceiros',
  component: AdminParceirosPage,
})

const adminLlmRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/admin/llm',
  component: AdminLlmPage,
})

const planosListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/crm',
  component: PlanosListPage,
})

const crmDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/crm/$playbookId',
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

const execucaoLegacyListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/execucao',
  beforeLoad: ({ location }) => {
    throw redirect({
      to: '/crm',
      search: location.search as Record<string, unknown>,
      replace: true,
    })
  },
})

const execucaoLegacyDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/execucao/$playbookId',
  beforeLoad: ({ location, params }) => {
    throw redirect({
      to: '/crm/$playbookId',
      params: { playbookId: params.playbookId },
      search: location.search as Record<string, unknown>,
      replace: true,
    })
  },
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
  prospectRoute,
  custosRoute,
  cnoObrasRoute,
  perfilRoute,
  dashboardRoute,
  marketAtlasRoute,
  pdfSmokeRoute,
  leadAccessRoute,
  assistenteRoute,
  consultorRoute,
  explorarRoute,
  degustacaoExplorarRoute,
  degustacaoRoute,
  testeRoute,
  agentesRoute,
  blogIndexRoute,
  blogSlugRoute,
  adminParceirosRoute,
  adminLlmRoute,
  planosListRoute,
  crmDetailRoute,
  execucaoLegacyListRoute,
  execucaoLegacyDetailRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
