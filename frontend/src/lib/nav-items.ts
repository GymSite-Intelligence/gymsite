import type { LucideIcon } from 'lucide-react'
import {
  BarChart3Icon,
  FileTextIcon,
  GitCompareIcon,
  Globe2Icon,
  LayoutDashboardIcon,
  MapIcon,
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
    title: 'Mapa',
    to: '/mapa',
    icon: MapIcon,
  },
  {
    title: 'Market Atlas',
    to: '/market-atlas',
    icon: Globe2Icon,
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
