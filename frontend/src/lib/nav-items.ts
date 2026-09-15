import type { LucideIcon } from 'lucide-react'
import {
  BarChart3Icon,
  BotIcon,
  ClipboardListIcon,
  Building2Icon,
  CompassIcon,
  FileTextIcon,
  GitCompareIcon,
  InboxIcon,
  LayoutDashboardIcon,
  TargetIcon,
} from 'lucide-react'

export type SidebarNavItem = {
  title: string
  to: string
  icon?: LucideIcon
}

export const appNavItems: SidebarNavItem[] = [
  {
    title: 'Dashboard',
    to: '/dashboard',
    icon: LayoutDashboardIcon,
  },
  {
    title: 'Relatórios',
    to: '/relatorios',
    icon: FileTextIcon,
  },
  {
    title: 'CRM',
    to: '/crm',
    icon: ClipboardListIcon,
  },
  {
    title: 'Explorar',
    to: '/explorar',
    icon: CompassIcon,
  },
  {
    title: 'Comparar',
    to: '/comparar',
    icon: GitCompareIcon,
  },
  {
    title: 'Prospecção',
    to: '/prospeccao',
    icon: TargetIcon,
  },
  {
    title: 'Captação de Leads',
    to: '/prospect',
    icon: InboxIcon,
  },
  {
    title: 'Consultor',
    to: '/consultor',
    icon: BotIcon,
  },
  {
    title: 'Obras CNO',
    to: '/cno-obras',
    icon: Building2Icon,
  },
]

export const custosNavItem: SidebarNavItem = {
  title: 'Custos',
  to: '/custos',
  icon: BarChart3Icon,
}

export function getSidebarNavItems(isOwnerOrAdmin: boolean): SidebarNavItem[] {
  if (!isOwnerOrAdmin) return appNavItems
  return [...appNavItems, custosNavItem]
}
