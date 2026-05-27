import type { LucideIcon } from 'lucide-react'
import {
  BarChart3Icon,
  FileTextIcon,
  GitCompareIcon,
  LayoutDashboardIcon,
  MapIcon,
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
    title: 'Mapa',
    to: '/mapa',
    icon: MapIcon,
  },
  {
    title: 'Comparar',
    to: '/comparar',
    icon: GitCompareIcon,
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
