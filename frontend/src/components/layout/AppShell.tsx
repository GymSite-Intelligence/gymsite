/**
 * AppShell — layout raiz com topbar fixa.
 *
 * UI Lote 4:
 * - Nav links com indicator bar inferior animado (border-b-2) em vez de pill amarelo
 * - Org "Vectra" virou Avatar + DropdownMenu (preparado pra switch de org)
 * - Separator vertical entre nav e área de org
 * - TooltipProvider envolve toda a árvore (Lote 3)
 *
 * #117 Auth (2026-05-12): o dropdown da org agora também mostra email do user
 * logado e ação de Sair — antes tinha dois avatares (org + user) e ficava
 * redundante. Mantém só o avatar VC.
 */
import { Link, Outlet, useNavigate, useRouterState } from '@tanstack/react-router'
import { ChevronDown, LogOut, Building2, BarChart3, UserCog } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { useMembership } from '@/hooks/useMembership'
import { notify } from '@/lib/notify'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

export function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const { isOwnerOrAdmin } = useMembership()

  return (
    <TooltipProvider delayDuration={300}>
      <div className="min-h-screen bg-background text-foreground">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-14 items-center gap-6">
            <Link
              to="/relatorios"
              className="flex items-center gap-2 font-semibold tracking-tight"
            >
              <span aria-hidden className="text-xl">🏋️</span>
              <span>GymSite Intelligence</span>
            </Link>

            <nav className="flex items-center gap-1 text-sm h-full">
              <NavItem to="/relatorios" active={pathname.startsWith('/relatorios')}>
                Relatórios
              </NavItem>
              <NavItem to="/mapa" active={pathname === '/mapa'}>
                Mapa
              </NavItem>
              <NavItem to="/comparar" active={pathname === '/comparar'}>
                Comparar
              </NavItem>
              {isOwnerOrAdmin && (
                <NavItem to="/custos" active={pathname === '/custos'}>
                  <BarChart3 size={14} className="inline mr-1.5 -mt-0.5" />
                  Custos
                </NavItem>
              )}
            </nav>

            <div className="ml-auto flex items-center gap-3">
              <Separator orientation="vertical" className="h-6" />
              <OrgDropdown />
            </div>
          </div>
        </header>

        <main className="container py-8">
          <Outlet />
        </main>
      </div>
    </TooltipProvider>
  )
}

/**
 * NavItem com indicator bar inferior animado.
 */
function NavItem({
  to,
  active,
  children,
}: {
  to: string
  active: boolean
  children: React.ReactNode
}) {
  return (
    <Link
      to={to}
      className={cn(
        'relative px-3 h-full flex items-center text-sm transition-colors',
        active
          ? 'text-foreground'
          : 'text-muted-foreground hover:text-foreground',
      )}
    >
      {children}
      {active && (
        <span
          aria-hidden
          className="absolute inset-x-3 bottom-0 h-0.5 bg-primary rounded-full"
        />
      )}
    </Link>
  )
}

/**
 * OrgDropdown — menu único do canto direito.
 *
 * Mostra avatar VC + nome da org (Vectra Cargo). Dropdown contém:
 *   - Org card (nome + CNPJ)
 *   - Email do user logado
 *   - Configurações da org (placeholder)
 *   - Trocar organização (placeholder pra multi-tenant)
 *   - Sair
 */
function OrgDropdown() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const email = user?.email ?? ''
  const metadata = (user?.user_metadata ?? {}) as {
    full_name?: string
    avatar_url?: string
  }
  const nomeExibicao = metadata.full_name?.trim() || ''
  const avatarUrl = metadata.avatar_url || null

  async function handleSignOut() {
    await signOut()
    notify.success('Você saiu.')
    navigate({ to: '/login', replace: true })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 hover:bg-muted/50 rounded-md pl-1 pr-2 py-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <Avatar>
          {avatarUrl ? (
            <AvatarImage src={avatarUrl} alt={nomeExibicao || email} />
          ) : (
            <AvatarFallback className="bg-primary/10 text-primary">VC</AvatarFallback>
          )}
        </Avatar>
        <div className="flex flex-col items-start leading-tight">
          <span className="text-xs font-semibold">Vectra Cargo</span>
          <span className="text-[10px] text-muted-foreground font-mono">
            org
          </span>
        </div>
        <ChevronDown size={12} className="text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[240px]">
        <DropdownMenuLabel>Organização</DropdownMenuLabel>
        <DropdownMenuItem disabled>
          <Building2 size={14} />
          <div className="flex flex-col">
            <span className="font-medium">Vectra Cargo</span>
            <span className="text-[10px] text-muted-foreground font-mono">
              CNPJ 59.650.913/0001-04
            </span>
          </div>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="flex flex-col gap-0 font-normal">
          <span className="text-xs text-muted-foreground">Conectado como</span>
          {nomeExibicao && (
            <span className="truncate text-sm text-foreground">
              {nomeExibicao}
            </span>
          )}
          <span
            className={cn(
              'truncate font-mono',
              nomeExibicao
                ? 'text-[10px] text-muted-foreground'
                : 'text-sm text-foreground',
            )}
          >
            {email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate({ to: '/perfil' })}>
          <UserCog size={14} />
          Editar perfil
        </DropdownMenuItem>
        <DropdownMenuItem disabled>
          <Building2 size={14} />
          Trocar organização…
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleSignOut}>
          <LogOut size={14} />
          Sair
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
