import { Link, useNavigate } from '@tanstack/react-router'
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar'
import { useAuth } from '@/lib/auth'
import { useMembership } from '@/hooks/useMembership'
import { ThemeMenuItems } from '@/components/theme-menu-items'
import {
  EllipsisVerticalIcon,
  CircleUserRoundIcon,
  LogOutIcon,
} from 'lucide-react'

function iniciais(email: string, nome?: string | null): string {
  if (nome?.trim()) {
    return nome
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase())
      .join('')
  }
  const local = email.split('@')[0] ?? '?'
  return local.slice(0, 2).toUpperCase()
}

export function NavUser() {
  const { isMobile } = useSidebar()
  const { user, signOut } = useAuth()
  const { orgNome } = useMembership()
  const navigate = useNavigate()

  if (!user?.email) return null

  const nome =
    (user.user_metadata?.full_name as string | undefined) ??
    user.email.split('@')[0]
  const avatarUrl = user.user_metadata?.avatar_url as string | undefined
  const initials = iniciais(user.email, nome)

  async function sair() {
    await signOut()
    navigate({ to: '/login', replace: true })
  }

  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="h-8 w-8 rounded-lg">
                {avatarUrl && <AvatarImage src={avatarUrl} alt={nome} />}
                <AvatarFallback className="rounded-lg">{initials}</AvatarFallback>
              </Avatar>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">{nome}</span>
                <span className="truncate text-xs text-muted-foreground">
                  {orgNome ?? user.email}
                </span>
              </div>
              <EllipsisVerticalIcon className="ml-auto size-4" />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-(--radix-dropdown-menu-trigger-width) min-w-56 rounded-lg"
            side={isMobile ? 'bottom' : 'right'}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <Avatar className="h-8 w-8 rounded-lg">
                  {avatarUrl && <AvatarImage src={avatarUrl} alt={nome} />}
                  <AvatarFallback className="rounded-lg">{initials}</AvatarFallback>
                </Avatar>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{nome}</span>
                  <span className="truncate text-xs text-muted-foreground">
                    {user.email}
                  </span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/perfil">
                <CircleUserRoundIcon />
                Perfil
              </Link>
            </DropdownMenuItem>
            <ThemeMenuItems />
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={sair}>
              <LogOutIcon />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  )
}
