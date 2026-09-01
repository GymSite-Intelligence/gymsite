/**
 * Layout autenticado único — sidebar shadcn (dashboard-01) + header + conteúdo.
 *
 * Substitui o AppShell (topbar) + DashboardPage (sidebar isolada).
 * Todas as rotas autenticadas compartilham o mesmo shell e tokens CSS.
 */
import type { CSSProperties } from 'react'
import { Outlet, useRouterState } from '@tanstack/react-router'
import { AppSidebar } from '@/components/app-sidebar'
import { PipelineMonitor } from '@/components/layout/PipelineMonitor'
import { SiteHeader } from '@/components/site-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/relatorios': 'Relatórios',
  '/mapa': 'Mapa',
  '/market-atlas': 'Market Atlas',
  '/execucao': 'Planos de abertura',
  '/comparar': 'Comparar',
  '/prospeccao': 'Prospecção',
  '/prospect': 'Captação de Leads',
  '/custos': 'Custos',
  '/perfil': 'Perfil',
  '/consultor': 'Consultor',
  '/explorar': 'Explorar',
  '/cno-obras': 'Obras CNO',
  '/carto-hex': 'Hex CARTO',
  '/admin/parceiros': 'Parceiros',
  '/admin/llm': 'Provedor de IA',
}

function titleFromPath(pathname: string): string {
  if (pathname.startsWith('/relatorios/new')) return 'Novo relatório'
  if (pathname.includes('/aguardando')) return 'Gerando relatório'
  if (pathname.startsWith('/relatorios/')) return 'Relatório'
  if (pathname.startsWith('/execucao/')) return 'Plano de abertura'
  if (pathname.startsWith('/consultor')) return 'Consultor'
  return PAGE_TITLES[pathname] ?? 'GymSite Intelligence'
}

export function AuthenticatedSidebarLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const title = titleFromPath(pathname)
  const fullBleed = pathname.startsWith('/consultor') || pathname.startsWith('/explorar')

  return (
    <TooltipProvider>
      <SidebarProvider
        style={
          {
            '--sidebar-width': 'calc(var(--spacing) * 72)',
            '--header-height': 'calc(var(--spacing) * 12)',
          } as CSSProperties
        }
      >
        <AppSidebar variant="inset" />
        <SidebarInset className="flex min-h-0 flex-col overflow-hidden">
          <SiteHeader title={title} />
          <PipelineMonitor />
          {fullBleed ? (
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <Outlet />
            </div>
          ) : (
            <div className="flex flex-1 flex-col gap-4 overflow-auto p-4 pt-0 md:gap-6 md:p-6 md:pt-0">
              <Outlet />
            </div>
          )}
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
