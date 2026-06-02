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
  '/comparar': 'Comparar',
  '/prospeccao': 'Prospecção',
  '/custos': 'Custos',
  '/perfil': 'Perfil',
}

function titleFromPath(pathname: string): string {
  if (pathname.startsWith('/relatorios/new')) return 'Novo relatório'
  if (pathname.includes('/aguardando')) return 'Gerando relatório'
  if (pathname.startsWith('/relatorios/')) return 'Relatório'
  return PAGE_TITLES[pathname] ?? 'GymSite Intelligence'
}

export function AuthenticatedSidebarLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const title = titleFromPath(pathname)

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
        <SidebarInset>
          <SiteHeader title={title} />
          <PipelineMonitor />
          <div className="flex flex-1 flex-col gap-4 p-4 pt-0 md:gap-6 md:p-6 md:pt-0">
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
