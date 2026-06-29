import type { LucideIcon } from 'lucide-react'
import {
  BarChart3Icon,
  BotIcon,
  ClipboardListIcon,
  FileTextIcon,
  GitCompareIcon,
  Globe2Icon,
  InboxIcon,
  LayoutDashboardIcon,
  MapIcon,
  MessageSquareIcon,
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
    title: 'Planos de abertura',
    to: '/execucao',
    icon: ClipboardListIcon,
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
    title: 'Assistente',
    to: '/assistente',
    icon: MessageSquareIcon,
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
